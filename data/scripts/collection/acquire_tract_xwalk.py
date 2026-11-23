"""
acquire_tract_xwalk.py
Stage:      collection (A1-A4)
Purpose:    Census Bureau tract relationship files: 2000 to 2010 tracts and 2010 to 2020 tracts (national).
Source:     https://www2.census.gov/geo/docs/maps-data/data/rel/trf_txt/us2010trf.txt; https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt
Reads:      network only (no credentials)
Writes:     data/raw/tract_xwalk/<files>, data/logs/acquire_tract_xwalk.log
Verified:   every expected file exists, is non-empty and parses as its declared format (A3)
Usage:      uv run python data/scripts/collection/acquire_tract_xwalk.py [--force]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import get_logger, project_root, verify_files  # noqa: E402

DATASET = "tract_xwalk"
RAW_DIR = Path("data/raw") / DATASET
SOURCES = {"us2010trf.txt": ("https://www2.census.gov/geo/docs/maps-data/data/rel/trf_txt/us2010trf.txt", "txt"),
           "tab20_tract20_tract10_natl.txt": ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt", "txt")}


def main(force: bool) -> None:
    log = get_logger("acquire_tract_xwalk")
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
