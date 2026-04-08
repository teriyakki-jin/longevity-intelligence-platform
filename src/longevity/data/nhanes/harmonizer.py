"""NHANES cross-cycle variable harmonizer.

Maps variable names that changed across survey cycles to a consistent schema,
handles unit conversions, and produces a single unified DataFrame.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from longevity.common.exceptions import DataPipelineError
from longevity.common.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Variable mapping tables
# Each entry: target_col -> {cycle: source_col}
# If a cycle is not listed, the variable is assumed not available.
# ---------------------------------------------------------------------------

DEMOGRAPHICS_MAP: dict[str, dict[str, str]] = {
    "SEQN":       {c: "SEQN" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                         "2007-2008","2009-2010","2011-2012","2013-2014",
                                         "2015-2016","2017-2018","2017-2020"]},
    "age_years":  {c: "RIDAGEYR" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                             "2007-2008","2009-2010","2011-2012","2013-2014",
                                             "2015-2016","2017-2018","2017-2020"]},
    "sex":        {c: "RIAGENDR" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                            "2007-2008","2009-2010","2011-2012","2013-2014",
                                            "2015-2016","2017-2018","2017-2020"]},
    "race_ethnicity": {
        c: "RIDRETH1"
        for c in ["1999-2000","2001-2002","2003-2004","2005-2006","2007-2008","2009-2010"]
    } | {
        c: "RIDRETH3"
        for c in ["2011-2012","2013-2014","2015-2016","2017-2018","2017-2020"]
    },
    "psu":        {c: "SDMVPSU" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                           "2007-2008","2009-2010","2011-2012","2013-2014",
                                           "2015-2016","2017-2018","2017-2020"]},
    "strata":     {c: "SDMVSTRA" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                            "2007-2008","2009-2010","2011-2012","2013-2014",
                                            "2015-2016","2017-2018","2017-2020"]},
    "exam_weight":{c: "WTMEC2YR" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                            "2007-2008","2009-2010","2011-2012","2013-2014",
                                            "2015-2016","2017-2018","2017-2020"]},
}

GLUCOSE_MAP: dict[str, dict[str, str]] = {
    "glucose_mg_dl": {
        "1999-2000": "LBXGLU",
        "2001-2002": "LBXGLU",
        "2003-2004": "LBXGLU",
        "2005-2006": "LBXGLU",
        "2007-2008": "LBXGLU",
        "2009-2010": "LBXGLU",
        "2011-2012": "LBXGLU",
        "2013-2014": "LBXGLU",
        "2015-2016": "LBXGLU",
        "2017-2018": "LBXGLU",
        "2017-2020": "LBXGLU",
    },
}

# Glucose in 2005-2020 may be in mmol/L for some files; check and convert
GLUCOSE_UNIT_COLS = {
    # Files that store in mmol/L need *18.018 to get mg/dL
    "2005-2006": ("LBDGLUSI", 18.018),
}

HBAIC_MAP: dict[str, dict[str, str]] = {
    "hba1c_pct": {c: "LBXGH" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                         "2007-2008","2009-2010","2011-2012","2013-2014",
                                         "2015-2016","2017-2018","2017-2020"]},
}

LIPIDS_MAP: dict[str, dict[str, str]] = {
    "total_cholesterol_mg_dl": {c: "LBXTC" for c in ["1999-2000","2001-2002","2003-2004",
                                                       "2005-2006","2007-2008","2009-2010",
                                                       "2011-2012","2013-2014","2015-2016",
                                                       "2017-2018","2017-2020"]},
    "hdl_mg_dl": {
        "1999-2000": "LBDHDL", "2001-2002": "LBDHDL", "2003-2004": "LBDHDL",
        "2005-2006": "LBDHDD", "2007-2008": "LBDHDD", "2009-2010": "LBDHDD",
        "2011-2012": "LBDHDD", "2013-2014": "LBDHDD", "2015-2016": "LBDHDD",
        "2017-2018": "LBDHDD", "2017-2020": "LBDHDD",
    },
    "triglycerides_mg_dl": {
        "1999-2000": "LBXTR", "2001-2002": "LBXTR", "2003-2004": "LBXTR",
        "2005-2006": "LBXTR", "2007-2008": "LBXTR", "2009-2010": "LBXTR",
        "2011-2012": "LBXTR", "2013-2014": "LBXTR", "2015-2016": "LBXTR",
        "2017-2018": "LBXTR", "2017-2020": "LBXTR",
    },
}

BIOCHEMISTRY_MAP: dict[str, dict[str, str]] = {
    "creatinine_mg_dl": {c: "LBXSCR" for c in ["1999-2000","2001-2002","2003-2004",
                                                  "2005-2006","2007-2008","2009-2010",
                                                  "2011-2012","2013-2014","2015-2016",
                                                  "2017-2018","2017-2020"]},
    "alt_u_l":   {c: "LBXSATSI" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                            "2007-2008","2009-2010","2011-2012","2013-2014",
                                            "2015-2016","2017-2018","2017-2020"]},
    "ast_u_l":   {c: "LBXSASSI" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                            "2007-2008","2009-2010","2011-2012","2013-2014",
                                            "2015-2016","2017-2018","2017-2020"]},
    "albumin_g_dl": {c: "LBDSALSI" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                               "2007-2008","2009-2010","2011-2012","2013-2014",
                                               "2015-2016","2017-2018","2017-2020"]},
    "uric_acid_mg_dl": {c: "LBXSUA" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                "2007-2008","2009-2010","2011-2012","2013-2014",
                                                "2015-2016","2017-2018","2017-2020"]},
}

CBC_MAP: dict[str, dict[str, str]] = {
    "wbc_1000_ul":       {c: "LBXWBCSI" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                    "2007-2008","2009-2010","2011-2012","2013-2014",
                                                    "2015-2016","2017-2018","2017-2020"]},
    "hemoglobin_g_dl":   {c: "LBXHGB"   for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                    "2007-2008","2009-2010","2011-2012","2013-2014",
                                                    "2015-2016","2017-2018","2017-2020"]},
    "platelets_1000_ul": {c: "LBXPLTSI" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                    "2007-2008","2009-2010","2011-2012","2013-2014",
                                                    "2015-2016","2017-2018","2017-2020"]},
}

CRP_MAP: dict[str, dict[str, str]] = {
    "crp_mg_l": {
        "1999-2000": "LBXCRP",
        "2001-2002": "LBXCRP",
        "2003-2004": "LBXCRP",
        "2005-2006": "LBXCRP",
        "2007-2008": "LBXHSCRP",  # switched to high-sensitivity CRP
        "2009-2010": "LBXHSCRP",
        "2011-2012": "LBXHSCRP",
        "2013-2014": "LBXHSCRP",
        "2015-2016": "LBXHSCRP",
        "2017-2018": "LBXHSCRP",
        "2017-2020": "LBXHSCRP",
    },
}

BODY_MAP: dict[str, dict[str, str]] = {
    "height_cm":    {c: "BMXHT"   for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                             "2007-2008","2009-2010","2011-2012","2013-2014",
                                             "2015-2016","2017-2018","2017-2020"]},
    "weight_kg":    {c: "BMXWT"   for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                             "2007-2008","2009-2010","2011-2012","2013-2014",
                                             "2015-2016","2017-2018","2017-2020"]},
    "waist_cm":     {c: "BMXWAIST" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                              "2007-2008","2009-2010","2011-2012","2013-2014",
                                              "2015-2016","2017-2018","2017-2020"]},
}

SMOKING_MAP: dict[str, dict[str, str]] = {
    "smoking_status_code": {c: "SMQ020" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                   "2007-2008","2009-2010","2011-2012","2013-2014",
                                                   "2015-2016","2017-2018","2017-2020"]},
    "smoking_now":         {c: "SMQ040" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                   "2007-2008","2009-2010","2011-2012","2013-2014",
                                                   "2015-2016","2017-2018","2017-2020"]},
    "cigarettes_per_day":  {c: "SMD650" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                                   "2007-2008","2009-2010","2011-2012","2013-2014",
                                                   "2015-2016","2017-2018","2017-2020"]},
    "years_smoked":        {c: "SMD641" for c in ["2003-2004","2005-2006","2007-2008","2009-2010",
                                                   "2011-2012","2013-2014","2015-2016",
                                                   "2017-2018","2017-2020"]},
}

ALCOHOL_MAP: dict[str, dict[str, str]] = {
    "drinks_per_day": {c: "ALQ130" for c in ["1999-2000","2001-2002","2003-2004","2005-2006",
                                              "2007-2008","2009-2010","2011-2012","2013-2014",
                                              "2015-2016","2017-2018","2017-2020"]},
    "alcohol_per_year": {c: "ALQ110" for c in ["2005-2006","2007-2008","2009-2010","2011-2012",
                                                "2013-2014","2015-2016","2017-2018","2017-2020"]},
}

SLEEP_MAP: dict[str, dict[str, str]] = {
    "sleep_hours": {
        "2005-2006": "SLD010H",
        "2007-2008": "SLD010H",
        "2009-2010": "SLD010H",
        "2011-2012": "SLD010H",
        "2013-2014": "SLD012",
        "2015-2016": "SLD012",
        "2017-2018": "SLD012",
        "2017-2020": "SLD012",
    },
}

# Combined mapping by component
COMPONENT_MAPS: dict[str, dict[str, dict[str, str]]] = {
    "demographics": DEMOGRAPHICS_MAP,
    "blood_glucose": GLUCOSE_MAP,
    "glycohemoglobin": HBAIC_MAP,
    "lipids_cholesterol": LIPIDS_MAP,
    "lipids_hdl": LIPIDS_MAP,
    "lipids_triglycerides": LIPIDS_MAP,
    "biochemistry": BIOCHEMISTRY_MAP,
    "complete_blood_count": CBC_MAP,
    "crp": CRP_MAP,
    "body_measures": BODY_MAP,
    "smoking": SMOKING_MAP,
    "alcohol": ALCOHOL_MAP,
    "sleep": SLEEP_MAP,
}


def _extract_columns(df: pd.DataFrame, col_map: dict[str, str], cycle: str) -> pd.DataFrame:
    """Extract and rename columns from a raw DataFrame using the mapping."""
    result: dict[str, pd.Series] = {"SEQN": df["SEQN"]}
    for target_col, source_map in col_map.items():
        if target_col == "SEQN":
            continue
        source_col = source_map.get(cycle)
        if source_col and source_col in df.columns:
            result[target_col] = df[source_col]
        else:
            result[target_col] = pd.Series(np.nan, index=df.index)
    return pd.DataFrame(result)


def _encode_sex(df: pd.DataFrame) -> pd.DataFrame:
    """Encode NHANES sex codes: 1=Male, 2=Female -> 'male'/'female'."""
    if "sex" in df.columns:
        df["sex"] = df["sex"].map({1: "male", 2: "female"})
    return df


def _encode_smoking(df: pd.DataFrame) -> pd.DataFrame:
    """Derive smoking_status from NHANES smoking variables.

    SMQ020: 1=Yes (smoked >=100 cigarettes lifetime), 2=No
    SMQ040: 1=Every day, 2=Some days, 3=Not at all
    """
    if "smoking_status_code" not in df.columns:
        return df

    conditions = [
        (df["smoking_status_code"] == 2),                          # Never smoked
        (df["smoking_status_code"] == 1) & (df.get("smoking_now", pd.Series(3)) == 3),  # Former
        (df["smoking_status_code"] == 1) & (df.get("smoking_now", pd.Series(3)).isin([1, 2])),  # Current
    ]
    choices = ["never", "former", "current"]
    df["smoking_status"] = np.select(conditions, choices, default=None)

    # Pack-years
    if "cigarettes_per_day" in df.columns and "years_smoked" in df.columns:
        df["pack_years"] = (df["cigarettes_per_day"] / 20) * df["years_smoked"]
    else:
        df["pack_years"] = np.nan

    return df.drop(columns=["smoking_status_code", "smoking_now", "cigarettes_per_day",
                             "years_smoked"], errors="ignore")


def _encode_race_ethnicity(df: pd.DataFrame) -> pd.DataFrame:
    """Encode race/ethnicity codes."""
    mapping = {
        1: "mexican_american",
        2: "other_hispanic",
        3: "non_hispanic_white",
        4: "non_hispanic_black",
        5: "other",
        6: "non_hispanic_asian",  # RIDRETH3 only (2011+)
        7: "other",
    }
    if "race_ethnicity" in df.columns:
        df["race_ethnicity"] = df["race_ethnicity"].map(mapping)
    return df


def _compute_drinks_per_week(df: pd.DataFrame) -> pd.DataFrame:
    """Convert alcohol variables to standard drinks per week."""
    if "drinks_per_day" in df.columns:
        # ALQ130: avg drinks per day on drinking days in past 12 months
        # Approximate weekly: multiply by ~3.5 days/week (population average)
        df["drinks_per_week"] = df["drinks_per_day"] * 3.5
        df = df.drop(columns=["drinks_per_day", "alcohol_per_year"], errors="ignore")
    return df


def harmonize_cycle(
    interim_dir: Path,
    cycle: str,
) -> pd.DataFrame:
    """Harmonize all components for a single cycle into one DataFrame.

    Returns a DataFrame with SEQN as the unique participant identifier.
    """
    cycle_dir = interim_dir / cycle
    if not cycle_dir.exists():
        raise DataPipelineError(f"Interim directory for cycle {cycle} not found: {cycle_dir}")

    component_dfs: dict[str, pd.DataFrame] = {}

    for component, col_map in COMPONENT_MAPS.items():
        comp_dir = cycle_dir / component
        if not comp_dir.exists():
            logger.debug("component_missing", cycle=cycle, component=component)
            continue

        parquet_files = list(comp_dir.glob("*.parquet"))
        if not parquet_files:
            continue

        # Read and concatenate if multiple files
        raw_df = pd.concat(
            [pd.read_parquet(f) for f in parquet_files],
            ignore_index=True,
        )

        extracted = _extract_columns(raw_df, col_map, cycle)
        component_dfs[component] = extracted

    if "demographics" not in component_dfs:
        raise DataPipelineError(f"Demographics missing for cycle {cycle}")

    # Start with demographics as base
    merged = component_dfs["demographics"].copy()

    # Merge all other components
    for comp, df in component_dfs.items():
        if comp == "demographics":
            continue
        # Drop duplicate target columns that may appear in multiple component files
        new_cols = [c for c in df.columns if c not in merged.columns or c == "SEQN"]
        merged = merged.merge(df[new_cols], on="SEQN", how="left")

    # Encode categorical variables
    merged = _encode_sex(merged)
    merged = _encode_race_ethnicity(merged)
    merged = _encode_smoking(merged)
    merged = _compute_drinks_per_week(merged)

    # Add cycle column
    merged["cycle"] = cycle

    # Filter to adults (18+) only
    if "age_years" in merged.columns:
        merged = merged[merged["age_years"] >= 18].copy()

    logger.info(
        "cycle_harmonized",
        cycle=cycle,
        n_participants=len(merged),
        n_columns=len(merged.columns),
    )
    return merged


def harmonize_all_cycles(
    interim_dir: Path,
    output_path: Path,
    cycles: list[str] | None = None,
) -> pd.DataFrame:
    """Harmonize all cycles and save to a single parquet file."""
    available_cycles = cycles or [
        d.name for d in interim_dir.iterdir() if d.is_dir()
    ]

    all_dfs: list[pd.DataFrame] = []
    for cycle in sorted(available_cycles):
        try:
            df = harmonize_cycle(interim_dir, cycle)
            all_dfs.append(df)
        except DataPipelineError as e:
            logger.error("harmonize_cycle_failed", cycle=cycle, error=str(e))

    if not all_dfs:
        raise DataPipelineError("No cycles successfully harmonized")

    combined = pd.concat(all_dfs, ignore_index=True)

    # Merge mortality linkage
    mort_dfs = []
    for cycle in available_cycles:
        mort_dir = interim_dir / cycle / "mortality"
        if mort_dir.exists():
            for pf in mort_dir.glob("*.parquet"):
                mort_dfs.append(pd.read_parquet(pf))

    if mort_dfs:
        mortality = pd.concat(mort_dfs, ignore_index=True)
        mort_cols = ["SEQN", "mortstat", "cause_category",
                     "person_months_interview", "person_months_exam",
                     "diabetes_flag", "hypertension_flag"]
        mort_cols = [c for c in mort_cols if c in mortality.columns]
        combined = combined.merge(mortality[mort_cols], on="SEQN", how="left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_path, index=False, compression="snappy")

    logger.info(
        "all_cycles_harmonized",
        total_participants=len(combined),
        cycles=len(all_dfs),
        columns=len(combined.columns),
        output=str(output_path),
    )
    return combined
