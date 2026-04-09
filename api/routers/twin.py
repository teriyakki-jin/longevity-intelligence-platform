"""Digital twin simulation endpoint."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from longevity.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class InterventionRequest(BaseModel):
    variable: str
    current_value: float
    target_value: float


class SimulationRequest(BaseModel):
    user_features: dict[str, float | str | None] = Field(default_factory=dict)
    interventions: list[InterventionRequest] = Field(..., min_length=1, max_length=10)
    n_simulations: int = Field(500, ge=100, le=2000)
    time_horizon_years: int = Field(5, ge=1, le=20)


class InterventionEffect(BaseModel):
    intervention: str
    current_value: float
    target_value: float
    bioage_impact: float


class TrajectoryPoint(BaseModel):
    year: int
    bioage_baseline: float
    bioage_counterfactual: float


class BaselineResult(BaseModel):
    biological_age: float


class CounterfactualResult(BaseModel):
    biological_age_mean: float
    bioage_change_mean: float
    bioage_change_ci: tuple[float, float]


class SimulationResponse(BaseModel):
    success: bool
    baseline: BaselineResult
    counterfactual: CounterfactualResult
    intervention_effects: list[InterventionEffect]
    trajectory: list[TrajectoryPoint]


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_intervention(req: SimulationRequest) -> SimulationResponse:
    """Simulate health outcomes under hypothetical lifestyle interventions."""
    try:
        from api.routers.bioage import _get_bioage_model
        from longevity.models.twin.simulator import HealthTwinSimulator, Intervention

        bioage_model = _get_bioage_model()
        if bioage_model is None:
            raise HTTPException(status_code=503, detail="Bioage model not available")

        # Build feature DataFrame from flat dict; fill defaults for required fields
        features = dict(req.user_features)
        features.setdefault("age_years", 40.0)
        features.setdefault("sex", "male")
        features.setdefault("exercise_minutes_per_week", 60.0)
        features.setdefault("sleep_hours", 6.5)
        features.setdefault("drinks_per_week", 7.0)
        features.setdefault("smoking_status", "never")
        features.setdefault("pack_years", 0.0)

        # Merge in intervention current values so baseline uses them
        for iv in req.interventions:
            features[iv.variable] = iv.current_value

        df = pd.DataFrame([features])

        simulator = HealthTwinSimulator()
        simulator.set_models(bioage_model=bioage_model, mortality_model=None)

        interventions = [
            Intervention(
                variable=iv.variable,
                current_value=iv.current_value,
                target_value=iv.target_value,
            )
            for iv in req.interventions
        ]

        result = simulator.simulate(
            user_features=df,
            interventions=interventions,
            n_simulations=req.n_simulations,
            time_horizon_years=req.time_horizon_years,
        )

        return SimulationResponse(
            success=True,
            baseline=BaselineResult(
                biological_age=result["baseline"]["biological_age"],
            ),
            counterfactual=CounterfactualResult(
                biological_age_mean=result["counterfactual"]["biological_age_mean"],
                bioage_change_mean=result["counterfactual"]["bioage_change_mean"],
                bioage_change_ci=result["counterfactual"]["bioage_change_ci"],
            ),
            intervention_effects=[
                InterventionEffect(**e) for e in result["intervention_effects"]
            ],
            trajectory=[TrajectoryPoint(**t) for t in result["trajectory"]],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("simulation_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")
