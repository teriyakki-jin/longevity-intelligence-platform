"""NHANES data downloader.

Downloads XPT (SAS transport) files from CDC for each survey cycle.
Files are saved to data/raw/nhanes/{cycle}/{component}.XPT
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import NamedTuple

import requests
from tqdm import tqdm

from longevity.common.exceptions import DataPipelineError
from longevity.common.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

# (cycle, component_code, filename)
class NHANESFile(NamedTuple):
    cycle: str
    component: str
    filename: str
    url_path: str  # relative path after BASE_URL


# Core components to download for each cycle
# Format: (component_name, file_prefix, cycle_suffix_map)
COMPONENTS = {
    "demographics": {
        "1999-2000": "DEMO.XPT",
        "2001-2002": "DEMO_B.XPT",
        "2003-2004": "DEMO_C.XPT",
        "2005-2006": "DEMO_D.XPT",
        "2007-2008": "DEMO_E.XPT",
        "2009-2010": "DEMO_F.XPT",
        "2011-2012": "DEMO_G.XPT",
        "2013-2014": "DEMO_H.XPT",
        "2015-2016": "DEMO_I.XPT",
        "2017-2018": "DEMO_J.XPT",
        "2017-2020": "P_DEMO.XPT",
    },
    "blood_glucose": {
        "1999-2000": "LAB10AM.XPT",
        "2001-2002": "L10AM_B.XPT",
        "2003-2004": "L10AM_C.XPT",
        "2005-2006": "GLU_D.XPT",
        "2007-2008": "GLU_E.XPT",
        "2009-2010": "GLU_F.XPT",
        "2011-2012": "GLU_G.XPT",
        "2013-2014": "GLU_H.XPT",
        "2015-2016": "GLU_I.XPT",
        "2017-2018": "GLU_J.XPT",
        "2017-2020": "P_GLU.XPT",
    },
    "glycohemoglobin": {
        "1999-2000": "LAB10.XPT",
        "2001-2002": "L10_B.XPT",
        "2003-2004": "L10_C.XPT",
        "2005-2006": "GHB_D.XPT",
        "2007-2008": "GHB_E.XPT",
        "2009-2010": "GHB_F.XPT",
        "2011-2012": "GHB_G.XPT",
        "2013-2014": "GHB_H.XPT",
        "2015-2016": "GHB_I.XPT",
        "2017-2018": "GHB_J.XPT",
        "2017-2020": "P_GHB.XPT",
    },
    "lipids_cholesterol": {
        "1999-2000": "LAB13.XPT",
        "2001-2002": "L13_B.XPT",
        "2003-2004": "L13_C.XPT",
        "2005-2006": "TCHOL_D.XPT",
        "2007-2008": "TCHOL_E.XPT",
        "2009-2010": "TCHOL_F.XPT",
        "2011-2012": "TCHOL_G.XPT",
        "2013-2014": "TCHOL_H.XPT",
        "2015-2016": "TCHOL_I.XPT",
        "2017-2018": "TCHOL_J.XPT",
        "2017-2020": "P_TCHOL.XPT",
    },
    "lipids_hdl": {
        "1999-2000": "LAB13.XPT",
        "2001-2002": "L13_B.XPT",
        "2003-2004": "L13_C.XPT",
        "2005-2006": "HDL_D.XPT",
        "2007-2008": "HDL_E.XPT",
        "2009-2010": "HDL_F.XPT",
        "2011-2012": "HDL_G.XPT",
        "2013-2014": "HDL_H.XPT",
        "2015-2016": "HDL_I.XPT",
        "2017-2018": "HDL_J.XPT",
        "2017-2020": "P_HDL.XPT",
    },
    "lipids_triglycerides": {
        "1999-2000": "LAB13AM.XPT",
        "2001-2002": "L13AM_B.XPT",
        "2003-2004": "L13AM_C.XPT",
        "2005-2006": "TRIGLY_D.XPT",
        "2007-2008": "TRIGLY_E.XPT",
        "2009-2010": "TRIGLY_F.XPT",
        "2011-2012": "TRIGLY_G.XPT",
        "2013-2014": "TRIGLY_H.XPT",
        "2015-2016": "TRIGLY_I.XPT",
        "2017-2018": "TRIGLY_J.XPT",
        "2017-2020": "P_TRIGLY.XPT",
    },
    "biochemistry": {
        "1999-2000": "LAB18.XPT",
        "2001-2002": "L40_B.XPT",
        "2003-2004": "L40_C.XPT",
        "2005-2006": "BIOPRO_D.XPT",
        "2007-2008": "BIOPRO_E.XPT",
        "2009-2010": "BIOPRO_F.XPT",
        "2011-2012": "BIOPRO_G.XPT",
        "2013-2014": "BIOPRO_H.XPT",
        "2015-2016": "BIOPRO_I.XPT",
        "2017-2018": "BIOPRO_J.XPT",
        "2017-2020": "P_BIOPRO.XPT",
    },
    "crp": {
        "1999-2000": "LAB11.XPT",
        "2001-2002": "L11_B.XPT",
        "2003-2004": "L11_C.XPT",
        "2005-2006": "CRP_D.XPT",
        "2007-2008": "CRP_E.XPT",
        "2009-2010": "CRP_F.XPT",
        "2011-2012": "HSCRP_G.XPT",
        "2013-2014": "HSCRP_H.XPT",
        "2015-2016": "HSCRP_I.XPT",
        "2017-2018": "HSCRP_J.XPT",
        "2017-2020": "P_HSCRP.XPT",
    },
    "complete_blood_count": {
        "1999-2000": "LAB25.XPT",
        "2001-2002": "L25_B.XPT",
        "2003-2004": "L25_C.XPT",
        "2005-2006": "CBC_D.XPT",
        "2007-2008": "CBC_E.XPT",
        "2009-2010": "CBC_F.XPT",
        "2011-2012": "CBC_G.XPT",
        "2013-2014": "CBC_H.XPT",
        "2015-2016": "CBC_I.XPT",
        "2017-2018": "CBC_J.XPT",
        "2017-2020": "P_CBC.XPT",
    },
    "body_measures": {
        "1999-2000": "BMX.XPT",
        "2001-2002": "BMX_B.XPT",
        "2003-2004": "BMX_C.XPT",
        "2005-2006": "BMX_D.XPT",
        "2007-2008": "BMX_E.XPT",
        "2009-2010": "BMX_F.XPT",
        "2011-2012": "BMX_G.XPT",
        "2013-2014": "BMX_H.XPT",
        "2015-2016": "BMX_I.XPT",
        "2017-2018": "BMX_J.XPT",
        "2017-2020": "P_BMX.XPT",
    },
    "blood_pressure": {
        "1999-2000": "BPX.XPT",
        "2001-2002": "BPX_B.XPT",
        "2003-2004": "BPX_C.XPT",
        "2005-2006": "BPX_D.XPT",
        "2007-2008": "BPX_E.XPT",
        "2009-2010": "BPX_F.XPT",
        "2011-2012": "BPX_G.XPT",
        "2013-2014": "BPX_H.XPT",
        "2015-2016": "BPX_I.XPT",
        "2017-2018": "BPX_J.XPT",
        "2017-2020": "P_BPXO.XPT",
    },
    "smoking": {
        "1999-2000": "SMQ.XPT",
        "2001-2002": "SMQ_B.XPT",
        "2003-2004": "SMQ_C.XPT",
        "2005-2006": "SMQ_D.XPT",
        "2007-2008": "SMQ_E.XPT",
        "2009-2010": "SMQ_F.XPT",
        "2011-2012": "SMQ_G.XPT",
        "2013-2014": "SMQ_H.XPT",
        "2015-2016": "SMQ_I.XPT",
        "2017-2018": "SMQ_J.XPT",
        "2017-2020": "P_SMQ.XPT",
    },
    "alcohol": {
        "1999-2000": "ALQ.XPT",
        "2001-2002": "ALQ_B.XPT",
        "2003-2004": "ALQ_C.XPT",
        "2005-2006": "ALQ_D.XPT",
        "2007-2008": "ALQ_E.XPT",
        "2009-2010": "ALQ_F.XPT",
        "2011-2012": "ALQ_G.XPT",
        "2013-2014": "ALQ_H.XPT",
        "2015-2016": "ALQ_I.XPT",
        "2017-2018": "ALQ_J.XPT",
        "2017-2020": "P_ALQ.XPT",
    },
    "physical_activity": {
        "1999-2000": "PAQ.XPT",
        "2001-2002": "PAQ_B.XPT",
        "2003-2004": "PAQ_C.XPT",
        "2005-2006": "PAQ_D.XPT",
        "2007-2008": "PAQ_E.XPT",
        "2009-2010": "PAQ_F.XPT",
        "2011-2012": "PAQ_G.XPT",
        "2013-2014": "PAQ_H.XPT",
        "2015-2016": "PAQ_I.XPT",
        "2017-2018": "PAQ_J.XPT",
        "2017-2020": "P_PAQ.XPT",
    },
    "sleep": {
        "2005-2006": "SLQ_D.XPT",
        "2007-2008": "SLQ_E.XPT",
        "2009-2010": "SLQ_F.XPT",
        "2011-2012": "SLQ_G.XPT",
        "2013-2014": "SLQ_H.XPT",
        "2015-2016": "SLQ_I.XPT",
        "2017-2018": "SLQ_J.XPT",
        "2017-2020": "P_SLQ.XPT",
    },
}

# Mortality linkage files (separate source)
MORTALITY_BASE_URL = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality"
MORTALITY_FILES = {
    "1999-2000": "NHANES_1999_2000_MORT_2019_PUBLIC.dat",
    "2001-2002": "NHANES_2001_2002_MORT_2019_PUBLIC.dat",
    "2003-2004": "NHANES_2003_2004_MORT_2019_PUBLIC.dat",
    "2005-2006": "NHANES_2005_2006_MORT_2019_PUBLIC.dat",
    "2007-2008": "NHANES_2007_2008_MORT_2019_PUBLIC.dat",
    "2009-2010": "NHANES_2009_2010_MORT_2019_PUBLIC.dat",
    "2011-2012": "NHANES_2011_2012_MORT_2019_PUBLIC.dat",
    "2013-2014": "NHANES_2013_2014_MORT_2019_PUBLIC.dat",
    "2015-2016": "NHANES_2015_2016_MORT_2019_PUBLIC.dat",
    "2017-2018": "NHANES_2017_2018_MORT_2019_PUBLIC.dat",
}

# Cycle-to-start-year mapping (new CDC URL: /Nchs/Data/Nhanes/Public/{year}/DataFiles/{file})
CYCLE_URL_MAP = {
    "1999-2000": "1999",
    "2001-2002": "2001",
    "2003-2004": "2003",
    "2005-2006": "2005",
    "2007-2008": "2007",
    "2009-2010": "2009",
    "2011-2012": "2011",
    "2013-2014": "2013",
    "2015-2016": "2015",
    "2017-2018": "2017",
    "2017-2020": "2017",  # prepandemic files also under 2017
}


def _build_nhanes_url(cycle: str, filename: str, component_type: str) -> str:
    """Build CDC NHANES file URL.

    New CDC URL format (2024+):
    https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{start_year}/DataFiles/{filename}
    """
    start_year = CYCLE_URL_MAP[cycle]
    return f"{BASE_URL}/{start_year}/DataFiles/{filename}"


def _compute_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path, retry: int = 3) -> bool:
    """Download a single file with retry logic. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info("skipping_existing_file", path=str(dest))
        return True

    for attempt in range(retry):
        try:
            response = requests.get(url, stream=True, timeout=60)
            if response.status_code == 404:
                logger.warning("file_not_found", url=url)
                return False
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            with dest.open("wb") as f, tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=dest.name,
                leave=False,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

            logger.info("downloaded", path=str(dest), size_bytes=dest.stat().st_size)
            return True

        except requests.RequestException as e:
            logger.warning("download_failed", url=url, attempt=attempt + 1, error=str(e))
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                if dest.exists():
                    dest.unlink()
    return False


