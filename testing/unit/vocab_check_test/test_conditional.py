
import pandas as pd
import pytest
import numpy as np

from vocab_check.apply_conditional_check import apply_conditional_rules


def test_c11_considered_p_allows_only_p_options(cond_cfg: dict):
    """
    When C11 = [considered-p] (pressure only),
    C45 must only contain pressure-specific options, not temperature or pT.
    """
    rule_name = "c11_considered_p_c45"
    flag_col = f"C45__cond_{rule_name}"
    
    # Valid C45 options for C11=[considered-p]
    valid_options = [
        "[replicated-in-situ-(p)]",
        "[corrected-in-situ-(p)]",
        "[site-specific-experimental-relationships]",
        "[other-(specify-in-comments)]"
    ]
    
    # Invalid C45 options (contain T or pT)
    invalid_options = [
        "[actual-in-situ-(pt)-conditions]",  # pT not allowed
        "[replicated-in-situ-(pt)]",         # pT not allowed
        "[corrected-in-situ-(pt)]",          # pT not allowed
        "[replicated-in-situ-(t)]",          # T not allowed
        "[corrected-in-situ-(t)]",           # T not allowed
    ]
    
    # Test valid options - should NOT trigger error
    for valid_c45 in valid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": valid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        
        assert flag_col in result.columns, f"Flag column {flag_col} not created"
        assert result.loc[0, flag_col] == False, \
            f"Valid C45='{valid_c45}' incorrectly flagged as error"
    
    # Test invalid options - SHOULD trigger error
    for invalid_c45 in invalid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": invalid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        
        assert flag_col in result.columns, f"Flag column {flag_col} not created"
        assert result.loc[0, flag_col] == True, \
            f"Invalid C45='{invalid_c45}' not flagged as error (should fail!)"


def test_c11_considered_t_allows_only_t_options(cond_cfg: dict):
    """
    When C11 = [considered-t] (temperature only),
    C45 must only contain temperature-specific options, not pressure or pT.
    """
    rule_name = "c11_considered_t_c45"
    flag_col = f"C45__cond_{rule_name}"
    
    # Valid C45 options
    valid_options = [
        "[replicated-in-situ-(t)]",
        "[corrected-in-situ-(t)]",
        "[site-specific-experimental-relationships]",
        "[other-(specify-in-comments)]"
    ]
    
    # Invalid C45 options (contain p or pT)
    invalid_options = [
        "[actual-in-situ-(pt)-conditions]",
        "[replicated-in-situ-(pt)]",
        "[corrected-in-situ-(pt)]",
        "[replicated-in-situ-(p)]",
        "[corrected-in-situ-(p)]",
    ]
    
    # Test valid options
    for valid_c45 in valid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-t]",
            "C45": valid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == False, \
            f"Valid C45='{valid_c45}' incorrectly flagged"
    
    # Test invalid options
    for invalid_c45 in invalid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-t]",
            "C45": invalid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == True, \
            f"Invalid C45='{invalid_c45}' not flagged (should fail!)"


def test_c11_considered_pt_allows_only_pt_options(cond_cfg: dict):
    """
    When C11 = [considered-pt] (both pressure and temperature),
    C45 must contain pT options, not just p or just T.
    """
    rule_name = "c11_considered_pt_c45"
    flag_col = f"C45__cond_{rule_name}"
    
    # Valid C45 options
    valid_options = [
        "[actual-in-situ-(pt)-conditions]",
        "[replicated-in-situ-(pt)]",
        "[corrected-in-situ-(pt)]",
        "[site-specific-experimental-relationships]",
        "[other-(specify-in-comments)]"
    ]
    
    # Invalid C45 options (only p or only T, not pT)
    invalid_options = [
        "[replicated-in-situ-(p)]",   # Only p
        "[corrected-in-situ-(p)]",    # Only p
        "[replicated-in-situ-(t)]",   # Only T
        "[corrected-in-situ-(t)]",    # Only T
    ]
    
    # Test valid options
    for valid_c45 in valid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-pt]",
            "C45": valid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == False, \
            f"Valid C45='{valid_c45}' incorrectly flagged"
    
    # Test invalid options
    for invalid_c45 in invalid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[considered-pt]",
            "C45": invalid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == True, \
            f"Invalid C45='{invalid_c45}' not flagged (should fail!)"


