"""Abstract base class for all longevity models."""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from longevity.common.exceptions import ModelNotFoundError, PredictionError
from longevity.common.logging import get_logger

logger = get_logger(__name__)


class BaseModel(abc.ABC):
    """Abstract base for all longevity prediction models."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._model: Any = None
        self._is_fitted: bool = False
        self._feature_names: list[str] = []

    @abc.abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> "BaseModel":
        """Train the model."""

    @abc.abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions."""

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise PredictionError(f"Model '{self.name}' is not fitted. Call fit() first.")

    def _align_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Align input features to training feature order, filling missing with 0."""
        if not self._feature_names:
            return X
        missing = set(self._feature_names) - set(X.columns)
        if missing:
            logger.warning("missing_features_at_inference", model=self.name, missing=list(missing))
            for col in missing:
                X = X.copy()
                X[col] = 0.0
        return X[self._feature_names]

    def save(self, path: str | Path) -> Path:
        """Serialize model to disk."""
        self._check_fitted()
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model": self._model, "feature_names": self._feature_names, "name": self.name},
            dest,
            compress=3,
        )
        logger.info("model_saved", name=self.name, path=str(dest))
        return dest

    @classmethod
    def load(cls, path: str | Path) -> "BaseModel":
        """Load model from disk."""
        dest = Path(path)
        if not dest.exists():
            raise ModelNotFoundError(f"Model file not found: {dest}")
        payload = joblib.load(dest)
        instance = cls.__new__(cls)
        instance._model = payload["model"]
        instance._feature_names = payload["feature_names"]
        instance.name = payload["name"]
        instance._is_fitted = True
        logger.info("model_loaded", name=instance.name, path=str(dest))
        return instance

    def get_params(self) -> dict[str, Any]:
        """Return model hyperparameters."""
        if self._model is None:
            return {}
        if hasattr(self._model, "get_params"):
            return self._model.get_params()
        return {}