def download_nhanes(
    output_dir: str | Path = "data/raw/nhanes",
    cycles: list[str] | None = None,
    components: list[str] | None = None,
    include_mortality: bool = True,
) -> dict[str, list[Path]]:
    """Download NHANES XPT files from CDC.

    Args:
        output_dir: Root directory for raw NHANES files.
        cycles: Survey cycles to download. Defaults to all available.
        components: Components to download. Defaults to all.
        include_mortality: Whether to download mortality linkage files.

    Returns:
        Dict mapping component names to lists of downloaded file paths.
    """
    out = Path(output_dir)
    target_cycles = cycles or list(CYCLE_URL_MAP.keys())
    target_components = components or list(COMPONENTS.keys())

    downloaded: dict[str, list[Path]] = {}
    total_files = sum(
        1
        for comp in target_components
        for cycle in target_cycles
        if cycle in COMPONENTS.get(comp, {})
    )

    logger.info(
        "starting_nhanes_download",
        cycles=len(target_cycles),
        components=len(target_components),
        total_files=total_files,
    )

    for comp in target_components:
        comp_files = COMPONENTS.get(comp, {})
        downloaded[comp] = []

        for cycle in target_cycles:
            if cycle not in comp_files:
                continue

            filename = comp_files[cycle]
            url = _build_nhanes_url(cycle, filename, comp)
            dest = out / cycle / comp / filename

            success = _download_file(url, dest)
            if success:
                downloaded[comp].append(dest)

    if include_mortality:
        downloaded["mortality"] = []
        for cycle, mort_file in MORTALITY_FILES.items():
            if cycle not in target_cycles:
                continue
            url = f"{MORTALITY_BASE_URL}/{mort_file}"
            dest = out / cycle / "mortality" / mort_file
            if _download_file(url, dest):
                downloaded["mortality"].append(dest)

    total_downloaded = sum(len(v) for v in downloaded.values())
    logger.info("nhanes_download_complete", total_files_downloaded=total_downloaded)
    return downloaded


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Download NHANES data from CDC")
    parser.add_argument("--output-dir", default="data/raw/nhanes")
    parser.add_argument("--cycles", nargs="+", default=None)
    parser.add_argument("--components", nargs="+", default=None)
    parser.add_argument("--no-mortality", action="store_true")
    args = parser.parse_args()

    download_nhanes(
        output_dir=args.output_dir,
        cycles=args.cycles,
        components=args.components,
        include_mortality=not args.no_mortality,
    )


if __name__ == "__main__":
    main()
