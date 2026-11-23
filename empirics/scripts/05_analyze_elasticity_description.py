"""
05_analyze_elasticity_description.py
Stage:      analysis (descriptive)
Purpose:    Descriptive link between housing supply elasticity (Baum-Snow & Han tract predictions) and
            job access: (1) elasticity by within-metro job-access decile; (2) where homes built since
            2010 went, by elasticity quintile; (3) metro level: is the gap between new and older homes
            (scripts 02 and 04) larger where the job-rich core is less elastic than the edge;
            (4) which ingredient (built-up share, flatness, distance to CBD) separates job-rich tracts
            from the edge. Descriptive only: no causal claim (ANALYSIS_PLAN.md D14).
Reproduces: n/a: original analysis
Specs:      e1 elasticity ~ access percentile | metro (tract); e2-e4 metro gaps ~ core-minus-edge elasticity
SEs:        e1 clustered by metro (D8); metro-level regressions heteroskedasticity-robust
Reads:      data/processed/tract_vintage/tracts.csv, tract_vintage.csv, tract_commute.csv;
            data/processed/tract_elasticity/tract_elasticity.csv;
            empirics/results/analyze_jobs_housing_growth_metros.csv
Writes:     empirics/results/analyze_elasticity_description.csv (regressions), ..._by_access.csv,
            ..._new_homes.csv, ..._metros.csv, ..._ingredients.csv, warnings/, logs/
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
    N_METROS,
    N_TRACTS,
    TRACT_VINTAGE,
    TRACTS,
    VCOV,
    WF,
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
ELAST = Path("data/processed/tract_elasticity/tract_elasticity.csv")
EXPECTED_N = 42156          # tracts with elasticity coverage >= 50% (D13)
NEW = ["2010_2019", "2020plus"]  # D14: homes built after the 2011 ingredients are measured
INGR = ["bsh_frac_developed_2011", "bsh_frac_flat", "bsh_frac_to_edge"]
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
el = pd.read_csv(root / ELAST, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
cm = pd.read_csv(root / WF / "tract_commute.csv", dtype=DTYPES)

# == INPUT ASSERTIONS =========================================================
check(len(tr) == N_TRACTS, "tract count changed")
check(len(el) == EXPECTED_N and el["tract_geoid"].is_unique, f"expected N={EXPECTED_N} unique elasticity tracts, got {len(el)}")
check(len(tv) == N_TRACTS * len(DECADES), "tract_vintage is not tracts x decades")
t = (tr.merge(el, on="tract_geoid", how="inner", validate="1:1")
       .merge(cm[["tract_geoid", "commute_median_km", "commute_median_close_pctile"]], on="tract_geoid", how="left", validate="1:1"))
check(t["cbsa_code"].nunique() == N_METROS, "a metro lost all tracts")
new = tv[tv["vintage"].isin(NEW)].groupby("tract_geoid")["units"].sum().rename("units_new")
t = t.merge(new, on="tract_geoid", how="left", validate="1:1")
t["units_old"] = t["units_total"] - t["units_new"]
t["access_decile"] = np.minimum((t["access10_mid_pctile"] // 10).astype(int) + 1, 10)
t["elast_quintile"] = np.minimum((t["elast_units_pctile"] // 20).astype(int) + 1, 5)


def wm(g, c, w="units_total"):
    return (g[c] * g[w]).sum() / g[w].sum()


# == (1) ELASTICITY BY JOB-ACCESS DECILE ======================================
by_access = (t.groupby("access_decile")
             .apply(lambda g: pd.Series({"units": g["units_total"].sum(), "elast_units": wm(g, "elast_units"),
                                         "elast_newunits": wm(g, "elast_newunits"),
                                         "share_negative_elast": wm(g.assign(n=(g["elast_units"] < 0).astype(float)), "n")}
                                        | {c: wm(g, c) for c in INGR}), include_groups=False).reset_index())
log.info("by_access", table="\n" + by_access.round(3).to_string(index=False))
write_table(log, by_access, f"empirics/results/{EXERCISE}_by_access.csv", sort_by=["access_decile"])

# == (2) WHERE HOMES BUILT SINCE 2010 WENT, BY ELASTICITY QUINTILE ============
rows = []
for q, g in t.groupby("elast_quintile"):
    rows.append({"elast_quintile": q, "share_of_all_homes": g["units_total"].sum() / t["units_total"].sum(),
                 "share_of_new_homes": g["units_new"].sum() / t["units_new"].sum(),
                 "elast_units": wm(g, "elast_units"), "access10_pctile": wm(g, "access10_mid_pctile"),
                 "access10_pctile_new_homes": wm(g, "access10_mid_pctile", "units_new"),
                 "commute_median_km_new_homes": wm(g.dropna(subset=["commute_median_km"]), "commute_median_km", "units_new")})
newh = pd.DataFrame(rows)
log.info("new_homes", table="\n" + newh.round(3).to_string(index=False))
write_table(log, newh, f"empirics/results/{EXERCISE}_new_homes.csv", sort_by=["elast_quintile"])

# == (4) INGREDIENTS: NEAR-JOBS VS EDGE TRACTS ================================
t["zone"] = np.select([t["access10_mid_pctile"] >= 80, t["access10_mid_pctile"] < 20], ["near jobs (top 20%)", "far (bottom 20%)"], "middle")
ingr = (t.groupby("zone").apply(lambda g: pd.Series({c: wm(g, c) for c in ["elast_units"] + INGR}), include_groups=False)
        .reset_index())
log.info("ingredients", table="\n" + ingr.round(3).to_string(index=False))
write_table(log, ingr, f"empirics/results/{EXERCISE}_ingredients.csv", sort_by=["zone"])

# == (3) METRO LEVEL ==========================================================
gm = pd.read_csv(root / "empirics/results/analyze_jobs_housing_growth_metros.csv", dtype=DTYPES)
rows = []
for code, g in t.groupby("cbsa_code"):
    near, far = g[g["zone"] == "near jobs (top 20%)"], g[g["zone"] == "far (bottom 20%)"]
    n, o = g.assign(w=g["units_new"]), g.assign(w=g["units_old"])
    rows.append({"cbsa_code": code, "elast_metro": wm(g, "elast_units"), "elast_near_jobs": wm(near, "elast_units"),
                 "elast_far": wm(far, "elast_units"),
                 "new_minus_old_access_pctile": wm(n, "access10_mid_pctile", "w") - wm(o, "access10_mid_pctile", "w"),
                 "new_minus_old_commute_km": wm(n.dropna(subset=["commute_median_km"]), "commute_median_km", "w")
                 - wm(o.dropna(subset=["commute_median_km"]), "commute_median_km", "w"),
                 "new_share": g["units_new"].sum() / g["units_total"].sum()})
m = pd.DataFrame(rows).merge(gm[["cbsa_code", "cbsa_title", "growth_gap", "early_year_mixed"]], on="cbsa_code", validate="1:1")
m["elast_core_minus_edge"] = m["elast_near_jobs"] - m["elast_far"]
check(len(m) == N_METROS, "metro table incomplete")
write_table(log, m, f"empirics/results/{EXERCISE}_metros.csv", sort_by=["cbsa_code"])
log.info("metros", table="\n" + m.sort_values("elast_near_jobs")[["cbsa_title", "elast_near_jobs", "elast_far",
         "new_minus_old_access_pctile", "growth_gap"]].round(2).to_string(index=False))

# == REGRESSIONS ==============================================================
results, caught = [], []


def fit(fml, spec, data, vcov, weights=None, label="main"):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = pf.feols(fml, data=data, vcov=vcov, weights=weights)
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(r._N), r2=round(float(r._r2), 3))
    results.append(tidy_model(r, spec, sample=label, fe="cbsa_code" if "|" in fml else ""))


fit("elast_units ~ access10_mid_pctile | cbsa_code", "e1_elast_on_access", t, VCOV, "units_total", "tract")
fit("elast_units ~ access10_mid_pctile + dist_center_pctile | cbsa_code", "e1b_plus_center", t, VCOV, "units_total", "tract")
mm = m[~m["early_year_mixed"]]
fit("new_minus_old_access_pctile ~ elast_core_minus_edge", "e2_access_gap", m, "hetero", label="metros_48")
fit("new_minus_old_commute_km ~ elast_core_minus_edge", "e3_commute_gap", m, "hetero", label="metros_48")
fit("growth_gap ~ elast_core_minus_edge", "e4_growth_gap", mm, "hetero", label="metros_44")
fit("new_minus_old_access_pctile ~ elast_near_jobs + elast_far", "e5_access_gap_levels", m, "hetero", label="metros_48")
res = pd.concat(results, ignore_index=True)
check_sample_consistency(log, res, EXERCISE, warnings_text=caught)
write_table(log, res, f"empirics/results/{EXERCISE}.csv")
log.info("end")
