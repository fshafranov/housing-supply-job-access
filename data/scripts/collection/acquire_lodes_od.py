"""
acquire_lodes_od.py
Stage:      collection (A1-A4)
Purpose:    LEHD LODES 8 Origin-Destination files (all jobs, JT00, 2020 census blocks) for two
            years per state: latest available (2023, else 2022, else 2021) and earliest available
            (2002, else the next year that exists), plus Massachusetts 2011 and Arkansas 2010
            because their earliest files are incomplete (as in the WAC files, D3). "main" = home
            and work in the state, "aux" = work in the state, home in another state. Every state
            except Alaska. Downloads run six at a time (one connection runs at ~0.5 MB/s;
            four in parallel reached ~2 MB/s in a test on 2026-11-23).
Source:     https://lehd.ces.census.gov/data/lodes/LODES8/{st}/od/{st}_od_{part}_JT00_{year}.csv.gz
Reads:      network only (no credentials)
Writes:     data/raw/lodes_od/{st}_od_{part}_JT00_{year}.csv.gz, data/logs/acquire_lodes_od.log
Verified:   one main and one aux file per state, non-empty, gzip (A3)
Usage:      uv run python data/scripts/collection/acquire_lodes_od.py [--force]
Decisions:  ANALYSIS_PLAN.md D3 (early-year fallbacks), D9 (commute years)
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import check, get_logger, project_root, verify_files  # noqa: E402

DATASET = "lodes_od"
RAW_DIR = Path("data/raw") / DATASET
URL = "https://lehd.ces.census.gov/data/lodes/LODES8/{st}/od/{st}_od_{part}_JT00_{year}.csv.gz"
STATES = ["al", "ar", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il",
          "in", "ks", "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "nc", "nd", "ne",
          "nh", "nj", "nm", "nv", "ny", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
          "va", "vt", "wa", "wi", "wv", "wy"]
# ANALYSIS_PLAN.md D9: first available year in each list, same rules as the WAC files (D3)
ROLES = {"late": [2023, 2022, 2021], "early": list(range(2002, 2012))}
EXTRA = {"ma": [2011], "ar": [2010]}  # D3: earliest MA and AR files are near-empty / incomplete
WORKERS = 6


def name(st, part, year):
    return f"{st}_od_{part}_JT00_{year}.csv.gz"


def fetch_state(st: str, force: bool, root: Path, log) -> dict:
    """First available year per role for one state; main and aux must share the year."""
    got = {}
    for role, years in ROLES.items():
        for y in years:
            try:
                for p in ("main", "aux"):
                    dest = root / RAW_DIR / name(st, p, y)
                    if force or not dest.exists():
                        download(URL.format(st=st, part=p, year=y), dest)
                        time.sleep(0.5)  # LEHD drops bursts of requests
                got[role] = y
                log.info("state_done", state=st, role=role, year=y)
                break
            except httpx.HTTPStatusError as e:
                check(e.response.status_code == 404, f"{st} {y}: HTTP {e.response.status_code}")
                log.warning("not_available", state=st, role=role, year=y)
    for y in EXTRA.get(st, []):
        for p in ("main", "aux"):
            dest = root / RAW_DIR / name(st, p, y)
            if force or not dest.exists():
                download(URL.format(st=st, part=p, year=y), dest)
        got[f"extra{y}"] = y
    return got


def main(force: bool) -> None:
    log = get_logger("acquire_lodes_od")
    root = project_root()
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)

    # == STEP 1: DOWNLOAD (six states at a time) ==
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = dict(zip(STATES, pool.map(lambda st: fetch_state(st, force, root, log), STATES), strict=True))

    # == STEP 2: VERIFY (A3) ==
    missing = [(st, r) for st in STATES for r in ROLES if r not in results[st]]
    check(not missing, f"no OD year for {missing}")
    log.info("nonstandard_years", **{f"{st}_{r}": y for st, g in results.items() for r, y in g.items()
                                     if r in ROLES and y != ROLES[r][0]})
    files = {str(RAW_DIR / name(st, p, y)): "gz" for st, g in results.items() for y in set(g.values())
             for p in ("main", "aux")}
    verify_files(log, files)
    log.info("end", files_verified=len(files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    main(parser.parse_args().force)
