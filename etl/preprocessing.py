from pathlib import Path
import pandas as pd

from etl.extract_excel import excel_to_parquet
from etl.normalization_dataframe import normalize_only_data_rows
from etl.typecasting import apply_schema_types


def prepare_data_from_excel(
    excel_path: str,
    schema: dict,
    sheet_name: int = 0,
    meta_rows: int = 7,
    parquet_path: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Full preprocessing pipeline:
    - Reads Excel
    - Converts to Parquet (optional)
    - Ensures 'row_type' column
    - Normalizes and typecasts data rows

    Returns:
        df_raw         (original raw DataFrame),
        df_meta        (meta/header rows),
        df_data_typed  (preprocessed data rows)
    """

    # Set default output path for intermediate Parquet
    if parquet_path is None:
        parquet_path = str(Path(excel_path).with_suffix(".raw.parquet"))

    # Step 1: Read Excel, convert to Parquet
    df_raw = excel_to_parquet(
        excel_path=excel_path,
        parquet_path=parquet_path,
        sheet_name=sheet_name,
        meta_rows=meta_rows,
    )

    # Step 2: Add 'row_type' if missing
    if "row_type" not in df_raw.columns:
        df_raw["row_type"] = "data"

    # Step 3: Split into meta + data, normalize data rows
    df_meta, df_data_norm = normalize_only_data_rows(df_raw, schema)

    # Step 4: Apply types based on schema
    df_data_typed = apply_schema_types(df_data_norm, schema)

    return df_raw, df_meta, df_data_typed
