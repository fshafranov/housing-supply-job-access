"""
06_explore_job_growth_location.py
Stage:      analysis (descriptive)
Purpose:    Did new jobs (2002-2023) stay in the existing centers, or did they move out with new homes?
            Shares of each metro's jobs, job change and homes by distance ring from the job center,
            pooled over metros (each metro weighted equally), plus the gap between where jobs and
            homes were added. Metros whose jobs grew less than 10% are excluded (D15).
Reproduces: n/a: original analysis
Specs:      none (shares)
Reads:      data/processed/tract_vintage/tracts.csv, tract_vintage.csv, metros.csv
Writes:     empirics/results/explore_job_growth_location.csv (pooled ring shares),
            empirics/results/explore_job_growth_location_metros.csv, logs/explore_job_growth_location.log
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import DECADES, DTYPES, METROS, N_TRACTS, TRACT_VINTAGE, TRACTS, script_name  # noqa: E402
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

EXERCISE = script_name(__file__)
RINGS = [0, 5, 10, 20, 30, 50, np.inf]
MIN_GROWTH = 0.10  # ANALYSIS_PLAN.md D15
LABELS = ["0-5 km", "5-10 km", "10-20 km", "20-30 km", "30-50 km", "50+ km"]
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
metros = pd.read_csv(root / METROS, dtype=DTYPES)

# == INPUT ASSERTIONS =========================================================
check(len(tr) == N_TRACTS and tr["tract_geoid"].is_unique, "tracts changed")
check(len(tv) == N_TRACTS * len(DECADES), "tract_vintage is not tracts x decades")
keep = metros.loc[~metros["early_year_mixed"], "cbsa_code"]  # D3: comparable 2002 (or near) job counts
t = tr[tr["cbsa_code"].isin(keep)].copy()
log.info("sample", metros=int(t["cbsa_code"].nunique()), tracts=len(t),
         dropped=metros.loc[metros["early_year_mixed"], "cbsa_title"].tolist())

piv = tv.pivot(index="tract_geoid", columns="vintage", values="units")
t = t.merge(pd.DataFrame({"homes_2000plus": piv[["2000_2009", "2010_2019", "2020plus"]].sum(axis=1),
                          "homes_2010plus": piv[["2010_2019", "2020plus"]].sum(axis=1),
                          "homes_pre2000": piv[DECADES[:7]].sum(axis=1)}).reset_index(),
            on="tract_geoid", how="left", validate="1:1")
# ANALYSIS_PLAN.md D15: ring shares of net job change are unstable where a metro barely grew
# (Rochester, Cleveland: shares above 100%); keep metros whose jobs grew at least 10%
growth = t.groupby("cbsa_code")[["jobs_early", "jobs_late"]].sum()
growth = growth["jobs_late"] / growth["jobs_early"] - 1
slow = growth[growth < MIN_GROWTH].index
log.info("slow_metros_dropped", n=len(slow), titles=metros.set_index("cbsa_code").loc[slow, "cbsa_title"].tolist())
t = t[~t["cbsa_code"].isin(slow)].copy()
t["job_change"] = t["jobs_late"] - t["jobs_early"]
t["job_gain"] = t["job_change"].clip(lower=0)
t["ring"] = pd.cut(t["dist_center_km"], RINGS, labels=LABELS, right=False)
check(t["ring"].notna().all(), "tract without ring")

# == RING SHARES PER METRO, THEN MEAN OVER METROS =============================
COLS = ["jobs_early", "jobs_late", "job_change", "job_gain", "homes_pre2000", "homes_2000plus", "homes_2010plus"]
g = t.groupby(["cbsa_code", "ring"], observed=False)[COLS].sum()
shares = g / g.groupby("cbsa_code").transform("sum")
shares = shares.reset_index()
write_table(log, shares, f"empirics/results/{EXERCISE}_metros.csv", sort_by=["cbsa_code", "ring"])
pooled = shares.groupby("ring", observed=False)[COLS].mean().reindex(LABELS).reset_index()
pooled.columns = ["ring"] + [f"share_{c}" for c in COLS]
med = shares.groupby("ring", observed=False)[["job_change", "homes_2010plus"]].median().reindex(LABELS)
pooled["median_share_job_change"] = med["job_change"].to_numpy()
pooled["median_share_homes_2010plus"] = med["homes_2010plus"].to_numpy()
log.info("pooled", table="\n" + pooled.round(3).to_string(index=False))

# metro-level summary: share of net job growth and of new homes within 10 km of the center
w10 = shares[shares["ring"].isin(LABELS[:2])].groupby("cbsa_code")[COLS].sum()
summ = pd.DataFrame({"jobs_within10_2002": w10["jobs_early"], "jobs_within10_2023": w10["jobs_late"],
                     "net_job_growth_within10": w10["job_change"], "homes_2010plus_within10": w10["homes_2010plus"]})
summ = summ.merge(metros.set_index("cbsa_code")[["cbsa_title"]], left_index=True, right_index=True).reset_index()
log.info("within10", table="\n" + summ.describe().round(3).to_string())
pooled.attrs = {}
out = pooled.copy()
out["metros"] = int(t["cbsa_code"].nunique())
write_table(log, out, f"empirics/results/{EXERCISE}.csv")
write_table(log, summ, f"empirics/results/{EXERCISE}_within10.csv", sort_by=["cbsa_code"])
log.info("end")
