# quality_score/calculate_m_score.py
from __future__ import annotations
import numpy as np
import pandas as pd

from quality_score.apply_m_quality_score_borehole import calculate_m_score_borehole
from quality_score.apply_m_quality_score_marine import calculate_m_score_marine

def _get_route(cell_value: str) -> str:
    if not cell_value:
        return "not_determined"
    
    value_norm = str(cell_value).strip().lower()
    tokens = {t.strip() for t in value_norm.split(";") if t.strip()}
    
    # Marine: contains "probing" and any of onshore/lake/river/offshore/ocean/clustering
    if "probing" in value_norm and any(word in value_norm for word in [
        "onshore", "lake", "river", "offshore", "ocean", "clustering"
    ]):
        return "marine"
    
    # Borehole: contains drilling/mining/tunneling/indirect
    if any(word in value_norm for word in [
        "drilling", "mining", "tunneling", "indirect", "gtm", "bsr", "cpd"
    ]):
        return "borehole"
    
    return "not_determined"


def calculate_m_score(
    df: pd.DataFrame,
    qc_schema: dict,
    return_debug: bool = False
) -> pd.Series | tuple[pd.Series, dict]:
    """
    Router for M-score calculation based on P12 route.
    
    When return_debug=True:
        Returns (m_score_series, debug_dict) where debug_dict has:
        - debug_t_score, debug_tc_score, debug_raw_combined (marine & borehole rows)
    """
    m_cfg = qc_schema.get("m_score", {})
    calc = m_cfg.get("calculation", {})
    route_col = calc.get("m_route_col", "P12")
    thr = m_cfg.get("thresholds", {})
    missing_suffix = str(thr.get("missing_suffix", "x"))

    p12_values = (
        df[route_col]
        .astype("string")
        .str.lower()
        .fillna("")
        .str.strip()
    )

    routes = p12_values.apply(_get_route)

    out = pd.Series(pd.NA, index=df.index, dtype="string")

    marine_idx   = df.index[routes == "marine"]
    borehole_idx = df.index[routes == "borehole"]
    nd_idx       = df.index[routes == "not_determined"]

    debug_dict = {
        "debug_t_score": pd.Series(np.nan, index=df.index, dtype=float),
        "debug_tc_score": pd.Series(np.nan, index=df.index, dtype=float),
        "debug_raw_combined": pd.Series(np.nan, index=df.index, dtype=float),
    } if return_debug else None

    if len(marine_idx):
        if return_debug:
            marine_result, marine_debug = calculate_m_score_marine(
                df.loc[marine_idx].copy(),
                qc_schema,
                return_debug=True
            )
            out.loc[marine_idx] = marine_result
            for key in debug_dict:
                debug_dict[key].loc[marine_idx] = marine_debug.get(key, pd.NA)
        else:
            out.loc[marine_idx] = calculate_m_score_marine(
                df.loc[marine_idx].copy(),
                qc_schema
            )

    if len(borehole_idx):
        if return_debug:
            borehole_result, borehole_debug = calculate_m_score_borehole(
                df.loc[borehole_idx].copy(),
                qc_schema,
                return_debug=True   # ← assumes borehole function supports this
            )
            out.loc[borehole_idx] = borehole_result
            for key in debug_dict:
                debug_dict[key].loc[borehole_idx] = borehole_debug.get(key, pd.NA)
        else:
            out.loc[borehole_idx] = calculate_m_score_borehole(
                df.loc[borehole_idx].copy(),
                qc_schema
            )

    if len(nd_idx):
        out.loc[nd_idx] = "Mx"  # not determined, no calculation

    if return_debug:
        return out, debug_dict
    else:
        return out


def calculate_m_route_debug(df: pd.DataFrame, qc_schema: dict) -> pd.Series:
    """Debug column: returns 'marine', 'borehole', or 'not_determined' per row."""
    calc = qc_schema.get("m_score", {}).get("calculation", {})
    route_col = calc.get("m_route_col", "P12")

    p12_values = (
        df[route_col]
        .astype("string")
        .str.lower()
        .fillna("")
        .str.strip()
    )
    return p12_values.apply(_get_route).astype("string")