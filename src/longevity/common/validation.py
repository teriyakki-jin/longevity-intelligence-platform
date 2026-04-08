from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal


SexType = Literal["male", "female"]
SmokingStatus = Literal["never", "former", "current"]


class BloodMarkersSchema(BaseModel):
    glucose_mg_dl: float | None = Field(None, ge=30, le=600, description="Fasting glucose (mg/dL)")
    hba1c_pct: float | None = Field(None, ge=3.0, le=20.0, description="HbA1c (%)")
    total_cholesterol_mg_dl: float | None = Field(None, ge=50, le=700, description="Total cholesterol (mg/dL)")
    hdl_mg_dl: float | None = Field(None, ge=10, le=150, description="HDL cholesterol (mg/dL)")
    ldl_mg_dl: float | None = Field(None, ge=10, le=500, description="LDL cholesterol (mg/dL)")
    triglycerides_mg_dl: float | None = Field(None, ge=10, le=5000, description="Triglycerides (mg/dL)")
    creatinine_mg_dl: float | None = Field(None, ge=0.1, le=20.0, description="Serum creatinine (mg/dL)")
    alt_u_l: float | None = Field(None, ge=1, le=5000, description="ALT (U/L)")
    ast_u_l: float | None = Field(None, ge=1, le=5000, description="AST (U/L)")
    albumin_g_dl: float | None = Field(None, ge=1.0, le=6.0, description="Albumin (g/dL)")
    wbc_1000_ul: float | None = Field(None, ge=0.5, le=50.0, description="WBC (1000/uL)")
    hemoglobin_g_dl: float | None = Field(None, ge=3.0, le=25.0, description="Hemoglobin (g/dL)")
    platelets_1000_ul: float | None = Field(None, ge=10, le=1500, description="Platelets (1000/uL)")
    crp_mg_l: float | None = Field(None, ge=0.0, le=300.0, description="High-sensitivity CRP (mg/L)")
    uric_acid_mg_dl: float | None = Field(None, ge=0.5, le=20.0, description="Uric acid (mg/dL)")
    insulin_uu_ml: float | None = Field(None, ge=0.5, le=200.0, description="Fasting insulin (uU/mL)")

    @field_validator("hba1c_pct")
    @classmethod
    def validate_hba1c(cls, v: float | None) -> float | None:
        if v is not None and v > 15:
            raise ValueError("HbA1c > 15% is extremely rare — please verify the value")
        return v


class DemographicsSchema(BaseModel):
    chronological_age: float = Field(..., ge=18, le=120, description="Age in years")
    sex: SexType
    height_cm: float | None = Field(None, ge=100, le=250, description="Height (cm)")
    weight_kg: float | None = Field(None, ge=20, le=400, description="Weight (kg)")
    waist_cm: float | None = Field(None, ge=40, le=200, description="Waist circumference (cm)")
    race_ethnicity: str | None = None

    @model_validator(mode="after")
    def validate_bmi_plausibility(self) -> "DemographicsSchema":
        if self.height_cm and self.weight_kg:
            bmi = self.weight_kg / ((self.height_cm / 100) ** 2)
            if bmi < 10 or bmi > 70:
                raise ValueError(f"Computed BMI {bmi:.1f} is implausible — check height/weight")
        return self


class LifestyleSchema(BaseModel):
    smoking_status: SmokingStatus = "never"
    pack_years: float = Field(0.0, ge=0, le=300, description="Pack-years smoked")
    drinks_per_week: float = Field(0.0, ge=0, le=150, description="Standard alcoholic drinks per week")
    exercise_minutes_per_week: float = Field(0.0, ge=0, le=2000, description="Moderate-vigorous exercise minutes/week")
    sleep_hours: float = Field(7.0, ge=2.0, le=14.0, description="Average sleep hours per night")

    @field_validator("pack_years")
    @classmethod
    def validate_pack_years_with_status(cls, v: float) -> float:
        return v


class UserProfileSchema(BaseModel):
    blood_markers: BloodMarkersSchema
    demographics: DemographicsSchema
    lifestyle: LifestyleSchema
    include_explanation: bool = True

    def has_minimum_blood_markers(self) -> bool:
        required = ["glucose_mg_dl", "total_cholesterol_mg_dl", "hdl_mg_dl", "creatinine_mg_dl"]
        return all(
            getattr(self.blood_markers, field) is not None
            for field in required
        )


class InterventionSchema(BaseModel):
    variable: str = Field(..., description="Variable name to intervene on")
    current: float = Field(..., description="Current value")
    target: float = Field(..., description="Target value after intervention")

    VALID_VARIABLES = {
        "exercise_minutes_per_week",
        "sleep_hours",
        "drinks_per_week",
        "bmi",
        "smoking_status_encoded",
    }

    @field_validator("variable")
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        if v not in cls.VALID_VARIABLES:
            raise ValueError(f"Variable '{v}' is not a valid intervention target. Valid: {cls.VALID_VARIABLES}")
        return v


class SimulationRequestSchema(BaseModel):
    user_profile: UserProfileSchema
    interventions: list[InterventionSchema] = Field(..., min_length=1, max_length=10)
    time_horizon_years: int = Field(5, ge=1, le=20)
    n_simulations: int = Field(1000, ge=100, le=5000)


class ChatMessageSchema(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    user_profile: UserProfileSchema | None = None
    stream: bool = True
