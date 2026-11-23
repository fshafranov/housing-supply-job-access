"""
acquire_lodes.py
Stage:      collection (A1-A4)
Purpose:    LEHD LODES 8 Workplace Area Characteristics (all jobs, all job types, census
            blocks, 2020 block geography) for every state except Alaska, for three job years:
            early (2002, else the first later year that exists), 2010, and latest (2023, else 2022).
Source:     https://lehd.ces.census.gov/data/lodes/LODES8/{st}/wac/{st}_wac_S000_JT00_{year}.csv.gz
Reads:      network only (no credentials)
Writes:     data/raw/lodes/{st}_wac_S000_JT00_{year}.csv.gz, data/logs/acquire_lodes.log
Verified:   one file per state and job role exists, is non-empty and is gzip (A3)
Usage:      uv run python data/scripts/collection/acquire_lodes.py [--force]
Decisions:  ANALYSIS_PLAN.md D3 (job years and fallbacks)
"""
import argparse
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import check, get_logger, project_root, verify_files  # noqa: E402

DATASET = "lodes"
RAW_DIR = Path("data/raw") / DATASET
URL = "https://lehd.ces.census.gov/data/lodes/LODES8/{st}/wac/{st}_wac_S000_JT00_{year}.csv.gz"
# Alaska has no metro in the sample and lacks 2020+ files (probe 2026-11-23).
STATES = ["al", "ar", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il",
          "in", "ks", "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "nc", "nd", "ne",
          "nh", "nj", "nm", "nv", "ny", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
          "va", "vt", "wa", "wi", "wv", "wy"]
# ANALYSIS_PLAN.md D3: candidate years per role, first available wins
# Massachusetts 2002-2010 files exist but are near-empty (7 and 17 jobs; clean_lodes.log), so the
# first full year is downloaded too; processing picks the first plausible year (D3).
EXTRA = {"ma": [2011]}
ROLES = {"early": [2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010], "mid": [2010], "late": [2023, 2022, 2021, 2020]}


def name(st: str, year: int) -> str:
    return f"{st}_wac_S000_JT00_{year}.csv.gz"


def main(force: bool) -> None:
    log = get_logger("acquire_lodes")
    root = project_root()
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)
    got = {}

    # == STEP 1: DOWNLOAD (first existing candidate year per state and role) ==
    for st in STATES:
        for role, years in ROLES.items():
            for y in years:
                dest = root / RAW_DIR / name(st, y)
                if dest.exists() and not force:
                    got[(st, role)] = y
                    break
                try:
                    download(URL.format(st=st, year=y), dest)
                    got[(st, role)] = y
                    log.info("downloaded", state=st, role=role, year=y)
                    time.sleep(0.5)  # be gentle: LEHD drops bursts of requests
                    break
                except httpx.HTTPStatusError as e:
                    check(e.response.status_code == 404, f"{st} {y}: HTTP {e.response.status_code}")
                    log.warning("not_available", state=st, role=role, year=y)
            if (st, role) not in got:
                log.warning("no_file_for_role", state=st, role=role, candidates=years)

    for st, ys in EXTRA.items():
        for y in ys:
            dest = root / RAW_DIR / name(st, y)
            if force or not dest.exists():
                download(URL.format(st=st, year=y), dest)
            got[(st, f"extra{y}")] = y

    # == STEP 2: VERIFY (A3) ==
    missing = [(st, r) for st in STATES for r in ROLES if (st, r) not in got]
    check(not missing, f"no file for state/role: {missing}")
    fallback = {f"{st}_{r}": y for (st, r), y in got.items() if r in ROLES and y != ROLES[r][0]}
    log.info("fallback_years", **fallback)
    verify_files(log, {str(RAW_DIR / name(st, y)): "gz" for (st, _r), y in got.items()})
    log.info("end", files_verified=len(got))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    main(parser.parse_args().force)
