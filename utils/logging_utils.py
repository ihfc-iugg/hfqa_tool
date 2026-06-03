# utils/logging_utils.py
from __future__ import annotations

import logging
from typing import Any


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def log_file_written(file_type: str, path: str) -> None:
    logging.info("%s file created successfully: %s", file_type, path)


def log_vocab_validation_summary(summary: dict[str, Any]) -> None:
    logging.info("==== VOCABULARY VALIDATION SUMMARY ====")
    logging.info("Total rows in sheet (incl. meta): %d", summary["total_rows_in_sheet"])
    logging.info("Data rows validated: %d", summary["data_rows_validated"])
    logging.info("Rows with any error: %d", summary["rows_with_any_error"])
    logging.info("Rows with functional errors: %d", summary["rows_with_functional_error"])
    logging.info("Rows with conditional errors: %d", summary["rows_with_conditional_error"])
    logging.info("Functional errors (cell count): %d", summary["functional_error_count"])
    logging.info("  ├─ Missing errors: %d", summary["functional_missing_error_count"])
    logging.info("  ├─ Range errors: %d", summary["functional_range_error_count"])
    logging.info("  ├─ Allowed-value errors: %d", summary["functional_allowed_error_count"])
    logging.info("  └─ Other functional errors: %d", summary["functional_other_error_count"])
    logging.info("Conditional errors (cell count): %d", summary["conditional_error_count"])
    logging.info("Processing time: %.2f seconds", summary["runtime_seconds"])


def log_row_results(row_results: list[dict[str, Any]]) -> None:
    """
    One console line per data row: OK / ERRORS.
    """
    for r in row_results:
        excel_row = r["row_excel_number"]
        site = r.get("site_name", "N/A")
        status = r.get("status", "OK")

        if status == "OK":
            logging.info("row=%d site=%s status=OK", excel_row, site)
        else:
            tags = r.get("issue_tags", [])
            logging.info("row=%d site=%s status=ERRORS %s", excel_row, site, "; ".join(tags))


def log_violations(violations: list[dict[str, Any]]) -> None:
    """
    Cell-level logs (old style): one console line per violation.
    """
    for v in violations:
        logging.info(
            "row=%d col=%s flag=%s site=%s comment=%s",
            v["row_excel_number"],
            v["column"],
            v["flag"],
            v["site_name"],
            v["comment"],
        )