def test_c11_not_considered_requires_ambient_conditions(cond_cfg: dict):
    """
    When C11 = [not-considered] (pT not considered),
    C45 must indicate ambient conditions, not in-situ.
    """
    rule_name = "c11_not_considered_c45"
    flag_col = f"C45__cond_{rule_name}"
    
    # Valid C45 options
    valid_options = [
        "[unrecorded-ambient-pt-conditions]",
        "[recorded-ambient-pt-conditions]"
    ]
    
    # Invalid C45 options (any in-situ conditions)
    invalid_options = [
        "[actual-in-situ-(pt)-conditions]",
        "[replicated-in-situ-(pt)]",
        "[corrected-in-situ-(pt)]",
        "[replicated-in-situ-(p)]",
        "[corrected-in-situ-(p)]",
        "[replicated-in-situ-(t)]",
        "[corrected-in-situ-(t)]",
        "[site-specific-experimental-relationships]",
        "[other-(specify-in-comments)]"
    ]
    
    # Test valid options
    for valid_c45 in valid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[not-considered]",
            "C45": valid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == False, \
            f"Valid C45='{valid_c45}' incorrectly flagged"
    
    # Test invalid options
    for invalid_c45 in invalid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[not-considered]",
            "C45": invalid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == True, \
            f"Invalid C45='{invalid_c45}' not flagged (should fail!)"


def test_c11_unspecified_requires_c45_unspecified(cond_cfg: dict):
    """
    When C11 = [unspecified] (unknown what was considered),
    C45 must also be [unspecified].
    """
    rule_name = "c11_unspecified_c45"
    flag_col = f"C45__cond_{rule_name}"
    
    # Valid C45 option
    valid_option = "[unspecified]"
    
    # Invalid C45 options (any specific value)
    invalid_options = [
        "[actual-in-situ-(pt)-conditions]",
        "[replicated-in-situ-(pt)]",
        "[replicated-in-situ-(p)]",
        "[replicated-in-situ-(t)]",
        "[unrecorded-ambient-pt-conditions]",
        "[site-specific-experimental-relationships]",
    ]
    
    # Test valid option
    df = pd.DataFrame([{
        "row_type": "data",
        "C11": "[unspecified]",
        "C45": valid_option
    }])
    
    result = apply_conditional_rules(df, cond_cfg)
    assert result.loc[0, flag_col] == False, \
        f"Valid C45='{valid_option}' incorrectly flagged"
    
    # Test invalid options
    for invalid_c45 in invalid_options:
        df = pd.DataFrame([{
            "row_type": "data",
            "C11": "[unspecified]",
            "C45": invalid_c45
        }])
        
        result = apply_conditional_rules(df, cond_cfg)
        assert result.loc[0, flag_col] == True, \
            f"Invalid C45='{invalid_c45}' not flagged (should fail!)"


def test_c11_c45_multi_value_handling(cond_cfg: dict):
    """
    Test that multi-value C45 fields are handled correctly.
    If C45 contains multiple values separated by semicolons,
    ALL values must be valid for the given C11.
    """
    # Test C11=[considered-p] with multi-value C45
    df = pd.DataFrame([
        {
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": "[replicated-in-situ-(p)];[corrected-in-situ-(p)]"  # Both valid
        },
        {
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": "[replicated-in-situ-(p)];[actual-in-situ-(pt)-conditions]"  # One invalid
        }
    ])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    flag_col = "C45__cond_c11_considered_p_c45"
    assert result.loc[0, flag_col] == False, "Both valid values flagged incorrectly"
    assert result.loc[1, flag_col] == True, "Mixed valid/invalid not flagged"


def test_c11_c45_meta_rows_not_validated(cond_cfg: dict):
    """
    Verify that meta rows are not validated even with invalid C11-C45 combinations.
    """
    df = pd.DataFrame([
        {
            "row_type": "meta",
            "C11": "[considered-p]",
            "C45": "[actual-in-situ-(pt)-conditions]"  # Invalid but meta
        },
        {
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": "[actual-in-situ-(pt)-conditions]"  # Invalid and data
        }
    ])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    flag_col = "C45__cond_c11_considered_p_c45"
    assert result.loc[0, flag_col] == False, "Meta row incorrectly validated"
    assert result.loc[1, flag_col] == True, "Data row not validated"


def test_c11_c45_missing_values_not_flagged(cond_cfg: dict):
    """
    Verify that missing/NaN values in C45 don't trigger conditional errors.
    (They may trigger mandatory field errors elsewhere, but not conditional errors)
    """
    df = pd.DataFrame([
        {
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": np.nan
        },
        {
            "row_type": "data",
            "C11": "[considered-p]",
            "C45": None
        }
    ])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    flag_col = "C45__cond_c11_considered_p_c45"
    assert result.loc[0, flag_col] == False, "NaN incorrectly flagged"
    assert result.loc[1, flag_col] == False, "None incorrectly flagged"


