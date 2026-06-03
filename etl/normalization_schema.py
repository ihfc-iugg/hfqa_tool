# etl/normalization_schema.py

import copy
import pandas as pd

from etl.normalization_utils import (
    is_bracketed_token,
    normalize_bracketed_token_series,
    normalize_token,
    normalize_token_list,
)


def normalize_allowed_values(
    allowed_values, col_spec: dict, global_string_norm: dict
) -> set:
    """
    Normalize schema allowed-values to a lowercase set.

    Applies bracketed token normalization only when:
      - column enforce_brackets is True, or
      - global enforce_brackets is True, or
      - allowed values already contain bracketed tokens
    """
    if allowed_values is None:
        return set()

    allowed_series = pd.Series(list(allowed_values), dtype="string")
    has_bracketed = any(is_bracketed_token(str(a)) for a in allowed_values if a is not None)

    col_norm = col_spec.get("normalization", {})
    enforce_brackets = col_norm.get("enforce_brackets")
    if enforce_brackets is None:
        enforce_brackets = global_string_norm.get("enforce_brackets", False)

    if enforce_brackets or has_bracketed:
        allowed_series = normalize_bracketed_token_series(allowed_series)

    return {str(a).strip().lower() for a in allowed_series.dropna()}


def normalize_schema(schema: dict) -> dict:
    """
    Normalize 'allowed' values and token-like values inside schema conditions/logic blocks.
    Supports:
      - heatflow schema (columns/core/conditions)
      - quality_score schema (m_score blocks)
      - top-level conditional_rules.yaml format (when/target/params/require)

    Returns a normalized deep copy (does not mutate the input).
    """
    schema = copy.deepcopy(schema)

    norm_cfg = schema.get("normalization", {})
    global_string_norm = norm_cfg.get("string", {})

    def _normalize_when_block(when: dict) -> None:
        if not isinstance(when, dict):
            return
        for key, value in when.items():
            if isinstance(value, dict) and isinstance(value.get("value"), str):
                value["value"] = normalize_token(value["value"])
            elif isinstance(value, str):
                when[key] = normalize_token(value)

    def _normalize_mapping_keys(mapping: dict) -> dict:
        if not isinstance(mapping, dict):
            return mapping
        return {
            normalize_token(k) if is_bracketed_token(k) else k.strip().lower(): v
            for k, v in mapping.items()
        }

    def _normalize_bins(bins: dict) -> None:
        if not isinstance(bins, dict):
            return
        for _, bin_def in bins.items():
            when = bin_def.get("when")
            if isinstance(when, dict) and isinstance(when.get("value"), str):
                when["value"] = normalize_token(when["value"])

    def _normalize_corrected_if(corrected_if: dict) -> None:
        if not isinstance(corrected_if, dict):
            return
        if "flag_col" in corrected_if:
            corrected_if["flag_col"] = str(corrected_if["flag_col"]).strip()
        if isinstance(corrected_if.get("flag_value"), str):
            corrected_if["flag_value"] = normalize_token(corrected_if["flag_value"])

    def _normalize_conditional_rules_when_all(rules: list) -> None:
        if not isinstance(rules, list):
            return
        for rule in rules:
            when_all = rule.get("when_all")
            if isinstance(when_all, dict):
                _normalize_when_block(when_all)

    # NEW: Normalize conditions inside cases (e.g. saturation C44_any / C43_any)
    def _normalize_cases(cases: list[dict]) -> None:
        if not isinstance(cases, list):
            return
        for case in cases:
            when = case.get("when")
            if isinstance(when, dict):
                for key, value in when.items():
                    if isinstance(value, str):
                        when[key] = normalize_token(value)
                    elif isinstance(value, list):
                        when[key] = [normalize_token(v) for v in value]

    # Normalize columns/core allowed values (deterministic order)
    for section in ("columns", "core"):
        for col_name, col_spec in schema.get(section, {}).items():
            allowed = col_spec.get("allowed")
            if allowed is not None:
                col_spec["allowed"] = sorted(
                    normalize_allowed_values(allowed, col_spec, global_string_norm)
                )

    # Normalize generic conditions (heatflow schema)
    if "conditions" in schema:
        for cond in schema["conditions"]:
            for key in ("when", "then"):
                if key in cond:
                    _normalize_when_block(cond[key])

    # Normalize top-level conditional_rules (rules-file format) — unchanged
    rules = schema.get("conditional_rules")
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            when = rule.get("when")
            if isinstance(when, dict):
                if isinstance(when.get("column"), str):
                    when["column"] = when["column"].strip()
                if isinstance(when.get("mode"), str):
                    when["mode"] = when["mode"].strip().lower()
                if isinstance(when.get("value"), str):
                    when["value"] = normalize_token(when["value"])
                if isinstance(when.get("values"), list):
                    when["values"] = [normalize_token(v) for v in when["values"]]
                if isinstance(when.get("columns"), list):
                    when["columns"] = [str(c).strip() for c in when["columns"]]

            target = rule.get("target")
            if isinstance(target, dict):
                if isinstance(target.get("column"), str):
                    target["column"] = target["column"].strip()
                if isinstance(target.get("allowed"), list):
                    target["allowed"] = sorted(
                        [normalize_token(v) for v in target["allowed"]]
                    )

            params = rule.get("params")
            if isinstance(params, dict):
                for k, v in params.items():
                    if k.endswith("_tokens") and isinstance(v, list):
                        params[k] = [normalize_token(x) for x in v]

            require = rule.get("require")
            if isinstance(require, list):
                for item in require:
                    if not isinstance(item, dict):
                        continue
                    if isinstance(item.get("column"), str):
                        item["column"] = item["column"].strip()
                    if isinstance(item.get("mode"), str):
                        item["mode"] = item["mode"].strip().lower()
                    if isinstance(item.get("value"), str):
                        item["value"] = normalize_token(item["value"])
                    if isinstance(item.get("values"), list):
                        item["values"] = [normalize_token(x) for x in item["values"]]
            elif isinstance(require, dict):
                if isinstance(require.get("column"), str):
                    require["column"] = require["column"].strip()
                if isinstance(require.get("mode"), str):
                    require["mode"] = require["mode"].strip().lower()
                if isinstance(require.get("value"), str):
                    require["value"] = normalize_token(require["value"])
                if isinstance(require.get("values"), list):
                    require["values"] = [normalize_token(x) for x in require["values"]]

    # Normalize m_score / quality_score blocks
    m_score = schema.get("m_score")
    if isinstance(m_score, dict):
        # Borehole logic 
        bh_logic = m_score.get("borehole_logic")
        if isinstance(bh_logic, dict):
            conductivity = bh_logic.get("conductivity")
            if isinstance(conductivity, dict):
                blocks = conductivity.get("blocks")
                if isinstance(blocks, dict):
                    # Normalize inside cases for source_type, saturation, pT_conditions
                    for block_name in ("source_type", "saturation", "pT_conditions"):
                        blk = blocks.get(block_name)
                        if isinstance(blk, dict) and "cases" in blk:
                            _normalize_cases(blk["cases"])

                    # Other conductivity blocks (bins, mapping, etc.) — unchanged
                    for _, block in blocks.items():
                        if not isinstance(block, dict):
                            continue
                        if block.get("C_field"):
                            block["C_field"] = str(block["C_field"]).strip()
                        if block.get("apply_only_if"):
                            _normalize_when_block(block["apply_only_if"])
                        if block.get("mapping"):
                            block["mapping"] = _normalize_mapping_keys(block["mapping"])
                        if block.get("bins"):
                            _normalize_bins(block["bins"])
                        if block.get("corrected_if"):
                            _normalize_corrected_if(block["corrected_if"])

        # Temperature cases (unchanged — your original code already handles rules)
        temperature = bh_logic.get("temperature")
        if isinstance(temperature, dict):
            cases = temperature.get("cases")
            if isinstance(cases, dict):
                for _, case in cases.items():
                    if isinstance(case, dict):
                        when = case.get("when")
                        if isinstance(when, dict):
                            _normalize_when_block(when)
                        rules = case.get("rules")
                        if isinstance(rules, dict):
                            for _, rule in rules.items():
                                if isinstance(rule, dict):
                                    for key in ("methods_any_of", "C32_methods_any_of"):
                                        if isinstance(rule.get(key), list):
                                            rule[key] = normalize_token_list(rule[key])
                                    for k, v in rule.items():
                                        if isinstance(v, str):
                                            rule[k] = normalize_token(v)

        # Marine logic
        marine_logic = m_score.get("marine_logic")
        if isinstance(marine_logic, dict):

            # Temperature
            t = marine_logic.get("temperature")
            if isinstance(t, dict):
                blocks = t.get("blocks")
                if isinstance(blocks, dict):
                    for _, blk in blocks.items():
                        if not isinstance(blk, dict):
                            continue
                        if blk.get("C_field"):
                            blk["C_field"] = str(blk["C_field"]).strip()
                        _normalize_corrected_if(blk.get("corrected_if"))
                        _normalize_bins(blk.get("bins"))

            # Conductivity — NEW: normalize saturation & pT cases
            c = marine_logic.get("conductivity")
            if isinstance(c, dict):
                blocks = c.get("blocks")
                if isinstance(blocks, dict):
                    # Normalize saturation and pT_conditions cases
                    for block_name in ("saturation", "pT_conditions"):
                        blk = blocks.get(block_name)
                        if isinstance(blk, dict):
                            cases = blk.get("cases")
                            if isinstance(cases, list):
                                _normalize_cases(cases)

                    # Existing block normalization
                    for _, blk in blocks.items():
                        if not isinstance(blk, dict):
                            continue
                        if blk.get("C_field"):
                            blk["C_field"] = str(blk["C_field"]).strip()
                        apply_only_if = blk.get("apply_only_if")
                        if isinstance(apply_only_if, dict):
                            _normalize_when_block(apply_only_if)
                        mapping = blk.get("mapping")
                        if isinstance(mapping, dict):
                            blk["mapping"] = _normalize_mapping_keys(mapping)
                        _normalize_bins(blk.get("bins"))
                        _normalize_corrected_if(blk.get("corrected_if"))

                _normalize_conditional_rules_when_all(c.get("conditional_rules"))

        # p_flags
        p_flags = m_score.get("p_flags")
        if isinstance(p_flags, dict):
            if "fields" in p_flags and isinstance(p_flags["fields"], dict):
                for k, v in p_flags["fields"].items():
                    if isinstance(v, str):
                        p_flags["fields"][k] = v.strip()
            if "letters" in p_flags and isinstance(p_flags["letters"], dict):
                for k, v in p_flags["letters"].items():
                    if isinstance(v, str):
                        p_flags["letters"][k] = v.strip()
            if "encoding" in p_flags and isinstance(p_flags["encoding"], dict):
                new_enc = {}
                for k, v in p_flags["encoding"].items():
                    nk = normalize_token(k) if isinstance(k, str) else k
                    new_enc[nk] = v
                p_flags["encoding"] = new_enc

    return schema