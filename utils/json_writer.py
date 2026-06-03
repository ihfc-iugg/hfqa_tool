# utils/json_writer.py
from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype

from utils.logging_utils import log_file_written
from utils.schema_loader import get_col_comment
from utils.summary_utils import build_summary

import math

def _num_or_zero(x):
    if x is None:
        return 0
    if isinstance(x, float) and math.isnan(x):
        return 0
    return x


def _uniq_keep_order(seq: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def collect_validation_results(
    df_checked: pd.DataFrame,
    schema: dict,
    row_offset: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """
    Pure function (no logging):
      - violations: cell-level, one entry per flagged cell
      - row_results: row-level, one entry per data row (OK/ERRORS + compact reasons)
      - stats: aggregates for summary

    Row numbering:
      row_excel_number is absolute Excel row number (incl. meta + header),
      computed position-based: row_offset + pos.
    """
    violations: list[dict[str, Any]] = []
    row_results: list[dict[str, Any]] = []

    stats: dict[str, Any] = {
        "functional_error_count": 0,
        "conditional_error_count": 0,
        "per_flag_counts": {},
        "missing_error_count": 0,
        "range_error_count": 0,
        "allowed_error_count": 0,
        "other_functional_error_count": 0,
        "rows_any_error": set(),
        "rows_functional_error": set(),
        "rows_conditional_error": set(),
    }

    flag_cols = [c for c in df_checked.columns if "__" in c]

    # Robust boolean view: works for bool, pandas BooleanDtype, int/object flags
    flags_view: dict[str, pd.Series] = {}
    for c in flag_cols:
        s = df_checked[c]
        if not is_bool_dtype(s):
            flags_view[c] = s.fillna(False).astype(bool)
        else:
            flags_view[c] = s.fillna(False)

    for pos, idx in enumerate(df_checked.index):
        excel_row = row_offset + pos
        site_name = str(df_checked.at[idx, "P3"]) if "P3" in df_checked.columns else "N/A"

        row_issue_tags: list[str] = []
        row_comments: list[str] = []

        for col in flag_cols:
            if not bool(flags_view[col].iat[pos]):
                continue

            col_name, flag_type = col.split("__", 1)
            is_conditional = flag_type.startswith("cond_")
            comment = get_col_comment(schema, col_name)

            # ---- violations (cell-level, old design) ----
            violations.append(
                {
                    "row_excel_number": excel_row,
                    "column": col_name,
                    "site_name": site_name,
                    "flag": flag_type,
                    "comment": comment,
                }
            )

            # ---- stats (cell-level counts) ----
            stats["per_flag_counts"][flag_type] = stats["per_flag_counts"].get(flag_type, 0) + 1
            stats["rows_any_error"].add(excel_row)

            if is_conditional:
                stats["conditional_error_count"] += 1
                stats["rows_conditional_error"].add(excel_row)
            else:
                stats["functional_error_count"] += 1
                stats["rows_functional_error"].add(excel_row)

                if flag_type == "missing":
                    stats["missing_error_count"] += 1
                elif flag_type == "out_of_range":
                    stats["range_error_count"] += 1
                elif flag_type == "invalid":
                    stats["allowed_error_count"] += 1
                else:
                    stats["other_functional_error_count"] += 1

            # ---- row-level aggregation ----
            if flag_type.startswith("cond_"):
                row_issue_tags.append(f"cond:{flag_type}")
                row_comments.append(f"[CONDITIONAL ERROR] {col_name} ({comment}): {flag_type}")
            elif flag_type == "missing":
                row_issue_tags.append(f"missing:{col_name}")
                row_comments.append(f"[MISSING] {col_name} ({comment})")
            elif flag_type == "out_of_range":
                row_issue_tags.append(f"out_of_range:{col_name}")
                row_comments.append(f"[RANGE ERROR] {col_name} ({comment})")
            elif flag_type == "invalid":
                row_issue_tags.append(f"invalid:{col_name}")
                row_comments.append(f"[INVALID VALUE] {col_name} ({comment})")
            else:
                row_issue_tags.append(f"{flag_type}:{col_name}")
                row_comments.append(f"[ERROR] {col_name} ({comment}): {flag_type}")

        row_issue_tags = _uniq_keep_order(row_issue_tags)
        row_comments = _uniq_keep_order(row_comments)

        row_ok = len(row_issue_tags) == 0

        row_results.append(
            {
                "row_excel_number": excel_row,
                "site_name": site_name,
                "status": "OK" if row_ok else "ERRORS",
                "issue_tags": row_issue_tags,
                "validation_comments": "OK" if row_ok else " | ".join(row_comments),
            }
        )

    return violations, row_results, stats


def write_validation_report(
    df_checked: pd.DataFrame,
    schema: dict,
    meta_rows: int,
    first_data_index: int,  # kept for compatibility; not used for mapping
    df_raw: pd.DataFrame,
    df_data_typed: pd.DataFrame,
    start_time: float,
    out_path: str,
    include_row_results_in_json: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Writes JSON. Returns (summary, row_results, violations) so caller can log them.

    JSON contains:
      - violations
      - summary
      - optionally row_results (if include_row_results_in_json=True)
    """
    row_offset = meta_rows + 1  # meta + header

    violations, row_results, stats = collect_validation_results(
        df_checked=df_checked,
        schema=schema,
        row_offset=row_offset,
    )

    summary = build_summary(
        data_len=len(df_data_typed),
        raw_len=len(df_raw),
        meta_rows=meta_rows,
        first_data_index=first_data_index,
        stats=stats,
        runtime=time.time() - start_time,
    )

    payload: dict[str, Any] = {
        "violations": violations,
        "summary": summary,
    }
    if include_row_results_in_json:
        payload["row_results"] = row_results

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log_file_written("JSON", out_path)
    return summary, row_results, violations


def write_quality_report(
    df_data_typed: pd.DataFrame,
    meta_rows: int,
    start_time: float,
    out_path: str,
) -> None:
    """
    Build and write the quality scoring report as JSON.
    Row numbering aligns with validation report (Excel row numbers).

    Outputs:
      - U score
      - M score
      - P flags (7-letter paper code)
      - combined quality code: U.M.P
    """
    row_offset = meta_rows + 1  # meta + header (same as validation)

    child_determinations: list[dict[str, Any]] = []

    for pos0, (_, row) in enumerate(df_data_typed.iterrows()):
        excel_row = row_offset + pos0

        u = row.get("quality_U", "Ux")
        m = row.get("quality_M", "Mx")
        p = row.get("quality_P", "-------")

        # Prefer fully combined paper code if present
        q = row.get("quality_QP")
        if not q:
            # robust fallback
            q = f"{u}.{m}.{p}"

        rank = row.get("quality_rank")

        entry: dict[str, Any] = {
            "row_excel_number": excel_row,
            "site_id": row.get("ID"),
            "site_name": row.get("P3", "N/A"),

            # explicit, paper-aligned fields
            "u_score": u,
            "m_score": m,
            "p_flags": p,
            "quality_score": q,
            "quality_rank": rank,

            "values": {
                "C1_HF": _num_or_zero(row.get("C1")),
                "C2_Unc": _num_or_zero(row.get("C2")),
            },
        }

        child_determinations.append(entry)

    final_output = {
        "mode": "quality_scoring",
        "summary": {
            "total_determinations": len(df_data_typed),
            "high_accuracy_U1_U2": int(
                df_data_typed["quality_U"].isin(["U1", "U2"]).sum()
            ),
            "runtime_seconds": time.time() - start_time,
        },
        "detailed_results": child_determinations,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    log_file_written("JSON", out_path)
