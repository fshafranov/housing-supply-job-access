"""
process_tract_vintage.py
Stage:      processing (C1-C4)
Purpose:    Build the estimation sample: tracts of the 50 largest metros with their housing
            units by year built (surviving stock in 2019-2023) and their job access (share of
            the metro's jobs within 5/10/20 km straight-line of the tract internal point) for
            three job years, plus distance to the metro's job center.
Reads:      data/clean/acs/b25034.csv, b25127.csv; data/clean/gazetteer/tracts_2020.csv;
            data/clean/cbsa/county_cbsa.csv; data/clean/lodes/wac_blocks.parquet
Writes:     data/processed/tract_vintage/tracts.csv            (tract: access, jobs, units)
            data/processed/tract_vintage/tract_vintage.csv     (tract x decade built: units)
            data/processed/tract_vintage/tract_structure.csv   (tract x tenure x 20-year bin x structure)
            data/processed/tract_vintage/metros.csv            (metro: size, job years used)
            data/processed/tract_vintage/tract_vintage_dropped.csv, data/logs/process_tract_vintage.log
Unit:       2020 census tract (x vintage)
Decisions:  ANALYSIS_PLAN.md D1 (sample), D2 (Connecticut, Puerto Rico), D3 (job years),
            D4 (access measure), D5 (job center), D6 (access to job growth), D7 (percentiles)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import (  # noqa: E402
    AttritionTracker,
    check,
    checked_merge,
    get_logger,
    log_shape,
    project_root,
    summarize_var,
    write_table,
)
from spatial import haversine_km, unit_pctile  # noqa: E402

OUT = Path("data/processed/tract_vintage")
N_METROS = 50          # ANALYSIS_PLAN.md D1
RADII_KM = [5, 10, 20]  # ANALYSIS_PLAN.md D4
CENTER_RADIUS_KM = 3   # ANALYSIS_PLAN.md D5
DECADES = ["1939_earlier", "1940_1949", "1950_1959", "1960_1969", "1970_1979", "1980_1989",
           "1990_1999", "2000_2009", "2010_2019", "2020plus"]

log = get_logger("process_tract_vintage")
root = project_root()

# == PHASE 1: LOAD ===========================================================
b34 = pd.read_csv(root / "data/clean/acs/b25034.csv", dtype={"tract_geoid": str})
b127 = pd.read_csv(root / "data/clean/acs/b25127.csv", dtype={"tract_geoid": str})
gaz = pd.read_csv(root / "data/clean/gazetteer/tracts_2020.csv", dtype={"tract_geoid": str})
cbsa = pd.read_csv(root / "data/clean/cbsa/county_cbsa.csv", dtype={"county_fips": str, "cbsa_code": str})
wac = pd.read_parquet(root / "data/clean/lodes/wac_blocks.parquet")
for name, d in [("b25034", b34), ("b25127", b127), ("gazetteer", gaz), ("cbsa", cbsa), ("wac", wac)]:
    log_shape(log, d, name)

# == PHASE 2: SAMPLE SELECTION ===============================================
units = checked_merge(log, b34, b127[["tract_geoid"] + [c for c in b127.columns if c.startswith("units_")]],
                      on="tract_geoid", how="inner", validate="1:1", name="b25034_b25127")
units["county_fips"] = units["tract_geoid"].str[:5]
units = checked_merge(log, units, cbsa[["county_fips", "cbsa_code", "cbsa_title", "is_metro"]],
                      on="county_fips", how="left", validate="m:1", name="tract_to_cbsa")
units = checked_merge(log, units, gaz[["tract_geoid", "lat", "lon", "land_area_m2"]],
                      on="tract_geoid", how="left", validate="1:1", name="tract_to_gazetteer")

# D1: the 50 largest metropolitan CBSAs by housing units (ACS 2019-2023), ranked before D2
metro_units = (units[units["is_metro"].eq(True)].groupby(["cbsa_code", "cbsa_title"])["units_total"]
               .sum().sort_values(ascending=False).reset_index())
top = metro_units.head(N_METROS).copy()
top["size_rank"] = np.arange(1, len(top) + 1)
# D2: Connecticut tracts were renumbered in 2022 (planning regions); 2020 job geography does
# not line up with 2023 ACS tracts, so metros with Connecticut counties are excluded.
# Puerto Rico has no LODES files, so its metros are excluded too.
top["has_ct"] = top["cbsa_title"].str.contains(r"\b(?:CT|PR)\b")
log.info("top_metros", n=len(top), excluded=top.loc[top.has_ct, "cbsa_title"].tolist(),
         smallest=top["cbsa_title"].iloc[-1], smallest_units=int(top["units_total"].iloc[-1]))

att = AttritionTracker(log, units, "all ACS tracts")
units = att.filter(units, units["cbsa_code"].isin(top["cbsa_code"]), "not in the 50 largest metros (D1)")
units = att.filter(units, ~units["cbsa_code"].isin(top.loc[top.has_ct, "cbsa_code"]), "Connecticut or Puerto Rico metro (D2)")
units = att.filter(units, units["lat"].notna(), "no 2020 Gazetteer internal point")
att.summary()
att.write_dropped(str(OUT / "tract_vintage_dropped.csv"), sort_by=["tract_geoid"])
top = top[~top.has_ct].drop(columns="has_ct")

# == PHASE 3: JOBS PER TRACT (2020 tract geography) ===========================
# D3: per state, early = first available year (2002 where it exists), mid = 2010,
# late = latest available (2023 where it exists); fallbacks logged.
# A state-year counts as available only if its total is at least half the state's latest total
# (Massachusetts 2002 and 2010 files hold 7 and 17 jobs).
tot = wac.groupby(["state_abbr", "year"])["jobs"].sum().unstack()
ok = tot.ge(0.5 * tot.max(axis=1), axis=0) & tot.notna()
bad = (tot.notna() & ~ok).stack()
log.info("implausible_state_years", cells=[f"{s}_{y}" for (s, y), v in bad.items() if v])
role_year = {}
for st, r in ok.iterrows():
    yrs = sorted(int(y) for y in r.index[r])
    role_year[st] = {"early": yrs[0], "mid": min(y for y in yrs if y >= 2010), "late": yrs[-1]}
log.info("role_years_nonstandard", **{s: v for s, v in role_year.items()
                                       if v != {"early": 2002, "mid": 2010, "late": 2023}})
wac["tract_geoid"] = wac["block_geoid"].str[:11]
parts = []
for role in ["early", "mid", "late"]:
    keep = wac["year"] == wac["state_abbr"].map({s: y[role] for s, y in role_year.items()})
    t = wac[keep].groupby("tract_geoid")["jobs"].sum().rename(f"jobs_{role}")
    parts.append(t)
    log.info("jobs_role", role=role, jobs=int(t.sum()), tracts=int(t.size))
jobs = pd.concat(parts, axis=1).fillna(0).reset_index()

# job locations: every 2020 tract in the sample metros' counties (including tracts with no housing)
gaz["county_fips"] = gaz["tract_geoid"].str[:5]
loc = checked_merge(log, gaz, cbsa[["county_fips", "cbsa_code"]], on="county_fips", how="inner",
                    validate="m:1", name="gazetteer_to_cbsa")
loc = loc[loc["cbsa_code"].isin(top["cbsa_code"])]
loc = checked_merge(log, loc, jobs, on="tract_geoid", how="left", validate="1:1", name="tracts_to_jobs")
jcols = ["jobs_early", "jobs_mid", "jobs_late"]
loc[jcols] = loc[jcols].fillna(0)
share_jobs = loc["jobs_mid"].sum() / jobs["jobs_mid"].sum()
log.info("sample_share_of_us_jobs", role="mid", share=round(float(share_jobs), 4))
check(0.4 < share_jobs < 0.8, f"sample metros hold {share_jobs:.2f} of US jobs (expected roughly half)")

# metro job year (D3): the latest early-year among the metro's states
loc["state_abbr"] = loc["tract_geoid"].str[:2].map(
    dict(zip(gaz["tract_geoid"].str[:2], gaz["state_abbr"].str.lower(), strict=True)))
yr = loc.groupby("cbsa_code")["state_abbr"].agg(lambda s: sorted(set(s)))
top["states"] = top["cbsa_code"].map(lambda c: ",".join(yr[c]))
top["early_year"] = top["cbsa_code"].map(lambda c: max(role_year[s]["early"] for s in yr[c]))
top["late_year"] = top["cbsa_code"].map(lambda c: min(role_year[s]["late"] for s in yr[c]))
top["mid_year"] = top["cbsa_code"].map(lambda c: max(role_year[s]["mid"] for s in yr[c]))
top["early_year_mixed"] = top["cbsa_code"].map(lambda c: len({role_year[s]["early"] for s in yr[c]}) > 1)
top["mid_year_mixed"] = top["cbsa_code"].map(lambda c: len({role_year[s]["mid"] for s in yr[c]}) > 1)

# == PHASE 4: VARIABLE CONSTRUCTION: JOB ACCESS AND JOB CENTER ================
rows = []
for code, g in loc.groupby("cbsa_code"):
    h = units[units["cbsa_code"] == code]
    J = g[jcols].to_numpy()
    # D5: job center = job-location tract with the most mid-year jobs within 3 km
    dj = haversine_km(g["lat"].to_numpy(), g["lon"].to_numpy(), g["lat"].to_numpy(), g["lon"].to_numpy())
    center = int(np.argmax((dj <= CENTER_RADIUS_KM) @ J[:, 1]))
    clat, clon = g["lat"].iloc[center], g["lon"].iloc[center]
    d = haversine_km(h["lat"].to_numpy(), h["lon"].to_numpy(), g["lat"].to_numpy(), g["lon"].to_numpy())
    out = pd.DataFrame({"tract_geoid": h["tract_geoid"].to_numpy()})
    for r in RADII_KM:  # D4: share of metro jobs within r km
        within = (d <= r) @ J / J.sum(axis=0)
        for k, role in enumerate(["early", "mid", "late"]):
            out[f"access{r}_{role}"] = within[:, k]
    # D6: access to job growth = share of the metro's gross tract-level job gains (early -> late,
    # tracts that gained only) within 10 km; net change is unstable where metros barely grew
    gain = np.clip(J[:, 2] - J[:, 0], 0, None)
    out["access10_growth"] = ((d <= 10) @ gain) / gain.sum()
    out["dist_center_km"] = haversine_km(h["lat"].to_numpy(), h["lon"].to_numpy(),
                                          np.array([clat]), np.array([clon]))[:, 0]
    rows.append(out)
    top.loc[top.cbsa_code == code, ["center_tract", "center_lat", "center_lon"]] = \
        [g["tract_geoid"].iloc[center], clat, clon]
acc = pd.concat(rows, ignore_index=True)

tracts = checked_merge(log, units, acc, on="tract_geoid", how="inner", validate="1:1", name="units_to_access")
tracts = checked_merge(log, tracts, loc[["tract_geoid"] + jcols], on="tract_geoid", how="left",
                       validate="1:1", name="units_to_own_jobs")
check(tracts[jcols].notna().all().all(), "sample tract without job record (should be zero-filled)")
for c in [c for c in tracts.columns if c.startswith("access") and c != "access10_growth"]:
    summarize_var(log, tracts, c, lower=0, upper=1)
summarize_var(log, tracts, "access10_growth", lower=0, upper=1)

# D7: within-metro percentile of job access among all housing units (unit-weighted, 0-100);
# 50 means the tract is as close to jobs as the metro's median home (utils/spatial.py).
for c in ["access10_early", "access10_mid", "access10_late", "access5_mid", "access20_mid",
          "access10_growth"]:
    tracts[f"{c}_pctile"] = pd.concat([unit_pctile(g, c) for _, g in tracts.groupby("cbsa_code")])
    summarize_var(log, tracts, f"{c}_pctile", lower=0, upper=100)
tracts["dist_center_pctile"] = 100 - pd.concat(
    [unit_pctile(g, "dist_center_km") for _, g in tracts.groupby("cbsa_code")])  # high = central
summarize_var(log, tracts, "dist_center_pctile", lower=0, upper=100)
summarize_var(log, tracts, "dist_center_km", lower=0, upper=400)  # Riverside-San Bernardino spans ~275 km

# == PHASE 5: RESHAPE AND WRITE ==============================================
base = ["tract_geoid", "cbsa_code", "cbsa_title", "lat", "lon", "land_area_m2", "units_total",
        "dist_center_km", "dist_center_pctile"] + jcols + [c for c in tracts.columns if c.startswith("access")]
write_table(log, tracts[base], str(OUT / "tracts.csv"), sort_by=["tract_geoid"])

tv = tracts.melt(id_vars=["tract_geoid", "cbsa_code"], value_vars=[f"units_{v}" for v in DECADES],
                 var_name="vintage", value_name="units")
tv["vintage"] = tv["vintage"].str.removeprefix("units_")
check(len(tv) == len(tracts) * len(DECADES), "reshape lost rows")
check(tv["units"].sum() == tracts["units_total"].sum(), "units do not add up after reshape")
write_table(log, tv, str(OUT / "tract_vintage.csv"), sort_by=["tract_geoid", "vintage"])

scols = [c for c in tracts.columns if c.startswith(("units_own_", "units_rent_"))
         and c.endswith(("_sf", "_u2_4", "_u5_19", "_u20_49", "_u50plus", "_mobile"))]
ts = tracts.melt(id_vars=["tract_geoid", "cbsa_code"], value_vars=scols, var_name="cell", value_name="units")
cell = ts["cell"].str.extract(r"units_(own|rent)_(\d{4}plus|\d{4}_\d{4}|1939_earlier)_(.+)")
check(cell.notna().all().all(), "structure cell names did not parse")
ts[["tenure", "vintage20", "structure"]] = cell
write_table(log, ts.drop(columns="cell"), str(OUT / "tract_structure.csv"),
            sort_by=["tract_geoid", "tenure", "vintage20", "structure"])
write_table(log, top, str(OUT / "metros.csv"), sort_by=["size_rank"])
log.info("end", n_tracts=len(tracts), n_metros=tracts["cbsa_code"].nunique())
