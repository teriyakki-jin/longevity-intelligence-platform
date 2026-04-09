export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

export const COLORS = {
  bg: '#0d1117',
  surface: '#161b22',
  border: '#30363d',
  textPrimary: '#e6edf3',
  textMuted: '#8b949e',
  blue: '#58a6ff',
  green: '#3fb950',
  red: '#ff7b72',
  orange: '#ffa657',
  purple: '#d2a8ff',
} as const

export const DEFAULT_LIFESTYLE = {
  smoking_status: 'never' as const,
  pack_years: 0,
  drinks_per_week: 3,
  exercise_minutes_per_week: 150,
  sleep_hours: 7.5,
}

export const CAUSE_LABELS: Record<string, string> = {
  cardiovascular: 'Heart Disease',
  cancer: 'Cancer',
  respiratory: 'Respiratory',
  diabetes: 'Diabetes',
  accidents: 'Accidents',
  other: 'Other',
}

export const FEATURE_LABELS: Record<string, string> = {
  glucose_mg_dl: 'Glucose',
  hba1c_pct: 'HbA1c',
  total_cholesterol_mg_dl: 'Total Cholesterol',
  hdl_mg_dl: 'HDL Cholesterol',
  triglycerides_mg_dl: 'Triglycerides',
  creatinine_mg_dl: 'Creatinine',
  alt_u_l: 'ALT',
  ast_u_l: 'AST',
  albumin_g_dl: 'Albumin',
  wbc_1000_ul: 'White Blood Cells',
  hemoglobin_g_dl: 'Hemoglobin',
  platelets_1000_ul: 'Platelets',
  crp_mg_l: 'CRP (Inflammation)',
  uric_acid_mg_dl: 'Uric Acid',
  egfr: 'eGFR (Kidney)',
  fib4_score: 'FIB-4 (Liver)',
  bmi: 'BMI',
  waist_cm: 'Waist Circumference',
  pack_years: 'Smoking History',
  drinks_per_week: 'Alcohol Intake',
  sleep_hours: 'Sleep Duration',
  sex_encoded: 'Sex',
}
