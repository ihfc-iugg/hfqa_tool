import copy
from pathlib import Path

import pytest
import yaml

import etl.normalization_schema as ns

def _find_repo_root(start: Path) -> Path:
    """
    Walk upwards until we find the project root (the one that contains 'schemas/').
    This works when tests are executed from anywhere.
    """
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / "schemas").exists():
            return p
    raise FileNotFoundError("Could not locate repo root containing a 'schemas/' directory.")


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _find_repo_root(Path(__file__))


@pytest.fixture(scope="session")
def hf_schema(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "hf_schema.yaml")


@pytest.fixture(scope="session")
def conditional_rules_schema(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "conditional_rules.yaml")


@pytest.fixture(scope="session")
def quality_score_schema(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "quality_score_schema.yaml")

import copy
import pytest

import etl.normalization_schema as ns


def _is_token(s: str) -> bool:
    return isinstance(s, str) and s.startswith("[") and s.endswith("]")


def collect_hf_tokens(hf_schema_norm: dict) -> set[str]:
    tokens: set[str] = set()
    for section in ("core", "columns"):
        sec = hf_schema_norm.get(section, {})
        if not isinstance(sec, dict):
            continue
        for _, col_spec in sec.items():
            if not isinstance(col_spec, dict):
                continue
            allowed = col_spec.get("allowed")
            if isinstance(allowed, list):
                for a in allowed:
                    if isinstance(a, str) and _is_token(a):
                        tokens.add(a)
    return tokens


def collect_conditional_rules_tokens(cr_schema_norm: dict) -> set[str]:
    tokens: set[str] = set()
    rules = cr_schema_norm.get("conditional_rules", [])
    if not isinstance(rules, list):
        return tokens

    for r in rules:
        if not isinstance(r, dict):
            continue

        when = r.get("when")
        if isinstance(when, dict):
            v = when.get("value")
            if isinstance(v, str) and _is_token(v):
                tokens.add(v)
            vs = when.get("values")
            if isinstance(vs, list):
                for x in vs:
                    if isinstance(x, str) and _is_token(x):
                        tokens.add(x)

        target = r.get("target")
        if isinstance(target, dict):
            allowed = target.get("allowed")
            if isinstance(allowed, list):
                for a in allowed:
                    if isinstance(a, str) and _is_token(a):
                        tokens.add(a)

        params = r.get("params")
        if isinstance(params, dict):
            for k, v in params.items():
                if isinstance(v, list) and str(k).endswith("_tokens"):
                    for x in v:
                        if isinstance(x, str) and _is_token(x):
                            tokens.add(x)

        req = r.get("require")
        if isinstance(req, list):
            for item in req:
                if not isinstance(item, dict):
                    continue
                v = item.get("value")
                if isinstance(v, str) and _is_token(v):
                    tokens.add(v)
                vs = item.get("values")
                if isinstance(vs, list):
                    for x in vs:
                        if isinstance(x, str) and _is_token(x):
                            tokens.add(x)
        elif isinstance(req, dict):
            v = req.get("value")
            if isinstance(v, str) and _is_token(v):
                tokens.add(v)
            vs = req.get("values")
            if isinstance(vs, list):
                for x in vs:
                    if isinstance(x, str) and _is_token(x):
                        tokens.add(x)

    return tokens


