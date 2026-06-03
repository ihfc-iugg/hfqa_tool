import pytest
import pandas as pd
import numpy as np
from vocab_check.apply_functional_check import add_range_and_allowed_flags



@pytest.fixture
def schema_mock_allowed():
    return {
        "columns": {
            "C9": {
                "allowed": ["[Yes]", "[No]"],
                "dtype": "string",
                "multi_choice": False,
            },
            "C11": {
                "allowed": [
                    "[Considered - p]",
                    "[Considered - T]",
                    "[Considered - pT]",
                    "[Not considered]",
                    "[unspecified]"
                ],
                "dtype": "string",
                "multi_choice": True,
                "separator": ";"
            },
            "C25": {
                "allowed": [
                    "granite", "limestone", "basalt", "sandstone", "coal", "igneous rock"
                ],
                "dtype": "string",
                "multi_choice": True,
                "separator": ";"
            },
            "C49": {
                "dtype": "string"
            }
        }
    }



@pytest.fixture
def mock_allowed_entry_values():
    return pd.DataFrame({
        "row_type": ["data"] * 10,

        "C9": [
            "[Yes]", "[No]", "[Maybe]", "[unspecified]",
            "", np.nan, "NA", "[Other]", "[Yes];[No]", 123 #  "[Yes]", "[No]", np.nan allowed 
        ],

        "C11": [
            "[Considered - T];[Not considered]", #True
            "[Invalid];[Considered - T]", #Not valid 
            "[unspecified]", #True
            "[Other (specify in comments)]", # Not true
            "[Considered - p];[Maybe];[unspecified]", # Not true
            np.nan, "", "NA", # Not true
            "[Considered - pT]; [Not considered]",# True
            123 # Not true
        ],

        "C25": [
            "granite;limestone",
            "granite;unknown",
            "basalt",
            "", np.nan,
            "sandstone;basalt;coal",
            "sandstone;somethingelse",
            "igneous rock",
            "granite ; limestone",
            ["granite", "limestone"]
        ],

        "C49": [
            "IGSN001", "sample-123", "", np.nan, None,
            123, 12.5, True, ["text"], {"a": "b"}
        ]
    })
def test_multichoice_splitting_and_validation():
    schema = {
        "columns": {
            "C11": {
                "allowed": [
                    "[considered - p]",
                    "[considered - t]",
                    "[considered - pt]",
                    "[not considered]",
                    "[unspecified]",
                ],
                "dtype": "string",
                "multi_choice": True,
                "separator": ";"
            }
        }
    }

    df = pd.DataFrame({
        "row_type": ["data"] * 3,
        "C11": [
            "[Considered - p];[Not considered]",  # all valid
            "[Not considered];[Invalid]",         # 1 invalid
            "[Invalid];[Wrong]"                   # both invalid
        ]
    })

    df_out = add_range_and_allowed_flags(df, schema)

    print(df_out[["C11", "C11__invalid"]])
    expected = [False, True, True]
    actual = df_out["C11__invalid"].tolist()

    assert actual == expected, f"Expected {expected}, but got {actual}"


@pytest.mark.parametrize(
    "column, flag, expected_count",
    [
        ("C9", "invalid", 7),             # bad string values, NA, 123
        ("C11", "invalid", 5),            # invalid multi-choice values
        ("C25", "invalid", 3),            # unknown entries, non-strings
        ("C49", "invalid_dtype", 5),      # non-string types
    ],
    ids=[
        "C9-invalid-values",
        "C11-multiselect-invalid",
        "C25-invalid-geology",
        "C49-string-type-check"
    ]
)
def test_allowed_flags(mock_allowed_entry_values, schema_mock_allowed, column, flag, expected_count):
    df = add_range_and_allowed_flags(mock_allowed_entry_values, schema_mock_allowed)
    actual = df[f"{column}__{flag}"].sum()
    assert actual == expected_count, f"{column}: expected {expected_count} but got {actual}"
