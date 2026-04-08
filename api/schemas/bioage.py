from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class BloodMarkersRequest(BaseModel):
    glucose_mg_dl: float | None = Field(None, ge=30, le=600)
    hba1c_pct: float | None = Field(None, ge=3.0, le=20.0)
    total_cholesterol_mg_dl: float | None = Field(None, ge=50, le=700)
    hdl_mg_dl: float | None = Field(None, ge=10, le=150)
    ldl_mg_dl: float | None = Field(None, ge=10, le=500)
    triglycerides_mg_dl: float | None = Field(None, ge=10, le=5000)
    creatinine_mg_dl: float | None = Field(None, ge=0.1, le=20.0)
    alt_u_l: float | None = Field(None, ge=1, le=5000)
    ast_u_l: float | None = Field(None, ge=1, le=5000)
    albumin_g_dl: float | None = Field(None, ge=1.0, le=6.0)
    wbc_1000_ul: float | None = Field(None, ge=0.5, le=50.0)
    hemoglobin_g_dl: float | None = Field(None, ge=3.0, le=25.0)
    platelets_1000_ul: float | None = Field(None, ge=10, le=1500)
    crp_mg_l: float | None = Field(None, ge=0.0, le=300.0)
    uric_acid_mg_dl: float | None = Field(None, ge=0.5, le=20.0)


class DemographicsRequest(BaseModel):
    chronological_age: float = Field(..., ge=18, le=120)
    sex: Literal["male", "female"]
    height_cm: float | None = Field(None, ge=100, le=250)
    weight_kg: float | None = Field(None, ge=20, le=400)
    waist_cm: float | None = Field(None, ge=40, le=200)


class LifestyleRequest(BaseModel):
    smoking_status: Literal["never", "former", "current"] = "never"
    pack_years: float = Field(0.0, ge=0, le=300)
    drinks_per_week: float = Field(0.0, ge=0, le=150)
    exercise_minutes_per_week: float = Field(0.0, ge=0, le=2000)
    sleep_hours: float = Field(7.0, ge=2.0, le=14.0)


class BioAgeRequest(BaseModel):
    blood_markers: BloodMarkersRequest
    demographics: DemographicsRequest
    lifestyle: LifestyleRequest
    include_explanation: bool = True


class ShapFactor(BaseModel):
    feature: str
    value: float
    shap_impact_years: float
    direction: str


class BioAgeResponse(BaseModel):
    success: bool
    biological_age: float
    chronological_age: float
    age_acceleration: float
    percentile_for_age: float
    confidence_interval: tuple[float, float]
    interpretation: str
    top_aging_factors: list[ShapFactor] = []
    top_protective_factors: list[ShapFactor] = []
    disclaimer: str = (
        "This is a statistical estimate based on population data. "
        "It is not a medical diagnosis. Consult your doctor for personalized advice."
    )
