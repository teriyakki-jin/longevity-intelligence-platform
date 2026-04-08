"""NHANES XPT (SAS transport) file parser.

Converts raw XPT files to Parquet with consistent dtypes and
NHANES missing-value coding handled (7=Refused, 9=Don't Know -> NaN).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from longevity.common.exceptions import DataPipelineError
from longevity.common.logging import get_logger

logger = get_logger(__name__)

# NHANES codes that represent missing / refused / don't know
# These are variable-specific; we handle the most common patterns
NHANES_MISSING_CODES = {
    7777: None,   # Refused (4-digit)
    9999: None,   # Don't know (4-digit)
    77777: None,  # Refused (5-digit)
    99999: None,  # Don't know (5-digit)
    777: None,    # Refused (3-digit)
    999: None,    # Don't know (3-digit)
}


def _read_xpt(path: Path) -> pd.DataFrame:
    """Read SAS XPT file into a DataFrame."""
    try:
        df = pd.read_sas(str(path), format="xport", encoding="utf-8", index=None)
    except UnicodeDecodeError:
        df = pd.read_sas(str(path), format="xport", encoding="latin1", index=None)
    except Exception as e:
        raise DataPipelineError(f"Failed to read XPT file {path}: {e}") from e
    return df


def _apply_nhanes_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NHANES refused/don't-know codes with NaN for numeric columns."""
    for col in df.select_dtypes(include="number").columns:
        col_max = df[col].max()
        # Apply missing code replacements only for plausible ranges
        for code, replacement in NHANES_MISSING_CODES.items():
            if col_max >= code * 0.9:  # Only if the code is in the plausible range
                df[col] = df[col].replace(code, replacement)
    return df


