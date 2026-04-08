"""Digital twin simulation endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.schemas.bioage import BioAgeRequest
from longevity.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class InterventionRequest(BaseModel):
    variable: str
    current: float
    target: float


class SimulationRequest(BaseModel):
    user_profile: BioAgeRequest
    interventions: list[InterventionRequest] = Field(..., min_length=1, max_length=10)
    time_horizon_years: int = Field(5, ge=1, le=20)
    n_simulations: int = Field(500, ge=100, le=2000)


class InterventionEffect(BaseModel):
    intervention: str
    current_value: float
    target_value: float
    bioage_impact: float


class TrajectoryPoint(BaseModel):
    year: int
    bioage_baseline: float
    bioage_counterfactual: float


class SimulationResponse(BaseModel):
    success: bool
    baseline_biological_age: float
    counterfactual_biological_age_mean: float
    counterfactual_biological_age_ci: tuple[float, float]
    bioage_change_mean: float
    bioage_change_ci: tuple[float, float]
    intervention_effects: list[InterventionEffect]
    trajectory: list[TrajectoryPoint]
    n_simulations: int
    disclaimer: str


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_intervention(req: SimulationRequest) -> SimulationResponse:
    """Simulate health outcomes under hypothetical lifestyle interventions."""
    try:
        from api.routers.bioage import _get_bioage_model, _request_to_dataframe
        from longevity.models.twin.simulator import HealthTwinSimulator, Intervention

        bioage_model = _get_bioage_model()
        if bioage_model is None:
            raise HTTPException(status_code=503, detail="Bioage model not available")

        df = _request_to_dataframe(req.user_profile)

        simulator = HealthTwinSimulator()
        simulator.set_models(bioage_model=bioage_model, mortality_model=None)

        interventions = [
            Intervention(
                variable=iv.variable,
                current_value=iv.current,
                target_value=iv.target,
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
            baseline_biological_age=result["baseline"]["biological_age"],
            counterfactual_biological_age_mean=result["counterfactual"]["biological_age_mean"],
            counterfactual_biological_age_ci=result["counterfactual"]["biological_age_ci"],
            bioage_change_mean=result["counterfactual"]["bioage_change_mean"],
            bioage_change_ci=result["counterfactual"]["bioage_change_ci"],
            intervention_effects=[
                InterventionEffect(**e) for e in result["intervention_effects"]
            ],
            trajectory=[TrajectoryPoint(**t) for t in result["trajectory"]],
            n_simulations=result["n_simulations"],
            disclaimer=result["disclaimer"],
        )

    except Exception as e:
        logger.error("simulation_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")
