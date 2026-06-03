# quality_score/apply_u_quality_score.py
from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_u_score(df: pd.DataFrame, qc_schema: dict) -> pd.Series:
    u_cfg = qc_schema["u_score"]["calculation"]
    t = qc_schema["u_score"]["thresholds"]

    value_col = u_cfg["value_col"]
    uncertainty_col = u_cfg["uncertainty_col"]

    # thresholds
    U1 = float(t["U1"])
    U2 = float(t["U2"])
    U3 = float(t["U3"])

    val_num = pd.to_numeric(df[value_col], errors="coerce")
    unc_num = pd.to_numeric(df[uncertainty_col], errors="coerce")

    cov = np.full(len(df), np.nan, dtype=float)
    mask_valid = (val_num.abs() > 0) & val_num.notna() & unc_num.notna() & (unc_num != 0)
    cov[mask_valid] = (unc_num[mask_valid].abs() / val_num.abs()[mask_valid]) * 100.0
    cov = np.round(cov, 6)


    conditions = [
        cov < U1,                   # < 5            → U1
        (cov >= U1) & (cov <= U2),  # 5 ≤ cov ≤ 15  → U2
        (cov > U2) & (cov <= U3),   # 15 < cov ≤ 25 → U3
        cov > U3,                   # > 25           → U4
    ]

    choices = ["U1", "U2", "U3", "U4"]
    scores = np.select(conditions, choices, default="Ux")

    # NaN → Ux
    scores = np.where(~np.isfinite(cov), "Ux", scores)

    return pd.Series(scores, index=df.index, dtype="string")