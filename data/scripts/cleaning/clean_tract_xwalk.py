"""
clean_tract_xwalk.py
Stage:      cleaning (B1-B4)
Purpose:    Census tract relationship files, typed: 2000->2010 (with housing-unit parts) and
            2010->2020 (with land-area parts).
Codebook:   2010 file layout (no header in the file; 30 fields):
            https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/2010-tract-relationship-record-layout.html
            2020 file: header row in the file (pipe-delimited)
Reads:      data/raw/tract_xwalk/us2010trf.txt, tab20_tract20_tract10_natl.txt
Writes:     data/clean/tract_xwalk/tract00_tract10.csv, tract10_tract20.csv, data/logs/clean_tract_xwalk.log
Unit:       tract-pair part, unchanged (B3)
Decisions:  none
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, log_shape, project_root, write_table  # noqa: E402

COLS10 = ["STATE00", "COUNTY00", "TRACT00", "GEOID00", "POP00", "HU00", "PART00", "AREA00", "AREALAND00",
          "STATE10", "COUNTY10", "TRACT10", "GEOID10", "POP10", "HU10", "PART10", "AREA10", "AREALAND10",
          "AREAPT", "AREALANDPT", "AREAPCT00PT", "ARELANDPCT00PT", "AREAPCT10PT", "AREALANDPCT10PT",
          "POP10PT", "POPPCT00", "POPPCT10", "HU10PT", "HUPCT00", "HUPCT10"]
log = get_logger("clean_tract_xwalk")
root = project_root()

# == PHASE 1: LOAD AND PROFILE ==============================================
a = pd.read_csv(root / "data/raw/tract_xwalk/us2010trf.txt", header=None, names=COLS10, dtype=str)
b = pd.read_csv(root / "data/raw/tract_xwalk/tab20_tract20_tract10_natl.txt", sep="|", dtype=str, encoding="utf-8-sig")
log_shape(log, a, "2000-2010 raw")
log_shape(log, b, "2010-2020 raw")
na, nb = len(a), len(b)

# == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
check(a["GEOID00"].str.fullmatch(r"\d{11}").all() and a["GEOID10"].str.fullmatch(r"\d{11}").all(), "2000/2010 GEOIDs malformed")
check(b["GEOID_TRACT_20"].str.fullmatch(r"\d{11}").all() and b["GEOID_TRACT_10"].str.fullmatch(r"\d{11}").all(), "2010/2020 GEOIDs malformed")
check(not a.duplicated(["GEOID00", "GEOID10"]).any(), "2000-2010 pair not unique")
check(not b.duplicated(["GEOID_TRACT_20", "GEOID_TRACT_10"]).any(), "2010-2020 pair not unique")

# == PHASE 3: TRANSFORMATIONS ================================================
a = a.rename(columns={"GEOID00": "tract2000", "GEOID10": "tract2010", "HU10PT": "hu10_part", "HU10": "hu10_tract10",
                      "AREALANDPT": "land_part_m2", "AREALAND10": "land_tract10_m2"})
a = a[["tract2000", "tract2010", "hu10_part", "hu10_tract10", "land_part_m2", "land_tract10_m2"]]
for c in a.columns[2:]:
    a[c] = pd.to_numeric(a[c], errors="raise")
b = b.rename(columns={"GEOID_TRACT_20": "tract2020", "GEOID_TRACT_10": "tract2010", "AREALAND_PART": "land_part_m2",
                      "AREALAND_TRACT_20": "land_tract20_m2"})
b = b[["tract2020", "tract2010", "land_part_m2", "land_tract20_m2"]]
for c in b.columns[2:]:
    b[c] = pd.to_numeric(b[c], errors="raise")
log.info("rename", note="descriptive names for GEOIDs and part measures")

# == PHASE 4: POST-CLEANING ASSERTIONS =======================================
check(len(a) == na and len(b) == nb, "row count changed")
hu = a.groupby("tract2010").agg(parts=("hu10_part", "sum"), tot=("hu10_tract10", "first"))
check((hu["parts"] == hu["tot"]).mean() > 0.999, "2010 housing-unit parts do not add up to tract totals")
ld = b.groupby("tract2020").agg(parts=("land_part_m2", "sum"), tot=("land_tract20_m2", "first"))
check(((ld["parts"] - ld["tot"]).abs() <= 1).mean() > 0.999, "2020 land parts do not add up to tract land")

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
write_table(log, a, "data/clean/tract_xwalk/tract00_tract10.csv", sort_by=["tract2010", "tract2000"])
write_table(log, b, "data/clean/tract_xwalk/tract10_tract20.csv", sort_by=["tract2020", "tract2010"])
log.info("end")
