# main.py
import argparse
import logging
import time
from pathlib import Path
import pandas as pd

import yaml

from etl.preprocessing import prepare_data_from_excel
from vocab_check.apply_functional_check import add_mandatory_flags, add_range_and_allowed_flags
from vocab_check.apply_conditional_check import apply_conditional_rules
from quality_score.apply_u_quality_score import calculate_u_score
from quality_score.combine_scores import combine_u_m_p_scores
from quality_score.apply_m_quality_score import calculate_m_score,  calculate_m_route_debug
from quality_score.apply_p_flags import calculate_p_flags
import numpy as np


from utils.logging_utils import setup_logging

from utils.schema_loader import load_all_schemas
from utils.excel_writer import (
    generate_vocab_check_comments,
    write_excel_with_vocab_check_comments,
    generate_quality_score_column,
    write_excel_with_quality_score,
)


from utils.json_writer import write_validation_report, write_quality_report

# Resolves output path for Excel or JSON report

def resolve_output_path(input_path: Path, mode: str, kind: str) -> str:
    out_dir = input_path.parent / ("vocab" if mode == "vocab" else "qc")
    out_dir.mkdir(parents=True, exist_ok=True)

    if kind == "excel":
        return str(out_dir / input_path.name)

    if kind == "json":
        return str(out_dir / input_path.with_suffix(".json").name)

    raise ValueError(f"Unknown kind '{kind}'")


