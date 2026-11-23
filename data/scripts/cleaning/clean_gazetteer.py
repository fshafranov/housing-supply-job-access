"""
clean_gazetteer.py
Stage:      cleaning (B1-B4)
Purpose:    2020 tract Gazetteer: GEOID, land area and internal point, typed.
Codebook:   https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2020.html
Reads:      data/raw/gazetteer/2020_Gaz_tracts_national.zip
Writes:     data/clean/gazetteer/tracts_2020.csv, data/logs/clean_gazetteer.log
Unit:       2020 census tract, unchanged (B3)
Decisions:  none
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, log_shape, project_root, rename_logged, write_table  # noqa: E402

log = get_logger("clean_gazetteer")
root = project_root()

# == PHASE 1: LOAD AND PROFILE ==============================================
df = pd.read_csv(root / "data/raw/gazetteer/2020_Gaz_tracts_national.zip", sep="\t", dtype=str)
df.columns = df.columns.str.strip()  # last header carries trailing spaces in the source
log_shape(log, df, "raw")
n_in = len(df)

# == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
check({"USPS", "GEOID", "ALAND", "INTPTLAT", "INTPTLONG"} <= set(df.columns), f"columns: {list(df.columns)}")
check(df["GEOID"].is_unique, "GEOID not unique")

# == PHASE 3: TRANSFORMATIONS ================================================
df = df[["GEOID", "USPS", "ALAND", "INTPTLAT", "INTPTLONG"]].apply(lambda s: s.str.strip())
df = rename_logged(log, df, {"GEOID": "tract_geoid", "USPS": "state_abbr", "ALAND": "land_area_m2",
                             "INTPTLAT": "lat", "INTPTLONG": "lon"})
for c in ["land_area_m2", "lat", "lon"]:
    df[c] = pd.to_numeric(df[c], errors="raise")

# == PHASE 4: POST-CLEANING ASSERTIONS =======================================
check(len(df) == n_in, "row count changed")
check(df["tract_geoid"].str.fullmatch(r"\d{11}").all(), "GEOID not 11 digits")
check(df["lat"].between(-15, 72).all() and df["lon"].between(-180, 180).all(), "coordinates out of range")

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
log_shape(log, df, "clean")
write_table(log, df, "data/clean/gazetteer/tracts_2020.csv", sort_by=["tract_geoid"])
log.info("end")
