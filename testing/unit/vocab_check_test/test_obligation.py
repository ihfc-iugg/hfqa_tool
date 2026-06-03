import pandas as pd
import numpy as np
import pytest
from vocab_check.apply_functional_check import add_mandatory_flags

@pytest.fixture
def mock_obligation_schema():
    return {
        "columns": {
            "P1": {"obligation": "M"},
            "C22": {"obligation": "R"},
            "C24": {"obligation": "O"},
            "A1": {"obligation": "-"},
        }
    }

@pytest.mark.parametrize(
    "col, value, should_flag, should_have_column",
    [
        # ---- MANDATORY: Missing should be flagged, column should exist ----
        ("P1", np.nan, True, True),
        ("P1", 123, False, True),

        # ---- RELEVANT/OPTIONAL/ADMIN: No flag, column should NOT exist ----
        ("C22", np.nan, False, False),
        ("C22", 123, False, False),
        ("C24", np.nan, False, False),
        ("C24", 123, False, False),
        ("A1", np.nan, False, False),
        ("A1", 123, False, False),
    ],
)
def test_obligation_flagging(mock_obligation_schema, col, value, should_flag, should_have_column):
    df = pd.DataFrame({col: [value]})
    result = add_mandatory_flags(df, mock_obligation_schema)
    flag_col = f"{col}__missing"

    if should_have_column:
        assert flag_col in result.columns, f"{col}: Expected missing flag column"
        assert result[flag_col].iloc[0] == should_flag, f"{col}: Flag value incorrect"
    else:
        assert flag_col not in result.columns, f"{col}: Missing flag column should NOT exist"