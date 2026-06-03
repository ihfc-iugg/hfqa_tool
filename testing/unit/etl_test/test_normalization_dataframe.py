import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

import etl.normalization_dataframe as nd

def _find_schema_path() -> Path:
    start = Path(__file__).resolve()
    for p in [start] + list(start.parents):
        candidate = p / "schemas" / "hf_schema.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate schemas/hf_schema.yaml")


@pytest.fixture(scope="session")
def hf_schema_minimal() -> dict:
    schema_path = _find_schema_path()
    full_schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))

    # Minimal subset: global normalization + only tested columns
    minimal = {
        "normalization": full_schema["normalization"],
        "columns": {
            "P3": full_schema["columns"]["P3"],    # string
            "P7": full_schema["columns"]["P7"],    # list[string], bracketed allowed
            "P1": full_schema["columns"]["P1"],    # float64
            "C25": full_schema["columns"]["C25"],  # list[string], enforce_brackets false
            "C38": full_schema["columns"]["C38"],  # string, replace_dash
            "C26": full_schema["columns"]["C26"],  # stratigraphy, enforce_brackets false
        },
    }

    # Make C38 a "no separator, no lower" control column (so we can test separator disable)
    minimal["columns"]["C38"] = dict(minimal["columns"]["C38"])
    minimal["columns"]["C38"]["normalization"] = dict(minimal["columns"]["C38"].get("normalization", {}))
    minimal["columns"]["C38"]["normalization"]["enforce_brackets"] = False
    minimal["columns"]["C38"]["normalization"]["case_insensitive"] = False
    minimal["columns"]["C38"]["normalization"]["normalize_separator"] = False

    return minimal


@pytest.fixture()
def stub_bracket_normalizer(monkeypatch):
    calls = {"count": 0}

    def normalize_one(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return pd.NA
        s = str(val).strip()
        if s == "":
            return pd.NA

        # simple deterministic bracket-token behavior for unit tests
        parts = [p.strip() for p in s.split(";") if p.strip()]
        out = []
        for p in parts:
            p = p.lstrip("[").rstrip("]").strip().lower()
            out.append(f"[{p}]")
        return ";".join(out) if out else pd.NA

    def fake_normalize_bracketed_token_series(series: pd.Series) -> pd.Series:
        calls["count"] += 1
        return series.apply(normalize_one).astype("string")

    monkeypatch.setattr(nd, "normalize_bracketed_token_series", fake_normalize_bracketed_token_series)
    return calls

def test_numeric_normalization_decimal_comma_and_thousands(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame({"P1": ["1 234,56", "0,1", "NA", "<NA>", ""]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "P1"] == "1234.56"
    assert out.loc[1, "P1"] == "0.1"
    assert pd.isna(out.loc[2, "P1"])
    assert pd.isna(out.loc[3, "P1"])
    assert pd.isna(out.loc[4, "P1"])


def test_bracketed_vocab_column_triggers_bracket_normalization(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame({"P7": ["Onshore (continental), Offshore (marine)"]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    # normalize_separator: ',' -> ';', then lower, then bracket normalization
    assert out.loc[0, "P7"] == "[onshore (continental)];[offshore (marine)]"
    assert stub_bracket_normalizer["count"] == 1


def test_replace_dash_applied_on_C38_without_brackets(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame({"C38": ["2024–01"]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "C38"] == "2024-01"
    assert stub_bracket_normalizer["count"] == 0


def test_separator_normalization_multiple_tokens_on_non_bracket_column_C25(hf_schema_minimal, stub_bracket_normalizer):
    """
    C25 has enforce_brackets: false -> we can observe separator normalization directly.
    Goal: verify that multiple comma-separated tokens become semicolon-separated,
    and whitespace is normalized.
    """
    df = pd.DataFrame({"C25": ["  Granite,   Basalt ,  Diorite  "]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)


    # trim -> "Granite,   Basalt ,  Diorite"
    # collapse_space -> "Granite, Basalt , Diorite"
    # normalize_separator -> "Granite; Basalt ; Diorite"
    # lower -> "granite; basalt ; diorite"
    assert out.loc[0, "C25"] == "granite; basalt ; diorite"
    assert stub_bracket_normalizer["count"] == 0


def test_separator_normalization_multiple_tokens_stratigraphy_C26_no_brackets(hf_schema_minimal, stub_bracket_normalizer):
    """
    Stratigraphy column C26: dtype list[string], enforce_brackets false in schema.
    Verify:
      - comma -> semicolon
      - lowercasing happens (global case_insensitive true)
      - bracket normalizer is NOT invoked
    """
    df = pd.DataFrame({"C26": ["Cambrian,  Jurassic ,  Holocene"]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "C26"] == "cambrian; jurassic ; holocene"
    assert stub_bracket_normalizer["count"] == 0


def test_separator_not_normalized_when_disabled_on_column_C38(hf_schema_minimal, stub_bracket_normalizer):
    """
    We disabled normalize_separator for C38 in the fixture.
    Verify commas remain commas.
    """
    df = pd.DataFrame({"C38": ["A, B, C"]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "C38"] == "A, B, C"
    assert stub_bracket_normalizer["count"] == 0


def test_missing_token_with_whitespace_not_caught_due_to_order(hf_schema_minimal, stub_bracket_normalizer):
    """
    missing_tokens replacement happens BEFORE trim.
    So " NA " is not equal to "NA" at replace-time.
    After trim+lower, global enforce_brackets -> stub brackets it.
    """
    df = pd.DataFrame({"P3": [" NA "]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "P3"] == "[na]"
    assert stub_bracket_normalizer["count"] == 1


def test_unknown_column_is_ignored(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame({"NOT_IN_SCHEMA": ["  X  "]})
    out = nd.normalize_dataframe(df, hf_schema_minimal)

    assert out.loc[0, "NOT_IN_SCHEMA"] == "  X  "
    assert stub_bracket_normalizer["count"] == 0


def test_normalize_only_data_rows_without_row_type(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame({"P1": ["1 000,0"], "P3": ["Name"]})
    meta, data = nd.normalize_only_data_rows(df, hf_schema_minimal)

    assert meta is None
    assert (data["row_type"] == "data").all()
    assert data.loc[0, "P1"] == "1000.0"
    assert data.loc[0, "P3"] == "[name]"


def test_normalize_only_data_rows_preserves_meta_rows(hf_schema_minimal, stub_bracket_normalizer):
    df = pd.DataFrame(
        {
            "row_type": ["meta", "data", "meta", "data"],
            "P1": ["1 000,0", "2 500,50", "NA", "0,1"],
            "P3": [" META ", " DATA ", "none", "X"],
        }
    )
    meta, data = nd.normalize_only_data_rows(df, hf_schema_minimal)

    assert (meta["row_type"] == "meta").all()
    assert meta.iloc[0]["P1"] == "1 000,0"
    assert meta.iloc[0]["P3"] == " META "

    assert (data["row_type"] == "data").all()
    assert data.iloc[0]["P1"] == "2500.50"
    assert data.iloc[0]["P3"] == "[data]"
    assert data.iloc[1]["P1"] == "0.1"
    assert data.iloc[1]["P3"] == "[x]"
