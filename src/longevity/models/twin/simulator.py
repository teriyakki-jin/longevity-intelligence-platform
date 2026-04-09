"""Digital Health Twin Simulator.

Simulates counterfactual health outcomes by:
1. Propagating lifestyle interventions through a causal DAG
2. Re-running biological age and mortality models on counterfactual features
3. Monte Carlo sampling of uncertainty in causal effect sizes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from longevity.common.config import load_yaml_config
from longevity.common.exceptions import CausalInferenceError
from longevity.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Intervention:
    variable: str
    current_value: float
    target_value: float


@dataclass
class SimulationOutcome:
    """Result of a single Monte Carlo simulation run."""
    bioage_baseline: float
    bioage_counterfactual: float
    survival_5yr_baseline: float
    survival_5yr_counterfactual: float


class HealthTwinSimulator:
    """Monte Carlo digital twin for health intervention simulation.

    Uses causal DAG from config/twin.yaml to propagate interventions
    through related biomarkers, then re-evaluates health models.
    """

    def __init__(self, config_path: str = "config/twin.yaml") -> None:
        self._config = load_yaml_config(config_path)
        self._causal_edges = self._config.get("causal_graph", {}).get("edges", [])
        self._bioage_model: Any = None
        self._mortality_model: Any = None

    def set_models(self, bioage_model: Any, mortality_model: Any) -> None:
        """Inject fitted bioage and mortality models."""
        self._bioage_model = bioage_model
        self._mortality_model = mortality_model

    def _build_effect_map(self) -> dict[str, list[dict]]:
        """Build source -> downstream effects mapping from causal edges."""
        effect_map: dict[str, list[dict]] = {}
        for edge in self._causal_edges:
            src = edge["source"]
            if src not in effect_map:
                effect_map[src] = []
            effect_map[src].append({
                "target": edge["target"],
                "effect_size": edge["effect_size"],
                "effect_direction": edge["effect_direction"],
            })
        return effect_map

    def _apply_intervention_to_features(
        self,
        features: pd.DataFrame,
        intervention: Intervention,
        effect_map: dict[str, list[dict]],
        noise_scale: float = 1.0,
    ) -> pd.DataFrame:
        """Apply a single intervention and propagate through causal graph.

        Args:
            features: Current feature values (single row).
            intervention: The intervention to apply.
            effect_map: Source -> downstream effects from causal DAG.
            noise_scale: Multiplier for effect size noise (Monte Carlo sampling).

        Returns:
            Updated feature DataFrame with counterfactual values.
        """
        counterfactual = features.copy()
        delta = intervention.target_value - intervention.current_value

        # Direct change to intervention variable
        if intervention.variable in counterfactual.columns:
            counterfactual[intervention.variable] = intervention.target_value

        # Propagate through causal graph (one level of mediation)
        # Typical ranges for normalization (intervention variable -> typical SD)
        _typical_sd: dict[str, float] = {
            "exercise_minutes_per_week": 120.0,
            "sleep_hours": 1.5,
            "drinks_per_week": 7.0,
            "bmi": 5.0,
            "smoking_status": 1.0,
        }
        # Downstream target typical SD for absolute change scaling
        _target_sd: dict[str, float] = {
            "hdl_mg_dl": 12.0,
            "glucose_mg_dl": 18.0,
            "triglycerides_mg_dl": 50.0,
            "bmi": 5.0,
            "crp_mg_l": 3.0,
            "alt_u_l": 20.0,
            "total_cholesterol_mg_dl": 35.0,
        }

        downstream_effects = effect_map.get(intervention.variable, [])
        iv_sd = _typical_sd.get(intervention.variable, max(abs(delta), 1.0))
        delta_normalized = delta / iv_sd  # in SD units

        for effect in downstream_effects:
            target_col = effect["target"]
            if target_col not in counterfactual.columns:
                continue

            target_sd = _target_sd.get(target_col, 10.0)
            # Effect size (beta) in SD units: how many SDs target changes per SD of intervention
            effect_magnitude = delta_normalized * effect["effect_size"] * target_sd * noise_scale
            direction_sign = 1.0 if effect["effect_direction"] == "positive" else -1.0

            current_val = counterfactual[target_col].values[0]
            if not np.isnan(current_val):
                counterfactual[target_col] = current_val + direction_sign * abs(effect_magnitude)

        return counterfactual

    def simulate(
        self,
        user_features: pd.DataFrame,
        interventions: list[Intervention],
        n_simulations: int = 1000,
        time_horizon_years: int = 5,
        confidence_level: float = 0.95,
    ) -> dict[str, Any]:
        """Run Monte Carlo simulation of health interventions.

        Args:
            user_features: Single-row DataFrame with all feature values.
            interventions: List of interventions to apply.
            n_simulations: Number of Monte Carlo samples.
            time_horizon_years: Prediction horizon in years.
            confidence_level: CI coverage probability.

        Returns:
            Simulation results with means, CIs, and per-intervention breakdown.
        """
        if self._bioage_model is None:
            raise CausalInferenceError("bioage_model not set. Call set_models() first.")

        effect_map = self._build_effect_map()
        alpha = 1 - confidence_level
        ci_percentiles = [alpha / 2 * 100, (1 - alpha / 2) * 100]

        # Baseline predictions
        baseline_bioage_result = self._bioage_model.predict_biological_age(
            user_features,
            true_age=user_features["age_years"].values if "age_years" in user_features else None,
        )
        baseline_bioage = float(baseline_bioage_result["biological_age"])
        baseline_true_age = float(baseline_bioage_result["chronological_age"])

        # Monte Carlo simulation
        counterfactual_bioages: list[float] = []

        for sim_idx in range(n_simulations):
            # Sample noise for causal effect sizes (log-normal uncertainty)
            noise_scale = np.random.lognormal(mean=0, sigma=0.2)
            cf_features = user_features.copy()

            for intervention in interventions:
                cf_features = self._apply_intervention_to_features(
                    cf_features, intervention, effect_map, noise_scale
                )

            # Re-predict biological age with counterfactual features
            try:
                cf_result = self._bioage_model.predict_biological_age(
                    cf_features,
                    true_age=[baseline_true_age],
                )
                counterfactual_bioages.append(float(cf_result["biological_age"]))
            except Exception as e:
                logger.debug("simulation_sample_failed", sim_idx=sim_idx, error=str(e))
                counterfactual_bioages.append(baseline_bioage)

        cf_array = np.array(counterfactual_bioages)
        cf_mean = float(cf_array.mean())
        cf_ci = (float(np.percentile(cf_array, ci_percentiles[0])),
                 float(np.percentile(cf_array, ci_percentiles[1])))

        bioage_change_mean = cf_mean - baseline_bioage
        bioage_change_ci = (cf_ci[0] - baseline_bioage, cf_ci[1] - baseline_bioage)

        # Per-intervention attribution (sequential attribution)
        intervention_effects = self._compute_intervention_attribution(
            user_features, interventions, effect_map, baseline_bioage, baseline_true_age
        )

        # Build year-by-year trajectory
        trajectory = self._build_trajectory(
            baseline_bioage, cf_mean, time_horizon_years
        )

        return {
            "baseline": {
                "biological_age": baseline_bioage,
                "chronological_age": baseline_true_age,
            },
            "counterfactual": {
                "biological_age_mean": cf_mean,
                "biological_age_ci": cf_ci,
                "bioage_change_mean": bioage_change_mean,
                "bioage_change_ci": bioage_change_ci,
            },
            "intervention_effects": intervention_effects,
            "trajectory": trajectory,
            "n_simulations": n_simulations,
            "confidence_level": confidence_level,
            "disclaimer": (
                "Estimates are based on population-level causal inference from "
                "observational data. Individual responses may vary. This is not "
                "medical advice. Consult a healthcare provider before making changes."
            ),
        }

    def _compute_intervention_attribution(
        self,
        user_features: pd.DataFrame,
        interventions: list[Intervention],
        effect_map: dict[str, list[dict]],
        baseline_bioage: float,
        baseline_true_age: float,
    ) -> list[dict[str, Any]]:
        """Compute individual contribution of each intervention."""
        effects = []
        cumulative_features = user_features.copy()
        cumulative_bioage = baseline_bioage

        for intervention in interventions:
            single_cf = self._apply_intervention_to_features(
                cumulative_features, intervention, effect_map, noise_scale=1.0
            )
            try:
                result = self._bioage_model.predict_biological_age(
                    single_cf, true_age=[baseline_true_age]
                )
                new_bioage = float(result["biological_age"])
            except Exception:
                new_bioage = cumulative_bioage

            delta = new_bioage - cumulative_bioage
            effects.append({
                "intervention": intervention.variable,
                "current_value": intervention.current_value,
                "target_value": intervention.target_value,
                "bioage_impact": round(delta, 2),
            })
            cumulative_features = single_cf
            cumulative_bioage = new_bioage

        return effects

    def _build_trajectory(
        self,
        baseline_bioage: float,
        counterfactual_bioage: float,
        years: int,
    ) -> list[dict[str, float]]:
        """Build year-by-year trajectory showing divergence between scenarios."""
        trajectory = []
        # Assume ~0.8 biological years per chronological year (average aging rate)
        natural_aging_rate = 0.8
        intervention_aging_rate = natural_aging_rate * (
            1 + (counterfactual_bioage - baseline_bioage) / max(abs(baseline_bioage), 1) * 0.1
        )

        for year in range(years + 1):
            trajectory.append({
                "year": year,
                "bioage_baseline": round(baseline_bioage + year * natural_aging_rate, 1),
                "bioage_counterfactual": round(
                    counterfactual_bioage + year * intervention_aging_rate, 1
                ),
            })
        return trajectory
