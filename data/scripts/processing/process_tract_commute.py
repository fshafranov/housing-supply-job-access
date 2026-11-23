"""
process_tract_commute.py
Stage:      processing (C1-C4)
Purpose:    Actual commutes of each sample tract's residents (LODES OD, latest year): straight-line
            home-tract to work-tract distance for every resident job, summarised per home tract
            (median km, mean km of commutes up to 100 km, share within 10 km, share beyond
            100 km) and converted to within-metro percentiles (high = short commute).
Reads:      data/clean/lodes_od/*.parquet, files.csv; data/clean/gazetteer/tracts_2020.csv;
            data/processed/tract_vintage/tracts.csv
Writes:     data/processed/tract_vintage/tract_commute.csv, data/logs/process_tract_commute.log
Unit:       2020 census tract (home), sample tracts only
Decisions:  ANALYSIS_PLAN.md D7 (percentiles), D9 (commute year), D10 (within-tract distance),
            D11 (long-distance commutes)
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
from spatial import haversine_pairs_km, unit_pctile  # noqa: E402

CAP_KM = 100        # ANALYSIS_PLAN.md D11
NEAR_KM = 10
log = get_logger("process_tract_commute")
root = project_root()

# == PHASE 1: LOAD ===========================================================
tracts = pd.read_csv(root / "data/processed/tract_vintage/tracts.csv", dtype={"tract_geoid": str, "cbsa_code": str})
gaz = pd.read_csv(root / "data/clean/gazetteer/tracts_2020.csv", dtype={"tract_geoid": str})
files = pd.read_csv(root / "data/clean/lodes_od/files.csv")
check(len(files) == 204, f"expected 204 OD files, found {len(files)}")
files = files[files["year"] == files.groupby("state_abbr")["year"].transform("max")]  # D9: latest year
check(len(files) == 100, f"expected 100 latest-year OD files, found {len(files)}")
sample = set(tracts["tract_geoid"].astype("int64"))
log.info("od_years", years=files.groupby("year")["state_abbr"].nunique().to_dict())

# == PHASE 2: RESIDENT JOBS OF SAMPLE TRACTS, BY WORK TRACT =====================
parts = []
for _, f in files.iterrows():
    od = pd.read_parquet(root / f"data/clean/lodes_od/{f.state_abbr}_od_{f.part}_{f.year}.parquet")
    od["home_tract"] = od["home_block"] // 10_000
    od = od[od["home_tract"].isin(sample)]
    od["work_tract"] = od["work_block"] // 10_000
    parts.append(od.groupby(["home_tract", "work_tract"], as_index=False)["jobs"].sum())
flows = pd.concat(parts, ignore_index=True).groupby(["home_tract", "work_tract"], as_index=False)["jobs"].sum()
log_shape(log, flows, "home tract x work tract flows")
log.info("resident_jobs", jobs=int(flows["jobs"].sum()), home_tracts=int(flows["home_tract"].nunique()))

# == PHASE 3: DISTANCES ======================================================
g = gaz.assign(t=gaz["tract_geoid"].astype("int64"))[["t", "lat", "lon", "land_area_m2"]]
flows = checked_merge(log, flows, g.rename(columns={"t": "home_tract", "lat": "hlat", "lon": "hlon", "land_area_m2": "harea"}),
                      on="home_tract", how="left", validate="m:1", name="flows_home_coords")
flows = checked_merge(log, flows, g.rename(columns={"t": "work_tract", "lat": "wlat", "lon": "wlon"}).drop(columns="land_area_m2"),
                      on="work_tract", how="left", validate="m:1", name="flows_work_coords")
nowork = flows["wlat"].isna()
log.info("work_tract_without_coords", flows=int(nowork.sum()), jobs=int(flows.loc[nowork, "jobs"].sum()),
         reason="work tract not in 2020 Gazetteer; these jobs get no distance")
check(flows.loc[nowork, "jobs"].sum() < 0.001 * flows["jobs"].sum(), "more than 0.1% of jobs lack a work location")
flows = flows[~nowork].copy()
flows["km"] = haversine_pairs_km(flows["hlat"].to_numpy(), flows["hlon"].to_numpy(),
                                 flows["wlat"].to_numpy(), flows["wlon"].to_numpy())
# D10: home and work in the same tract -> mean distance between two random points of a square
# of the tract's land area (0.52 x side), instead of zero
same = flows["home_tract"] == flows["work_tract"]
flows.loc[same, "km"] = 0.52 * np.sqrt(flows.loc[same, "harea"] / 1e6)
log.info("same_tract_jobs", share=round(float(flows.loc[same, "jobs"].sum() / flows["jobs"].sum()), 4))
summarize_var(log, flows, "km", lower=0, upper=9000)  # Hawaii-Maine is ~8,300 km (D11)

# == PHASE 4: TRACT SUMMARIES ================================================
flows = flows.sort_values(["home_tract", "km"], kind="mergesort")
flows["cum"] = flows.groupby("home_tract")["jobs"].cumsum()
tot = flows.groupby("home_tract")["jobs"].transform("sum")
med = flows[flows["cum"] >= tot / 2].groupby("home_tract")["km"].first().rename("commute_median_km")
near = flows["km"] <= NEAR_KM
far = flows["km"] > CAP_KM  # D11: likely remote work or a firm's address, not a daily commute
agg = pd.DataFrame({
    "resident_jobs": flows.groupby("home_tract")["jobs"].sum(),
    "commute_share_le10km": flows[near].groupby("home_tract")["jobs"].sum(),
    "commute_share_gt100km": flows[far].groupby("home_tract")["jobs"].sum(),
    "commute_mean_km_le100": (flows.loc[~far, "km"] * flows.loc[~far, "jobs"]).groupby(flows.loc[~far, "home_tract"]).sum()
    / flows[~far].groupby("home_tract")["jobs"].sum(),
}).join(med)
agg[["commute_share_le10km", "commute_share_gt100km"]] = agg[["commute_share_le10km", "commute_share_gt100km"]].fillna(0)
agg["commute_share_le10km"] /= agg["resident_jobs"]
agg["commute_share_gt100km"] /= agg["resident_jobs"]
agg = agg.rename_axis("home_tract").reset_index()
agg.insert(0, "tract_geoid", agg.pop("home_tract").astype("int64").astype(str).str.zfill(11))
check(agg["tract_geoid"].str.fullmatch(r"\d{11}").all(), "home tract codes not 11 digits")

out = checked_merge(log, tracts[["tract_geoid", "cbsa_code", "units_total"]], agg, on="tract_geoid",
                    how="left", validate="1:1", name="sample_to_commutes")
nores = out["resident_jobs"].isna()
log.info("tracts_without_resident_jobs", n=int(nores.sum()), units=int(out.loc[nores, "units_total"].sum()))
out["resident_jobs"] = out["resident_jobs"].fillna(0)

# D7: within-metro percentiles among housing units, oriented so high = short commute
has = out[out["resident_jobs"] > 0].copy()
for col, name in [("commute_median_km", "commute_median_close_pctile"),
                  ("commute_mean_km_le100", "commute_mean_close_pctile")]:
    has["_neg"] = -has[col]
    has[name] = pd.concat([unit_pctile(gr, "_neg") for _, gr in has.groupby("cbsa_code")])
out = out.merge(has[["tract_geoid", "commute_median_close_pctile", "commute_mean_close_pctile"]],
                on="tract_geoid", how="left", validate="1:1")
for c in ["commute_median_km", "commute_mean_km_le100"]:
    summarize_var(log, out, c, lower=0, upper=9000)
for c in ["commute_share_le10km", "commute_share_gt100km"]:
    summarize_var(log, out, c, lower=0, upper=1)
for c in ["commute_median_close_pctile", "commute_mean_close_pctile"]:
    summarize_var(log, out, c, lower=0, upper=100)

# == PHASE 5: WRITE ==========================================================
write_table(log, out.drop(columns=["cbsa_code", "units_total"]), "data/processed/tract_vintage/tract_commute.csv",
            sort_by=["tract_geoid"])
log.info("end", tracts=len(out))
