"""Mortality risk prediction endpoint."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.schemas.bioage import BioAgeRequest
from longevity.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_mortality_model = None
_cause_model = None


def _get_models():
    global _mortality_model, _cause_model
    if _mortality_model is None:
        try:
            from longevity.models.mortality.cox_model import CoxMortalityModel
            from longevity.models.mortality.cause_specific import CauseSpecificMortalityModel
            _mortality_model = CoxMortalityModel.load("models/mortality/cox.joblib")
            _cause_model = CauseSpecificMortalityModel.load("models/mortality/cause_specific.joblib")
        except Exception as e:
            logger.warning("mortality_model_not_loaded", error=str(e))
    return _mortality_model, _cause_model


class RiskEntry(BaseModel):
    cause: str
    probability_5yr: float
    relative_risk: float
    vs_population: str


class SurvivalPoint(BaseModel):
    year: int
    probability: float


class MortalityResponse(BaseModel):
    success: bool
    five_year_survival_probability: float
    ten_year_survival_probability: float
    top_risks: list[RiskEntry]
    survival_curve: list[SurvivalPoint]
    disclaimer: str = (
        "Mortality risk estimates are based on population statistics. "
        "They do not predict individual outcomes. Consult your doctor."
    )


def _request_to_df(req: BioAgeRequest) -> pd.DataFrame:
    from api.routers.bioage import _request_to_dataframe
    return _request_to_dataframe(req)


@router.post("/predict", response_model=MortalityResponse)
async def predict_mortality(req: BioAgeRequest) -> MortalityResponse:
    """Predict 5-year and 10-year mortality risk with cause breakdown."""
    cox_model, cause_model = _get_models()

    if cox_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mortality model not available. Train the model first.",
        )

    try:
        df = _request_to_df(req)

        # Survival at 5 and 10 years
        surv = cox_model.predict_survival_function(df, times=[60, 120])
        five_yr_surv = float(surv.iloc[0, 0]) if not surv.empty else 0.95
        ten_yr_surv = float(surv.iloc[1, 0]) if len(surv) > 1 else 0.88

        # Survival curve (year 0-10)
        times_months = [y * 12 for y in range(11)]
        surv_curve = cox_model.predict_survival_function(df, times=times_months)
        survival_curve = [
            SurvivalPoint(year=y, probability=round(float(surv_curve.iloc[i, 0]), 4))
            for i, y in enumerate(range(11))
            if i < len(surv_curve)
        ]

        # Cause-specific risks
        top_risks: list[RiskEntry] = []
        if cause_model is not None:
            risks = cause_model.predict_top_risks(df, time_horizon_years=5)
            top_risks = [
                RiskEntry(
                    cause=r["cause"],
                    probability_5yr=round(r.get("probability_5yr", 0), 4),
                    relative_risk=round(r.get("relative_risk", 1.0), 2),
                    vs_population=r.get("vs_population", ""),
                )
                for r in risks
            ]

        return MortalityResponse(
            success=True,
            five_year_survival_probability=round(five_yr_surv, 4),
            ten_year_survival_probability=round(ten_yr_surv, 4),
            top_risks=top_risks,
            survival_curve=survival_curve,
        )

    except Exception as e:
        logger.error("mortality_prediction_error", error=str(e))
        raise HTTPException(status_code=500, detail="Mortality prediction failed")
