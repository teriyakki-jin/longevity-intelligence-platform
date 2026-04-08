"""Cox Proportional Hazards mortality risk model.

Uses lifelines CoxPHFitter as the interpretable baseline model.
Provides hazard ratios and survival curves.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index

from longevity.common.exceptions import InsufficientDataError, PredictionError
from longevity.common.logging import get_logger
from longevity.models.base import BaseModel

logger = get_logger(__name__)

# Features for mortality model (subset of blood clock features)
MORTALITY_FEATURES = [
    "age_years",
    "sex_encoded",
    "glucose_mg_dl",
    "hba1c_pct",
    "total_cholesterol_mg_dl",
    "hdl_mg_dl",
    "triglycerides_mg_dl",
    "creatinine_mg_dl",
    "egfr",
    "alt_u_l",
    "albumin_g_dl",
    "wbc_1000_ul",
    "hemoglobin_g_dl",
    "crp_mg_l",
    "bmi",
    "waist_cm",
    "pack_years",
    "drinks_per_week",
    "sleep_hours",
    "metabolic_syndrome_score",
    "fib4_score",
]


class CoxMortalityModel(BaseModel):
    """Cox PH model for all-cause mortality prediction."""

    def __init__(self, penalizer: float = 0.1, l1_ratio: float = 0.5) -> None:
        super().__init__("cox_mortality")
        self.penalizer = penalizer
        self.l1_ratio = l1_ratio
        self._duration_col = "person_months_exam"
        self._event_col = "mortstat"
        self._baseline_survival: pd.DataFrame | None = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series | None = None,  # Not used; duration + event in X
        duration_col: str = "person_months_exam",
        event_col: str = "mortstat",
        **kwargs: Any,
    ) -> "CoxMortalityModel":
        """Train Cox PH model.

        Args:
            X: DataFrame with feature columns + duration_col + event_col.
            y: Ignored (survival data is in X).
            duration_col: Column with time-to-event or censoring (months).
            event_col: Binary column: 1=deceased, 0=censored/alive.
        """
        self._duration_col = duration_col
        self._event_col = event_col

        # Select features that exist
        feature_cols = [c for c in MORTALITY_FEATURES if c in X.columns]
        train_df = X[feature_cols + [duration_col, event_col]].dropna(
            subset=[duration_col, event_col]
        )

        # Filter valid durations
        train_df = train_df[train_df[duration_col] > 0]
        train_df[event_col] = train_df[event_col].astype(int)

        self._feature_names = feature_cols

        logger.info(
            "fitting_cox_model",
            n_samples=len(train_df),
            n_events=int(train_df[event_col].sum()),
            event_rate=f"{train_df[event_col].mean():.3f}",
        )

        self._model = CoxPHFitter(penalizer=self.penalizer, l1_ratio=self.l1_ratio)
        self._model.fit(
            train_df,
            duration_col=duration_col,
            event_col=event_col,
            show_progress=False,
        )
        self._is_fitted = True

        # Compute training C-index
        train_preds = self._model.predict_log_partial_hazard(train_df[feature_cols])
        cindex = concordance_index(
            train_df[duration_col], -train_preds, train_df[event_col]
        )
        logger.info("cox_model_fitted", train_cindex=f"{cindex:.4f}")
        self._baseline_survival = self._model.baseline_survival_

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict log partial hazard (higher = more risk)."""
        self._check_fitted()
        feature_cols = [c for c in self._feature_names if c in X.columns]
        return self._model.predict_log_partial_hazard(X[feature_cols]).values

    def predict_survival_function(
        self,
        X: pd.DataFrame,
        times: list[float] | None = None,
    ) -> pd.DataFrame:
        """Predict survival probabilities at specified time points.

        Args:
            X: Feature DataFrame.
            times: Time points in months. Defaults to 12, 36, 60, 120 months.

        Returns:
            DataFrame with time as index, participants as columns.
        """
        self._check_fitted()
        feature_cols = [c for c in self._feature_names if c in X.columns]
        if times is None:
            times = [12, 36, 60, 120]  # 1, 3, 5, 10 years in months
        return self._model.predict_survival_function(X[feature_cols], times=times)

    def predict_risk_at_years(
        self,
        X: pd.DataFrame,
        years: list[int] = [5, 10],
    ) -> dict[str, list[float]]:
        """Predict mortality probability at specified year horizons.

        Returns:
            Dict with 'mortality_risk_{n}yr' keys mapping to probability lists.
        """
        self._check_fitted()
        times_months = [y * 12 for y in years]
        surv = self.predict_survival_function(X, times=times_months)

        result: dict[str, list[float]] = {}
        for year, month in zip(years, times_months):
            if month in surv.index:
                probs = (1 - surv.loc[month]).tolist()
            else:
                # Interpolate
                probs = (1 - surv.iloc[-1]).tolist()
            result[f"mortality_risk_{year}yr"] = probs

        return result

    def get_hazard_ratios(self) -> pd.DataFrame:
        """Return model hazard ratios with confidence intervals."""
        self._check_fitted()
        return self._model.summary[["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]

    def compute_cindex(self, X: pd.DataFrame, duration_col: str, event_col: str) -> float:
        """Evaluate C-index on new data."""
        self._check_fitted()
        feature_cols = [c for c in self._feature_names if c in X.columns]
        log_hazard = self._model.predict_log_partial_hazard(X[feature_cols])
        return float(concordance_index(X[duration_col], -log_hazard, X[event_col]))
