# etl/extract_excel.py
import pandas as pd
import logging

def excel_to_parquet(
    excel_path: str,
    parquet_path: str,
    sheet_name=0,
    meta_rows=7
) -> pd.DataFrame:
    """
    Read an Excel file, convert everything to canonical string form,
    mark meta/data rows, write Parquet, and return the dataframe.
    """
    logging.info(f"Reading Excel: {excel_path} (sheet={sheet_name})")

    df_raw = pd.read_excel(
        excel_path,
        sheet_name=sheet_name,
        header=0,
        dtype=str
    )

    logging.info(f"Shape: {df_raw.shape}")

    # Add row_type
    meta_rows = int(meta_rows)
    df_raw["row_type"] = ["meta"] * meta_rows + ["data"] * (len(df_raw) - meta_rows)

    # Convert to string[pyarrow] for guaranteed Parquet compatibility
    df_raw_str = df_raw.astype("string[pyarrow]")

    # Save Parquet
    logging.info(f"Writing Parquet: {parquet_path}")
    df_raw_str.to_parquet(parquet_path, index=False)

    return df_raw_str
