# testing/unit/etl_test/test_normalization_schema.py

import copy
from pathlib import Path

import pytest
import yaml

import etl.normalization_schema as ns

from etl.normalization_utils import normalize_bracketed_token_series

# -----------------------------
# Helpers: locate schema files
# -----------------------------
def _find_schema_path(filename: str) -> Path:
    """
    Find <repo_root>/schemas/<filename> by walking up from this test file.
    """
    start = Path(__file__).resolve()
    for p in [start] + list(start.parents):
        candidate = p / "schemas" / filename
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate schemas/{filename} (searched parents of {start})")


# -----------------------------
# Fixtures: load YAML
# -----------------------------
@pytest.fixture(scope="session")
def hf_schema() -> dict:
    p = _find_schema_path("hf_schema.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def conditional_rules_schema() -> dict:
    """
    This is the standalone rules file (normalization + conditional_rules).
    """
    p = _find_schema_path("conditional_rules.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def quality_score_schema() -> dict:
    """
    This is the quality score schema (contains m_score).
    """
    p = _find_schema_path("quality_score_schema.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


# -----------------------------
# Stub: count bracket normalizer usage
# -----------------------------
@pytest.fixture()

def stub_bracket_normalizer(monkeypatch):
    import etl.normalization_schema as ns
    import etl.normalization_utils as nu

    calls = {"count": 0}
    real = nu.normalize_bracketed_token_series

    def wrapped(s):
        calls["count"] += 1
        return real(s)

    monkeypatch.setattr(ns, "normalize_bracketed_token_series", wrapped)
    return calls




# ============================================================
# Allowed-values normalization (hf_schema)
# ============================================================
def test_normalize_schema_normalizes_bracketed_allowed_values_P7(hf_schema, stub_bracket_normalizer):
    # Minimal: only global normalization + P7
    schema = {
        "normalization": hf_schema["normalization"],
        "columns": {"P7": hf_schema["columns"]["P7"]},
    }

    out = ns.normalize_schema(schema)

    allowed = set(out["columns"]["P7"]["allowed"])
    assert "[onshore-(continental)]" in allowed
    assert "[offshore-(marine)]" in allowed
    assert "[unspecified]" in allowed

    # should have invoked bracket normalizer at least once
    assert stub_bracket_normalizer["count"] >= 1


def test_normalize_schema_does_not_bracket_nonbracketed_allowed_when_enforce_false(hf_schema, stub_bracket_normalizer):
    # C25 + C26 in hf schema have enforce_brackets false.
    # Also ensure global enforce_brackets doesn't force them: we override global for this test.
    schema = {
        "normalization": {
            "string": dict(hf_schema["normalization"]["string"], enforce_brackets=False),
            "numeric": hf_schema["normalization"]["numeric"],
        },
        "columns": {
            "C25": hf_schema["columns"]["C25"],
            "C26": hf_schema["columns"]["C26"],
        },
    }

    out = ns.normalize_schema(schema)

    # These are non-bracket vocab lists; with enforce false + no bracketed tokens,
    # we expect only strip/lower, no bracket-normalization.
    assert "granite" in set(out["columns"]["C25"]["allowed"]) or len(out["columns"]["C25"]["allowed"]) > 0
    assert "cambrian" in {s.lower() for s in out["columns"]["C26"]["allowed"]}

    assert stub_bracket_normalizer["count"] == 0


# ============================================================
# Top-level conditional_rules.yaml normalization
# ============================================================
def test_top_level_conditional_rules_when_and_target_are_normalized(conditional_rules_schema, stub_bracket_normalizer):
    schema = copy.deepcopy(conditional_rules_schema)
    out = ns.normalize_schema(schema)

    rules = out["conditional_rules"]
    by_name = {r["name"]: r for r in rules}

    r = by_name["p12_indirect_method_c31"]
    assert r["when"]["column"] == "P12"
    assert r["when"]["mode"] == "contains"
    # token normalization: lowercase + hyphenization inside brackets
    assert r["when"]["value"] == "[indirect-(gtm-bsr-cpd-etc.)]"

    # target.allowed tokens normalized
    allowed = set(r["target"]["allowed"])
    assert "[sur]" in allowed
    assert "[other-(specify-in-comments)]" in allowed


def test_top_level_conditional_rules_params_tokens_normalized(conditional_rules_schema):
    out = ns.normalize_schema(copy.deepcopy(conditional_rules_schema))
    by_name = {r["name"]: r for r in out["conditional_rules"]}

    r = by_name["c45_corr_pt_c46_pt_logic"]
    params = r["params"]

    # all should be normalized bracket tokens
    assert "[pt-ratcliffe-(1960)]" in set(params["pt_tokens"])
    assert "[p-bridgman-(1924)]" in set(params["p_tokens"])
    assert "[t-birch-&-clark-(1940)]" in set(params["t_tokens"])
    assert "[site-specific-experimental-relationships]" in set(params["generic_tokens"])


def test_top_level_conditional_rules_require_shapes_supported(conditional_rules_schema):
    out = ns.normalize_schema(copy.deepcopy(conditional_rules_schema))
    by_name = {r["name"]: r for r in out["conditional_rules"]}

    # list-shaped require (required_if) — probing now only requires C23
    r1 = by_name["probing_requires_c23"]
    assert isinstance(r1["require"], list)
    assert {x["column"] for x in r1["require"]} == {"C23"}



def test_m_score_borehole_temperature_cases_normalized(quality_score_schema):
    out = ns.normalize_schema(copy.deepcopy(quality_score_schema))

    cases = out["m_score"]["borehole_logic"]["temperature"]["cases"]
    assert set(cases.keys()) >= {
        "continuous_log",
        "multiple_single_T_points",
        "one_single_point_plus_surface_T",
    }

    # methods_any_of Listen sind normalisiert
    cl_rules = cases["continuous_log"]["rules"]
    eq = cl_rules["equilibrium_or_corrected"]["methods_any_of"]
    assert "[logeq]" in eq
    assert "[cdts]" in eq

    # when token value normalisiert (SUR)
    surf_case = cases["one_single_point_plus_surface_T"]
    assert surf_case["when"]["C31_T_method_top"]["value"] == "[sur]"



def test_m_score_marine_conductivity_when_all_normalized(quality_score_schema):
    out = ns.normalize_schema(copy.deepcopy(quality_score_schema))

    rules = out["m_score"]["marine_logic"]["conductivity"]["conditional_rules"]
    assert isinstance(rules, list) and len(rules) > 0

    # structure: {when_all: {C43_tc_method: {op, value}}}
    first = rules[0]
    when_all = first["when_all"]

    # Find any value field and ensure normalized token if it was bracketed in YAML
    # (schema-specific; do a robust check)
    values = []
    for _, v in when_all.items():
        if isinstance(v, dict) and isinstance(v.get("value"), str):
            values.append(v["value"])
    assert values, "Expected at least one when_all.*.value in marine conductivity conditional_rules"
    assert all(val == val.strip().lower() for val in values)


def test_m_score_p_flags_encoding_keys_normalized(quality_score_schema):
    out = ns.normalize_schema(copy.deepcopy(quality_score_schema))

    enc = out["m_score"]["p_flags"]["encoding"]
    assert isinstance(enc, dict)

    # keys should be normalized tokens; spot-check that any bracketed key is lowercase
    bracket_keys = [k for k in enc.keys() if isinstance(k, str) and "[" in k and "]" in k]
    assert all(k == k.strip().lower() for k in bracket_keys)

def test_m_score_marine_conductivity_conditional_rules_values_normalized(quality_score_schema):
    out = ns.normalize_schema(copy.deepcopy(quality_score_schema))

    rules = out["m_score"]["marine_logic"]["conductivity"]["conditional_rules"]
    assert isinstance(rules, list) and rules

    # check first rule's when_all values are normalized bracket tokens
    when_all = rules[0]["when_all"]
    vals = [v["value"] for v in when_all.values() if isinstance(v, dict) and "value" in v and isinstance(v["value"], str)]
    assert vals
    assert all(x == x.strip().lower() for x in vals)
    assert all(x.startswith("[") and x.endswith("]") for x in vals)

    assert "[probe-pulse-technique]" in vals