def run_pipeline(
    input_path: str,
    output_kind: str,
    mode: str,
    sheet_name: int = 1, # default datalist 
    meta_rows: int = 7,
    debug_prefix: str | None = None,
    include_row_results_in_json: bool = False,
) -> None:
    start_time = time.time()
    input_path = Path(input_path)

    # 1) Load schemas (already normalized by loader, if implemented there)
    schema, cond_cfg, qc_schema = load_all_schemas()

    # 2) Prepare data
    parquet_path = input_path.with_suffix(".raw.parquet")
    df_raw, df_meta, df_data_typed = prepare_data_from_excel(
        excel_path=str(input_path),
        schema=schema,
        sheet_name=sheet_name,
        meta_rows=meta_rows,
        parquet_path=str(parquet_path),
    )

    # Debug dumps (data + schemas)
    if debug_prefix:

        debug_dir = Path(debug_prefix)
        debug_dir.mkdir(parents=True, exist_ok=True)

        # dump prepared data
        df_data_typed.to_parquet(debug_dir / "02_data_prepared.parquet", index=False)

        # dump raw loaded schemas
        with open(debug_dir / "schema.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(schema, f, sort_keys=False, allow_unicode=True)

        with open(debug_dir / "conditional_rules.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(cond_cfg, f, sort_keys=False, allow_unicode=True)

        with open(debug_dir / "quality_schema.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(qc_schema, f, sort_keys=False, allow_unicode=True)

        # dump effective/normalized schema
        used_columns = set(df_data_typed.columns)
        schema_normalized = {
            "columns": {
                k: v
                for k, v in schema.get("columns", {}).items()
                if k in used_columns
            },
            "core": schema.get("core", {}),
        }

        with open(debug_dir / "schema_normalized.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(schema_normalized, f, sort_keys=False, allow_unicode=True)

        logging.info("Debug artifacts written to folder: %s", debug_dir)


    # 3) Vocab mode
    if mode == "vocab":
        logging.info("Starting Vocabulary Validation Mode...")

        df_checked = add_mandatory_flags(df_data_typed, schema)
        df_checked = add_range_and_allowed_flags(df_checked, schema)
        df_checked = apply_conditional_rules(df_checked, cond_cfg)

        first_data_index = int(df_checked.index.min()) if len(df_checked) > 0 else 0

        # JSON output (only if requested)
        if output_kind == "json":
            df_data_typed = df_data_typed.replace({pd.NA: None})
            out_path = resolve_output_path(input_path, mode="vocab", kind="json")

            write_validation_report(
                df_checked=df_checked,
                schema=schema,
                meta_rows=meta_rows,
                first_data_index=first_data_index,
                df_raw=df_raw,
                df_data_typed=df_data_typed,
                start_time=start_time,
                out_path=out_path,
                include_row_results_in_json=include_row_results_in_json,
            )

        # Excel output (default)
        if output_kind == "excel":
            out_path = resolve_output_path(input_path, mode="vocab", kind="excel")

            df_for_excel = generate_vocab_check_comments(
                df_raw=df_raw,
                df_checked=df_checked,
                schema=schema,
                meta_rows=meta_rows,
                out_col="Validation_Comments",
            )

            write_excel_with_vocab_check_comments(
                df_meta=df_meta,
                df_with_comments=df_for_excel.iloc[meta_rows:],
                output_path=out_path,
            )


        # 4) Quality mode
    elif mode == "quality":
        logging.info("Starting IHFC Quality Scoring Mode...")

        df_data_typed["quality_U"] = calculate_u_score(
            df_data_typed,
            qc_schema=qc_schema,
        )

        # Call M-score with debug support
        m_result = calculate_m_score(
            df_data_typed,
            qc_schema=qc_schema,
            return_debug=True
        )

        if isinstance(m_result, tuple):
            df_data_typed["quality_M"] = m_result[0]
            debug_info = m_result[1]
            # Assign debug columns (NaN where not applicable)
            df_data_typed["debug_t_score"] = debug_info["debug_t_score"]
            df_data_typed["debug_tc_score"] = debug_info["debug_tc_score"]
            df_data_typed["debug_raw_combined"] = debug_info["debug_raw_combined"]
        else:
            # Fallback if no debug returned (should not happen)
            df_data_typed["quality_M"] = m_result
            df_data_typed["debug_t_score"] = pd.NA
            df_data_typed["debug_tc_score"] = pd.NA
            df_data_typed["debug_raw_combined"] = pd.NA

        df_data_typed["debug_m_route"] = calculate_m_route_debug(
            df_data_typed, qc_schema=qc_schema
        )

        df_data_typed["quality_P"] = calculate_p_flags(
            df_data_typed,
            qc_schema=qc_schema,
        )

        df_data_typed = combine_u_m_p_scores(
            df_data_typed,
            u_col="quality_U",
            m_col="quality_M",
            p_col="quality_P",
            out_col_with_p="quality_QP",
            separator=".",
        )

        # Quick console debug (only when debug-prefix is set)
        if debug_prefix:
            print("\nDebug preview (first 5 rows):")
            preview_cols = [
                "debug_t_score",
                "debug_tc_score",
                "debug_raw_combined",
                "quality_M",
                "debug_m_route"
            ]
            print(df_data_typed[preview_cols].head(5).to_string())

        # only ONE output is written
        if output_kind == "json":
            df_data_typed = df_data_typed.replace({pd.NA: None})
            out_path = resolve_output_path(input_path, mode="quality", kind="json")

            write_quality_report(
                df_data_typed=df_data_typed,
                meta_rows=meta_rows,
                start_time=start_time,
                out_path=out_path,
            )

        else:  # excel
            out_path = resolve_output_path(input_path, mode="quality", kind="excel")

            # Start with your standard quality_score column
            df_for_excel = generate_quality_score_column(
                df_raw=df_raw,
                df_scored=df_data_typed,
                meta_rows=meta_rows,
                source_col="quality_QP",
                out_col="quality_score",
            )

            # Add debug_m_route (keep your existing call)
            df_for_excel = generate_quality_score_column(
                df_raw=df_for_excel,
                df_scored=df_data_typed,
                meta_rows=meta_rows,
                source_col="debug_m_route",
                out_col="debug_m_route",
            )

            # ────────────────────────────────────────────────────────────────
            # Force-add the numeric debug columns (T, TC, raw combined)
            # ────────────────────────────────────────────────────────────────
            debug_float_cols = [
                "debug_t_score",
                "debug_tc_score",
                "debug_raw_combined",
            ]

            for col in debug_float_cols:
                if col in df_data_typed.columns:
                    data_row_indices = df_for_excel.index[meta_rows:]
                    df_for_excel.loc[data_row_indices, col] = df_data_typed[col].values
                    df_for_excel[col] = df_for_excel[col].round(3)
                else:
                    df_for_excel[col] = pd.NA
  
            # Write the Excel file with all columns
            if "quality_score_inherited" in df_data_typed.columns:
                df_for_excel = generate_quality_score_column(
                    df_raw=df_for_excel,
                    df_scored=df_data_typed,
                    meta_rows=meta_rows,
                    source_col="quality_score_inherited",
                    out_col="quality_score_inherited",
                )
            write_excel_with_quality_score(
                df_meta=df_meta,
                df_with_quality=df_for_excel.iloc[meta_rows:],
                output_path=out_path,
            )
    
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to input Excel file")
    
    out_group = parser.add_mutually_exclusive_group()
    out_group.add_argument("--out-json", action="store_true")
    out_group.add_argument("--out-excel", action="store_true")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--vocab-check", action="store_true", help="Run vocabulary validation")
    mode_group.add_argument("--quality-score", action="store_true", help="Run quality scoring")

    parser.add_argument("--sheet", type=int, default=1)
    parser.add_argument("--meta-rows", type=int, default=7)
    parser.add_argument("--debug-prefix", default=None)

    parser.add_argument("--run-tests", action="store_true")

    # Logging toggles
    parser.add_argument("--no-row-log", action="store_true", help="Disable per-row OK/ERROR console logging")
    parser.add_argument("--no-violation-log", action="store_true", help="Disable per-violation console logging")
    parser.add_argument(
        "--include-row-results-in-json",
        action="store_true",
        help="Also store row_results array in the JSON report",
    )

    args = parser.parse_args()
    setup_logging()

    mode = "vocab" if args.vocab_check else "quality"

    output_kind = "excel"
    if args.out_json:
        output_kind = "json"

    run_pipeline(
        input_path=args.input,
        mode=mode,
        output_kind=output_kind,
        sheet_name=args.sheet,
        meta_rows=args.meta_rows,
        debug_prefix=args.debug_prefix,
        include_row_results_in_json=args.include_row_results_in_json,
    )


if __name__ == "__main__":
    main()
