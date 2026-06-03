import pandas as pd

from pandas.api.types import (
    is_integer_dtype,
    is_float_dtype,
    is_string_dtype,
    is_datetime64_any_dtype,
)

def _iter_schema_specs(schema: dict):
    """Combine 'core' and 'columns' specs into one iterator."""
    specs = {}
    specs.update(schema.get("core", {}))
    specs.update(schema.get("columns", {}))
    return specs.items()


def apply_schema_types(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Cast dataframe columns to target dtypes defined in schema (data rows only)."""
    df = df.copy()

    # Separate meta and data rows
    if "row_type" in df.columns:
        meta_rows = df[df["row_type"] == "meta"].copy()
        data_rows = df[df["row_type"] != "meta"].copy()
    else:
        meta_rows = pd.DataFrame(columns=df.columns)
        data_rows = df

    # Apply typecasting to data rows only
    for col_name, col_spec in _iter_schema_specs(schema):
        if col_name not in data_rows.columns:
            continue

        expected_dtype = str(col_spec.get("dtype", "")).strip().lower()
        if not expected_dtype:
            continue

        if "list[" in expected_dtype:
            data_rows[col_name] = data_rows[col_name].astype("string[pyarrow]")
        elif "string" in expected_dtype:
            data_rows[col_name] = data_rows[col_name].astype("string[pyarrow]")
        elif "float" in expected_dtype:
            data_rows[col_name] = pd.to_numeric(data_rows[col_name], errors="coerce").astype("float64")
        elif "int" in expected_dtype:
            data_rows[col_name] = pd.to_numeric(data_rows[col_name], errors="coerce").astype("Int64")
        elif "date" in expected_dtype or "datetime" in expected_dtype:
            date_format = col_spec.get("format")
            if date_format:
                data_rows[col_name] = pd.to_datetime(data_rows[col_name], format=date_format, errors="coerce")
            else:
                data_rows[col_name] = pd.to_datetime(data_rows[col_name], errors="coerce", dayfirst=True)
        else:
            data_rows[col_name] = data_rows[col_name].astype("string[pyarrow]")

    # Combine back with meta rows and preserve order
    parts = [part for part in [meta_rows, data_rows] if not part.empty]
    df_combined = pd.concat(parts).sort_index() if parts else df.iloc[0:0].copy()
    return df_combined



def verify_schema_types(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Return a DataFrame summarizing dtype verification."""
    rows = []

    for col_name, col_spec in schema.get("columns", {}).items():
        if col_name not in df.columns:
            rows.append((col_name, col_spec.get("dtype", ""), None, "MISSING"))
            continue

        expected = str(col_spec.get("dtype", "")).strip().lower()
        series = df[col_name]

        # Semantic type checking
        if "int" in expected:
            match = is_integer_dtype(series)
        elif "float" in expected:
            match = is_float_dtype(series)
        elif "string" in expected or "list[" in expected:
            match = is_string_dtype(series)
        elif "date" in expected or "datetime" in expected:
            match = is_datetime64_any_dtype(series)
        else:
            match = False

        actual_dtype = str(series.dtype)
        status = "OK" if match else "WARN"
        rows.append((col_name, expected, actual_dtype, status))
        

    result = pd.DataFrame(rows, columns=["column", "expected", "actual", "status"])
    return result

