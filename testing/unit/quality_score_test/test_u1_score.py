import pandas as pd

from quality_score.apply_u_quality_score import calculate_u_score


import pandas as pd
import pytest
from quality_score.apply_u_quality_score import calculate_u_score


def _qc_schema_u(value_col="C1", unc_col="C2", U1=5.0, U2=15.0, U3=25.0):
    return {
        "u_score": {
            "calculation": {"value_col": value_col, "uncertainty_col": unc_col},
            "thresholds": {"U1": U1, "U2": U2, "U3": U3, "U4": 100.0, "Ux": "missing"},
        }
    }


def test_u_score_schema_column_names_respected():
    schema = _qc_schema_u(value_col="VAL", unc_col="UNC")
    df = pd.DataFrame({"VAL": [100.0], "UNC": [20.0]})  # cov=20 → U3
    assert calculate_u_score(df, schema).iloc[0] == "U3"


# --- U1: cov < 5 ---

def test_u1_well_inside():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [2.0]})  # cov=2 < 5 → U1
    assert calculate_u_score(df, schema).iloc[0] == "U1"

def test_u1_just_below_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [4.9]})  # cov=4.9 < 5 → U1
    assert calculate_u_score(df, schema).iloc[0] == "U1"


# --- U2: 5 ≤ cov ≤ 15 ---

def test_u2_exact_lower_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [5.0]})  # cov=5.0 → U2
    assert calculate_u_score(df, schema).iloc[0] == "U2"

def test_u2_well_inside():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [10.0]})  # cov=10 → U2
    assert calculate_u_score(df, schema).iloc[0] == "U2"

def test_u2_exact_upper_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [15.0]})  # cov=15.0 → U2
    assert calculate_u_score(df, schema).iloc[0] == "U2"


# --- U3: 15 < cov ≤ 25 ---

def test_u3_just_above_lower_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [15.1]})  # cov=15.1 → U3
    assert calculate_u_score(df, schema).iloc[0] == "U3"

def test_u3_well_inside():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [20.0]})  # cov=20 → U3
    assert calculate_u_score(df, schema).iloc[0] == "U3"

def test_u3_exact_upper_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [25.0]})  # cov=25.0 → U3
    assert calculate_u_score(df, schema).iloc[0] == "U3"


# --- U4: cov > 25 ---

def test_u4_just_above_boundary():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [25.1]})  # cov=25.1 → U4
    assert calculate_u_score(df, schema).iloc[0] == "U4"

def test_u4_well_inside():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [30.0]})  # cov=30 → U4
    assert calculate_u_score(df, schema).iloc[0] == "U4"


# --- Ux: missing / zero ---

def test_ux_c2_missing():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [100.0], "C2": [None]})  # C2 empty → Ux
    assert calculate_u_score(df, schema).iloc[0] == "Ux"

def test_ux_c1_missing():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [None], "C2": [10.0]})  # C1 missing → Ux
    assert calculate_u_score(df, schema).iloc[0] == "Ux"

def test_ux_c1_zero():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [0.0], "C2": [10.0]})  # div by zero → Ux
    assert calculate_u_score(df, schema).iloc[0] == "Ux"

def test_ux_both_missing():
    schema = _qc_schema_u()
    df = pd.DataFrame({"C1": [None], "C2": [None]})  # both missing → Ux
    assert calculate_u_score(df, schema).iloc[0] == "Ux"

