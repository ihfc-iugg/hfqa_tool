import pandas as pd


def apply_conditional_rules(df: pd.DataFrame, cond_cfg: dict) -> pd.DataFrame:
    df = df.copy()
    rules = cond_cfg.get("conditional_rules", [])

    data_mask = df.get("row_type", "data") == "data"

    for rule in rules:
        kind = rule.get("kind", "allowed_subset")

        if kind == "allowed_subset":
            df = _apply_allowed_subset_rule(df, data_mask, rule)

        elif kind == "required_if":
            df = _apply_required_if_rule(df, data_mask, rule)

        elif kind == "imply_category":
            df = _apply_imply_category_rule(df, data_mask, rule)

        elif kind == "pt_function_combo":
            df = _apply_pt_function_combo_rule(df, data_mask, rule)

        else:
            print(f"WARNING: Unknown conditional rule type: {kind}")

    return df


# --- Shared utility ---
def _split_token_cell(cell: str, sep: str = ";") -> set:
    return {p.strip().lower() for p in str(cell).split(sep) if p.strip()}


# -------------------------------------------------------------------
# 1) allowed_subset
# -------------------------------------------------------------------
def _apply_allowed_subset_rule(df, data_mask, rule):
    when = rule.get("when", {})
    target = rule.get("target", {})
    target_col = target.get("column")
    allowed = set(target.get("allowed", []))  # already normalized
    sep = target.get("separator", ";")
    multi = target.get("multi_choice", False)

    if target_col not in df.columns or when.get("column") not in df.columns:
        return df

    s_when = df[when["column"]]
    value = when.get("value", "")
    mode = when.get("mode")

    if mode == "equals":
        cond = s_when == value
    elif mode == "contains":
        cond = s_when.str.contains(value, na=False, regex=False)
    else:
        return df

    cond &= data_mask
    s_target = df[target_col].astype("string")
    invalid_mask = pd.Series(False, index=df.index)

    if multi:
        for i, cell in s_target.loc[cond].items():
            if pd.isna(cell):
                continue
            if not _split_token_cell(cell, sep).issubset(allowed):
                invalid_mask.loc[i] = True
    else:
        invalid_mask.loc[cond] = ~s_target.loc[cond].isin(allowed)

    df[f"{target_col}__cond_{rule['name']}"] = invalid_mask
    return df


# -------------------------------------------------------------------
# 2) required_if
# -------------------------------------------------------------------
def _apply_required_if_rule(df, data_mask, rule):
    when = rule.get("when", {})
    requires = rule.get("require", [])
    when_col = when.get("column")

    if when_col not in df.columns:
        return df

    s_when = df[when_col]
    mode = when.get("mode")

    if mode == "contains_any":
        values = set(when.get("values", []))  # already normalized

        def match(x):
            return bool(_split_token_cell(x) & values) if pd.notna(x) else False

        wmask = s_when.apply(match)
    else:
        return df

    wmask &= data_mask

    for req in requires:
        col = req.get("column")
        if col in df.columns:
            df[f"{col}__cond_{rule['name']}"] = wmask & df[col].isna()

    return df


# -------------------------------------------------------------------
# 3) imply_category
# -------------------------------------------------------------------
def _apply_imply_category_rule(df, data_mask, rule):
    when = rule.get("when", {})
    req = rule.get("require", {})

    cols_when = when.get("columns", [])
    target_col = req.get("column")
    values = set(req.get("values", []))  # already normalized
    mode = req.get("mode")

    if not cols_when or target_col not in df.columns:
        return df

    wmask = pd.Series(False, index=df.index)
    for c in cols_when:
        if c in df.columns:
            wmask |= df[c].notna()
    wmask &= data_mask

    s_target = df[target_col]

    if mode == "contains_any":
        def _contains_any(x):
            if pd.isna(x):
                return False
            return bool(_split_token_cell(x) & values)

        ok_mask = s_target.apply(_contains_any)
    else:
        return df

    df[f"{target_col}__cond_{rule['name']}"] = wmask & (~ok_mask)
    return df


# -------------------------------------------------------------------
# 4) pt_function_combo
# -------------------------------------------------------------------
def _apply_pt_function_combo_rule(df, data_mask, rule):
    when = rule.get("when", {})
    target = rule.get("target", {})
    params = rule.get("params", {})

    when_col = when.get("column")
    col = target.get("column")
    sep = target.get("separator", ";")

    if when_col not in df.columns or col not in df.columns:
        return df

    s_when = df[when_col]
    value = when.get("value", "")
    mode = when.get("mode")

    if mode == "equals":
        wmask = s_when == value
    elif mode == "contains":
        wmask = s_when.str.contains(value, na=False, regex=False)
    else:
        return df

    wmask &= data_mask

    pt_tokens = set(params.get("pt_tokens", []))
    p_tokens = set(params.get("p_tokens", []))
    t_tokens = set(params.get("t_tokens", []))
    generic = set(params.get("generic_tokens", []))
    universe = pt_tokens | p_tokens | t_tokens | generic

    s_target = df[col].astype("string")
    invalid = pd.Series(False, index=df.index)

    for i, cell in s_target.loc[wmask].items():
        if pd.isna(cell):
            invalid[i] = True
            continue

        parts = _split_token_cell(cell, sep)

        if not parts <= universe:
            invalid[i] = True
        elif parts & pt_tokens or parts & generic:
            continue
        elif not (parts & p_tokens and parts & t_tokens):
            invalid[i] = True

    df[f"{col}__cond_{rule['name']}"] = invalid
    return df
