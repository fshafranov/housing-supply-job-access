"""
02_analyze_jobs_housing_growth.py
Stage:      analysis (D1-D4)
Purpose:    Do homes built since 2000 sit closer to where jobs were added (2002 -> 2023) than the
            older stock does? Estimand: per metro, unit-weighted mean percentile of access to job
            gains (D6, D7) for homes built 2000+, minus the same for homes built before 2000;
            then whether the gap is larger where metros added more housing.
Reproduces: n/a: original analysis
Specs:      s1 gap ~ 1 (mean over metros) -> s2 gap ~ housing growth share -> s3 + log metro size
SEs:        heteroskedasticity-robust (one row per metro)
Reads:      data/processed/tract_vintage/tracts.csv, tract_vintage.csv, metros.csv
Writes:     empirics/results/analyze_jobs_housing_growth.csv, ..._metros.csv,
            empirics/results/warnings/analyze_jobs_housing_growth.md, logs/analyze_jobs_housing_growth.log
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import (  # noqa: E402
    DECADES,
    DTYPES,
    METROS,
    N_METROS,
    N_TRACTS,
    TRACT_VINTAGE,
    TRACTS,
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
NEW = ["2000_2009", "2010_2019", "2020plus"]
EXPECTED_N = 44  # metros without mixed early job years (D3)
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
metros = pd.read_csv(root / METROS, dtype=DTYPES)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(tr) == N_TRACTS, f"expected {N_TRACTS} tracts, got {len(tr)}")
check(len(metros) == N_METROS, "metro count changed")
check(set(tv["vintage"]) == set(DECADES), "unexpected vintages")
check(tr["tract_geoid"].is_unique, "tracts: tract_geoid not unique")
check(len(tv) == N_TRACTS * len(DECADES), f"tract_vintage: expected {N_TRACTS * len(DECADES)} rows, got {len(tv)}")
check(not tv.duplicated(["tract_geoid", "vintage"]).any(), "tract x vintage not unique")

# == METRO-LEVEL GAPS ========================================================
df = tv.merge(tr[["tract_geoid", "access10_growth_pctile", "access10_early_pctile"]], on="tract_geoid",
              how="inner", validate="m:1")
df["new"] = df["vintage"].isin(NEW)
rows = []
for code, g in df.groupby("cbsa_code"):
    n, o = g[g["new"]], g[~g["new"]]
    def wm(x, c):
        return (x[c] * x["units"]).sum() / x["units"].sum()
    rows.append({"cbsa_code": code, "new_units": n["units"].sum(), "old_units": o["units"].sum(),
                 "new_growth_pctile": wm(n, "access10_growth_pctile"),
                 "old_growth_pctile": wm(o, "access10_growth_pctile"),
                 "new_level_pctile": wm(n, "access10_early_pctile"),
                 "old_level_pctile": wm(o, "access10_early_pctile")})
m = pd.DataFrame(rows).merge(metros[["cbsa_code", "cbsa_title", "size_rank", "early_year", "late_year",
                                     "early_year_mixed"]], on="cbsa_code", validate="1:1")
m["growth_gap"] = m["new_growth_pctile"] - m["old_growth_pctile"]
m["level_gap"] = m["new_level_pctile"] - m["old_level_pctile"]
m["new_share"] = m["new_units"] / (m["new_units"] + m["old_units"])
m["log_units"] = np.log(m["new_units"] + m["old_units"])
log.info("gaps", table="\n" + m.sort_values("growth_gap")[["cbsa_title", "new_share", "level_gap", "growth_gap"]]
         .round(2).to_string(index=False))
write_table(log, m, f"empirics/results/{EXERCISE}_metros.csv", sort_by=["size_rank"])

# == REGRESSIONS (metro level) ===============================================
clean = m[~m["early_year_mixed"]].copy()  # D3: mixed early years distort job gains
check(len(clean) == EXPECTED_N and clean["cbsa_code"].is_unique, f"expected N={EXPECTED_N} unique metros, got {len(clean)}")
log.info("sample", metros=len(clean), dropped=m.loc[m["early_year_mixed"], "cbsa_title"].tolist())
results, caught = [], []


def fit(fml, spec, data):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = pf.feols(fml, data=data, vcov="hetero")
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(r._N))
    results.append(tidy_model(r, spec))


fit("growth_gap ~ 1", "s1_mean_growth_gap", clean)
fit("level_gap ~ 1", "s1b_mean_level_gap", clean)
fit("growth_gap ~ new_share", "s2_growth_gap_on_new_share", clean)
fit("growth_gap ~ new_share + log_units", "s3_plus_size", clean)
res = pd.concat(results, ignore_index=True)
check_sample_consistency(log, res, EXERCISE, warnings_text=caught)
write_table(log, res, f"empirics/results/{EXERCISE}.csv")
log.info("end")
