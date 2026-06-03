import pandas as pd

from quality_score.apply_m_quality_score_borehole import calculate_m_score_borehole


# Ordnung für Vergleich (höher = besser)
_ORDER = {
    "M1": 4, "M2": 3, "M3": 2, "M4": 1,
    "M1x": 4, "M2x": 3, "M3x": 2, "M4x": 1,
}


def test_borehole_smoke_real_schema(quality_score_schema):
    """
    Smoke test: real schema, fully populated row, must return valid M-score.
    """
    qc = quality_score_schema

    df = pd.DataFrame([{
        # temperature
        "C31": "[logeq]",
        "C32": "[logeq]",
        "C37": 10,

        # conductivity gate
        "C4": 100.0,
        "C5": 200.0,

        # conductivity blocks
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 10,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_borehole(df, qc).iloc[0]
    assert out in _ORDER


def test_borehole_continuous_log_case_selected(quality_score_schema):
    """
    C37 > 3 and LOGeq => continuous_log case must apply.
    """
    qc = quality_score_schema

    df = pd.DataFrame([{
        "C31": "[logeq]",
        "C32": "[logeq]",
        "C37": 8,

        "C4": 100.0,
        "C5": 200.0,
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 10,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_borehole(df, qc).iloc[0]
    assert out.startswith("M")  # classification worked


def test_borehole_surface_plus_single_point_case(quality_score_schema):
    """
    C31 == [SUR] triggers one_single_point_plus_surface_T case.
    """
    qc = quality_score_schema

    df = pd.DataFrame([{
        "C31": "[sur]",          # surface
        "C32": "[cbht]",
        "C37": 1,

        "C4": 100.0,
        "C5": 200.0,
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 2,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_borehole(df, qc).iloc[0]
    assert out in _ORDER


def test_borehole_temperature_multi_entry_uses_worst_penalty(quality_score_schema):
    """
    CORE TEST:
    Multiple temperature methods => worst (most negative) penalty must be applied.
    """
    qc = quality_score_schema

    # GOOD only
    df_good = pd.DataFrame([{
        "C31": "[logeq]",
        "C32": "[logeq]",
        "C37": 5,

        "C4": 100.0,
        "C5": 200.0,
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 5,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    # GOOD + WORSE
    df_bad = pd.DataFrame([{
        "C31": "[logeq];[logpert]",   # perturbed included
        "C32": "[logeq]",
        "C37": 5,

        "C4": 100.0,
        "C5": 200.0,
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 5,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out_good = calculate_m_score_borehole(df_good, qc).iloc[0]
    out_bad = calculate_m_score_borehole(df_bad, qc).iloc[0]

    # multi-entry must never improve score
    assert _ORDER[out_bad] <= _ORDER[out_good]


def test_borehole_missing_gate_triggers_x_suffix(quality_score_schema):
    """
    Missing C4/C5 => gate_interval_depth_reported => fixed score + 'x'.
    """
    qc = quality_score_schema

    df = pd.DataFrame([{
        "C31": "[logeq]",
        "C32": "[logeq]",
        "C37": 5,

        # missing C4 / C5
        "C42": "[actual-heat-flow-location]",
        "C41": "[in-situ-probe]",
        "C47": 5,
        "C44": "[saturated-measured]",
        "C45": "[actual-in-situ-(pt)-conditions]",
    }])

    out = calculate_m_score_borehole(df, qc).iloc[0]
    assert out.endswith("x")


def test_borehole_explicit_unspecified_does_not_force_x(quality_score_schema):
    """
    Explicit [unspecified] should apply penalty but NOT force suffix x.
    """
    qc = quality_score_schema

    df = pd.DataFrame([{
        "C31": "[unspecified]",
        "C32": "[unspecified]",
        "C37": 5,

        "C4": 100.0,
        "C5": 200.0,
        "C42": "[literature/unspecified]",
        "C41": "[unspecified]",
        "C47": 1,
        "C44": "[unspecified]",
        "C45": "[unspecified]",
    }])

    out = calculate_m_score_borehole(df, qc).iloc[0]
    assert not out.endswith("x")
