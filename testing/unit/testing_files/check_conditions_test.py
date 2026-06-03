import yaml
import pandas as pd

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from etl.extract_excel import excel_to_parquet
from etl.normalization_dataframe import normalize_only_data_rows
from etl.typecasting import apply_schema_types
from vocab_check.apply_conditional_check import apply_conditional_rules


SCRIPT_DIR = Path(__file__).parent.parent.parent.parent
INPUT_XLSX = SCRIPT_DIR / "testing/validator/conditional/conditional_tests.xlsx"
SCHEMA_PATH = SCRIPT_DIR / "hf_schema.yaml"
COND_RULES_PATH = SCRIPT_DIR / "conditional_rules.yaml"


def main():
    # --- Schema laden ---
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    # --- Conditional rules laden ---
    with open(COND_RULES_PATH, "r", encoding="utf-8") as f:
        cond_cfg = yaml.safe_load(f)
    # --- Excel -> Parquet + row_type ---
    df_raw = excel_to_parquet(
        excel_path=str(INPUT_XLSX),
        parquet_path=str(SCRIPT_DIR / "testing/conditional_test.raw.parquet"),
        sheet_name=0,
        meta_rows=0,  # keine Meta-Zeilen in dieser Testdatei
    )

    #row_type absichern
    if "row_type" not in df_raw.columns:
        df_raw["row_type"] = "data"

    # --- Nur Daten normalisieren + Typen casten ---
    df_meta, df_data_norm = normalize_only_data_rows(df_raw, schema)
    df_typed = apply_schema_types(df_data_norm, schema)

    # --- Conditional-Regeln anwenden ---
    df_checked = apply_conditional_rules(df_typed, cond_cfg)

    # --- Prüfen, ob Hilfsspalten vorhanden sind ---
    if "__flag_col" not in df_checked.columns or "__case" not in df_checked.columns:
        print(
            "\nERROR: '__flag_col' und/oder '__case' Spalten fehlen in der Test-Datei.\n"
            "Bitte füge z.B. folgende Steuer-Spalten hinzu:\n"
            "  __flag_col  -> Name der zu prüfenden Flagspalte (z.B. C31__cond_p12_indirect_method_c31)\n"
            "  __case      -> 'violation' (Flag soll True sein) oder 'ok' (Flag soll False sein).\n"
        )
        return

    tests = []

    # --- Pro Zeile genau ein Testfall ---
    for idx, row in df_checked.iterrows():
        flag_col = row["__flag_col"]
        case = row["__case"]

        # leere Flag-Spalte ignorieren
        if pd.isna(flag_col):
            continue

        flag_col = str(flag_col).strip()
        case = str(case).strip()

        # Testname aufbauen
        name = f"[cond] {flag_col} case '{case}'"

        # prüfen, ob die Flag-Spalte existiert
        if flag_col not in df_checked.columns:
            msg = f"Flag column '{flag_col}' not found in DataFrame."
            tests.append((name, False, msg))
            continue

        flag_val = bool(row[flag_col])

        # Erwartetes Verhalten aus __case ableiten
        if case.lower() in ("violation", "should_flag", "error"):
            expected = True
            if flag_val == expected:
                tests.append((name, True, ""))
            else:
                msg = f"Expected {flag_col} = True for case '{case}', but got False."
                tests.append((name, False, msg))

        elif case.lower() in ("ok", "no_violation", "valid"):
            expected = False
            if flag_val == expected:
                tests.append((name, True, ""))
            else:
                msg = f"Expected {flag_col} = False for case '{case}', but got True."
                tests.append((name, False, msg))

        else:
            msg = (
                f"Unknown case label '{case}' for flag '{flag_col}'. "
                "Use e.g. 'violation' or 'ok'."
            )
            tests.append((name, False, msg))

    # --- Summary---

    total = len(tests)
    passed = sum(1 for _, ok, _ in tests if ok)
    failed = total - passed

    print("\nConditional rules test summary")
    if total == 0:
        print("No conditional tests were executed.")
        return

    bar_len = 40
    filled = int(bar_len * passed / total)
    bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"

    print(f"{bar}  {passed}/{total} test cases passed, {failed} failed.")

    print("\nDetailed conditional test cases:")
    for i, (name, ok, msg) in enumerate(tests, start=1):
        status = "PASS" if ok else "FAIL"
        print(f"{i:3d}) {status} - {name}")
        if not ok and msg:
            print(f"     {msg}")

    if failed == 0:
        print("\nAll conditional tests passed.")
    else:
        print("\nSome conditional tests failed.")


if __name__ == "__main__":
    main()
