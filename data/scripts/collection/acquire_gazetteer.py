"""
acquire_gazetteer.py
Stage:      collection (A1-A4)
Purpose:    2020 Census Gazetteer tract file (land area and internal point for every 2020 tract).
Source:     https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_tracts_national.zip
Reads:      network only (no credentials)
Writes:     data/raw/gazetteer/<files>, data/logs/acquire_gazetteer.log
Verified:   every expected file exists, is non-empty and parses as its declared format (A3)
Usage:      uv run python data/scripts/collection/acquire_gazetteer.py [--force]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import get_logger, project_root, verify_files  # noqa: E402

DATASET = "gazetteer"
RAW_DIR = Path("data/raw") / DATASET
SOURCES = {"2020_Gaz_tracts_national.zip": ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_tracts_national.zip", "zip")}


def main(force: bool) -> None:
    log = get_logger("acquire_gazetteer")
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
