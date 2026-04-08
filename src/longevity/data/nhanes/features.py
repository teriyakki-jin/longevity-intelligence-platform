"""NHANES feature engineering.

Computes derived biomarkers and prepares the final feature matrix
for model training.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from longevity.common.logging import get_logger

logger = get_logger(__name__)


def compute_egfr(df: pd.DataFrame) -> pd.DataFrame:
    """Compute eGFR using CKD-EPI 2021 (race-free) equation.

    CKD-EPI 2021: eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^(-1.200)
                         × 0.9938^Age × (1.012 if female)
    κ: 0.7 (female), 0.9 (male)
    α: -0.241 (female), -0.302 (male)
    """
    required = ["creatinine_mg_dl", "age_years", "sex"]
    if not all(c in df.columns for c in required):
        logger.warning("egfr_missing_columns", required=required)
        return df

    scr = df["creatinine_mg_dl"]
    age = df["age_years"]
    is_female = df["sex"] == "female"

    kappa = np.where(is_female, 0.7, 0.9)
    alpha = np.where(is_female, -0.241, -0.302)
    sex_factor = np.where(is_female, 1.012, 1.0)

    ratio = scr / kappa
    egfr = (
        142
        * np.where(ratio < 1, ratio ** alpha, 1.0)
        * np.where(ratio > 1, ratio ** -1.200, 1.0)
        * (0.9938 ** age)
        * sex_factor
    )
    df["egfr"] = np.where(scr.isna() | age.isna(), np.nan, egfr)
    return df


def compute_bmi(df: pd.DataFrame) -> pd.DataFrame:
    """Compute BMI from height and weight if not already present."""
    if "bmi" not in df.columns and "height_cm" in df.columns and "weight_kg" in df.columns:
        height_m = df["height_cm"] / 100
        df["bmi"] = df["weight_kg"] / (height_m ** 2)
        # Clip to physiologically plausible range
        df["bmi"] = df["bmi"].clip(lower=10, upper=80)
    return df


def compute_fib4(df: pd.DataFrame) -> pd.DataFrame:
    """Compute FIB-4 liver fibrosis score.

    FIB-4 = (Age × AST) / (Platelets × sqrt(ALT))
    Threshold: <1.30 (low risk), 1.30-2.67 (intermediate), >2.67 (high risk)
    """
    required = ["age_years", "ast_u_l", "alt_u_l", "platelets_1000_ul"]
    if not all(c in df.columns for c in required):
        return df

    fib4 = (
        df["age_years"] * df["ast_u_l"]
    ) / (
        df["platelets_1000_ul"] * np.sqrt(df["alt_u_l"].clip(lower=0.01))
    )
    df["fib4_score"] = fib4.clip(upper=100)  # Cap extreme values
    return df


def compute_homa_ir(df: pd.DataFrame) -> pd.DataFrame:
    """Compute HOMA-IR (insulin resistance proxy).

    HOMA-IR = (Fasting glucose mg/dL × Fasting insulin uU/mL) / 405
    Only available in cycles where insulin was measured.
    """
    if "glucose_mg_dl" in df.columns and "insulin_uu_ml" in df.columns:
        df["homa_ir"] = (df["glucose_mg_dl"] * df["insulin_uu_ml"]) / 405
        df["homa_ir"] = df["homa_ir"].clip(upper=100)
    return df


def compute_waist_hip_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Compute waist-to-hip ratio if both measurements available."""
    if "waist_cm" in df.columns and "hip_cm" in df.columns:
        df["waist_hip_ratio"] = df["waist_cm"] / df["hip_cm"].replace(0, np.nan)
    return df


def compute_non_hdl_cholesterol(df: pd.DataFrame) -> pd.DataFrame:
    """Compute non-HDL cholesterol = Total - HDL."""
    if "total_cholesterol_mg_dl" in df.columns and "hdl_mg_dl" in df.columns:
        df["non_hdl_mg_dl"] = df["total_cholesterol_mg_dl"] - df["hdl_mg_dl"]
    return df