def collect_qc_tokens(qc_schema_norm: dict) -> set[str]:
    tokens: set[str] = set()
    m = qc_schema_norm.get("m_score")
    if not isinstance(m, dict):
        return tokens

    bore = m.get("borehole_logic")
    if isinstance(bore, dict):
        temp = bore.get("temperature")
        if isinstance(temp, dict):
            cases = temp.get("cases")
            if isinstance(cases, dict):
                for _, case in cases.items():
                    if not isinstance(case, dict):
                        continue
                    when = case.get("when")
                    if isinstance(when, dict):
                        for _, w in when.items():
                            if isinstance(w, dict):
                                v = w.get("value")
                                if isinstance(v, str) and _is_token(v):
                                    tokens.add(v)
                    rules = case.get("rules")
                    if isinstance(rules, dict):
                        for _, rule in rules.items():
                            if not isinstance(rule, dict):
                                continue
                            for mk in ("methods_any_of", "C32_methods_any_of"):
                                mv = rule.get(mk)
                                if isinstance(mv, list):
                                    for x in mv:
                                        if isinstance(x, str) and _is_token(x):
                                            tokens.add(x)

        cond = bore.get("conductivity")
        if isinstance(cond, dict):
            blocks = cond.get("blocks")
            if isinstance(blocks, dict):
                for _, blk in blocks.items():
                    if not isinstance(blk, dict):
                        continue
                    mapping = blk.get("mapping")
                    if isinstance(mapping, dict):
                        for k in mapping.keys():
                            if isinstance(k, str) and _is_token(k):
                                tokens.add(k)
                    aoi = blk.get("apply_only_if")
                    if isinstance(aoi, dict):
                        for _, w in aoi.items():
                            if isinstance(w, dict):
                                v = w.get("value")
                                if isinstance(v, str) and _is_token(v):
                                    tokens.add(v)

    marine = m.get("marine_logic")
    if isinstance(marine, dict):
        for part in ("temperature", "conductivity"):
            p = marine.get(part)
            if not isinstance(p, dict):
                continue
            blocks = p.get("blocks")
            if isinstance(blocks, dict):
                for _, blk in blocks.items():
                    if not isinstance(blk, dict):
                        continue
                    mapping = blk.get("mapping")
                    if isinstance(mapping, dict):
                        for k in mapping.keys():
                            if isinstance(k, str) and _is_token(k):
                                tokens.add(k)
                    bins = blk.get("bins")
                    if isinstance(bins, dict):
                        for _, b in bins.items():
                            if isinstance(b, dict):
                                w = b.get("when")
                                if isinstance(w, dict):
                                    v = w.get("value")
                                    if isinstance(v, str) and _is_token(v):
                                        tokens.add(v)
                    ci = blk.get("corrected_if")
                    if isinstance(ci, dict):
                        fv = ci.get("flag_value")
                        if isinstance(fv, str) and _is_token(fv):
                            tokens.add(fv)

            crules = p.get("conditional_rules")
            if isinstance(crules, list):
                for rr in crules:
                    if not isinstance(rr, dict):
                        continue
                    wa = rr.get("when_all")
                    if isinstance(wa, dict):
                        for _, w in wa.items():
                            if isinstance(w, dict):
                                v = w.get("value")
                                if isinstance(v, str) and _is_token(v):
                                    tokens.add(v)

    pf = m.get("p_flags")
    if isinstance(pf, dict):
        enc = pf.get("encoding")
        if isinstance(enc, dict):
            for k in enc.keys():
                if isinstance(k, str) and _is_token(k):
                    tokens.add(k)

    return tokens


def _print_set(title: str, s: set[str], limit: int = 500) -> None:
    print(f"\n--- {title} (n={len(s)}) ---")
    for i, x in enumerate(sorted(s)):
        if i >= limit:
            print(f"... truncated at {limit}")
            break
        print(x)


def test_shared_tokens_normalize_identically_across_schemas(
    hf_schema, conditional_rules_schema, quality_score_schema
):

    hf = ns.normalize_schema(copy.deepcopy(hf_schema))
    cr = ns.normalize_schema(copy.deepcopy(conditional_rules_schema))
    qc = ns.normalize_schema(copy.deepcopy(quality_score_schema))

    hf_tokens = collect_hf_tokens(hf)
    cr_tokens = collect_conditional_rules_tokens(cr)
    qc_tokens = collect_qc_tokens(qc)

    shared_hf_cr = hf_tokens & cr_tokens
    shared_hf_qc = hf_tokens & qc_tokens
    shared_qc_cr = qc_tokens & cr_tokens

    qc_missing_in_hf = qc_tokens - hf_tokens

    _print_set("HF ∩ ConditionalRules", shared_hf_cr)
    _print_set("HF ∩ QualityScore", shared_hf_qc)
    _print_set("QualityScore ∩ ConditionalRules (should be empty)", shared_qc_cr)
    _print_set("QualityScore \\ HF (should be empty)", qc_missing_in_hf)

    cr_missing_in_hf = cr_tokens - hf_tokens
    assert cr_missing_in_hf == set()