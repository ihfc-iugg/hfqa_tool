# quality_score/apply_m_quality_score_borehole.py
from __future__ import annotations

import math
from typing import Any

import pandas as pd

_SEPS = (";", ",")


def _is_nan(x: Any) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _col_as_num(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Safe numeric column accessor:
    - if col missing → all-NaN series
    - else → numeric coercion
    """
    if col not in df.columns:
        return pd.Series([math.nan] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def _split_tokens(cell: Any) -> set[str]:
    """
    Parse multi-entry cells into a set of canonical tokens.
    Only strip + lower + separator splitting 
    """
    if _is_nan(cell):
        return set()

    if isinstance(cell, (list, tuple, set)):
        return {str(v).strip().lower() for v in cell if not _is_nan(v) and str(v).strip()}

    s = str(cell).strip().lower()
    if not s or s == "nan":
        return set()

    for sep in _SEPS[1:]:
        s = s.replace(sep, _SEPS[0])
    parts = [p.strip() for p in s.split(_SEPS[0])]
    return {p for p in parts if p}


def _eval_when(cond: Any, cell_value: Any) -> bool:
    """
    Evaluate schema condition:
    - {op, value}: numeric or token compare
    Assumes canonical tokens.
    """
    if cond is None:
        return False
    if isinstance(cond, dict) and "op" in cond and "value" in cond:
        op = str(cond["op"]).strip()
        rhs = cond["value"]

        # Numeric comparison
        if isinstance(rhs, (int, float)) and not _is_nan(rhs):
            if _is_nan(cell_value):
                return False
            try:
                lhs = float(cell_value)
                rhsf = float(rhs)
            except Exception:
                return False
            if op == ">":   return lhs > rhsf
            if op == ">=":  return lhs >= rhsf
            if op == "<":   return lhs < rhsf
            if op == "<=":  return lhs <= rhsf
            if op == "==":  return lhs == rhsf
            if op == "!=":  return lhs != rhsf
            return False

        # Token/string comparison
        rhs_s = str(rhs).strip().lower()
        lhs_tokens = _split_tokens(cell_value)
        if op == "==":
            return rhs_s in lhs_tokens
        if op == "!=":
            return rhs_s not in lhs_tokens
        return False

    return False


def _worst_matched_penalty(tokens: set[str], mapping: dict[str, float]) -> tuple[float, bool]:
    """
    For flat mapping blocks (currently only location):
    - matched → min penalty, missing=False
    - no match → worst penalty + missing=True
    """
    matched = [float(mapping[t]) for t in tokens if t in mapping]
    if matched:
        return min(matched), False
    worst = min(float(v) for v in mapping.values())
    return worst, True


def _eval_cases(
    cases: list[dict],
    row_tokens: dict[str, set[str]],
    i: int = None,
) -> tuple[float, bool]:
    """
    Evaluates case-based blocks (source_type, saturation, pT_conditions).
    Collects ALL matching cases and returns the worst (min) penalty.
    Fallback (empty when: {}) only used if nothing else matched.
    Returns (penalty, missing_flag)
    """
    required_fields = set()
    for case in cases:
        when = case.get("when", {})
        if when:  # only non-fallback cases contribute to required fields
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
        if not when:  # skip fallback cases in main loop
            continue
        match = True
        for field, condition in when.items():
            if field.endswith("_any"):
                col = field[:-4]
                tokens = row_tokens.get(col, set())
                values = set(str(v).strip().lower() for v in condition)
                if not tokens & values:
                    match = False
                    break
            else:
                col = field
                tokens = row_tokens.get(col, set())
                val = str(condition).strip().lower()
                if val not in tokens:
                    match = False
                    break
        if match:
            if i is not None and 80501 <= i <= 80520:
                print(f"Row {i} MATCHED {case.get('label', 'unnamed')} (penalty {case['penalty']})")
            matched_penalties.append(float(case["penalty"]))

    if matched_penalties:
        return min(matched_penalties), False  # worst = most negative

    # No match → check fallback (empty when: {})
    for case in cases:
        if not case.get("when", {}):
            return float(case["penalty"]), False

    # No match, no fallback → worst penalty, no missing flag
    worst = min(float(case["penalty"]) for case in cases)
    return worst, False

def _eval_bin(val: float, op: str, threshold: float) -> bool:
    if op == ">":   return val > threshold
    if op == ">=":  return val >= threshold
    if op == "<":   return val < threshold
    if op == "<=":  return val <= threshold
    if op == "==":  return val == threshold
    return False


def _eval_bins_largest_first(bins: dict, value: Any) -> tuple[float, bool]:
    """
    Evaluate numeric bins largest-threshold-first.
    Returns (penalty, missing_flag)
    """
    if _is_nan(value):
        if not bins:
            return 0.0, True
        worst = min(float(b["penalty"]) for b in bins.values())
        return worst, True

    try:
        fval = float(value)
    except (TypeError, ValueError):
        worst = min(float(b["penalty"]) for b in bins.values())
        return worst, True

    # Sort bins descending by threshold
    sorted_bins = sorted(
        bins.items(),
        key=lambda item: float(item[1].get("when", {}).get("value", 0)),
        reverse=True,
    )

    for _, bin_def in sorted_bins:
        cond = bin_def.get("when", {})
        op = cond.get("op", "")
        thresh = float(cond.get("value", 0))
        if _eval_bin(fval, op, thresh):
            return float(bin_def["penalty"]), False

    # No match → worst + no missing
    worst = min(float(b["penalty"]) for b in bins.values())
    return worst, False


def calculate_m_score_borehole(
    df: pd.DataFrame,
    qc_schema: dict,
    return_debug: bool = False
) -> pd.Series | tuple[pd.Series, dict]:
    """
    Borehole-only M-score.
    Assumes df values already normalized upstream.
    """
    m_cfg = qc_schema["m_score"]
    calc = m_cfg["calculation"]
    thr = m_cfg["thresholds"]
    missing_suffix = str(thr.get("missing_suffix", "x"))

    # Columns
    col_T_top = calc["t_method_top_col"]        # C31
    col_T_bot = calc["t_method_bottom_col"]     # C32
    col_T_n   = calc["t_number_col"]            # C37

    col_q_top = calc["q_top_col"]               # C4
    col_q_bot = calc["q_bottom_col"]            # C5

    col_tc_loc = calc["tc_location_col"]        # C42
    col_tc_src = calc["tc_source_col"]          # C41
    col_tc_n   = calc["tc_number_col"]          # C47
    col_tc_sat = calc["tc_saturation_col"]      # C44
    col_tc_pt  = calc["tc_pT_conditions_col"]   # C45

    # Numeric series
    T_n   = _col_as_num(df, col_T_n)
    q_top = _col_as_num(df, col_q_top)
    q_bot = _col_as_num(df, col_q_bot)
    tc_n  = _col_as_num(df, col_tc_n)

    bh = m_cfg["borehole_logic"]
    t_logic = bh["temperature"]
    tc_logic = bh["conductivity"]

    t_cases = t_logic["cases"]
    tc_blocks = tc_logic["blocks"]

    # Canonical tokens
    sur_tok = "[sur]"

    def classify(raw: float) -> str:
        if _is_nan(raw):
            return "M4"
        raw = round(float(raw), 3)
        if raw >= float(thr["M1"]):
            return "M1"
        if raw >= float(thr["M2"]):
            return "M2"
        if raw >= float(thr["M3"]):
            return "M3"
        return "M4"

    def _worst_rule_penalty(
        top: set[str],
        bot: set[str],
        rules: dict,
        methods_key: str = "methods_any_of",
        match_bot_only: bool = False,
    ) -> tuple[float | None, bool]:
        matched_penalties = []
        for _, rule in rules.items():
            methods = {str(x).strip().lower() for x in rule.get(methods_key, [])}
            if not methods:
                continue
            if match_bot_only:
                if bot & methods:
                    matched_penalties.append(float(rule["penalty"]))
            else:
                if (top & methods) or (bot & methods):
                    matched_penalties.append(float(rule["penalty"]))

        if not matched_penalties:
            return None, True
        return min(matched_penalties), False

    def apply_temperature(i) -> tuple[float, bool]:
        score = float(t_logic.get("start_value", 1.0))
        has_missing = False

        top = _split_tokens(df.at[i, col_T_top]) if col_T_top in df.columns else set()
        bot = _split_tokens(df.at[i, col_T_bot]) if col_T_bot in df.columns else set()
        nT = T_n.at[i]

        if 90550 <= i <= 90575:
            site_name = df.at[i, "P3"] if "P3" in df.columns else "P3 missing"  
            print(f"\n=== Row {i} — Borehole TEMPERATURE debug ===")
            raw_c11 = df.at[i, calc.get('corr_IS_flag_col', 'C11')]
            print(f"Row {i} — RAW C11 value: {raw_c11!r}")
            print(f"  Site:                 {site_name}")
            print(f"  C37 (T number):       {df.at[i, col_T_n]!r}")
            print(f"  C31 (T method top):   {df.at[i, col_T_top]!r}")
            print(f"  C32 (T method bottom):{df.at[i, col_T_bot]!r}")
            print(f"  Tokens top:           {top}")
            print(f"  Tokens bot:           {bot}")

        # Case 3: one single point + surface T
        case3 = t_cases["one_single_point_plus_surface_T"]
        case3_when = case3.get("when", {}).get("C31_T_method_top")
        cell_top = df.at[i, col_T_top] if col_T_top in df.columns else None
        is_case3 = _eval_when(case3_when, cell_top) if case3_when else (sur_tok in top)

        if is_case3:
            rules = case3["rules"]
            pen, miss = _worst_rule_penalty(top, bot, rules, "C32_methods_any_of", match_bot_only=True)
            if pen is None:
                score += min(float(r["penalty"]) for r in rules.values())
                has_missing = True
            else:
                score += pen
                has_missing |= miss
            return score, has_missing

        # Case 1: continuous log
        cont_case = t_cases["continuous_log"]
        cond = cont_case.get("when", {}).get("C37_T_number")
        c37_ok = _eval_when(cond, nT) if cond else ((not pd.isna(nT)) and (float(nT) > 3.0))

        cont_rules = cont_case.get("rules", {})
        cont_methods = set()
        for rule in cont_rules.values():
            cont_methods |= {str(x).strip().lower() for x in rule.get("methods_any_of", [])}

        has_cont_method = bool((top | bot) & cont_methods)
        non_cont_tokens = (top | bot) - cont_methods
        has_non_cont = bool(non_cont_tokens)
        is_cont = c37_ok and has_cont_method and not has_non_cont

        if is_cont:
            pen, miss = _worst_rule_penalty(top, bot, cont_rules)
            if pen is None:
                score += min(float(r["penalty"]) for r in cont_rules.values())
                has_missing = True
            else:
                score += pen
                has_missing |= miss
            return score, has_missing

        # Case 2: multiple single T points (default)
        case2 = t_cases["multiple_single_T_points"]
        rules = case2["rules"]
        pen, miss = _worst_rule_penalty(top, bot, rules)
        if pen is None:
            score += min(float(r["penalty"]) for r in rules.values())
            has_missing = True  
        else:
            score += pen
            has_missing |= miss

        return score, has_missing

    def apply_conductivity(i) -> tuple[float, bool]:
        score = float(tc_logic.get("start_value", 1.0))
        has_missing = False

        if 80501 <= i <= 80520:    
            site_name = df.at[i, "P3"] if "P3" in df.columns else "P3 missing" 
            print(f"\n=== Row {i} — Borehole CONDUCTIVITY debug ===")
            raw_c11 = df.at[i, calc.get('corr_IS_flag_col', 'C11')]
            print(f"Row {i} — RAW C11 value: {raw_c11!r}")
            print(f"  Site:             {site_name}")
            print(f"  Gate: q_top = {df.at[i, col_q_top]!r}, q_bot = {df.at[i, col_q_bot]!r}")
            print(f"  C42 (location):   {df.at[i, col_tc_loc]!r}")
            print(f"  C41 (source):     {df.at[i, col_tc_src]!r}")
            print(f"  C47 (number):     {df.at[i, col_tc_n]!r}")
            print(f"  C44 (saturation): {df.at[i, col_tc_sat]!r}")
            print(f"  C45 (pT):         {df.at[i, col_tc_pt]!r}")
            print(f"  C11 (corr_IS):    {df.at[i, calc.get('corr_IS_flag_col', 'C11')]!r}")

        # Gate: both q_top and q_bot missing → fixed TC + x
        if _is_nan(q_top.at[i]) and _is_nan(q_bot.at[i]):
            fixed = float(tc_logic["gate_interval_depth_reported"]["if_missing"]["tc_score_fixed"])
            return fixed, True

        # Token sets
        loc = _split_tokens(df.at[i, col_tc_loc]) if col_tc_loc in df.columns else set()
        src = _split_tokens(df.at[i, col_tc_src]) if col_tc_src in df.columns else set()
        sat = _split_tokens(df.at[i, col_tc_sat]) if col_tc_sat in df.columns else set()
        pt  = _split_tokens(df.at[i, col_tc_pt])  if col_tc_pt  in df.columns else set()
        nC  = tc_n.at[i]

        # C11 for pT_conditions (corr_IS_flag)
        col_corr_is = calc.get("corr_IS_flag_col", "C11")
        corr_is = _split_tokens(df.at[i, col_corr_is]) if col_corr_is in df.columns else set()

        # Block 1: location (still flat mapping)
        loc_map = {k.strip().lower(): float(v) for k, v in tc_blocks["location"]["mapping"].items()}  # ← changed here
        pen, miss = _worst_matched_penalty(loc, loc_map)
        score += pen
        has_missing |= miss

        # Block 2: source_type (cases)
        pen, miss = _eval_cases(
            tc_blocks["source_type"]["cases"],  # ← changed here
            {"C41": src},
            i=i
        )
        score += pen
        has_missing |= miss

        # Block 3: number_of_conductivities (bins)
        num_block = tc_blocks["number_of_conductivities"]  # ← changed here
        ao = num_block.get("apply_only_if", {}).get("C42_tc_location")
        do_apply = True
        if ao:
            rhs = ao.get("value", "").strip().lower()
            op = ao.get("op", "!=")
            do_apply = (rhs not in loc) if op == "!=" else (rhs in loc)

        if do_apply:
            pen_num, miss_num = _eval_bins_largest_first(num_block["bins"], nC)
            score += pen_num
            has_missing |= miss_num

        # Block 4: saturation (cases)
        pen, miss = _eval_cases(
            tc_blocks["saturation"]["cases"], 
            {"C44": sat},
            i=i
        )
        score += pen
        has_missing |= miss

        # Block 5: pT conditions (cases)
        pen, miss = _eval_cases(
            tc_blocks["pT_conditions"]["cases"],  
            {"C45": pt, "C11": corr_is},
            i=i
        )
        score += pen
        has_missing |= miss

        return score, has_missing
    # ────────────────────────────────────────────────────────────────
    # Main loop
    # ────────────────────────────────────────────────────────────────
    out: list[str] = []
    t_scores_list = [] if return_debug else None
    tc_scores_list = [] if return_debug else None
    raw_list = [] if return_debug else None

    for i in df.index:
        t_score, t_missing = apply_temperature(i)
        tc_score, tc_missing = apply_conductivity(i)

        if return_debug:
            t_scores_list.append(t_score)
            tc_scores_list.append(tc_score)
            raw = float(t_score) * float(tc_score)
            raw_list.append(raw)

        raw = float(t_score) * float(tc_score)
        base = classify(raw)
        out.append(f"{base}{missing_suffix}" if (t_missing or tc_missing) else base)

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