"""
acquire_acs.py
Stage:      collection (A1-A4)
Purpose:    ACS 2019-2023 5-year table-based summary files (all geographies, national) for B25034 (year structure built) and B25127 (tenure x year built x units in structure).
Source:     https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/
Reads:      network only (no credentials)
Writes:     data/raw/acs/<files>, data/logs/acquire_acs.log
Verified:   every expected file exists, is non-empty and parses as its declared format (A3)
Usage:      uv run python data/scripts/collection/acquire_acs.py [--force]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import get_logger, project_root, verify_files  # noqa: E402

DATASET = "acs"
RAW_DIR = Path("data/raw") / DATASET
BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/"
META = "https://api.census.gov/data/2023/acs/acs5/groups/{t}.json"  # variable labels (codebook), no key needed
SOURCES = {f"acsdt5y2023-{t}.dat": (BASE + f"acsdt5y2023-{t}.dat", "txt") for t in ("b25034", "b25127")}
SOURCES |= {f"labels_{t}.json": (META.format(t=t.upper()), "json") for t in ("b25034", "b25127")}


def main(force: bool) -> None:
    log = get_logger("acquire_acs")
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
