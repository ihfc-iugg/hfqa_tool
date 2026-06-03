import yaml
import pandas as pd

from etl.extract_excel import excel_to_parquet
from etl.normalization import normalize_only_data_rows
from etl.typecasting import apply_schema_types
from vocab_check.apply_functional_check import add_mandatory_flags


INPUT_XLSX = "testing/run/testing_files/obligation_test.xlsx"
SCHEMA_PATH = "hf_schema.yaml"


def main():
    # --- Load schema ---
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    # --- Excel -> Parquet + row_type ---
    df_raw = excel_to_parquet(
        excel_path=INPUT_XLSX,
        parquet_path="testing/run/testing_files/obligation_test.raw.parquet",
        sheet_name=0,
        meta_rows=0,  # no meta rows here
    )

    # --- Normalize only data rows ---
    df_meta, df_data_norm = normalize_only_data_rows(df_raw, schema)
    df_typed = apply_schema_types(df_data_norm, schema)

    # --- Add mandatory flags ---
    df_checked = add_mandatory_flags(df_typed, schema)

    # Columns that actually have a __missing flag
    missing_flag_cols = [c for c in df_checked.columns if c.endswith("__missing")]
    missing_flag_base = {c[:-9] for c in missing_flag_cols}  # column name without suffix

    print("Columns with __missing flag:")
    print("  " + ", ".join(sorted(missing_flag_base)) if missing_flag_base else "  (none)")

    # Map: column -> obligation
    obligations = {
        col_name: str(col_spec.get("obligation", "")).strip().upper()
        for col_name, col_spec in schema.get("columns", {}).items()
    }

    # Collect test results
    tests = []

    # --- Test group 1: structural consistency of flags ---

    # 1a) All M columns must have a __missing flag
    for col, obl in obligations.items():
        if obl == "M":
            has_flag = col in missing_flag_base
            name = f"[structure] mandatory column '{col}' has __missing flag"
            if has_flag:
                tests.append((name, True, ""))
            else:
                msg = f"Expected {col}__missing to exist for obligation 'M', but it is missing."
                tests.append((name, False, msg))

    # 1b) R/O/- columns must NOT have a __missing flag
    for col, obl in obligations.items():
        if obl != "M":
            has_flag = col in missing_flag_base
            name = f"[structure] non-mandatory column '{col}' has no __missing flag"
            if not has_flag:
                tests.append((name, True, ""))
            else:
                msg = f"Column '{col}' has obligation '{obl}' but {col}__missing flag exists."
                tests.append((name, False, msg))

    # --- Test group 2: value behaviour for M-columns (all_missing / all_present) ---

    # Ensure __case exists
    if "__case" not in df_checked.columns:
        print("\nWARNING: '__case' column not found – cannot test all_missing/all_present behaviour.")
    else:
        df_missing = df_checked[df_checked["__case"] == "all_missing"]
        df_present = df_checked[df_checked["__case"] == "all_present"]

        if df_missing.empty or df_present.empty:
            print("\nWARNING: '__case' values 'all_missing' or 'all_present' not found – "
                  "cannot test value behaviour.")
        else:
            row_missing = df_missing.iloc[0]
            row_present = df_present.iloc[0]

            for col, obl in obligations.items():
                if obl != "M":
                    continue

                flag_col = f"{col}__missing"
                if flag_col not in df_checked.columns:
                    # This should already be caught by structural test above
                    continue

                name_missing = f"[values] '{col}' (M) is flagged missing when all values are empty"
                name_present = f"[values] '{col}' (M) is NOT flagged missing when value is present"

                val_missing = bool(row_missing[flag_col])
                val_present = bool(row_present[flag_col])

                if val_missing:
                    tests.append((name_missing, True, ""))
                else:
                    msg = f"For column '{col}' in case 'all_missing', {flag_col} is False but should be True."
                    tests.append((name_missing, False, msg))

                if not val_present:
                    tests.append((name_present, True, ""))
                else:
                    msg = f"For column '{col}' in case 'all_present', {flag_col} is True but should be False."
                    tests.append((name_present, False, msg))

    # --- Summary output with simple bar and counters ---

    total = len(tests)
    passed = sum(1 for _, ok, _ in tests if ok)
    failed = total - passed

    print("\nObligation test summary")
    if total == 0:
        print("No tests were executed.")
        return

    # simple ASCII bar
    bar_len = 40
    filled = int(bar_len * passed / total)
    bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"

    print(f"{bar}  {passed}/{total} test cases passed, {failed} failed.")

    # Detailed per-test logging
    print("\nDetailed test cases:")
    for idx, (name, ok, msg) in enumerate(tests, start=1):
        status = "PASS" if ok else "FAIL"
        print(f"{idx:3d}) {status} - {name}")
        if not ok and msg:
            print(f"     {msg}")

    # Exit code hint (optional)
    if failed == 0:
        print("\nAll obligation tests passed.")
    else:
        print("\nSome obligation tests failed.")


if __name__ == "__main__":
    main()