def _ensure_seqn(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Ensure SEQN (participant ID) column exists and is integer."""
    if "SEQN" not in df.columns:
        raise DataPipelineError(f"No SEQN column in {path}. Columns: {df.columns.tolist()}")
    df["SEQN"] = df["SEQN"].astype("int64")
    return df


def parse_xpt_to_parquet(
    xpt_path: Path,
    output_path: Path,
    cycle: str,
    component: str,
    overwrite: bool = False,
) -> Path:
    """Parse a single XPT file and save as Parquet.

    Args:
        xpt_path: Path to the XPT file.
        output_path: Destination parquet path.
        cycle: NHANES survey cycle (e.g., "2017-2018").
        component: Component name (e.g., "demographics").
        overwrite: If True, overwrite existing parquet files.

    Returns:
        Path to the saved Parquet file.
    """
    if output_path.exists() and not overwrite:
        logger.info("parquet_exists_skip", path=str(output_path))
        return output_path

    logger.info("parsing_xpt", xpt=str(xpt_path), component=component, cycle=cycle)

    df = _read_xpt(xpt_path)
    df = _ensure_seqn(df, xpt_path)
    df = _apply_nhanes_missing(df)

    # Add metadata columns
    df["_cycle"] = cycle
    df["_component"] = component

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.info(
        "xpt_parsed",
        rows=len(df),
        cols=len(df.columns),
        output=str(output_path),
    )
    return output_path


def parse_mortality_dat(dat_path: Path, output_path: Path, cycle: str) -> Path:
    """Parse NHANES mortality linkage fixed-width .dat file.

    Column layout from CDC documentation:
    https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_III_2015_MORT_2015_PUBLIC_DOC.pdf
    """
    if output_path.exists():
        logger.info("mortality_parquet_exists_skip", path=str(output_path))
        return output_path

    colspecs = [
        (0, 14),    # SEQN
        (14, 15),   # eligstat (1=eligible, 2=under 18, 3=ineligible)
        (15, 16),   # mortstat (0=assumed alive, 1=deceased)
        (16, 19),   # ucod_leading (ICD-10 leading cause, 001-999)
        (19, 20),   # diabetes (1=yes, blank=no)
        (20, 21),   # hyperten (1=yes, blank=no)
        (21, 26),   # permth_int (person-months since interview)
        (26, 31),   # permth_exm (person-months since examination)
    ]

    names = [
        "SEQN",
        "eligstat",
        "mortstat",
        "ucod_leading",
        "diabetes_flag",
        "hypertension_flag",
        "person_months_interview",
        "person_months_exam",
    ]

    try:
        df = pd.read_fwf(
            dat_path,
            colspecs=colspecs,
            names=names,
            na_values=[" ", ""],
        )
    except Exception as e:
        raise DataPipelineError(f"Failed to parse mortality file {dat_path}: {e}") from e

    df["SEQN"] = pd.to_numeric(df["SEQN"], errors="coerce").astype("Int64")
    df["mortstat"] = pd.to_numeric(df["mortstat"], errors="coerce").astype("Int8")
    df["_cycle"] = cycle

    # Map ICD-10 leading cause to cause categories
    df["cause_category"] = df["ucod_leading"].apply(_map_icd_to_cause)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    alive = (df["mortstat"] == 0).sum()
    deceased = (df["mortstat"] == 1).sum()
    logger.info("mortality_parsed", cycle=cycle, alive=int(alive), deceased=int(deceased))
    return output_path


def _map_icd_to_cause(ucod: float | None) -> str | None:
    """Map NHANES mortality linkage UCOD_LEADING code (1-10) to cause category.

    CDC NHANES condensed cause codes:
    1  = Diseases of heart (cardiovascular)
    2  = Malignant neoplasms (cancer)
    3  = Chronic lower respiratory diseases
    4  = Accidents / unintentional injuries
    5  = Cerebrovascular diseases (stroke → cardiovascular)
    6  = Alzheimer's disease
    7  = Diabetes mellitus
    8  = Influenza and pneumonia
    9  = Nephritis / nephrotic syndrome
    10 = All other causes
    """
    if ucod is None or pd.isna(ucod):
        return None
    code = int(ucod)
    mapping = {
        1: "cardiovascular",
        2: "cancer",
        3: "respiratory",
        4: "accidents",
        5: "cardiovascular",   # stroke
        6: "other",            # alzheimer's
        7: "diabetes",
        8: "respiratory",      # pneumonia/influenza
        9: "other",            # nephritis
        10: "other",
    }
    return mapping.get(code, "other")


def batch_parse_cycle(
    raw_dir: Path,
    interim_dir: Path,
    cycle: str,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Parse all XPT files for a given cycle.

    Args:
        raw_dir: Root raw directory (data/raw/nhanes).
        interim_dir: Root interim directory (data/interim/nhanes).
        cycle: Survey cycle to parse.
        overwrite: Overwrite existing parquet files.

    Returns:
        Dict mapping component name to parquet path.
    """
    cycle_raw = raw_dir / cycle
    cycle_out = interim_dir / cycle
    results: dict[str, Path] = {}

    if not cycle_raw.exists():
        logger.warning("cycle_directory_missing", cycle=cycle, path=str(cycle_raw))
        return results

    for component_dir in cycle_raw.iterdir():
        if not component_dir.is_dir():
            continue
        component = component_dir.name

        if component == "mortality":
            for dat_file in component_dir.glob("*.dat"):
                out = cycle_out / component / (dat_file.stem + ".parquet")
                try:
                    results[component] = parse_mortality_dat(dat_file, out, cycle)
                except DataPipelineError as e:
                    logger.error("mortality_parse_failed", cycle=cycle, error=str(e))
        else:
            for xpt_file in component_dir.glob("*.XPT"):
                out = cycle_out / component / (xpt_file.stem + ".parquet")
                try:
                    results[component] = parse_xpt_to_parquet(
                        xpt_file, out, cycle, component, overwrite
                    )
                except DataPipelineError as e:
                    logger.error(
                        "xpt_parse_failed",
                        cycle=cycle,
                        component=component,
                        error=str(e),
                    )

    return results
