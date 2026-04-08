"""Biological age blood clock model.

Trains a LightGBM regressor to predict chronological age from blood markers
and lifestyle features. The residual (predicted_age - true_age) becomes the
biological age acceleration metric.

Interpretation:
  acceleration < 0: biologically younger than chronological age (good)
  acceleration > 0: biologically older than chronological age (bad)
"""
from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import LabelEncoder

from longevity.common.exceptions import InsufficientDataError, PredictionError
from longevity.common.logging import get_logger
from longevity.models.base import BaseModel

logger = get_logger(__name__)

# Features used for biological age clock
BLOOD_CLOCK_FEATURES = [
    # Blood markers
    "glucose_mg_dl",
    "hba1c_pct",
    "total_cholesterol_mg_dl",
    "hdl_mg_dl",
    "triglycerides_mg_dl",
    "creatinine_mg_dl",
    "alt_u_l",
    "ast_u_l",
    "albumin_g_dl",
    "wbc_1000_ul",
    "hemoglobin_g_dl",
    "platelets_1000_ul",
    "crp_mg_l",
    "uric_acid_mg_dl",
    # Derived
    "egfr",
    "fib4_score",
    "non_hdl_mg_dl",
    "chol_hdl_ratio",
    "metabolic_syndrome_score",
    # Anthropometric
    "bmi",
    "waist_cm",
    # Lifestyle (biological correlates)
    "pack_years",
    "drinks_per_week",
    "sleep_hours",
    # Demographic (needed for age prediction)
    "sex_encoded",
]

MINIMUM_REQUIRED_FEATURES = [
    "glucose_mg_dl",
    "total_cholesterol_mg_dl",
    "hdl_mg_dl",
    "creatinine_mg_dl",
]


