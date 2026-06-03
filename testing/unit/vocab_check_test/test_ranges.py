import pandas as pd
import pytest
import numpy as np
from vocab_check.apply_functional_check import add_range_and_allowed_flags

@pytest.fixture
def mock_range_schema():
    return {
        "columns": {
            "P1": {"dtype": "float64", "range": [-999999.9, 999999.9]},
            "P2": {"dtype": "float64", "range": [0.0, 999999.9]},
            "P4": {"dtype": "float64", "range": [-90.0, 90.0]},
            "P5": {"dtype": "float64", "range": [-180.0, 180.0]},
            "P6": {"dtype": "float64", "range": [-12000.0, 9000.0]},
            "C4": {"dtype": "float64", "range": [0.0, 19999.9]},
            "C6": {"dtype": "float64", "range": [0.0, 999.9]},
            "C22": {"dtype": "float64", "range": [0.0, 99.99]},
            "C24": {"dtype": "float64", "range": [-273.15, 999.99]},
            "C27": {"dtype": "float64", "range": [-99999.99, 99999.99]},
            "C33": {"dtype": "float64", "range": [0, 99999.0]},
            "C47": {"dtype": "int64", "range": [0, 9999]},
            "C37": {"dtype": "int64", "range": [0, 999999]},
        }
    }


columns = [
    ("P1", "float64", -999999.9, 999999.9),
    ("P2", "float64", 0.0, 999999.9),
    ("P4", "float64", -90.0, 90.0),
    ("P5", "float64", -180.0, 180.0),
    ("P6", "float64", -12000.0, 9000.0),
    ("C4", "float64", 0.0, 19999.9),
    ("C6", "float64", 0.0, 999.9),
    ("C22", "float64", 0.0, 99.99),
    ("C24", "float64", -273.15, 999.99),
    ("C27", "float64", -99999.99, 99999.99),
    ("C33", "float64", 0, 99999.0),
    ("C47", "int64", 0, 9999),
    ("C37", "int64", 0, 999999),
]
# ---- Test: Valid values (check all columns) ----
@pytest.mark.parametrize(
    "col,dtype,min_val,max_val",
    columns,
    ids=[f"{col}-valid" for col, *_ in columns]
)
def test_valid_values(mock_range_schema, col, dtype, min_val, max_val):
    value = int((min_val + max_val) // 2) if "int" in dtype else (min_val + max_val) / 2
    df = pd.DataFrame({col: [value]})
    result = add_range_and_allowed_flags(df, mock_range_schema)

    flagged = [c for c in result.columns if "__" in c and result[c].iloc[0]]
    assert not flagged, f"{col}: Unexpected flags for valid value -> {flagged}"


# ---- Test: Out-of-range values (check all columns) ----
@pytest.mark.parametrize(
    "col,dtype,min_val,max_val",
    columns,
    ids=[f"{col}-range" for col, *_ in columns]
)
def test_out_of_range(mock_range_schema, col, dtype, min_val, max_val):
    out_val = max_val + 1 if "float" in dtype else max_val + 10
    df = pd.DataFrame({col: [out_val]})
    result = add_range_and_allowed_flags(df, mock_range_schema)

    assert f"{col}__out_of_range" in result.columns
    assert result[f"{col}__out_of_range"].iloc[0], f"{col}: Out-of-range not flagged"


# ---- Test: Wrong data types (only subset of columns) ----
@pytest.mark.parametrize(
    "col,dtype",
    [("P1", "float64"), ("C47", "int64"), ("C6", "float64")],
    ids=["P1-dtype", "C47-dtype", "C6-dtype"]
)
def test_wrong_dtype(mock_range_schema, col, dtype):
    wrong_val = "not_a_number" if "float" in dtype else 1.234
    df = pd.DataFrame({col: [wrong_val]})
    result = add_range_and_allowed_flags(df, mock_range_schema)

    assert f"{col}__invalid_dtype" in result.columns
    assert result[f"{col}__invalid_dtype"].iloc[0], f"{col}: Wrong dtype not flagged"


# ---- Test: Missing / NaN values (only subset of columns) ----
@pytest.mark.parametrize(
    "col",
    ["P2", "C4", "C47"],
    ids=["P2-missing", "C4-missing", "C47-missing"]
)
def test_missing_value(mock_range_schema, col):
    df = pd.DataFrame({col: [np.nan]})
    result = add_range_and_allowed_flags(df, mock_range_schema)

    flagged = [
        c for c in result.columns
        if result[c].iloc[0] and ("__out_of_range" in c or "__invalid_dtype" in c)
    ]
    assert not flagged, f"{col}: NaN incorrectly flagged -> {flagged}"