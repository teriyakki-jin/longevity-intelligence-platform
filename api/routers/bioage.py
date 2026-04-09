"""Biological age prediction endpoint."""
from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, status

from api.schemas.bioage import BioAgeRequest, BioAgeResponse, ShapFactor
from longevity.common.exceptions import InsufficientDataError, ModelNotFoundError
from longevity.common.logging import get_logger
from longevity.explainability.report import generate_bioage_interpretation

logger = get_logger(__name__)
router = APIRouter()

# Lazy-loaded model singleton
_bioage_model = None
_explainer = None


def _get_bioage_model():
    global _bioage_model, _explainer
    if _bioage_model is None:
        try:
            from longevity.models.bioage.blood_clock import BloodAgeClock
            _bioage_model = BloodAgeClock.load("models/bioage/blood_clock.joblib")
        except Exception as e:
            logger.warning("bioage_model_not_loaded", error=str(e))
            _bioage_model = None
    return _bioage_model


def _request_to_dataframe(req: BioAgeRequest) -> pd.DataFrame:
    """Convert API request to feature DataFrame."""
    row: dict = {}

    # Blood markers
    for field, val in req.blood_markers.model_dump().items():
        row[field] = val

    # Demographics
    row["age_years"] = req.demographics.chronological_age
    row["sex"] = req.demographics.sex
    row["height_cm"] = req.demographics.height_cm
    row["weight_kg"] = req.demographics.weight_kg
    row["waist_cm"] = req.demographics.waist_cm

    # Compute BMI
    if row.get("height_cm") and row.get("weight_kg"):
        row["bmi"] = row["weight_kg"] / ((row["height_cm"] / 100) ** 2)

    # Lifestyle
    row["smoking_status"] = req.lifestyle.smoking_status
    row["pack_years"] = req.lifestyle.pack_years
    row["drinks_per_week"] = req.lifestyle.drinks_per_week
    row["exercise_minutes_per_week"] = req.lifestyle.exercise_minutes_per_week
    row["sleep_hours"] = req.lifestyle.sleep_hours

    return pd.DataFrame([row])


@router.post("/predict", response_model=BioAgeResponse)
async def predict_bioage(req: BioAgeRequest) -> BioAgeResponse:
    """Predict biological age from blood markers and lifestyle data."""
    model = _get_bioage_model()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Biological age model not available. Train the model first.",
        )

    try:
        df = _request_to_dataframe(req)
        result = model.predict_biological_age(df, true_age=[req.demographics.chronological_age])

        biological_age = float(result["biological_age"])
        chronological_age = float(result["chronological_age"])
        acceleration = float(result["age_acceleration"])
        percentile = float(result["percentile_for_age"])
        ci = result["confidence_interval"]

        interpretation = generate_bioage_interpretation(
            biological_age, chronological_age, acceleration, percentile
        )

        aging_factors: list[ShapFactor] = []
        protective_factors: list[ShapFactor] = []

        if req.include_explanation:
            try:
                from longevity.explainability.shap_explainer import BioAgeExplainer
                explainer = BioAgeExplainer(model)
                explanation = explainer.explain(df)
                aging_factors = [ShapFactor(**f) for f in explanation.get("top_aging_factors", [])]
                protective_factors = [ShapFactor(**f) for f in explanation.get("top_protective_factors", [])]
            except Exception as e:
                logger.warning("shap_explanation_failed", error=str(e))

        return BioAgeResponse(
            success=True,
            biological_age=biological_age,
            chronological_age=chronological_age,
            age_acceleration=acceleration,
            percentile_for_age=percentile,
            confidence_interval=ci,
            interpretation=interpretation,
            top_aging_factors=aging_factors,
            top_protective_factors=protective_factors,
        )

    except InsufficientDataError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("bioage_prediction_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction failed: {e}")
