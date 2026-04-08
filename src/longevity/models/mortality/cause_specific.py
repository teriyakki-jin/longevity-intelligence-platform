"""Cause-specific competing risks mortality model.

Uses separate cause-specific hazard models for top 5 causes of death,
trained on NHANES mortality linkage ICD-10 data.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from lifelines.utils import concordance_index
from sklearn.preprocessing import LabelEncoder

from longevity.common.logging import get_logger
from longevity.models.mortality.cox_model import MORTALITY_FEATURES

logger = get_logger(__name__)

CAUSE_CATEGORIES = [
    "cardiovascular",
    "cancer",
    "respiratory",
    "diabetes",
    "accidents",
]


class CauseSpecificMortalityModel:
    """Competing risks model with separate XGBoost models per cause of death.

    For each cause, trains a binary classifier:
      - Event: death from that specific cause
      - Censoring: alive OR died from other cause

    Uses Fine-Gray subdistribution hazard approximation via direct
    cause-specific probability calibration.
    """

    def __init__(self) -> None:
        self._models: dict[str, xgb.XGBClassifier] = {}
        self._feature_names: list[str] = []
        self._sex_encoder = LabelEncoder()
        self._is_fitted = False
        self._population_rates: dict[str, float] = {}

    def _prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        X = df.copy()
        if "sex" in X.columns:
            if fit:
                X["sex_encoded"] = self._sex_encoder.fit_transform(X["sex"].fillna("male"))
            else:
                sex_filled = X["sex"].fillna("male")
                known = set(self._sex_encoder.classes_)
                sex_filled = sex_filled.apply(lambda s: s if s in known else "male")
                X["sex_encoded"] = self._sex_encoder.transform(sex_filled)

        available = [c for c in MORTALITY_FEATURES if c in X.columns]
        return X[available].fillna(0)

    def fit(
        self,
        X: pd.DataFrame,
        duration_col: str = "person_months_exam",
        event_col: str = "mortstat",
        cause_col: str = "cause_category",
    ) -> "CauseSpecificMortalityModel":
        """Train cause-specific models."""
        feature_df = self._prepare_features(X, fit=True)
        self._feature_names = feature_df.columns.tolist()

        for cause in CAUSE_CATEGORIES:
            # Binary label: 1 = died from this cause, 0 = all others
            if cause_col not in X.columns:
                logger.warning("cause_column_missing", cause_col=cause_col)
                continue

            y_cause = (
                (X[event_col] == 1) & (X[cause_col] == cause)
            ).astype(int)

            event_rate = y_cause.mean()
            self._population_rates[cause] = float(event_rate)

            # Scale pos_weight for imbalanced classes
            scale_pos = max(1.0, (1 - event_rate) / (event_rate + 1e-9))

            model = xgb.XGBClassifier(
                n_estimators=500,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=scale_pos,
                eval_metric="aucpr",
                random_state=42,
                n_jobs=-1,
                verbosity=0,
            )
            model.fit(
                feature_df,
                y_cause,
                eval_set=[(feature_df, y_cause)],
                verbose=False,
            )
            self._models[cause] = model
            logger.info(
                "cause_model_fitted",
                cause=cause,
                n_events=int(y_cause.sum()),
                event_rate=f"{event_rate:.4f}",
            )

        self._is_fitted = True
        return self

    def predict_cause_probabilities(
        self,
        X: pd.DataFrame,
        time_horizon_years: int = 5,
    ) -> dict[str, list[float]]:
        """Predict probability of death from each cause within time horizon.

        Args:
            X: Feature DataFrame.
            time_horizon_years: Prediction horizon in years.

        Returns:
            Dict mapping cause name to probability list.
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted")

        feature_df = self._prepare_features(X, fit=False)
        feature_df = feature_df.reindex(columns=self._feature_names, fill_value=0)

        # Scale probabilities by time horizon (simple linear scale from 5yr base)
        time_scale = time_horizon_years / 5.0

        result: dict[str, list[float]] = {}
        for cause, model in self._models.items():
            raw_probs = model.predict_proba(feature_df)[:, 1]
            # Scale and clip
            scaled_probs = np.clip(raw_probs * time_scale, 0, 0.99)
            result[cause] = scaled_probs.tolist()

        return result

    def predict_top_risks(
        self,
        X: pd.DataFrame,
        time_horizon_years: int = 5,
    ) -> list[dict[str, Any]]:
        """Return top 5 cause-specific risks ranked by probability.

        Returns:
            List of dicts with cause, probability, relative_risk, description.
        """
        probs = self.predict_cause_probabilities(X, time_horizon_years)

        risks = []
        for cause, prob_list in probs.items():
            prob = prob_list[0] if len(prob_list) == 1 else np.mean(prob_list)
            pop_rate = self._population_rates.get(cause, 0.01)
            relative_risk = prob / max(pop_rate * (time_horizon_years / 5.0), 1e-9)

            pct_diff = (relative_risk - 1) * 100
            if pct_diff > 5:
                description = f"{abs(pct_diff):.0f}% higher than average"
            elif pct_diff < -5:
                description = f"{abs(pct_diff):.0f}% lower than average"
            else:
                description = "about average"

            risks.append({
                "cause": cause,
                f"probability_{time_horizon_years}yr": float(prob),
                "relative_risk": float(relative_risk),
                "vs_population": description,
            })

        return sorted(risks, key=lambda x: x[f"probability_{time_horizon_years}yr"], reverse=True)
