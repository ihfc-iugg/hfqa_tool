import pandas as pd
import pytest
from etl.normalization_utils import (
    normalize_bracketed_token_series,
    normalize_token,
    normalize_token_list,
)

# -------------------------------
# Tests for normalize_bracketed_token_series
# -------------------------------

@pytest.mark.parametrize("input_val, expected", [
    ("[Yes];[No]", "[yes];[no]"),
    ("Yes;No", "[yes];[no]"),
    ("yes;no", "[yes];[no]"),
    ("[Yes]", "[yes]"),
    ("  [Yes ] ;  No ", "[yes];[no]"),
    (None, pd.NA),
    ("", pd.NA),
])
def test_normalize_bracketed_token_series(input_val, expected):
    s = pd.Series([input_val], dtype="string")
    result = normalize_bracketed_token_series(s).iloc[0]
    if pd.isna(expected):
        assert pd.isna(result)
    else:
        assert result == expected


def test_normalize_bracketed_token_series_already_bracketed():
    s = pd.Series(["[Already-Formatted];[Second-Entry]"], dtype="string")
    result = normalize_bracketed_token_series(s).iloc[0]
    expected = "[already-formatted];[second-entry]"
    assert result == expected


# -------------------------------
# Tests for normalize_token
# -------------------------------

@pytest.mark.parametrize("input_val, expected", [
    ("[Yes]", "[yes]"),
    (" Yes ", "yes"),
    ("[Untrimmed / text]", "[untrimmed-text]"),
    (None, ""),
    ("", ""),
])
def test_normalize_token(input_val, expected):
    assert normalize_token(input_val) == expected


@pytest.mark.parametrize("input_val, expected", [
    ("[Already-Bracketed]", "[already-bracketed]"),
    ("[With / Separators]", "[with-separators]"),
    ("[Extra   spaces]", "[extra-spaces]"),
])
def test_normalize_token_already_bracketed_variants(input_val, expected):
    assert normalize_token(input_val) == expected


# -------------------------------
# Tests for normalize_token_list
# -------------------------------

def test_normalize_token_list_basic():
    vals = ["[Yes]", "No", "Maybe"]
    expected = ["[yes]", "[no]", "[maybe]"]
    out = normalize_token_list(vals)
    assert out == expected


def test_normalize_token_list_handles_empty_and_none():
    assert normalize_token_list([]) == []
    assert normalize_token_list(None) == []


def test_normalize_token_list_with_bracketed_inputs():
    vals = ["[Already-Bracketed]", " Raw/Text "]
    expected = ["[already-bracketed]", "[raw-text]"]
    result = normalize_token_list(vals)
    assert result == expected
