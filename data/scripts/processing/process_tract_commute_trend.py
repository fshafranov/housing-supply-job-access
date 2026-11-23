"""
process_tract_commute_trend.py
Stage:      processing (C1-C4)
Purpose:    Commutes of each sample tract's working residents in the early year (2002 where
            available) and the latest year (2023), same definitions as process_tract_commute.py,
            for the commute trend and its within/between split.
Reads:      data/clean/lodes_od/*.parquet, files.csv; data/clean/gazetteer/tracts_2020.csv;
            data/processed/tract_vintage/tracts.csv
Writes:     data/processed/tract_commute_trend/tract_commute_trend.csv, state_years.csv,
            data/logs/process_tract_commute_trend.log
Unit:       2020 census tract (home) x role (early, late); LODES 8 uses 2020 blocks in every year
Decisions:  ANALYSIS_PLAN.md D3 (plausible early year), D9, D10, D11, D16 (trend sample)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import (  # noqa: E402
    check,
    checked_merge,
    get_logger,
    log_shape,
    project_root,
    summarize_var,
    write_table,
)
from spatial import haversine_pairs_km  # noqa: E402

CAP_KM, NEAR_KM = 100, 10   # D11
OUT = Path("data/processed/tract_commute_trend")
log = get_logger("process_tract_commute_trend")
root = project_root()

# == PHASE 1: LOAD AND PICK YEARS ============================================
tracts = pd.read_csv(root / "data/processed/tract_vintage/tracts.csv", dtype={"tract_geoid": str, "cbsa_code": str})
gaz = pd.read_csv(root / "data/clean/gazetteer/tracts_2020.csv", dtype={"tract_geoid": str})
files = pd.read_csv(root / "data/clean/lodes_od/files.csv")
check(len(files) == 204, f"expected 204 OD files, found {len(files)}")
tot = files.groupby(["state_abbr", "year"])["jobs"].sum().unstack()
ok = tot.ge(0.5 * tot.max(axis=1), axis=0) & tot.notna()  # D3: plausible state-years only
years = pd.DataFrame({"early": [min(int(y) for y in r.index[r]) for _, r in ok.iterrows()],
                      "late": [max(int(y) for y in r.index[r]) for _, r in ok.iterrows()]}, index=ok.index)
years.index.name = "state_abbr"
log.info("state_years_nonstandard", **{s: f"{r.early}-{r.late}" for s, r in years.iterrows() if (r.early, r.late) != (2002, 2023)})
write_table(log, years.reset_index(), str(OUT / "state_years.csv"), sort_by=["state_abbr"])
sample = set(tracts["tract_geoid"].astype("int64"))
g = gaz.assign(t=gaz["tract_geoid"].astype("int64"))[["t", "lat", "lon", "land_area_m2"]]

out = []
for role in ["early", "late"]:
    # == PHASE 2: FLOWS FOR THIS ROLE ==========================================
    parts = []
    for st, y in years[role].items():
        for part in ("main", "aux"):
            od = pd.read_parquet(root / f"data/clean/lodes_od/{st}_od_{part}_{y}.parquet")
            od["home_tract"] = od["home_block"] // 10_000
            od = od[od["home_tract"].isin(sample)]
            od["work_tract"] = od["work_block"] // 10_000
            parts.append(od.groupby(["home_tract", "work_tract"], as_index=False)["jobs"].sum())
    fl = pd.concat(parts, ignore_index=True).groupby(["home_tract", "work_tract"], as_index=False)["jobs"].sum()
    log_shape(log, fl, f"{role} flows")

    # == PHASE 3: DISTANCES (D10) ==============================================
    fl = checked_merge(log, fl, g.rename(columns={"t": "home_tract", "lat": "hlat", "lon": "hlon", "land_area_m2": "harea"}),
                       on="home_tract", how="left", validate="m:1", name=f"{role}_home_coords")
    fl = checked_merge(log, fl, g.rename(columns={"t": "work_tract", "lat": "wlat", "lon": "wlon"}).drop(columns="land_area_m2"),
                       on="work_tract", how="left", validate="m:1", name=f"{role}_work_coords")
    check(fl["wlat"].notna().all(), f"{role}: work tracts without coordinates")
    fl["km"] = haversine_pairs_km(fl["hlat"].to_numpy(), fl["hlon"].to_numpy(), fl["wlat"].to_numpy(), fl["wlon"].to_numpy())
    same = fl["home_tract"] == fl["work_tract"]
    fl.loc[same, "km"] = 0.52 * np.sqrt(fl.loc[same, "harea"] / 1e6)

    # == PHASE 4: TRACT SUMMARIES ==============================================
    fl = fl.sort_values(["home_tract", "km"], kind="mergesort")
    fl["cum"] = fl.groupby("home_tract")["jobs"].cumsum()
    half = fl.groupby("home_tract")["jobs"].transform("sum") / 2
    far = fl["km"] > CAP_KM
    a = pd.DataFrame({
        "resident_jobs": fl.groupby("home_tract")["jobs"].sum(),
        "jobs_le100": fl[~far].groupby("home_tract")["jobs"].sum(),
        "km_sum_le100": (fl.loc[~far, "km"] * fl.loc[~far, "jobs"]).groupby(fl.loc[~far, "home_tract"]).sum(),
        "jobs_le10": fl[fl["km"] <= NEAR_KM].groupby("home_tract")["jobs"].sum(),
        "commute_median_km": fl[fl["cum"] >= half].groupby("home_tract")["km"].first(),
    }).fillna({"jobs_le100": 0, "km_sum_le100": 0, "jobs_le10": 0})
    a["commute_mean_km_le100"] = a["km_sum_le100"] / a["jobs_le100"].replace(0, np.nan)
    a["commute_share_le10km"] = a["jobs_le10"] / a["resident_jobs"]
    a["commute_share_gt100km"] = 1 - a["jobs_le100"] / a["resident_jobs"]
    a = a.rename_axis("home_tract").reset_index()
    a.insert(0, "tract_geoid", a.pop("home_tract").astype("int64").astype(str).str.zfill(11))
    a.insert(1, "role", role)
    log.info("role_totals", role=role, resident_jobs=int(a["resident_jobs"].sum()), tracts=len(a))
    out.append(a)

df = pd.concat(out, ignore_index=True)
check(not df.duplicated(["tract_geoid", "role"]).any(), "tract x role not unique")
for c in ["commute_median_km", "commute_mean_km_le100"]:
    summarize_var(log, df, c, lower=0, upper=9000)
for c in ["commute_share_le10km", "commute_share_gt100km"]:
    summarize_var(log, df, c, lower=0, upper=1)

# == PHASE 5: WRITE ==========================================================
write_table(log, df.drop(columns=["jobs_le10"]), str(OUT / "tract_commute_trend.csv"), sort_by=["tract_geoid", "role"])
log.info("end", rows=len(df))
