"""
clean_lodes_od.py
Stage:      cleaning (B1-B4)
Purpose:    LODES 8 OD files (main and aux, all jobs): home block, work block, job count, typed;
            one Parquet file per raw file to keep memory bounded.
Codebook:   https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.pdf (OD layout)
Reads:      data/raw/lodes_od/{st}_od_{main|aux}_JT00_{year}.csv.gz
Writes:     data/clean/lodes_od/{st}_od_{part}_{year}.parquet, data/clean/lodes_od/files.csv,
            data/logs/clean_lodes_od.log
Unit:       home block x work block (one state file), unchanged (B3)
Decisions:  none
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

log = get_logger("clean_lodes_od")
root = project_root()
OUT = Path("data/clean/lodes_od")
files = sorted((root / "data/raw/lodes_od").glob("*_od_*_JT00_*.csv.gz"))
check(len(files) == 204, f"expected 204 OD files (50 states x 2 years x main/aux + MA 2011, AR 2010), found {len(files)}")
st_fips = pd.read_csv(root / "data/clean/gazetteer/tracts_2020.csv", dtype=str, usecols=["tract_geoid", "state_abbr"])
st_fips = dict(zip(st_fips["state_abbr"].str.lower(), st_fips["tract_geoid"].str[:2], strict=True))
summary = []

for f in files:
    st, part, year = f.name[:2], f.name.split("_")[2], int(f.name[-11:-7])
    # == PHASE 1: LOAD AND PROFILE ==============================================
    df = pd.read_csv(f, usecols=["w_geocode", "h_geocode", "S000"], dtype={"w_geocode": str, "h_geocode": str, "S000": "int64"})
    n_in = len(df)

    # == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
    check(df["w_geocode"].str.fullmatch(r"\d{15}").all() and df["h_geocode"].str.fullmatch(r"\d{15}").all(),
          f"{f.name}: block codes not 15 digits")
    check((df["S000"] > 0).all(), f"{f.name}: rows with zero jobs")
    check(df["w_geocode"].str[:2].eq(st_fips[st]).all(), f"{f.name}: work block outside the file's state")
    home_in = df["h_geocode"].str[:2].eq(st_fips[st])
    check(home_in.all() if part == "main" else (~home_in).all(),
          f"{f.name}: home-state rule of the {part} file violated ({int((~home_in).sum())} out-of-state homes)")
    check(not df.duplicated(["w_geocode", "h_geocode"]).any(), f"{f.name}: block pair not unique")

    # == PHASE 3: TRANSFORMATIONS ================================================
    out = pd.DataFrame({"home_block": df["h_geocode"].astype("int64"), "work_block": df["w_geocode"].astype("int64"),
                        "jobs": df["S000"].astype("int32")})

    # == PHASE 4: POST-CLEANING ASSERTIONS =======================================
    check(len(out) == n_in, "row count changed")

    # == PHASE 5: FINAL PROFILE AND WRITE ========================================
    write_table(log, out, str(OUT / f"{st}_od_{part}_{year}.parquet"), sort_by=["home_block", "work_block"])
    summary.append({"state_abbr": st, "part": part, "year": year, "rows": n_in, "jobs": int(out["jobs"].sum())})

summary = pd.DataFrame(summary)
log.info("totals", rows=int(summary["rows"].sum()), jobs=int(summary["jobs"].sum()))
write_table(log, summary, str(OUT / "files.csv"), sort_by=["state_abbr", "part"])
log.info("end")
