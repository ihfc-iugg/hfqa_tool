import pandas as pd
from etl.normalization_utils import normalize_bracketed_token_series


def normalize_dataframe(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Normalize all string and numeric fields in the DataFrame based on the schema rules.
    """
    df = df.copy()
    norm_cfg = schema.get("normalization", {})
    global_string_norm = norm_cfg.get("string", {})
    global_numeric_norm = norm_cfg.get("numeric", {})

    for col_name, col_spec in schema.get("columns", {}).items():
        if col_name not in df.columns:
            continue

        dtype = str(col_spec.get("dtype", "")).lower()
        col_norm = col_spec.get("normalization", {})
        effective_string_norm = global_string_norm.copy()
        effective_string_norm.update(col_norm)

        s = df[col_name]

        # ---------- STRING ----------
        if "string" in dtype:
            s = s.astype("string")

            # 1. Handle missing tokens
            missing_tokens = effective_string_norm.get("missing_tokens", [])
            if missing_tokens:
                s = s.replace(missing_tokens, pd.NA)

            # 2. Basic string cleanup
            if effective_string_norm.get("trim", False):
                s = s.str.strip()
            if effective_string_norm.get("collapse_space", False):
                s = s.str.replace(r"\s+", " ", regex=True)

            # 3. Separator normalization
            if effective_string_norm.get("normalize_separator", False):
                s = s.str.replace(",", ";", regex=False)

            # 4. Lowercasing
            if effective_string_norm.get("case_insensitive", False):
                s = s.str.lower()

            # 5. Replace dash characters (e.g. EM dash)
            if "replace_dash" in effective_string_norm:
                dash_char = effective_string_norm["replace_dash"]
                s = s.str.replace(dash_char, "-", regex=False)

            # 6. Bracketed token normalization
            allowed = col_spec.get("allowed")
            has_bracketed_allowed = bool(allowed) and any("[" in str(a) or "]" in str(a) for a in allowed)
            enforce_brackets = effective_string_norm.get("enforce_brackets", False)

            if enforce_brackets or has_bracketed_allowed:
                s = normalize_bracketed_token_series(s)

            df[col_name] = s

        # ---------- NUMERIC ----------
        elif "float" in dtype or "int" in dtype:
            s = s.astype("string")

            missing_tokens = global_numeric_norm.get("missing_tokens", [])
            if missing_tokens:
                s = s.replace(missing_tokens, pd.NA)

            for sep in global_numeric_norm.get("strip_thousands_separators", []):
                s = s.str.replace(sep, "", regex=False)

            if global_numeric_norm.get("decimal_comma_to_dot", False):
                s = s.str.replace(",", ".", regex=False)

            df[col_name] = s

    return df


def normalize_only_data_rows(df: pd.DataFrame, schema: dict):
    """
    Normalize only the 'data' rows in the DataFrame, preserving 'meta' rows as-is.
    Returns a tuple of (meta_df, normalized_data_df), or (None, df) if no row_type exists.
    """
    df = df.copy()

    if "row_type" not in df.columns:
        df_data_norm = normalize_dataframe(df, schema)
        df_data_norm["row_type"] = "data"
        return None, df_data_norm

    df_meta = df[df["row_type"] == "meta"].copy()
    df_data = df[df["row_type"] == "data"].copy()

    df_data_norm = normalize_dataframe(df_data, schema)
    df_data_norm["row_type"] = "data"
    df_meta["row_type"] = "meta"

    return df_meta, df_data_norm
