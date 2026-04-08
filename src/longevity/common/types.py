from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SexType = Literal["male", "female"]
SmokingStatus = Literal["never", "former", "current"]
RaceEthnicity = Literal[
    "mexican_american",
    "other_hispanic",
    "non_hispanic_white",
    "non_hispanic_black",
    "non_hispanic_asian",
    "other",
]


@dataclass(frozen=True)
class BloodMarkers:
    glucose_mg_dl: float | None = None
    hba1c_pct: float | None = None
    total_cholesterol_mg_dl: float | None = None
    hdl_mg_dl: float | None = None
    ldl_mg_dl: float | None = None
    triglycerides_mg_dl: float | None = None
    creatinine_mg_dl: float | None = None
    alt_u_l: float | None = None
    ast_u_l: float | None = None
    albumin_g_dl: float | None = None
    wbc_1000_ul: float | None = None
    hemoglobin_g_dl: float | None = None
    platelets_1000_ul: float | None = None
    crp_mg_l: float | None = None
    uric_acid_mg_dl: float | None = None
    insulin_uu_ml: float | None = None


@dataclass(frozen=True)
class Demographics:
    chronological_age: float
    sex: SexType
    height_cm: float | None = None
    weight_kg: float | None = None
    waist_cm: float | None = None
    race_ethnicity: RaceEthnicity | None = None


@dataclass(frozen=True)
class Lifestyle:
    smoking_status: SmokingStatus = "never"
    pack_years: float = 0.0
    drinks_per_week: float = 0.0
    exercise_minutes_per_week: float = 0.0
    sleep_hours: float = 7.0


@dataclass(frozen=True)
class UserProfile:
    blood_markers: BloodMarkers
    demographics: Demographics
    lifestyle: Lifestyle


@dataclass
class BioAgePrediction:
    biological_age: float
    chronological_age: float
    age_acceleration: float
    percentile_for_age: float
    confidence_interval: tuple[float, float]
    interpretation: str
    shap_values: dict[str, float] = field(default_factory=dict)
    top_positive_factors: list[dict] = field(default_factory=list)
    top_negative_factors: list[dict] = field(default_factory=list)


@dataclass
class MortalityRisk:
    cause: str
    five_year_probability: float
    ten_year_probability: float
    relative_risk: float
    vs_population_description: str


@dataclass
class MortalityPrediction:
    five_year_survival_probability: float
    ten_year_survival_probability: float
    top_risks: list[MortalityRisk]
    survival_curve: list[dict[str, float]]
    key_modifiable_risks: list[dict]


@dataclass
class InterventionEffect:
    intervention: str
    variable: str
    current_value: float
    target_value: float
    bioage_impact_mean: float
    bioage_impact_ci: tuple[float, float]
    survival_impact_mean: float


@dataclass
class SimulationResult:
    baseline_bioage: float
    baseline_survival_5yr: float
    counterfactual_bioage_mean: float
    counterfactual_bioage_ci: tuple[float, float]
    counterfactual_survival_5yr_mean: float
    counterfactual_survival_5yr_ci: tuple[float, float]
    intervention_effects: list[InterventionEffect]
    trajectory: list[dict[str, float]]


@dataclass
class FoodRecognitionResult:
    foods_detected: list[dict]
    total_nutrition: dict[str, float]
    health_score: float
    bioage_impact: Literal["very_positive", "positive", "neutral_to_positive", "neutral", "negative", "very_negative"]
