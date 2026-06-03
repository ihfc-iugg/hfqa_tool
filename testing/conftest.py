# testing/unit/conftest.py
import os
import sys
from pathlib import Path

import pytest
import yaml

import etl.normalization_schema as ns

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _find_repo_root(start: Path) -> Path:
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


# --------- Quality score schema ---------

@pytest.fixture(scope="session")
def quality_score_schema_raw(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "quality_score_schema.yaml")


@pytest.fixture(scope="session")
def quality_score_schema(quality_score_schema_raw: dict) -> dict:
    return ns.normalize_schema(quality_score_schema_raw)


# --------- Conditional rules schema ---------

@pytest.fixture(scope="session")
def conditional_rules_schema_raw(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "conditional_rules.yaml")


@pytest.fixture(scope="session")
def cond_cfg(conditional_rules_schema_raw: dict) -> dict:
    # normalized, canonical tokens/modes/allowed
    return ns.normalize_schema(conditional_rules_schema_raw)


# --------- Optional: HF schema (if you want it globally too) ---------
@pytest.fixture(scope="session")
def hf_schema_raw(repo_root: Path) -> dict:
    return _load_yaml(repo_root / "schemas" / "hf_schema.yaml")


@pytest.fixture(scope="session")
def hf_schema(hf_schema_raw: dict) -> dict:
    return ns.normalize_schema(hf_schema_raw)


# --------- Helpers: expose as fixtures (recommended) ---------

@pytest.fixture
def rule_by_name():
    def _rule_by_name(cfg: dict, name: str) -> dict:
        rules = cfg.get("conditional_rules", [])
        for r in rules:
            if isinstance(r, dict) and r.get("name") == name:
                return r
        raise KeyError(f"Rule not found: {name}")
    return _rule_by_name


@pytest.fixture
def first_rule_of_kind():
    def _first_rule_of_kind(cfg: dict, kind: str) -> dict:
        rules = cfg.get("conditional_rules", [])
        for r in rules:
            if isinstance(r, dict) and r.get("kind") == kind:
                return r
        raise KeyError(f"No rule of kind '{kind}' found.")
    return _first_rule_of_kind
