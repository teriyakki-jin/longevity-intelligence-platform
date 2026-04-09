export interface InterventionRequest {
  variable: string
  current_value: number
  target_value: number
}

export interface SimulationRequest {
  user_features: Record<string, number | string | null>
  interventions: InterventionRequest[]
  n_simulations: number
  time_horizon_years: number
}

export interface InterventionEffect {
  intervention: string
  current_value: number
  target_value: number
  bioage_impact: number
}

export interface TrajectoryPoint {
  year: number
  bioage_baseline: number
  bioage_counterfactual: number
}

export interface SimulationResponse {
  success: boolean
  baseline: { biological_age: number }
  counterfactual: {
    biological_age_mean: number
    bioage_change_mean: number
    bioage_change_ci: [number, number]
  }
  intervention_effects: InterventionEffect[]
  trajectory: TrajectoryPoint[]
}
