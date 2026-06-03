# quality_score/apply_m_quality_score_marine.py
from __future__ import annotations

import math
from typing import Any

import pandas as pd

_SEPS = (";", ",")


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _is_nan(x: Any) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _col_as_num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([math.nan] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def _split_tokens(cell: Any) -> set[str]:
    if _is_nan(cell):
        return set()
    if isinstance(cell, (list, tuple, set)):
        return {str(v).strip().lower() for v in cell if not _is_nan(v) and str(v).strip()}
    s = str(cell).strip().lower()
    if not s or s == "nan":
        return set()
    for sep in _SEPS[1:]:
        s = s.replace(sep, _SEPS[0])
    return {p.strip() for p in s.split(_SEPS[0]) if p.strip()}


# ---------------------------------------------------------------------------
# Bin evaluator (numeric threshold blocks)
# ---------------------------------------------------------------------------

def _eval_bin(val: float, op: str, threshold: float) -> bool:
    if op == ">":  return val > threshold
    if op == ">=": return val >= threshold
    if op == "<":  return val < threshold
    if op == "<=": return val <= threshold
    if op == "==": return val == threshold
    return False


def _eval_bins_largest_first(bins: dict, value: Any) -> tuple[float, bool]:
    """
    Evaluate numeric bins largest-threshold-first.

    Returns (penalty, missing_flag):
      - Value present and matched:      (penalty, False)
      - Value empty / NaN / unparseable: (worst_penalty, True)   ← largest penalty + x flag
      - Value present, nothing matched: (worst_penalty, False)   ← data issue, no x
    """
    if _is_nan(value):
        if not bins:
            return 0.0, True
        worst_penalty = min(float(bin_def["penalty"]) for bin_def in bins.values())
        return worst_penalty, True

    try:
        fval = float(value)
    except (TypeError, ValueError):
        if not bins:
            return 0.0, True
        worst_penalty = min(float(bin_def["penalty"]) for bin_def in bins.values())
        return worst_penalty, True

    sorted_bins = sorted(
        bins.items(),
        key=lambda item: float(item[1].get("when", {}).get("value", 0)),
        reverse=True,
    )

    for _, bin_def in sorted_bins:
        cond   = bin_def.get("when", {})
        op     = cond.get("op", "")
        thresh = float(cond.get("value", 0))
        if _eval_bin(fval, op, thresh):
            return float(bin_def["penalty"]), False

    if not bins:
        return 0.0, False
    worst_penalty = min(float(bin_def["penalty"]) for bin_def in bins.values())
    return worst_penalty, False


# ---------------------------------------------------------------------------
# Flat mapping evaluator (location block)
# ---------------------------------------------------------------------------

def _worst_matched_penalty(tokens: set[str], mapping: dict[str, float]) -> tuple[float, bool]:
    """
    Returns (penalty, missing_flag):
      - Token matched:             (worst matched penalty, False)
      - Empty tokens:              (worst_penalty, True)   ← x flag + largest penalty
      - Present but no match:      (worst_penalty, False)  ← data issue, no x
    """
    if not tokens:
        if not mapping:
            return 0.0, True
        worst = min(float(v) for v in mapping.values())
        return worst, True

    matched = [float(mapping[t]) for t in tokens if t in mapping]
    if matched:
        return min(matched), False

    if not mapping:
        return 0.0, False
    worst = min(float(v) for v in mapping.values())
    return worst, False


# ---------------------------------------------------------------------------
# Cases evaluator (saturation + pT blocks)
# ---------------------------------------------------------------------------

def _eval_cases(
    cases: list[dict],
    row_tokens: dict[str, set[str]],
) -> tuple[float, bool]:
    required_fields = set()
    for case in cases:
        when = case.get("when", {})
        if when:
            required_fields.update(when.keys())

    missing_required = any(
        not row_tokens.get(field.replace("_any", ""), set())
        for field in required_fields
    )

    if missing_required:
        if not cases:
            return 0.0, True
        worst = min(float(case["penalty"]) for case in cases)
        return worst, True

    matched_penalties = []
    for case in cases:
        when = case.get("when", {})
        if not when:
            continue
        match = True
        for field, condition in when.items():
            if field.endswith("_any"):
                col = field[:-4]
                tokens = row_tokens.get(col, set())
                values = set(condition)
                if not tokens & values:
                    match = False
                    break
            else:
                col = field
                tokens = row_tokens.get(col, set())
                val = condition
                if val not in tokens:
                    match = False
                    break
        if match:
            matched_penalties.append(float(case["penalty"]))

    if matched_penalties:
        return min(matched_penalties), False

    # No match → check fallback (empty when: {})
    for case in cases:
        if not case.get("when", {}):
            return float(case["penalty"]), False

    worst = min(float(case["penalty"]) for case in cases)
    return worst, False

# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def calculate_m_score_marine(
    df: pd.DataFrame,
    qc_schema: dict,
    return_debug: bool = False
) -> pd.Series | tuple[pd.Series, dict]:
    m_cfg = qc_schema["m_score"]
    calc  = m_cfg["calculation"]
    thr   = m_cfg["thresholds"]
    missing_suffix = str(thr.get("missing_suffix", "x"))

    # --- column names resolved from schema ---
    col_pen_depth = calc["probe_penetration_col"]   # C6
    col_T_n       = calc["t_number_col"]             # C37
    col_elev      = calc["elevation_col"]            # P6
    col_BWT_flag  = calc["corr_BWT_flag_col"]        # C17
    col_tilt      = calc["probe_tilt_col"]           # C23
    col_tilt_flag = calc["corr_T_flag_col"]         # C12
    col_tc_loc    = calc["tc_location_col"]          # C42
    col_tc_src    = calc["tc_source_col"]            # C41
    col_tc_method = calc["tc_method_col"]            # C43
    col_tc_sat    = calc["tc_saturation_col"]        # C44
    col_tc_pt     = calc["tc_pT_conditions_col"]     # C45
    col_tc_n      = calc["tc_number_col"]            # C47

    # --- numeric series ---
    pen_depth_s = _col_as_num(df, col_pen_depth)
    T_n_s       = _col_as_num(df, col_T_n)
    elev_s      = _col_as_num(df, col_elev)
    tilt_s      = _col_as_num(df, col_tilt)
    tc_n_s      = _col_as_num(df, col_tc_n)

    marine    = m_cfg["marine_logic"]
    t_logic   = marine["temperature"]
    tc_logic  = marine["conductivity"]
    t_blocks  = t_logic["blocks"]
    tc_blocks = tc_logic["blocks"]

    # --- flag tokens read from schema (never hardcoded) ---
    BWT_corrected_tok  = t_blocks["water_depth"]["corrected_if"]["flag_value"].strip().lower()
    tilt_corrected_tok = t_blocks["probe_tilt"]["corrected_if"]["flag_value"].strip().lower()

    # --- flat mapping for location block ---
    _loc_map = {k.strip().lower(): float(v) for k, v in tc_blocks["location"]["mapping"].items()}

    def classify(raw: float) -> str:
        if _is_nan(raw):
            return "M4"
        
        # Round to avoid floating-point issues
        raw_rounded = round(float(raw), 3)
        
        if raw_rounded >= float(thr["M1"]): return "M1"
        if raw_rounded >= float(thr["M2"]): return "M2"
        if raw_rounded >= float(thr["M3"]): return "M3"
        return "M4"



    # ------------------------------------------------------------------
    def apply_temperature(i) -> tuple[float, bool]:
        score       = float(t_logic.get("start_value", 1.0))
        has_missing = False

        # --- T1: Penetration depth ---
        pen_t1, miss_t1 = _eval_bins_largest_first(
            t_blocks["penetration_depth"]["bins"],
            pen_depth_s.at[i],
        )
        score += pen_t1
        has_missing = has_missing or miss_t1

        # --- T2: Number of T points ---
        pen_t2, miss_t2 = _eval_bins_largest_first(
            t_blocks["number_of_temperature_points"]["bins"],
            T_n_s.at[i],
        )
        score += pen_t2
        has_missing = has_missing or miss_t2

        # --- T3: Water depth ---
        bwt_tokens = _split_tokens(
            df.at[i, col_BWT_flag] if col_BWT_flag in df.columns else None
        )
        pen_t3, miss_t3 = 0.0, False
        if BWT_corrected_tok in bwt_tokens:
            # corrected → 0.0, no miss
            pass
        else:
            raw_elev = elev_s.at[i]
            if _is_nan(raw_elev):
                water_depth = float("nan")
            elif raw_elev >= 0:
                water_depth = float("nan")  # positive elevation → treat as missing
            else:
                water_depth = abs(float(raw_elev))

            pen_t3, miss_t3 = _eval_bins_largest_first(
                t_blocks["water_depth"]["bins"],
                water_depth,
            )
            score += pen_t3
            has_missing = has_missing or miss_t3

        # --- T4: Probe tilt ---
        tilt_flag_tokens = _split_tokens(
            df.at[i, col_tilt_flag] if col_tilt_flag in df.columns else None
        )
        pen_t4, miss_t4 = 0.0, False
        if tilt_corrected_tok in tilt_flag_tokens:
            # corrected → 0.0, no miss
            pass
        else:
            pen_t4, miss_t4 = _eval_bins_largest_first(
                t_blocks["probe_tilt"]["bins"],
                tilt_s.at[i],
            )
            score += pen_t4
            has_missing = has_missing or miss_t4

        # --- Debug print for temperature (same rows as conductivity) ---
        if 4950 <= i <= 4959:
            print(f"\n=== Row {i} — Temperature penalties ===")
            print(f"  Penetration depth (T1):  {pen_t1:+.1f}  (miss: {miss_t1})")
            print(f"  Number T points (T2):    {pen_t2:+.1f}  (miss: {miss_t2})")
            print(f"  Water depth (T3):        {pen_t3:+.1f}  (miss: {miss_t3})")
            print(f"  Probe tilt (T4):         {pen_t4:+.1f}  (miss: {miss_t4})")
            print(f"  Final T-score:           {score:.3f}")
            print(f"  Has missing (T):         {has_missing}")

        return score, has_missing
    # ------------------------------------------------------------------
    def apply_conductivity(i) -> tuple[float, bool]:
        score       = float(tc_logic.get("start_value", 1.0))
        has_missing = False

        def _tok(col):
            return _split_tokens(df.at[i, col] if col in df.columns else None)

        row_tokens = {
            "C41": _tok(col_tc_src),
            "C42": _tok(col_tc_loc),
            "C43": _tok(col_tc_method),
            "C44": _tok(col_tc_sat),
            "C45": _tok(col_tc_pt),
        }

        # --- Debug: print saturation tokens for rows 2830–2837 ---
        if 4950 <= i <= 4959:
            print(f"\n=== Row {i} — Saturation tokens ===")
            print(f"  C44 (saturation): {row_tokens['C44']}")
            print(f"  C43 (method):     {row_tokens['C43']}")
            print(f"  C41 (source):     {row_tokens['C41']}")

        # --- TC1: location ---
        pen_loc, miss_loc = _worst_matched_penalty(row_tokens["C42"], _loc_map)
        score += pen_loc
        has_missing = has_missing or miss_loc

        # --- TC2: saturation ---
        pen_sat, miss_sat = _eval_cases(
            tc_blocks["saturation"]["cases"],
            row_tokens,
        )
        score += pen_sat
        has_missing = has_missing or miss_sat

        # --- TC3: number of conductivities ---
        num_block = tc_blocks["number_of_conductivities"]
        ao = num_block.get("apply_only_if", {}).get("C42_tc_location")
        do_apply = True
        if ao:
            rhs = ao.get("value", "").strip().lower()
            op = ao.get("op", "!=")
            do_apply = (rhs not in row_tokens["C42"]) if op == "!=" else (rhs in row_tokens["C42"])

        pen_num, miss_num = 0.0, False
        if do_apply:
            pen_num, miss_num = _eval_bins_largest_first(num_block["bins"], tc_n_s.at[i])
            score += pen_num
            has_missing = has_missing or miss_num

        # --- TC4: pT conditions ---
        pen_pt, miss_pt = _eval_cases(
            tc_blocks["pT_conditions"]["cases"],
            row_tokens,
        )
        score += pen_pt
        has_missing = has_missing or miss_pt

        # --- Debug print for specific rows ---
        if 4950 <= i <= 4959:
            print(f"\n=== Row {i} — Conductivity penalties ===")
            print(f"  Location (C42):       {pen_loc:+.1f}  (miss: {miss_loc})")
            print(f"  Saturation (TC2):     {pen_sat:+.1f}  (miss: {miss_sat})")
            print(f"  Number cond. (TC3):   {pen_num:+.1f}  (miss: {miss_num})")
            print(f"  pT conditions (TC4):  {pen_pt:+.1f}  (miss: {miss_pt})")
            print(f"  Final TC-score:       {score:.3f}")
            print(f"  Has missing (TC):     {has_missing}")

        return score, has_missing

    # ────────────────────────────────────────────────────────────────
    # Debug collection (only if requested)
    t_scores_list = [] if return_debug else None
    tc_scores_list = [] if return_debug else None
    raw_list = [] if return_debug else None
    # ────────────────────────────────────────────────────────────────

    out: list[str] = []
    for i in df.index:
        t_score,  t_miss  = apply_temperature(i)
        tc_score, tc_miss = apply_conductivity(i)

        # Collect debug values
        if return_debug:
            t_scores_list.append(t_score)
            tc_scores_list.append(tc_score)
            raw  = float(t_score) * float(tc_score)
            raw_list.append(raw)

        raw = float(t_score) * float(tc_score)
        base = classify(raw)
        out.append(f"{base}{missing_suffix}" if (t_miss or tc_miss) else base)

    out_series = pd.Series(out, index=df.index, dtype="string")

    if return_debug:
        debug_dict = {
            "debug_t_score": pd.Series(t_scores_list, index=df.index, dtype=float),
            "debug_tc_score": pd.Series(tc_scores_list, index=df.index, dtype=float),
            "debug_raw_combined": pd.Series(raw_list, index=df.index, dtype=float),
        }
        return out_series, debug_dict
    else:
        return out_series




