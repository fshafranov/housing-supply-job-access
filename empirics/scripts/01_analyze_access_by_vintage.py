"""
01_analyze_access_by_vintage.py
Stage:      analysis (D1-D4)
Purpose:    How close to jobs is housing of each construction decade? Estimand: the
            unit-weighted mean within-metro percentile of job access (share of metro jobs within
            10 km, 2010 job geography) of homes built in each decade, relative to pre-1940 homes.
Reproduces: n/a: original analysis
Specs:      s1 pooled OLS on decade dummies -> s2 + metro FE -> s3/s4 5 km and 20 km radius
            -> s5 distance to job center -> s6 2002 and s7 2023 job geography
SEs:        clustered by metro (ANALYSIS_PLAN.md D8)
Reads:      data/processed/tract_vintage/tracts.csv, tract_vintage.csv, metros.csv
Writes:     empirics/results/analyze_access_by_vintage.csv (regressions),
            empirics/results/analyze_access_by_vintage_means.csv (metro x decade means),
            empirics/results/analyze_access_by_vintage_pooled.csv (decade means over metros),
            empirics/results/analyze_access_by_vintage_contemporaneous.csv,
            empirics/results/warnings/analyze_access_by_vintage.md, logs/analyze_access_by_vintage.log
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import (  # noqa: E402
    DECADES,
    DTYPES,
    MAIN_ACCESS,
    METROS,
    N_METROS,
    N_TRACTS,
    TRACT_VINTAGE,
    TRACTS,
    VCOV,
    script_name,
)
from pipeline import (  # noqa: E402
    check,
    check_sample_consistency,
    get_logger,
    project_root,
    tidy_model,
    write_table,
)

EXERCISE = script_name(__file__)
OUTCOMES = {"s1_pooled": MAIN_ACCESS, "s2_metro_fe": MAIN_ACCESS, "s3_radius5": "access5_mid_pctile",
            "s4_radius20": "access20_mid_pctile", "s5_center": "dist_center_pctile",
            "s6_jobs_early": "access10_early_pctile", "s7_jobs_late": "access10_late_pctile"}

log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
metros = pd.read_csv(root / METROS, dtype=DTYPES)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(tr) == N_TRACTS and tr["tract_geoid"].is_unique, f"tracts: expected {N_TRACTS} unique, got {len(tr)}")
check(len(tv) == N_TRACTS * len(DECADES), "tract_vintage is not tracts x decades")
check(tr["cbsa_code"].nunique() == N_METROS, "metro count changed")
missing = [v for v in set(OUTCOMES.values()) if v not in tr.columns]
check(not missing, f"required variables missing: {missing}")
df = tv.merge(tr[["tract_geoid", "cbsa_title", "dist_center_km"] + list(set(OUTCOMES.values()))],
              on="tract_geoid", how="inner", validate="m:1")
check(len(df) == len(tv), "merge lost rows")
sample = df[df["units"] > 0].copy()  # zero-unit cells carry no weight
sample["decade"] = pd.Categorical(sample["vintage"], categories=DECADES)
log.info("estimation_sample", rows=len(sample), units=int(sample["units"].sum()))

# == DESCRIPTIVES: metro x decade means ======================================
def wm(g, col):
    return (g[col] * g["units"]).sum() / g["units"].sum()


means = (sample.groupby(["cbsa_code", "cbsa_title", "vintage"], observed=True)
         .apply(lambda g: pd.Series({"units": g["units"].sum(), "access10_pctile": wm(g, MAIN_ACCESS),
                                     "center_pctile": wm(g, "dist_center_pctile"),
                                     "dist_center_km": wm(g, "dist_center_km")}), include_groups=False)
         .reset_index())
check(means.groupby("cbsa_code").size().eq(len(DECADES)).all(), "a metro lacks a decade")
write_table(log, means, f"empirics/results/{EXERCISE}_means.csv", sort_by=["cbsa_code", "vintage"])

pooled = (means.groupby("vintage")
          .agg(metros=("cbsa_code", "nunique"), access10_pctile_mean=("access10_pctile", "mean"),
               access10_pctile_p10=("access10_pctile", lambda s: s.quantile(0.1)),
               access10_pctile_p90=("access10_pctile", lambda s: s.quantile(0.9)),
               center_pctile_mean=("center_pctile", "mean"), dist_center_km_median=("dist_center_km", "median"),
               units=("units", "sum"))
          .reindex(DECADES).reset_index())
log.info("pooled", table="\n" + pooled.round(1).to_string(index=False))
write_table(log, pooled, f"empirics/results/{EXERCISE}_pooled.csv")

# == CONTEMPORANEOUS JOB GEOGRAPHY ===========================================
# Each recent decade against the jobs at its start, relative to the stock built before it
# (percentiles are within today's whole stock, so the earlier stock is the benchmark).
ctab = []
for vint, role, before in [("2000_2009", "early", DECADES[:7]), ("2010_2019", "mid", DECADES[:8]),
                           ("2020plus", "late", DECADES[:9])]:
    col = f"access10_{role}_pctile"
    for code, g in sample.groupby("cbsa_code"):
        new, old = g[g["vintage"] == vint], g[g["vintage"].isin(before)]
        ctab.append({"cbsa_code": code, "vintage": vint, "job_role": role,
                     "new_pctile": wm(new, col), "older_stock_pctile": wm(old, col)})
ctab = pd.DataFrame(ctab).merge(metros[["cbsa_code", "early_year", "mid_year", "late_year", "early_year_mixed"]],
                                on="cbsa_code", validate="m:1")
ctab["gap"] = ctab["new_pctile"] - ctab["older_stock_pctile"]
log.info("contemporaneous", table="\n" + ctab.groupby("vintage")[["new_pctile", "older_stock_pctile", "gap"]]
         .mean().round(1).to_string())
write_table(log, ctab, f"empirics/results/{EXERCISE}_contemporaneous.csv", sort_by=["cbsa_code", "vintage"])

# == REGRESSIONS: decade gradient (pre-1940 = reference) =====================
results, caught = [], []


def fit(fml, spec):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m = pf.feols(fml, data=sample, vcov=VCOV, weights="units")
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(m._N))
    results.append(tidy_model(m, spec, fe="cbsa_code" if "|" in fml else ""))


rhs = "C(decade, contr.treatment(base='1939_earlier'))"
for spec, y in OUTCOMES.items():
    fit(f"{y} ~ {rhs}" + ("" if spec == "s1_pooled" else " | cbsa_code"), spec)

res = pd.concat(results, ignore_index=True)
res["term"] = res["term"].str.extract(r"\[T\.(.+)\]", expand=False).fillna(res["term"])
check_sample_consistency(log, res, EXERCISE, warnings_text=caught)
write_table(log, res, f"empirics/results/{EXERCISE}.csv")
log.info("end")