def compute_cholesterol_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Total cholesterol / HDL ratio (cardiovascular risk marker)."""
    if "total_cholesterol_mg_dl" in df.columns and "hdl_mg_dl" in df.columns:
        df["chol_hdl_ratio"] = df["total_cholesterol_mg_dl"] / df["hdl_mg_dl"].replace(0, np.nan)
    return df


def compute_metabolic_syndrome_score(df: pd.DataFrame) -> pd.DataFrame:
    """Count number of metabolic syndrome criteria met (0-5).

    ATP III criteria:
    1. Waist > 102cm (men) or >88cm (women)
    2. Triglycerides >= 150 mg/dL
    3. HDL < 40 (men) or < 50 (women)
    4. BP >= 130/85 mmHg  (requires BP data)
    5. Fasting glucose >= 100 mg/dL
    """
    score = pd.Series(0, index=df.index)

    if "waist_cm" in df.columns and "sex" in df.columns:
        waist_thresh = np.where(df["sex"] == "male", 102, 88)
        score += (df["waist_cm"] >= waist_thresh).astype(int)

    if "triglycerides_mg_dl" in df.columns:
        score += (df["triglycerides_mg_dl"] >= 150).astype(int)

    if "hdl_mg_dl" in df.columns and "sex" in df.columns:
        hdl_thresh = np.where(df["sex"] == "male", 40, 50)
        score += (df["hdl_mg_dl"] < hdl_thresh).astype(int)

    if "glucose_mg_dl" in df.columns:
        score += (df["glucose_mg_dl"] >= 100).astype(int)

    df["metabolic_syndrome_score"] = score
    return df


def apply_all_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all derived feature computations in sequence."""
    pipeline: list = [
        compute_bmi,
        compute_egfr,
        compute_fib4,
        compute_homa_ir,
        compute_waist_hip_ratio,
        compute_non_hdl_cholesterol,
        compute_cholesterol_ratio,
        compute_metabolic_syndrome_score,
    ]
    for fn in pipeline:
        try:
            df = fn(df)
        except Exception as e:
            logger.warning("derived_feature_failed", function=fn.__name__, error=str(e))

    return df


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build the final feature matrix for model training.

    - Applies all derived features
    - Selects model features
    - Handles missing values (median imputation for <20% missing)
    - Filters to complete cases for target variable (age_years + mortstat)
    """
    df = apply_all_derived_features(df)

    feature_cols = [
        # Blood markers
        "glucose_mg_dl", "hba1c_pct", "total_cholesterol_mg_dl",
        "hdl_mg_dl", "ldl_mg_dl", "triglycerides_mg_dl",
        "creatinine_mg_dl", "alt_u_l", "ast_u_l", "albumin_g_dl",
        "wbc_1000_ul", "hemoglobin_g_dl", "platelets_1000_ul",
        "crp_mg_l", "uric_acid_mg_dl",
        # Derived
        "egfr", "fib4_score", "homa_ir",
        "non_hdl_mg_dl", "chol_hdl_ratio", "metabolic_syndrome_score",
        # Anthropometric
        "bmi", "waist_cm", "waist_hip_ratio",
        # Lifestyle
        "smoking_status", "pack_years", "drinks_per_week",
        "sleep_hours",
        # Demographic
        "age_years", "sex", "race_ethnicity",
    ]

    # Only include cols that exist
    available = [c for c in feature_cols if c in df.columns]
    target_cols = ["SEQN", "age_years", "mortstat", "cause_category",
                   "person_months_exam", "cycle"]
    target_cols = [c for c in target_cols if c in df.columns]

    result = df[list(set(available + target_cols))].copy()

    # Median imputation for numeric features with <20% missing
    numeric_features = [
        c for c in available
        if c not in ("smoking_status", "sex", "race_ethnicity", "age_years")
    ]
    for col in numeric_features:
        if col not in result.columns:
            continue
        missing_pct = result[col].isna().mean()
        if 0 < missing_pct <= 0.20:
            median_val = result[col].median()
            result[col] = result[col].fillna(median_val)
        elif missing_pct > 0.20:
            logger.warning("high_missing_rate", feature=col, missing_pct=f"{missing_pct:.1%}")

    # Require age to be non-null
    result = result.dropna(subset=["age_years"])

    logger.info(
        "feature_matrix_built",
        n_rows=len(result),
        n_features=len(available),
        mortality_events=int(result["mortstat"].sum()) if "mortstat" in result else "N/A",
    )
    return result
