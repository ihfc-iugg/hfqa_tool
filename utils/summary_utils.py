# utils/summary_utils.py

def build_summary(data_len, raw_len, meta_rows, first_data_index, stats, runtime):
    return {
        "total_rows_in_sheet": raw_len,
        "data_rows_validated": data_len,
        "rows_with_any_error": len(stats["rows_any_error"]),
        "rows_with_functional_error": len(stats["rows_functional_error"]),
        "rows_with_conditional_error": len(stats["rows_conditional_error"]),
        "functional_error_count": stats["functional_error_count"],
        "conditional_error_count": stats["conditional_error_count"],
        "functional_missing_error_count": stats["missing_error_count"],
        "functional_range_error_count": stats["range_error_count"],
        "functional_allowed_error_count": stats["allowed_error_count"],
        "functional_other_error_count": stats["other_functional_error_count"],
        "per_flag_counts": stats["per_flag_counts"],
        "runtime_seconds": runtime,
    }
