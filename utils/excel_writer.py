# utils/excel_writer.py

from __future__ import annotations

import pandas as pd
from pandas.api.types import is_bool_dtype
from utils.logging_utils import log_file_written

def write_excel_with_vocab_check_comments(
    df_meta: pd.DataFrame | None,
    df_with_comments: pd.DataFrame,
    output_path: str,
) -> None:
    """
    Writes an Excel file where meta rows (if provided) are placed on top,
    and data rows contain 'Validation_Comments'.
    """
    if df_meta is not None and len(df_meta) > 0:
        df_meta = df_meta.copy()
        df_meta["Validation_Comments"] = "META ROW"

        # Ensure meta has all columns present in df_with_comments
        for col in df_with_comments.columns:
            if col not in df_meta.columns:
                df_meta[col] = pd.NA

        # Align column order exactly
        df_meta = df_meta[df_with_comments.columns]

        # Keep stable ordering: meta first, then data
        df_final = pd.concat([df_meta, df_with_comments], ignore_index=True)
    else:
        df_final = df_with_comments.copy()

    df_final.to_excel(output_path, index=False, sheet_name="Validation Results")
    log_file_written("Excel", output_path)


def get_col_comment(schema_dict: dict, col_name: str) -> str:
    """Extract the 'comment' field for a column from the schema."""
    for section in ("columns", "core"):
        section_dict = schema_dict.get(section, {})
        if col_name in section_dict:
            return section_dict[col_name].get("comment", "")
    return ""


def generate_vocab_check_comments(
    df_raw: pd.DataFrame,
    df_checked: pd.DataFrame,
    schema: dict,
    meta_rows: int,
    out_col: str = "Validation_Comments",
) -> pd.DataFrame:
    """
    Return RAW Excel dataframe with ONE appended Validation_Comments column.
    Meta rows get 'META ROW', data rows get vocab validation comments.
    """

    df_out = df_raw.copy()

    # prepare empty column
    df_out[out_col] = pd.NA

    # ---- build comments from df_checked (data rows only) ----
    flag_cols = [c for c in df_checked.columns if "__" in c]

    flags_view = {}
    for c in flag_cols:
        s = df_checked[c]
        if not is_bool_dtype(s):
            flags_view[c] = s.fillna(False).astype(bool)
        else:
            flags_view[c] = s.fillna(False)

    comments: list[str] = []

    for idx in df_checked.index:
        row_comments: list[str] = []

        for col in flag_cols:
            if not bool(flags_view[col].at[idx]):
                continue

            col_name, flag_type = col.split("__", 1)
            col_description = get_col_comment(schema, col_name)

            if flag_type == "missing":
                msg = f"[MISSING] {col_name} ({col_description})"
            elif flag_type == "out_of_range":
                msg = f"[RANGE ERROR] {col_name} ({col_description})"
            elif flag_type == "invalid":
                msg = f"[INVALID VALUE] {col_name} ({col_description})"
            elif flag_type.startswith("cond_"):
                msg = f"[CONDITIONAL ERROR] {col_name} ({col_description}): {flag_type}"
            else:
                msg = f"[ERROR] {col_name} ({col_description}): {flag_type}"

            row_comments.append(msg)

        comments.append(" | ".join(row_comments) if row_comments else "OK")

    # ---- write comments into RAW df (after meta rows) ----
    #df_out.iloc[:meta_rows, df_out.columns.get_loc(out_col)] = "META ROW"
    df_out.iloc[meta_rows:, df_out.columns.get_loc(out_col)] = comments

    return df_out



def generate_quality_score_column(
    df_raw: pd.DataFrame,
    df_scored: pd.DataFrame,
    meta_rows: int,
    source_col: str = "quality_QP",
    out_col: str = "quality_score",
) -> pd.DataFrame:
    """
    Append one QC column to RAW Excel dataframe.
    Meta rows get empty values, data rows get QC score.
    """

    if source_col not in df_scored.columns:
        raise KeyError(f"Source QC column '{source_col}' not found in df_scored")

    df_out = df_raw.copy()

    # initialize column with NA
    df_out[out_col] = pd.NA

    # assign only to data rows
    df_out.iloc[meta_rows:, df_out.columns.get_loc(out_col)] = (
        df_scored[source_col].astype("string").values
    )

    return df_out



def write_excel_with_quality_score(
    df_meta: pd.DataFrame | None,
    df_with_quality: pd.DataFrame,
    output_path: str,
    sheet_name: str = "Quality Results",
) -> None:
    """
    Writes an Excel file where meta rows (if provided) are placed on top,
    and data rows contain the original columns + `quality_score`.
    """
    if df_meta is not None and len(df_meta) > 0:
        df_meta = df_meta.copy()
        df_meta["quality_score"] = "META ROW"

        # Ensure meta has all columns present in df_with_quality
        for col in df_with_quality.columns:
            if col not in df_meta.columns:
                df_meta[col] = pd.NA

        # Align column order exactly
        df_meta = df_meta[df_with_quality.columns]

        df_final = pd.concat([df_meta, df_with_quality], ignore_index=True)
    else:
        df_final = df_with_quality.copy()

    df_final.to_excel(output_path, index=False, sheet_name=sheet_name)
    log_file_written("Excel", output_path)
