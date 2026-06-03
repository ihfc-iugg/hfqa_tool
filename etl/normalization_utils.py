import pandas as pd
import re


def is_bracketed_token(val: str) -> bool:
    """Check if a token has [brackets] around it."""
    return isinstance(val, str) and "[" in val and "]" in val


def normalize_bracketed_token_series(s: pd.Series) -> pd.Series:
    """
    Normalize bracketed vocabulary entries, including multi-valued cells.
    Used for both schema (allowed values) and data values.
    """
    s = s.astype("string")

    def _norm_value(val):
        if val is None or pd.isna(val):
            return pd.NA

        text = str(val).strip()
        if not text:
            return pd.NA

        parts = [p.strip() for p in text.split(";") if p.strip()]
        norm_parts = []

        for p in parts:
            p = p.lower().strip()

            if p.startswith("[") and p.endswith("]"):
                p = p[1:-1].strip()

            p = p.replace("\u2013", "-").replace("\u2014", "-")

            # Normalize internal separators
            p = re.sub(r"[ ,/]+", "-", p)
            p = re.sub(r"-{2,}", "-", p)
            p = re.sub(r"\s*\(\s*", "(", p)
            p = re.sub(r"\s*\)\s*", ")", p)
            p = re.sub(r"\s*-\s*", "-", p)

            norm_parts.append(f"[{p}]")

        return ";".join(norm_parts) if norm_parts else pd.NA

    return s.map(_norm_value)


def normalize_token(val: str) -> str:
    """Normalize a single token value (bracketed or not)."""
    if val is None:
        return ""
    s = str(val)
    if is_bracketed_token(s):
        series = pd.Series([s], dtype="string")
        return str(normalize_bracketed_token_series(series).iloc[0]).strip().lower()
    else:
        return s.strip().lower()


def normalize_token_list(vals) -> list:
    """Normalize a list of tokens using bracketed logic if needed."""
    if not vals:
        return []
    series = pd.Series(list(vals), dtype="string")
    norm = normalize_bracketed_token_series(series)
    return [str(v).strip().lower() for v in norm.dropna()]


def normalize_token_series(df: pd.DataFrame, col_name: str, value_for_mode) -> pd.Series:
    """Normalize a dataframe column based on whether its tokens are bracketed."""
    s = df[col_name].astype("string")
    if value_for_mode and is_bracketed_token(value_for_mode):
        s = normalize_bracketed_token_series(s)
    return s.astype("string").str.strip().str.lower()
