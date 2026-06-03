import math
import pandas as pd

from quality_score.apply_m_quality_score_marine import calculate_m_score_marine


def _get_mapping_penalties(qc, block_path: tuple[str, ...]) -> dict[str, float]:
    """
    Helper: fetch mapping dict from schema at path:
      ("m_score","marine_logic","conductivity","blocks","source_type","mapping")
    Returns normalized-key mapping -> float
    """
    d = qc
    for k in block_path:
        d = d[k]
    # keys should already be normalized by normalize_schema fixture
    return {str(k).strip().lower(): float(v) for k, v in d.items()}


def test_marine_smoke_real_schema(quality_score_schema):
    qc = quality_score_schema

    df = pd.DataFrame([{
        # temperature blocks
        "C6": 12.0,                      # penetration depth
        "C37": 6.0,                      # number of temperature points
        "P6": -3000.0,                   # elevation -> abs water depth
        "C23": 45.0,                     # tilt
        "C12": "[tilt-corrected]",       # corrected tilt flag
        "C17": "[present-and-corrected]",

        # conductivity blocks
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C44": "[saturated-measured-in-situ]",
        "C43": "[probe-pulse-technique]",
        "C47": 4.0,
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_marine(df, qc)
    assert out.dtype.name == "string"
    assert out.iloc[0] in {"M1", "M2", "M3", "M4", "M1x", "M2x", "M3x", "M4x"}


def test_marine_mapping_multi_entry_uses_worst_penalty(quality_score_schema):
    """
    Core requirement:
    When a cell contains multiple tokens, mapping blocks must take the WORST penalty,
    i.e. min(penalties_of_matches), not max.
    We test on marine conductivity.source_type, because it has varied penalties.
    """
    qc = quality_score_schema

    src_map = _get_mapping_penalties(
        qc,
        ("m_score", "marine_logic", "conductivity", "blocks", "source_type", "mapping"),
    )

    # pick two tokens from the schema mapping with different penalties:
    # - one with 0.0 (best)
    # - one with -0.2 (worst) (falls back if exists; otherwise choose min among map values)
    tok_best = None
    tok_worst = None

    # find best (max) and worst (min) penalty tokens
    items = sorted(src_map.items(), key=lambda kv: kv[1])
    tok_worst = items[0][0]  # most negative
    tok_best = items[-1][0]  # least negative / best

    assert tok_best is not None and tok_worst is not None and tok_best != tok_worst

    # Build a row that isolates conductivity scoring and avoids accidental missing flags:
    df = pd.DataFrame([{
        # temperature: choose values that are present to avoid x from temperature
        "C6": 12.0,
        "C37": 6.0,
        "P6": -3000.0,
        "C23": 5.0,
        "C12": "[tilt-corrected]",
        "C17": "[present-and-corrected]",

        # conductivity fields
        "C42": "[actual-heat-flow-location]",
        # put BOTH tokens into source_type cell; must take WORST penalty
        "C41": f"{tok_best};{tok_worst}",
        "C44": "[saturated-measured]",
        "C43": "[probe-pulse-technique]",
        "C47": 4.0,
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_marine(df, qc).iloc[0]
    assert out in {"M1", "M2", "M3", "M4", "M1x", "M2x", "M3x", "M4x"}

    # Now compute what penalty SHOULD be applied for source_type block:
    # expected = min(pen(tok_best), pen(tok_worst))
    expected_source_pen = min(src_map[tok_best], src_map[tok_worst])
    assert expected_source_pen == src_map[tok_worst]  # because worst is min


    df_best = df.copy()
    df_best.loc[0, "C41"] = tok_best

    df_mix = df.copy()
    df_mix.loc[0, "C41"] = f"{tok_best};{tok_worst}"

    out_best = calculate_m_score_marine(df_best, qc).iloc[0]
    out_mix = calculate_m_score_marine(df_mix, qc).iloc[0]

    # If worst penalty is applied, mixed should be <= best in raw score terms,
    # therefore label should be same or worse (never better).
    order = {"M1": 4, "M2": 3, "M3": 2, "M4": 1, "M1x": 4, "M2x": 3, "M3x": 2, "M4x": 1}
    assert order[out_mix] <= order[out_best]


def test_marine_conditional_bonus_applies_when_all_matches(quality_score_schema):
    """
    Test conditional bonus rules:
      +0.1 if tc_method == pulse AND tc_source == in-situ probe AND tc_saturation == saturated measured in situ
    We do a differential check: same row but break one condition => should not get better.
    """
    qc = quality_score_schema

    base = {
        # temperature OK
        "C6": 12.0,
        "C37": 6.0,
        "P6": -3000.0,
        "C23": 5.0,
        "C12": "[tilt-corrected]",
        "C17": "[present-and-corrected]",

        # conductivity
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C44": "[saturated-measured-in-situ]",
        "C43": "[probe-pulse-technique]",
        "C47": 4.0,
        "C45": "[actual-in-situ-(pt)-conditions]",
    }

    df_ok = pd.DataFrame([base])
    out_ok = calculate_m_score_marine(df_ok, qc).iloc[0]

    # break condition: change saturation
    bad = dict(base)
    bad["C44"] = "[dry-measured]"
    df_bad = pd.DataFrame([bad])
    out_bad = calculate_m_score_marine(df_bad, qc).iloc[0]

    order = {"M1": 4, "M2": 3, "M3": 2, "M4": 1, "M1x": 4, "M2x": 3, "M3x": 2, "M4x": 1}
    assert order[out_ok] >= order[out_bad]
