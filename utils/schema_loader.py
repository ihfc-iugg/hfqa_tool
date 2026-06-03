# utils/schema_loader.py
import yaml
from etl.normalization_schema import normalize_schema

def load_and_normalize_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return normalize_schema(yaml.safe_load(f))

def load_raw_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_col_comment(schema_dict: dict, col_name: str) -> str:
    """
    Retrieve comment for a column from the schema.

    """
    for section in ("columns", "core"):
        section_dict = schema_dict.get(section, {})
        if col_name in section_dict:
            return section_dict[col_name].get("comment", "")
    return ""
def load_all_schemas() -> tuple[dict, dict, dict]:
    """
    Loads and normalizes all required schemas:
    - Functional (HF) schema
    - Conditional check schema
    - Quality control (QC) schema (raw)
    """
    hf_schema = load_and_normalize_schema("schemas/hf_schema.yaml")
    qc_schema = load_and_normalize_schema("schemas/quality_score_schema.yaml")
    conditional_schema = load_and_normalize_schema("schemas/conditional_rules.yaml")
    return hf_schema, conditional_schema, qc_schema