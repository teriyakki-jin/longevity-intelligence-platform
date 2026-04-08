"""SHAP-based model explainability for biological age and mortality predictions."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import shap

from longevity.common.logging import get_logger

logger = get_logger(__name__)


class BioAgeExplainer:
    """SHAP TreeExplainer wrapper for the biological age clock."""

    def __init__(self, model: Any) -> None:
        """Initialize with a fitted BloodAgeClock or LGBMRegressor."""
        self._model = model
        # Get underlying LightGBM model
        underlying = model._model if hasattr(model, "_model") else model
        self._explainer = shap.TreeExplainer(underlying)
        self._feature_names: list[str] = getattr(model, "_feature_names", [])

    def explain(
        self,
        X: pd.DataFrame,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """Compute SHAP values and return structured explanation.

        Args:
            X: Feature DataFrame (single or multiple rows).
            top_n: Number of top factors to return.

        Returns:
            Dict with shap_values, top positive/negative factors, waterfall data.
        """
        shap_values = self._explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]  # For binary classifiers

        feature_names = X.columns.tolist()

        if len(X) == 1:
            sv = shap_values[0]
            base_value = float(self._explainer.expected_value
                               if not isinstance(self._explainer.expected_value, np.ndarray)
                               else self._explainer.expected_value[0])

            # Sort by absolute value
            sorted_idx = np.argsort(np.abs(sv))[::-1]

            positive_factors = []  # Factors adding biological age (bad)
            negative_factors = []  # Factors reducing biological age (good)

            for idx in sorted_idx[:top_n]:
                feat = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
                val = float(X.iloc[0, idx]) if idx < len(X.columns) else 0.0
                impact = float(sv[idx])

                entry = {
                    "feature": feat,
                    "value": round(val, 3),
                    "shap_impact_years": round(impact, 3),
                    "direction": "aging" if impact > 0 else "protective",
                }
                if impact > 0:
                    positive_factors.append(entry)
                else:
                    negative_factors.append(entry)

            return {
                "base_value": round(base_value, 2),
                "shap_values": {
                    feature_names[i]: round(float(sv[i]), 4)
                    for i in range(len(sv))
                    if i < len(feature_names)
                },
                "top_aging_factors": positive_factors[:top_n // 2],
                "top_protective_factors": negative_factors[:top_n // 2],
                "waterfall": [
                    {
                        "feature": feature_names[i] if i < len(feature_names) else f"f{i}",
                        "value": round(float(X.iloc[0, i]) if i < len(X.columns) else 0, 3),
                        "contribution": round(float(sv[i]), 3),
                    }
                    for i in sorted_idx[:top_n]
                ],
            }
        else:
            # Multi-sample: return mean absolute SHAP values
            mean_abs = np.mean(np.abs(shap_values), axis=0)
            sorted_idx = np.argsort(mean_abs)[::-1]
            return {
                "mean_abs_shap": {
                    feature_names[i]: round(float(mean_abs[i]), 4)
                    for i in sorted_idx[:top_n]
                    if i < len(feature_names)
                },
                "n_samples": len(X),
            }

    def global_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Compute global feature importance from SHAP values."""
        shap_values = self._explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        return (
            pd.DataFrame({
                "feature": X.columns.tolist(),
                "mean_abs_shap": mean_abs,
            })
            .sort_values("mean_abs_shap", ascending=False)
            .reset_index(drop=True)
        )
