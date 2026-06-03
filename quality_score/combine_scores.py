# quality_score/combine_quality_scores.py
from __future__ import annotations
import re
import pandas as pd

# ordering: higher index = worse quality 

_U_ORDER = {"U1": 1, "U2": 2, "U3": 3, "U4": 4, "Ux": 9}
_M_ORDER = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "Mx": 9}

# list form neede for inherited score
_U_LIST = ["U1", "U2", "U3", "U4", "Ux"]
_M_LIST = ["M1", "M2", "M3", "M4", "M1x", "M2x", "M3x", "M4x", "Mx"]

# helpers
def _norm_u(u: str | None) -> str:
    if u is None:
        return "Ux"
    s = str(u).strip()
    return s if s in _U_ORDER else "Ux"


def _norm_m(m: str | None) -> str:
    if m is None:
        return "Mx"
    s = str(m).strip()
    if s in ("M1", "M2", "M3", "M4", "M1x", "M2x", "M3x", "M4x"):
        return s
    return "Mx"


def _base_m(m: str) -> str:
    return m[:2] if m.startswith("M") and len(m) >= 2 else "Mx"


def _norm_p(p: str | None) -> str:
    """
    P-flags are expected as 7-character code (e.g. 'SxxXPxR') or '-------'.
    Missing/invalid -> '-------' (paper uses '-' for insufficient info).
    """
    if p is None:
        return "-------"
    s = str(p).strip()
    return s if len(s) == 7 else "-------"

# helpers for inheritance

def _extract_u(score: str) -> str | None:
    m = re.search(r"U[0-9x]+", score)
    if m and m.group() in _U_LIST:
        return m.group()
    return None
 
 
def _extract_m(score: str) -> str | None:
    m = re.search(r"M[0-9x]+x?", score)
    if m and m.group() in _M_LIST:
        return m.group()
    return None
 
 
def _extract_p(score: str) -> str | None:
    m = re.search(r"\.([-SETPVCRsetpvcrxX]{7})$", score)
    return m.group(1) if m else None

def _worst_u(scores: pd.Series) -> str:
    """Return the worst (highest index) U token across all scores."""
    candidates = []
    for s in scores:
        if not isinstance(s, str):
            continue
        u = _extract_u(s)
        if u:
            candidates.append(u)
    if not candidates:
        return "Ux"
    return max(candidates, key=lambda x: _U_LIST.index(x))
 
 
def _worst_m(scores: pd.Series) -> str:
    """Return the worst (highest index) M token across all scores."""
    candidates = []
    for s in scores:
        if not isinstance(s, str):
            continue
        m = _extract_m(s)
        if m:
            candidates.append(m)
    if not candidates:
        return "Mx"
    return max(candidates, key=lambda x: _M_LIST.index(x))
 
 
def _worst_p(scores: pd.Series) -> str:
    """
    Return the P-flags from the single worst child.
    Worst = highest U rank; M rank used as tiebreaker.
    """
    best_rank = (-1, -1)
    best_p = "-------"
 
    for s in scores:
        if not isinstance(s, str):
            continue
 
        u = _extract_u(s)
        m = _extract_m(s)
        p = _extract_p(s)
 
        u_rank = _U_LIST.index(u) if u else 99
        m_rank = _M_LIST.index(m) if m else 99
 
        if (u_rank, m_rank) > best_rank:
            best_rank = (u_rank, m_rank)
            best_p = p if p else "-------"
 
    return best_p

def calculate_inherited_score(
    df: pd.DataFrame,
    score_col: str = "quality_QP",
    out_col: str = "quality_score_inherited",
    relevance_col: str = "C9",
    id_parent_col: str = "ID_parent",
    id_col: str = "ID",
    separator: str = ".",
) -> pd.DataFrame:
    """
    Add an inherited quality score column to df.
 
    For each parent row, the inherited score is derived from its relevant
    children (C9 == "[yes]"):
      - worst U across all relevant children
      - worst M across all relevant children
      - P from the single worst child (U rank first, M as tiebreaker)
 
    Rows with no relevant children fall back to their own score_col value.
 
    Required columns: ID_parent, ID, C9, and score_col.
    If any required column is missing the function returns df unchanged.
    """
    required = {id_parent_col, id_col, relevance_col, score_col}
    missing_cols = required - set(df.columns)
    if missing_cols:
        return df
 
    df = df.copy()
 
    # Relevant children only
    relevant_mask = (
        df[relevance_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        == "[yes]"
    )
    relevant = df[relevant_mask]
 
    if relevant.empty:
        df[out_col] = df[score_col]
        return df
 
    # Aggregate worst U, M, P per parent
    inherited = (
        relevant.groupby(id_parent_col)[score_col]
        .agg(
            U=_worst_u,
            M=_worst_m,
            P=_worst_p,
        )
        .reset_index()
    )
 
    inherited[out_col] = (
        inherited["U"]
        + separator
        + inherited["M"]
        + separator
        + inherited["P"]
    )
    inherited = inherited.drop(columns=["U", "M", "P"])
 
    # Merge back on ID_parent
    df = df.merge(inherited, on=id_parent_col, how="left")
 
    # Fallback: rows with no relevant children keep their own score
    df[out_col] = df[out_col].fillna(df[score_col])
 
    return df
 

def combine_u_m_p_scores(
    df: pd.DataFrame,
    u_col: str = "quality_U",
    m_col: str = "quality_M",
    p_col: str = "quality_P",
    out_col: str = "quality_Q",
    out_rank_col: str = "quality_rank",
    out_col_with_p: str = "quality_QP",
    separator: str = ".",
) -> pd.DataFrame:
    """
    If ID_parent and ID columns are present, also adds:
      - quality_score_inherited: score inherited from worst relevant children
    """
    u = (
        df[u_col].astype("string")
        if u_col in df.columns
        else pd.Series(["Ux"] * len(df), index=df.index, dtype="string")
    )
    m = (
        df[m_col].astype("string")
        if m_col in df.columns
        else pd.Series(["Mx"] * len(df), index=df.index, dtype="string")
    )
    p = (
        df[p_col].astype("string")
        if p_col in df.columns
        else pd.Series(["-------"] * len(df), index=df.index, dtype="string")
    )
 
    u_norm = u.fillna("Ux").map(_norm_u)
    m_norm = m.fillna("Mx").map(_norm_m)
    p_norm = p.fillna("-------").map(_norm_p)
 
    df[out_col] = (u_norm.astype("string") + separator + m_norm.astype("string")).astype("string")
 
    # rank = max(U-rank, M-rank) using base M (ignore suffix for rank)
    u_rank = u_norm.map(lambda x: _U_ORDER.get(x, 9)).astype("int64")
    m_rank = m_norm.map(lambda x: _M_ORDER.get(_base_m(x), 9)).astype("int64")
    df[out_rank_col] = u_rank.where(u_rank >= m_rank, m_rank)
 
    df[out_col_with_p] = (
        df[out_col].astype("string") + separator + p_norm.astype("string")
    ).astype("string")
 
    # Inherited score: only if parent/child ID columns are present
    if "ID_parent" in df.columns and "ID" in df.columns:
        df = calculate_inherited_score(
            df,
            score_col=out_col_with_p,
            out_col="quality_score_inherited",
            separator=separator,
        )
 
    return df
 
