"""
clean_cbsa.py
Stage:      cleaning (B1-B4)
Purpose:    OMB July 2023 delineation: one row per county with its CBSA, typed.
Codebook:   header row of data/raw/cbsa/list1_2023.xlsx (row 3); OMB Bulletin 23-01
Reads:      data/raw/cbsa/list1_2023.xlsx
Writes:     data/clean/cbsa/county_cbsa.csv, data/logs/clean_cbsa.log
Unit:       county (or equivalent) x CBSA, unchanged (B3); title and note rows are not data
Decisions:  none
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, log_shape, project_root, rename_logged, write_table  # noqa: E402

log = get_logger("clean_cbsa")
root = project_root()

# == PHASE 1: LOAD AND PROFILE ==============================================
df = pd.read_excel(root / "data/raw/cbsa/list1_2023.xlsx", header=2, dtype=str)
log_shape(log, df, "raw incl. footnote rows")

# == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
note = ~df["CBSA Code"].fillna("").str.fullmatch(r"\d{5}")
log.info("set_aside_footnotes", n_rows=int(note.sum()), first=df.loc[note, "CBSA Code"].head(3).tolist())
check(note.sum() <= 5, f"unexpectedly many non-data rows: {int(note.sum())}")
df = df.loc[~note].copy()
n_in = len(df)
check(set(df["Metropolitan/Micropolitan Statistical Area"]) ==
      {"Metropolitan Statistical Area", "Micropolitan Statistical Area"}, "unexpected area types")

# == PHASE 3: TRANSFORMATIONS ================================================
df["county_fips"] = df["FIPS State Code"].str.zfill(2) + df["FIPS County Code"].str.zfill(3)
df["is_metro"] = df["Metropolitan/Micropolitan Statistical Area"].eq("Metropolitan Statistical Area")
df = rename_logged(log, df, {"CBSA Code": "cbsa_code", "CBSA Title": "cbsa_title",
                             "Central/Outlying County": "central_outlying", "State Name": "state_name"})
df = df[["county_fips", "cbsa_code", "cbsa_title", "is_metro", "central_outlying", "state_name"]]

# == PHASE 4: POST-CLEANING ASSERTIONS =======================================
check(len(df) == n_in, "row count changed")
check(df["county_fips"].is_unique, "a county appears in more than one CBSA")

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
log.info("profile", n_cbsa=df["cbsa_code"].nunique(), n_metro=df.loc[df.is_metro, "cbsa_code"].nunique())
write_table(log, df, "data/clean/cbsa/county_cbsa.csv", sort_by=["county_fips"])
log.info("end")
