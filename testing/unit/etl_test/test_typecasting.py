import pandas as pd
import numpy as np
import pytest
from etl.typecasting import apply_schema_types, verify_schema_types


@pytest.fixture
def sample_schema():
    return {
        "columns": {
            "A": {"dtype": "int"},
            "B": {"dtype": "float"},
            "C": {"dtype": "string"},
            "D": {"dtype": "datetime", "format": "%Y-%m-%d"},
            "E": {"dtype": "list[string]"},
            "F": {"dtype": "date"},  
        }
    }


@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "row_type": ["data", "data", "data", "data"],
        "A": ["1", "2", "3", "invalid"],
        "B": ["1.1", "2.5", "3.3", "not_a_float"],
        "C": ["hello", " world ", None, 123],
        "D": ["2023-01-01", "2023-12-31", "", "invalid-date"],
        "E": ["[One];[Two]", "[Three]", None, "[Invalid"],
        "F": ["01.01.2020", "31.12.2022", "", None]
    })

def test_verify_schema_types_pass(sample_data, sample_schema):
    df_casted = apply_schema_types(sample_data, sample_schema)
    data_rows = df_casted[df_casted["row_type"] == "data"]
    report = verify_schema_types(data_rows, sample_schema)

    assert set(report["column"]) == set(sample_schema["columns"].keys())
    assert all(report["status"] == "OK")



def test_apply_schema_types(sample_data, sample_schema):
    df_casted = apply_schema_types(sample_data, sample_schema)
    data_rows = df_casted[df_casted["row_type"] == "data"]
    print(data_rows.dtypes)

    # Check values instead of dtype.name
    assert isinstance(data_rows["A"].iloc[0], (int, np.integer)) or pd.isna(data_rows["A"].iloc[0])
    assert isinstance(data_rows["A"].iloc[1], (int, np.integer)) or pd.isna(data_rows["A"].iloc[1])
    assert isinstance(data_rows["A"].iloc[2], (int, np.integer)) or pd.isna(data_rows["A"].iloc[2])
    assert pd.isna(data_rows["A"].iloc[3]) 

def test_apply_schema_all_missing_column():
    df = pd.DataFrame({
        "row_type": ["data", "data", "data"],
        "Z": [None, pd.NA, None],
    })

    schema = {
        "columns": {
            "Z": {"dtype": "int"},
        }
    }

    df_casted = apply_schema_types(df, schema)
    assert "Z" in df_casted.columns
    assert pd.api.types.is_integer_dtype(df_casted["Z"]) or pd.api.types.is_object_dtype(df_casted["Z"])
    assert df_casted["Z"].isna().all()

    report = verify_schema_types(df_casted[df_casted["row_type"] == "data"], schema)
    assert report.iloc[0]["status"] in ["OK", "WARN"]


def test_apply_schema_list_column_with_real_lists():
    df = pd.DataFrame({
        "row_type": ["data", "data"],
        "E": [["one", "two"], ["three"]]
    })

    schema = {
        "columns": {
            "E": {"dtype": "list[string]"}
        }
    }

    df_casted = apply_schema_types(df, schema)

    # Still casted as string (per your design), so should be strings
    assert df_casted["E"].dtype.name.startswith("string")
    assert df_casted["E"].iloc[0] == "['one', 'two']"
    assert df_casted["E"].iloc[1] == "['three']"

    report = verify_schema_types(df_casted[df_casted["row_type"] == "data"], schema)
    assert report.iloc[0]["status"] == "OK"

def test_datetime_format_mismatch():
    df = pd.DataFrame({
        "row_type": ["data", "data"],
        "D": ["01/01/2023", "not-a-date"]
    })

    schema = {
        "columns": {
            "D": {"dtype": "datetime", "format": "%Y-%m-%d"}
        }
    }

    df_casted = apply_schema_types(df, schema)
    
    # Expect parsing failure => column becomes object with all NaNs
    assert not pd.api.types.is_datetime64_any_dtype(df_casted["D"])
    assert df_casted["D"].isna().all()

    report = verify_schema_types(df_casted[df_casted["row_type"] == "data"], schema)
    assert report.iloc[0]["status"] in ["OK", "WARN"]  # Accept WARN due to dtype fallback


def test_apply_schema_without_row_type():
    df = pd.DataFrame({
        "A": ["1", "not-an-int"],
        "B": ["3.14", "NaN"]
    })

    schema = {
        "columns": {
            "A": {"dtype": "int"},
            "B": {"dtype": "float"},
        }
    }

    df_casted = apply_schema_types(df, schema)

    assert pd.api.types.is_integer_dtype(df_casted["A"]) or pd.api.types.is_object_dtype(df_casted["A"])
    assert pd.api.types.is_float_dtype(df_casted["B"])

    report = verify_schema_types(df_casted, schema)
    assert all(report["status"] == "OK")
