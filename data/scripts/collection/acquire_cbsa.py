"""
acquire_cbsa.py
Stage:      collection (A1-A4)
Purpose:    OMB July 2023 CBSA delineation file (county to metro area) as published by the Census Bureau.
Source:     https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx
Reads:      network only (no credentials)
Writes:     data/raw/cbsa/<files>, data/logs/acquire_cbsa.log
Verified:   every expected file exists, is non-empty and parses as its declared format (A3)
Usage:      uv run python data/scripts/collection/acquire_cbsa.py [--force]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import get_logger, project_root, verify_files  # noqa: E402

DATASET = "cbsa"
RAW_DIR = Path("data/raw") / DATASET
SOURCES = {"list1_2023.xlsx": ("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx", "xlsx")}


def main(force: bool) -> None:
    log = get_logger("acquire_cbsa")
    root = project_root()
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)

    # == STEP 1: DOWNLOAD (files already present are kept unless --force) ==
    for name, (url, _fmt) in sorted(SOURCES.items()):
        dest = root / RAW_DIR / name
        if dest.exists() and not force:
            log.info("present", file=name)
            continue
        log.info("download", file=name, url=url)
        download(url, dest)

    # == STEP 2: VERIFY (A3) ==
    verify_files(log, {str(RAW_DIR / n): fmt for n, (_u, fmt) in SOURCES.items()})
    log.info("end", files_verified=len(SOURCES))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    main(parser.parse_args().force)