def test_c11_different_value_does_not_trigger_rules(cond_cfg: dict):
    """
    Verify that when C11 has a value that doesn't match any rule trigger,
    no C45 flags are set regardless of C45 value.
    """
    df = pd.DataFrame([{
        "row_type": "data",
        "C11": "[some-other-value]",  # Doesn't match any rule
        "C45": "[actual-in-situ-(pt)-conditions]"
    }])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    # No C11-C45 flags should be True
    c11_c45_flags = [c for c in result.columns if "C45__cond_c11_" in c]
    for flag in c11_c45_flags:
        assert result.loc[0, flag] == False, \
            f"Flag {flag} triggered despite C11 not matching rule"


def test_all_c11_c45_flag_columns_created(cond_cfg: dict):
    """
    Verify that all 5 C11-C45 flag columns are created.
    """
    # Create DataFrame with data that triggers all rules
    df = pd.DataFrame([
        {"row_type": "data", "C11": "[considered-p]", "C45": "[replicated-in-situ-(p)]"},
        {"row_type": "data", "C11": "[considered-t]", "C45": "[replicated-in-situ-(t)]"},
        {"row_type": "data", "C11": "[considered-pt]", "C45": "[actual-in-situ-(pt)-conditions]"},
        {"row_type": "data", "C11": "[not-considered]", "C45": "[unrecorded-ambient-pt-conditions]"},
        {"row_type": "data", "C11": "[unspecified]", "C45": "[unspecified]"},
    ])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    expected_flags = [
        "C45__cond_c11_considered_p_c45",
        "C45__cond_c11_considered_t_c45",
        "C45__cond_c11_considered_pt_c45",
        "C45__cond_c11_not_considered_c45",
        "C45__cond_c11_unspecified_c45"
    ]
    
    for flag in expected_flags:
        assert flag in result.columns, f"Expected flag column {flag} not created"


def test_c11_c45_comprehensive_validation(cond_cfg: dict):
    """
    Comprehensive test with multiple valid and invalid combinations.
    """
    df = pd.DataFrame([
        # Valid combinations
        {"row_type": "data", "C11": "[considered-p]", "C45": "[replicated-in-situ-(p)]", "expected_error": False},
        {"row_type": "data", "C11": "[considered-t]", "C45": "[corrected-in-situ-(t)]", "expected_error": False},
        {"row_type": "data", "C11": "[considered-pt]", "C45": "[actual-in-situ-(pt)-conditions]", "expected_error": False},
        {"row_type": "data", "C11": "[not-considered]", "C45": "[unrecorded-ambient-pt-conditions]", "expected_error": False},
        {"row_type": "data", "C11": "[unspecified]", "C45": "[unspecified]", "expected_error": False},
        
        # Invalid combinations
        {"row_type": "data", "C11": "[considered-p]", "C45": "[actual-in-situ-(pt)-conditions]", "expected_error": True},
        {"row_type": "data", "C11": "[considered-t]", "C45": "[corrected-in-situ-(p)]", "expected_error": True},
        {"row_type": "data", "C11": "[considered-pt]", "C45": "[replicated-in-situ-(p)]", "expected_error": True},
        {"row_type": "data", "C11": "[not-considered]", "C45": "[actual-in-situ-(pt)-conditions]", "expected_error": True},
        {"row_type": "data", "C11": "[unspecified]", "C45": "[replicated-in-situ-(t)]", "expected_error": True},
    ])
    
    result = apply_conditional_rules(df, cond_cfg)
    
    # Check each row
    c45_flags = [c for c in result.columns if "C45__cond_c11_" in c]
    
    for idx, row in result.iterrows():
        # Check if any C45 conditional flag is True
        has_error = any(row[flag] for flag in c45_flags)
        expected_error = df.loc[idx, "expected_error"]
        
        assert has_error == expected_error, \
            f"Row {idx}: C11={row['C11']}, C45={row['C45']}, " \
            f"expected_error={expected_error}, got_error={has_error}"

