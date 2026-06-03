import pandas as pd
import pytest

from vocab_check.apply_functional_check import add_range_and_allowed_flags


def _make_schema_for_ranges():
    # minimal schema dict for range tests (only what the checker needs)
    return {
        "columns": {
            "P4": {"dtype": "float64", "range": [-90.0, 90.0]},          # latitude
            "P5": {"dtype": "float64", "range": [-180.0, 180.0]},        # longitude
            "P6": {"dtype": "float64", "range": [-12000.0, 9000.0]},     # elevation
            "C4": {"dtype": "float64", "range": [0.0, 19999.9]},         # interval top
            "C5": {"dtype": "float64", "range": [0.0, 19999.9]},         # interval bottom
            "C27": {"dtype": "float64", "range": [-99999.99, 99999.99]}, # temp gradient (allows negative)
            "C37": {"dtype": "int64", "range": [0, 9999]},               # count
        }
    }


@pytest.mark.parametrize(
    "col,val,expected_out_of_range",
    [
        # -------- P4 latitude [-90, 90] --------
        ("P4", -90.0, False),
        ("P4", 90.0, False),
        ("P4", -90.0001, True),
        ("P4", 90.0001, True),

        # -------- P5 longitude [-180, 180] --------
        ("P5", -180.0, False),
        ("P5", 180.0, False),
        ("P5", -180.01, True),
        ("P5", 180.01, True),

        # -------- P6 elevation [-12000, 9000] --------
        ("P6", -12000.0, False),
        ("P6", 9000.0, False),
        ("P6", -12000.1, True),
        ("P6", 9000.1, True),

        # -------- C4 / C5 depth interval [0, 19999.9] --------
        ("C4", 0.0, False),
        ("C4", 19999.9, False),
        ("C4", -0.0001, True),
        ("C4", 20000.0, True),

        ("C5", 0.0, False),
        ("C5", 19999.9, False),
        ("C5", -1.0, True),
        ("C5", 25000.0, True),

        # -------- C27 gradient allows negative [-99999.99, 99999.99] --------
        ("C27", -99999.99, False),
        ("C27", 99999.99, False),
        ("C27", -100000.0, True),
        ("C27", 100000.0, True),

        # -------- C37 integer count [0, 9999] --------
        ("C37", 0, False),
        ("C37", 9999, False),
        ("C37", -1, True),
        ("C37", 10000, True),
    ],
)
def test_ranges_out_of_range_flags(col, val, expected_out_of_range):
    schema = _make_schema_for_ranges()

    df = pd.DataFrame({col: [val]})
    df_checked = add_range_and_allowed_flags(df, schema)

    # Adjust suffix if your implementation uses a different one
    flag_col = f"{col}__out_of_range"
    assert flag_col in df_checked.columns, f"Expected flag column '{flag_col}' to be created"

    assert bool(df_checked.loc[0, flag_col]) == expected_out_of_range


def test_ranges_missing_value_not_flagged():
    schema = _make_schema_for_ranges()

    df = pd.DataFrame({"P4": [pd.NA]})
    df_checked = add_range_and_allowed_flags(df, schema)

    flag_col = "P4__out_of_range"
    assert flag_col in df_checked.columns
    assert bool(df_checked.loc[0, flag_col]) is False
