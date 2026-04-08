"""Natural language report generator for health predictions."""
from __future__ import annotations

from longevity.common.types import BioAgePrediction, MortalityPrediction


FEATURE_LABELS: dict[str, str] = {
    "glucose_mg_dl": "Fasting glucose",
    "hba1c_pct": "HbA1c (blood sugar control)",
    "total_cholesterol_mg_dl": "Total cholesterol",
    "hdl_mg_dl": "HDL ('good') cholesterol",
    "ldl_mg_dl": "LDL ('bad') cholesterol",
    "triglycerides_mg_dl": "Triglycerides",
    "creatinine_mg_dl": "Creatinine (kidney marker)",
    "alt_u_l": "ALT (liver enzyme)",
    "ast_u_l": "AST (liver enzyme)",
    "albumin_g_dl": "Albumin (protein level)",
    "wbc_1000_ul": "White blood cell count",
    "hemoglobin_g_dl": "Hemoglobin",
    "platelets_1000_ul": "Platelet count",
    "crp_mg_l": "C-reactive protein (inflammation)",
    "uric_acid_mg_dl": "Uric acid",
    "egfr": "eGFR (kidney function)",
    "fib4_score": "FIB-4 (liver health score)",
    "bmi": "BMI",
    "waist_cm": "Waist circumference",
    "pack_years": "Smoking history (pack-years)",
    "drinks_per_week": "Alcohol consumption",
    "sleep_hours": "Sleep duration",
    "sex_encoded": "Sex",
    "chol_hdl_ratio": "Cholesterol-to-HDL ratio",
    "non_hdl_mg_dl": "Non-HDL cholesterol",
    "metabolic_syndrome_score": "Metabolic syndrome score",
}

CAUSE_LABELS: dict[str, str] = {
    "cardiovascular": "Cardiovascular Disease (heart attack, stroke)",
    "cancer": "Cancer (all types)",
    "respiratory": "Respiratory Disease (COPD, pneumonia)",
    "diabetes": "Diabetes complications",
    "accidents": "Accidents & injuries",
}


def generate_bioage_interpretation(
    biological_age: float,
    chronological_age: float,
    acceleration: float,
    percentile: float,
) -> str:
    """Generate human-readable biological age interpretation."""
    diff = abs(acceleration)
    direction = "younger" if acceleration < 0 else "older"
    peer_pct = 100 - int(percentile)

    if acceleration < -5:
        quality = "excellent"
    elif acceleration < -2:
        quality = "good"
    elif acceleration < 2:
        quality = "average"
    elif acceleration < 5:
        quality = "below average"
    else:
        quality = "concerning"

    text = (
        f"Your biological age is {biological_age:.1f} years — "
        f"{diff:.1f} years {direction} than your chronological age of {chronological_age:.0f}. "
        f"This places you in {quality} health for your age, "
        f"healthier than {peer_pct}% of people your age in the population."
    )

    if acceleration < -3:
        text += " Your body is aging at a slower rate than average — keep it up."
    elif acceleration > 3:
        text += (
            " There is room for improvement. Small lifestyle changes can meaningfully "
            "reduce your biological age over 6–12 months."
        )

    return text


def generate_shap_narrative(
    top_aging_factors: list[dict],
    top_protective_factors: list[dict],
) -> str:
    """Generate narrative from SHAP factors."""
    lines = []

    if top_aging_factors:
        lines.append("**Factors adding to your biological age:**")
        for factor in top_aging_factors[:3]:
            label = FEATURE_LABELS.get(factor["feature"], factor["feature"])
            impact = factor["shap_impact_years"]
            val = factor["value"]
            lines.append(
                f"  • {label} ({val}) is adding approximately "
                f"{impact:.1f} years to your biological age."
            )

    if top_protective_factors:
        lines.append("\n**Factors protecting your biological age:**")
        for factor in top_protective_factors[:3]:
            label = FEATURE_LABELS.get(factor["feature"], factor["feature"])
            impact = abs(factor["shap_impact_years"])
            val = factor["value"]
            lines.append(
                f"  • {label} ({val}) is reducing your biological age "
                f"by approximately {impact:.1f} years."
            )

    return "\n".join(lines)


def generate_mortality_narrative(risks: list[dict]) -> str:
    """Generate narrative for mortality risks."""
    lines = ["**Your top health risks:**"]
    for risk in risks[:3]:
        cause = CAUSE_LABELS.get(risk["cause"], risk["cause"])
        prob = risk.get("probability_5yr", 0) * 100
        vs_pop = risk.get("vs_population", "")
        lines.append(
            f"  • {cause}: {prob:.1f}% 5-year risk ({vs_pop})"
        )
    lines.append(
        "\n⚠️ These are population-based estimates. Consult your doctor "
        "for personalized medical assessment."
    )
    return "\n".join(lines)


def format_intervention_summary(effects: list[dict]) -> str:
    """Format intervention simulation results as readable summary."""
    lines = []
    total_impact = sum(e.get("bioage_impact", 0) for e in effects)

    for effect in effects:
        feat = FEATURE_LABELS.get(effect["intervention"], effect["intervention"])
        impact = effect.get("bioage_impact", 0)
        direction = "reduce" if impact < 0 else "increase"
        lines.append(
            f"  • Changing {feat} from {effect['current_value']} to "
            f"{effect['target_value']} would {direction} biological age by "
            f"{abs(impact):.1f} years."
        )

    total_direction = "reduce" if total_impact < 0 else "increase"
    lines.append(
        f"\nTotal combined effect: {total_direction} biological age by "
        f"{abs(total_impact):.1f} years."
    )
    return "\n".join(lines)