def test_p12_probing_requires_c23_all_combinations(cond_cfg: dict, hf_schema: dict):
    rule_name = "probing_requires_c23"
    flag_col = f"C23__cond_{rule_name}"

    # Alle erlaubten P12-Werte (normalisiert)
    p12_values = hf_schema["columns"]["P12"]["allowed"]

    # Trigger aus der Regel (normalisiert durch cond_cfg)
    rule = next(r for r in cond_cfg["conditional_rules"] if r.get("name") == rule_name)
    probing_values = set(rule["when"]["values"])  # z.B. "[probing-(offshore-ocean)]", ...

    missing_values = [np.nan, None]
    present_value = 1.23

    for p12 in p12_values:
        is_probing = p12 in probing_values

        # Case A: C23 missing -> True nur bei probing
        for miss in missing_values:
            df = pd.DataFrame([{
                "row_type": "data",
                "P12": p12,
                "C23": miss,
            }])

            result = apply_conditional_rules(df, cond_cfg)

            assert flag_col in result.columns, f"Flag column {flag_col} not created"
            expected = True if is_probing else False
            assert result.loc[0, flag_col] == expected, (
                f"P12={p12}, C23={miss}: expected {expected}, got {result.loc[0, flag_col]}"
            )

        # Case B: C23 present -> nie flaggen
        df = pd.DataFrame([{
            "row_type": "data",
            "P12": p12,
            "C23": present_value,
        }])

        result = apply_conditional_rules(df, cond_cfg)

        assert flag_col in result.columns, f"Flag column {flag_col} not created"
        assert bool(result.loc[0, flag_col]) is False, (
            f"P12={p12}, C23 present: expected False, got {result.loc[0, flag_col]}"
        )

def test_probing_c31_c32_must_be_empty_or_unspecified(cond_cfg: dict):
    # rule names
    c31_rules = [
        "probing_c31_empty_or_unspecified_onshore",
        "probing_c31_empty_or_unspecified_offshore",
        "probing_c31_empty_or_unspecified_cluster",
    ]
    c32_rules = [
        "probing_c32_empty_or_unspecified_onshore",
        "probing_c32_empty_or_unspecified_offshore",
        "probing_c32_empty_or_unspecified_cluster",
    ]

    # derive normalized P12 probing tokens from cond_cfg (so test never breaks on normalization)
    probing_tokens = set()
    for rn in c31_rules:  # any of them has the probing value
        r = next(x for x in cond_cfg["conditional_rules"] if x.get("name") == rn)
        probing_tokens.add(r["when"]["value"])  # normalized by ns.normalize_schema

    def _any_true(out, cols):
        return any(bool(out.loc[0, c]) for c in cols)

    # --- probing: allowed -> empty or [unspecified] must NOT flag
    for p12 in probing_tokens:
        for val in [np.nan, None, "[unspecified]"]:
            df = pd.DataFrame([{
                "row_type": "data",
                "P12": p12,
                "C31": val,
                "C32": val,
            }])

            out = apply_conditional_rules(df, cond_cfg)

            c31_flag_cols = [f"C31__cond_{r}" for r in c31_rules]
            c32_flag_cols = [f"C32__cond_{r}" for r in c32_rules]

            for c in c31_flag_cols + c32_flag_cols:
                assert c in out.columns, f"Missing flag column {c}"

            assert _any_true(out, c31_flag_cols) is False, f"C31 wrongly flagged for P12={p12}, C31={val}"
            assert _any_true(out, c32_flag_cols) is False, f"C32 wrongly flagged for P12={p12}, C32={val}"


def test_p12_borehole_requires_c4_c5(cond_cfg, hf_schema):
    rule_name = "borehole_requires_c4_c5"
    flag_c4 = f"C4__cond_{rule_name}"
    flag_c5 = f"C5__cond_{rule_name}"

    probing = "[probing-(offshore-ocean)]"
    borehole = "[drilling]"

    # probing: missing is allowed => False
    df = pd.DataFrame([{"row_type":"data","P12": probing,"C4": np.nan,"C5": None}])
    out = apply_conditional_rules(df, cond_cfg)
    assert bool(out.loc[0, flag_c4]) is False
    assert bool(out.loc[0, flag_c5]) is False

    # borehole: missing is not allowed => True
    df = pd.DataFrame([{"row_type":"data","P12": borehole,"C4": np.nan,"C5": None}])
    out = apply_conditional_rules(df, cond_cfg)
    assert bool(out.loc[0, flag_c4]) is True
    assert bool(out.loc[0, flag_c5]) is True

