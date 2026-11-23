"""
clean_lodes.py
Stage:      cleaning (B1-B4)
Purpose:    Stack LODES 8 WAC files: total jobs (C000) per census block and year, typed.
Codebook:   https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.pdf (WAC layout)
Reads:      data/raw/lodes/{st}_wac_S000_JT00_{year}.csv.gz
Writes:     data/clean/lodes/wac_blocks.parquet (about 10 million rows), data/logs/clean_lodes.log
Unit:       2020 census block x year, unchanged (B3)
Decisions:  none
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, log_shape, project_root, write_table  # noqa: E402

log = get_logger("clean_lodes")
root = project_root()

# == PHASE 1: LOAD AND PROFILE ==============================================
files = sorted((root / "data/raw/lodes").glob("*_wac_S000_JT00_*.csv.gz"))
check(len(files) == 150, f"expected 150 WAC files (acquire_lodes.log), found {len(files)}")
frames = []
for f in files:
    d = pd.read_csv(f, usecols=["w_geocode", "C000"], dtype={"w_geocode": str, "C000": "int64"})
    d["state_abbr"] = f.name[:2]
    d["year"] = int(f.name[-11:-7])
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
n_in = len(df)
log_shape(log, df, "raw stacked")

# == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
check(df["w_geocode"].str.fullmatch(r"\d{15}").all(), "block code not 15 digits")
check(not df.duplicated(["w_geocode", "year"]).any(), "block x year not unique")
check((df["C000"] > 0).all(), "WAC rows with zero or negative total jobs")

# == PHASE 3: TRANSFORMATIONS ================================================
df = df.rename(columns={"w_geocode": "block_geoid", "C000": "jobs"})
log.info("rename", old="w_geocode,C000", new="block_geoid,jobs")

# == PHASE 4: POST-CLEANING ASSERTIONS =======================================
check(len(df) == n_in, "row count changed")
by = df.groupby("year")["jobs"].sum()
log.info("jobs_by_year", **{str(k): int(v) for k, v in by.items()})

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
write_table(log, df, "data/clean/lodes/wac_blocks.parquet", sort_by=["block_geoid", "year"])
log.info("end")
