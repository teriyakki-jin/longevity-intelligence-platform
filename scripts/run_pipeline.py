"""End-to-end data pipeline: download -> parse -> harmonize -> feature matrix."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from longevity.common.logging import configure_logging, get_logger
from longevity.data.nhanes.downloader import download_nhanes
from longevity.data.nhanes.parser import batch_parse_cycle
from longevity.data.nhanes.harmonizer import harmonize_all_cycles
from longevity.data.nhanes.features import build_feature_matrix

logger = get_logger(__name__)


def run_pipeline(
    raw_dir: str = "data/raw/nhanes",
    interim_dir: str = "data/interim/nhanes",
    output_path: str = "data/processed/nhanes_features.parquet",
    cycles: list[str] | None = None,
    skip_download: bool = False,
) -> None:
    configure_logging()

    raw = Path(raw_dir)
    interim = Path(interim_dir)
    out = Path(output_path)

    # Step 1: Download
    if not skip_download:
        logger.info("step_1_download")
        download_nhanes(output_dir=raw, cycles=cycles)
    else:
        logger.info("step_1_skipped_download")

    # Step 2: Parse XPT -> Parquet
    logger.info("step_2_parse")
    available_cycles = cycles or [d.name for d in raw.iterdir() if d.is_dir()]
    for cycle in sorted(available_cycles):
        batch_parse_cycle(raw, interim, cycle)

    # Step 3: Harmonize
    logger.info("step_3_harmonize")
    df = harmonize_all_cycles(interim, out.parent / "nhanes_harmonized.parquet", cycles=cycles)

    # Step 4: Feature engineering
    logger.info("step_4_features")
    features = build_feature_matrix(df)
    features.to_parquet(out, index=False, compression="snappy")

    logger.info("pipeline_complete", output=str(out), n_rows=len(features))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NHANES data pipeline")
    parser.add_argument("--raw-dir", default="data/raw/nhanes")
    parser.add_argument("--interim-dir", default="data/interim/nhanes")
    parser.add_argument("--output", default="data/processed/nhanes_features.parquet")
    parser.add_argument("--cycles", nargs="+", default=None)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    run_pipeline(
        raw_dir=args.raw_dir,
        interim_dir=args.interim_dir,
        output_path=args.output,
        cycles=args.cycles,
        skip_download=args.skip_download,
    )
