export interface BloodMarkers {
  glucose_mg_dl: number | null
  hba1c_pct: number | null
  total_cholesterol_mg_dl: number | null
  hdl_mg_dl: number | null
  ldl_mg_dl: number | null
  triglycerides_mg_dl: number | null
  creatinine_mg_dl: number | null
  alt_u_l: number | null
  ast_u_l: number | null
  albumin_g_dl: number | null
  wbc_1000_ul: number | null
  hemoglobin_g_dl: number | null
  platelets_1000_ul: number | null
  crp_mg_l: number | null
  uric_acid_mg_dl: number | null
}

export interface Demographics {
  chronological_age: number
  sex: 'male' | 'female'
  height_cm: number | null
  weight_kg: number | null
  waist_cm: number | null
}

export interface Lifestyle {
  smoking_status: 'never' | 'former' | 'current'
  pack_years: number
  drinks_per_week: number
  exercise_minutes_per_week: number
  sleep_hours: number
}

export interface BioAgeRequest {
  blood_markers: BloodMarkers
  demographics: Demographics
  lifestyle: Lifestyle
  include_explanation: boolean
}

export interface ShapFactor {
  feature: string
  value: number
  shap_impact_years: number
  direction: 'aging' | 'protective'
}

export interface BioAgeResponse {
  success: boolean
  biological_age: number
  chronological_age: number
  age_acceleration: number
  percentile_for_age: number
  confidence_interval: [number, number]
  interpretation: string
  top_aging_factors: ShapFactor[]
  top_protective_factors: ShapFactor[]
  disclaimer: string
}