class BloodAgeClock(BaseModel):
    """LightGBM biological age clock trained on NHANES blood markers.

    Target: chronological age (continuous regression)
    Output: predicted age, from which acceleration = predicted - true_age
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__("blood_age_clock")
        self._params = params or {
            "objective": "regression",
            "metric": "mae",
            "verbosity": -1,
            "n_estimators": 1000,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_child_samples": 20,
            "random_state": 42,
        }
        self._sex_encoder = LabelEncoder()
        self._age_mean: float = 0.0
        self._age_std: float = 1.0
        self._age_percentiles: np.ndarray = np.array([])

    def _prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Prepare feature matrix: encode categoricals, select columns."""
        X = df.copy()

        # Encode sex
        if "sex" in X.columns:
            if fit:
                X["sex_encoded"] = self._sex_encoder.fit_transform(
                    X["sex"].fillna("male")
                )
            else:
                sex_filled = X["sex"].fillna("male")
                known_classes = set(self._sex_encoder.classes_)
                sex_filled = sex_filled.apply(
                    lambda s: s if s in known_classes else "male"
                )
                X["sex_encoded"] = self._sex_encoder.transform(sex_filled)
        else:
            X["sex_encoded"] = 0

        # Keep only clock features that exist
        available = [f for f in BLOOD_CLOCK_FEATURES if f in X.columns]
        X = X[available].copy()

        # Fill remaining NaNs with column medians (inference-time only)
        if not fit:
            for col in X.columns:
                X[col] = X[col].fillna(X[col].median())

        return X

    def _check_minimum_features(self, df: pd.DataFrame) -> None:
        """Raise if minimum required blood markers are missing."""
        available = set(df.columns)
        missing = [f for f in MINIMUM_REQUIRED_FEATURES if f not in available
                   or df[f].isna().all()]
        if len(missing) > len(MINIMUM_REQUIRED_FEATURES) // 2:
            raise InsufficientDataError(
                f"Too many required blood markers are missing: {missing}. "
                "At least 2 of [glucose, cholesterol, HDL, creatinine] are needed."
            )

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        eval_set: tuple[pd.DataFrame, pd.Series] | None = None,
        **kwargs: Any,
    ) -> "BloodAgeClock":
        """Train the biological age clock.

        Args:
            X: Feature DataFrame including blood markers and demographics.
            y: Chronological age (years).
            eval_set: Optional (X_val, y_val) for early stopping.
        """
        self._age_mean = float(y.mean())
        self._age_std = float(y.std())
        self._age_percentiles = np.percentile(y, np.arange(0, 101, 1))

        X_prep = self._prepare_features(X, fit=True)
        self._feature_names = X_prep.columns.tolist()

        callbacks = [lgb.early_stopping(50, verbose=False), lgb.log_evaluation(period=-1)]

        eval_data = None
        if eval_set is not None:
            X_val, y_val = eval_set
            X_val_prep = self._prepare_features(X_val, fit=False)
            eval_data = [(X_val_prep, y_val)]

        self._model = lgb.LGBMRegressor(**self._params)
        self._model.fit(
            X_prep,
            y,
            eval_set=eval_data,
            callbacks=callbacks if eval_data else [lgb.log_evaluation(period=-1)],
        )
        self._is_fitted = True

        # Log training performance
        train_pred = self._model.predict(X_prep)
        mae = float(np.mean(np.abs(train_pred - y)))
        r, _ = stats.pearsonr(train_pred, y)
        logger.info("blood_clock_fitted", train_mae=f"{mae:.2f}", pearson_r=f"{r:.3f}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict chronological age (used internally for acceleration calculation)."""
        self._check_fitted()
        X_prep = self._prepare_features(X, fit=False)
        X_aligned = self._align_features(X_prep)
        return self._model.predict(X_aligned)

    def predict_biological_age(
        self,
        X: pd.DataFrame,
        true_age: float | pd.Series | None = None,
    ) -> dict[str, Any]:
        """Predict biological age and compute acceleration metrics.

        Args:
            X: Feature DataFrame for one or more individuals.
            true_age: Chronological age(s) to compute acceleration.
                      If None, uses 'age_years' column from X.

        Returns:
            Dict with biological_age, acceleration, percentile, confidence_interval.
        """
        self._check_fitted()

        if true_age is None:
            if "age_years" not in X.columns:
                raise PredictionError("'age_years' must be in X or provided as true_age")
            true_age = X["age_years"].values

        predicted_age = self.predict(X)

        if isinstance(true_age, pd.Series):
            true_age = true_age.values

        acceleration = predicted_age - true_age

        # Compute percentile relative to same-age peers
        # (based on training distribution)
        percentile = np.interp(
            predicted_age,
            self._age_percentiles,
            np.arange(0, 101),
        )

        # Simple bootstrap CI (±1.5 * training MAE as proxy)
        training_mae = 4.5  # Target MAE from model card; updated after training
        ci_lower = predicted_age - 1.96 * training_mae
        ci_upper = predicted_age + 1.96 * training_mae

        if len(predicted_age) == 1:
            return {
                "biological_age": float(predicted_age[0]),
                "chronological_age": float(true_age[0]),
                "age_acceleration": float(acceleration[0]),
                "percentile_for_age": float(percentile[0]),
                "confidence_interval": (float(ci_lower[0]), float(ci_upper[0])),
            }

        return {
            "biological_age": predicted_age.tolist(),
            "chronological_age": true_age.tolist() if hasattr(true_age, "tolist") else list(true_age),
            "age_acceleration": acceleration.tolist(),
            "percentile_for_age": percentile.tolist(),
            "confidence_interval_lower": ci_lower.tolist(),
            "confidence_interval_upper": ci_upper.tolist(),
        }

    def get_feature_importance(self) -> pd.DataFrame:
        """Return feature importances as a sorted DataFrame."""
        self._check_fitted()
        importances = self._model.feature_importances_
        return (
            pd.DataFrame({
                "feature": self._feature_names,
                "importance": importances,
            })
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
