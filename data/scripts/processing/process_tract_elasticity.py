"""
process_tract_elasticity.py
Stage:      processing (C1-C4)
Purpose:    Put Baum-Snow & Han's 2000-tract supply elasticities (and the tract traits they are built
            from) on 2020 tracts of the sample, and add within-metro percentiles.
Reads:      data/clean/bsh/tract_elasticity_2000.csv; data/clean/tract_xwalk/tract00_tract10.csv,
            tract10_tract20.csv; data/processed/tract_vintage/tracts.csv
Writes:     data/processed/tract_elasticity/tract_elasticity.csv, tract_elasticity_dropped.csv,
            data/logs/process_tract_elasticity.log
Unit:       2020 census tract (sample tracts)
Decisions:  ANALYSIS_PLAN.md D7 (percentiles), D12 (crosswalk weights), D13 (coverage threshold)
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
from spatial import unit_pctile  # noqa: E402

VARS = ["elast_units", "elast_newunits", "elast_floorspace", "elast_land_dev", "elast_units_fmm",
        "bsh_frac_developed_2011", "bsh_frac_flat", "bsh_frac_to_edge"]
MIN_COVERAGE = 0.5  # ANALYSIS_PLAN.md D13
OUT = Path("data/processed/tract_elasticity")
log = get_logger("process_tract_elasticity")
root = project_root()

# == PHASE 1: LOAD ===========================================================
bsh = pd.read_csv(root / "data/clean/bsh/tract_elasticity_2000.csv", dtype={"tract2000": str})
x0010 = pd.read_csv(root / "data/clean/tract_xwalk/tract00_tract10.csv", dtype={"tract2000": str, "tract2010": str})
x1020 = pd.read_csv(root / "data/clean/tract_xwalk/tract10_tract20.csv", dtype={"tract2010": str, "tract2020": str})
tracts = pd.read_csv(root / "data/processed/tract_vintage/tracts.csv", dtype={"tract_geoid": str, "cbsa_code": str})
for n, d in [("bsh", bsh), ("x0010", x0010), ("x1020", x1020), ("tracts", tracts)]:
    log_shape(log, d, n)

# == PHASE 2: ONE ROW PER 2000 TRACT =========================================
# a tract in two BSH regions appears twice with weight 1/2: weighted mean across regions
att0 = AttritionTracker(log, bsh, "BSH tract x region rows")
bsh = att0.filter(bsh, bsh["elast_units"].notna(), "no elasticity in source (clean_bsh discrepancies.csv)")
att0.summary()
w = bsh["bsh_weight"]
t00 = (bsh[VARS].mul(w, axis=0).groupby(bsh["tract2000"]).sum()
       .div(w.groupby(bsh["tract2000"]).sum(), axis=0).reset_index())
check(t00["tract2000"].is_unique, "2000 tracts not unique after collapsing regions")
log.info("tracts2000_with_elasticity", n=len(t00))


def carry(src: pd.DataFrame, key_src: str, xw: pd.DataFrame, key_dst: str, wcol: str) -> pd.DataFrame:
    """Weighted mean of VARS over the source parts of each destination tract; coverage = weight share with data."""
    m = checked_merge(log, xw[[key_src, key_dst, wcol]], src, on=key_src, how="left", validate="m:1",
                      name=f"{key_src}_to_{key_dst}")
    m["has"] = m["elast_units"].notna()
    wv = m[wcol].where(m["has"], 0.0)
    num = m[VARS].fillna(0).mul(wv, axis=0).groupby(m[key_dst]).sum()
    den = wv.groupby(m[key_dst]).sum()
    tot = m[wcol].groupby(m[key_dst]).sum()
    out = num.div(den.replace(0, np.nan), axis=0)
    out["coverage"] = (den / tot.replace(0, np.nan)).fillna(0)
    return out.reset_index()


# == PHASE 3: 2000 -> 2010 (housing-unit weights, D12) ========================
# 2010 tracts with no housing units fall back to land-area weights
x0010["w"] = np.where(x0010.groupby("tract2010")["hu10_part"].transform("sum") > 0,
                      x0010["hu10_part"], x0010["land_part_m2"])
t10 = carry(t00, "tract2000", x0010, "tract2010", "w")
t10 = t10[t10["coverage"] > 0].rename(columns={"coverage": "coverage10"})
log.info("tracts2010_with_elasticity", n=len(t10))

# == PHASE 4: 2010 -> 2020 (land-area weights, D12) ==========================
x1020["w"] = x1020["land_part_m2"].where(x1020.groupby("tract2020")["land_part_m2"].transform("sum") > 0, 1.0)
t20 = carry(t10.drop(columns="coverage10"), "tract2010", x1020, "tract2020", "w").rename(columns={"tract2020": "tract_geoid"})

# == PHASE 5: SAMPLE, COVERAGE, PERCENTILES ==================================
df = checked_merge(log, tracts[["tract_geoid", "cbsa_code", "units_total"]], t20, on="tract_geoid", how="left",
                   validate="1:1", name="sample_to_elasticity")
df["coverage"] = df["coverage"].fillna(0)
log.info("coverage", share_tracts_full=round(float((df["coverage"] > 0.99).mean()), 4),
         share_units_ge_threshold=round(float(df.loc[df["coverage"] >= MIN_COVERAGE, "units_total"].sum() / df["units_total"].sum()), 4))
att = AttritionTracker(log, df, "sample tracts")
df = att.filter(df, df["coverage"] >= MIN_COVERAGE, f"less than {MIN_COVERAGE:.0%} of the tract covered by BSH tracts (D13)")
att.summary()
att.write_dropped(str(OUT / "tract_elasticity_dropped.csv"), sort_by=["tract_geoid"])
for c in VARS:
    summarize_var(log, df, c)
# weighted means cannot leave the source range; ~20% of source predictions are negative (linear spec)
lo, hi = bsh["elast_units"].min(), bsh["elast_units"].max()
check(df["elast_units"].between(lo - 1e-9, hi + 1e-9).all(), f"elasticity outside the source range [{lo}, {hi}]")
log.info("negative_elasticity", share_tracts=round(float((df["elast_units"] < 0).mean()), 4))
# D7: within-metro, unit-weighted percentile of the unit elasticity (high = elastic)
df["elast_units_pctile"] = pd.concat([unit_pctile(g, "elast_units") for _, g in df.groupby("cbsa_code")])
summarize_var(log, df, "elast_units_pctile", lower=0, upper=100)

write_table(log, df.drop(columns=["cbsa_code", "units_total"]), str(OUT / "tract_elasticity.csv"), sort_by=["tract_geoid"])
log.info("end", tracts=len(df), metros=int(df["cbsa_code"].nunique()))
