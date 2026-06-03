# quality_score/apply_p_flags.py
from __future__ import annotations

import pandas as pd
from etl.normalization_utils import normalize_token


def calculate_p_flags(df: pd.DataFrame, qc_schema: dict) -> pd.Series:
    """
    Generate 7-character p-flag codes (paper style) from perturbation columns.

    Returns: Series of strings like "SxxxCxh" or "-------"
    """
    p_cfg = qc_schema.get("m_score", {}).get("p_flags", {})
    if not p_cfg:
        return pd.Series(["-" * 7] * len(df), index=df.index, dtype="string")

    order = p_cfg.get("order", [])
    fields = p_cfg.get("fields", {})
    letters = p_cfg.get("letters", {})
    encoding = p_cfg.get("encoding", {})

    if not order or not fields or not letters or not encoding:
        return pd.Series(["-" * 7] * len(df), index=df.index, dtype="string")

    def normalize_p_value(val) -> str:
        """
        Normalize values exactly like schema token normalization.
        - bracketed token -> normalize_token (keeps brackets, hyphenizes, lowercases)
        - otherwise -> strip/lower
        """
        if val is None or pd.isna(val):
            return ""

        s = str(val).strip()
        if not s:
            return ""

        # If it has brackets, use token normalization (same as schema)
        if "[" in s and "]" in s:
            return normalize_token(s)

        return s.lower()

    def encode_flag(process_name: str, flag_value) -> str:
        """Encode a single flag position."""
        col = fields.get(process_name)
        letter = letters.get(process_name)

        if not col or not letter:
            return "-"

        flag_norm = normalize_p_value(flag_value)

        # encoding keys are already normalized in schema normalization
        action = encoding.get(flag_norm, "-")

        if action == "UPPER":
            return letter.upper()
        if action == "LOWER":
            return letter.lower()
        if action in ("X", "x", "-"):
            return action
        return "-"

    # Build p-flag strings
    out = []
    for idx in df.index:
        code = ""
        for process in order:
            col = fields.get(process)
            val = df.loc[idx, col] if col and col in df.columns else None
            code += encode_flag(process, val)
        out.append(code)

    return pd.Series(out, index=df.index, dtype="string")