def test_p12_probing_requires_c6_all_combinations(cond_cfg: dict, hf_schema: dict):
    """
    For probe sensing (P12 probing / probing-clustering), C6 (Penetration Depth) is mandatory.
    Expect flag True iff:
      - row_type == 'data'
      - P12 is probing/probing-clustering
      - C6 is missing (NaN/None)

    And always False when C6 is present.
    """
    rule_name = "probing_requires_c6"
    flag_col = f"C6__cond_{rule_name}"

    # All allowed P12 options from schema (already normalized by hf_schema fixture)
    p12_values = hf_schema["columns"]["P12"]["allowed"]

    # Derive probing trigger values from the actual rule (robust against normalization)
    rule = next(r for r in cond_cfg["conditional_rules"] if r.get("name") == rule_name)
    probing_values = set(rule["when"]["values"])

    missing_values = [np.nan, None]
    present_value = 10.0  # any non-missing numeric value

    for p12 in p12_values:
        is_probing = p12 in probing_values

        # Case A: C6 missing => should be True only for probing P12
        for miss in missing_values:
            df = pd.DataFrame([{
                "row_type": "data",
                "P12": p12,
                "C6": miss,
            }])

            result = apply_conditional_rules(df, cond_cfg)

            assert flag_col in result.columns, f"Flag column {flag_col} not created"
            expected = True if is_probing else False
            assert result.loc[0, flag_col] == expected, (
                f"P12={p12}, C6={miss}: expected {expected}, got {result.loc[0, flag_col]}"
            )
         # Case B: C6 present => must never be flagged (even for probing)
        df = pd.DataFrame([{
            "row_type": "data",
            "P12": p12,
            "C6": present_value,
        }])

        result = apply_conditional_rules(df, cond_cfg)

        assert flag_col in result.columns, f"Flag column {flag_col} not created"
        assert bool(result.loc[0, flag_col]) is False, (
            f"P12={p12}, C6 present: expected False, got {result.loc[0, flag_col]}"
        )

    
def test_p12_borehole_requires_c31_c32_all_combinations(cond_cfg: dict, hf_schema: dict):
    """
    For borehole data (P12 drilling/mining/tunneling/drilling-clustering/indirect),
    C31 and C32 are mandatory.

    Expect:
      - If P12 is borehole and C31/C32 missing -> corresponding flags True
      - If P12 is borehole and C31/C32 present -> flags False
      - If P12 is not borehole -> flags False even if missing
    """
    rule_name = "borehole_requires_c31_c32"
    flag_c31 = f"C31__cond_{rule_name}"
    flag_c32 = f"C32__cond_{rule_name}"

    # all allowed P12 values
    p12_values = hf_schema["columns"]["P12"]["allowed"]

    # derive borehole trigger values from the actual rule (robust against normalization)
    rule = next(r for r in cond_cfg["conditional_rules"] if r.get("name") == rule_name)
    borehole_values = set(rule["when"]["values"])

    missing_values = [np.nan, None]
    present_c31 = "[SUR]"  # any non-missing token is fine
    present_c32 = "[GTM]"  # any non-missing token is fine

    for p12 in p12_values:
        is_borehole = p12 in borehole_values

        # Case A: missing -> True only for borehole P12
        for miss in missing_values:
            df = pd.DataFrame([{
                "row_type": "data",
                "P12": p12,
                "C31": miss,
                "C32": miss,
            }])

            out = apply_conditional_rules(df, cond_cfg)

            assert flag_c31 in out.columns, f"Flag column {flag_c31} not created"
            assert flag_c32 in out.columns, f"Flag column {flag_c32} not created"

            expected = True if is_borehole else False
            assert out.loc[0, flag_c31] == expected, (
                f"P12={p12}, C31 missing: expected {expected}, got {out.loc[0, flag_c31]}"
            )
            assert out.loc[0, flag_c32] == expected, (
                f"P12={p12}, C32 missing: expected {expected}, got {out.loc[0, flag_c32]}"
            )

        # Case B: present -> never flagged (require_if flags missing only)
        df = pd.DataFrame([{
            "row_type": "data",
            "P12": p12,
            "C31": present_c31,
            "C32": present_c32,
        }])

        out = apply_conditional_rules(df, cond_cfg)

        assert bool(out.loc[0, flag_c31]) is False, (
            f"P12={p12}, C31 present: expected False, got {out.loc[0, flag_c31]}"
        )
        assert bool(out.loc[0, flag_c32]) is False, (
            f"P12={p12}, C32 present: expected False, got {out.loc[0, flag_c32]}"
        )