"""
04_analyze_commute_by_vintage.py
Stage:      analysis (D1-D4)
Purpose:    Same question as 01 with actual commutes instead of potential access: how far do the
            residents of tracts with homes of each construction decade (and each structure type)
            commute? Estimand: unit-weighted mean of the tract's median resident commute (km,
            LODES OD 2023) and its within-metro percentile (high = short), by decade built; plus
            how much of actual commuting the access and centrality measures capture.
Reproduces: n/a: original analysis
Specs:      s1 commute percentile ~ decade | metro -> s2 median km -> s3 share within 10 km
            -> s4 mean km up to 100 km; m1-m3 commute percentile on access and centrality (tract level)
SEs:        clustered by metro (ANALYSIS_PLAN.md D8)
Reads:      data/processed/tract_vintage/tracts.csv, tract_vintage.csv, tract_structure.csv, tract_commute.csv
Writes:     empirics/results/analyze_commute_by_vintage.csv (regressions), ..._pooled.csv,
            ..._structure.csv, warnings/analyze_commute_by_vintage.md, logs/analyze_commute_by_vintage.log
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
    N_TRACTS,
    TRACT_STRUCTURE,
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
COMMUTE = ["commute_median_close_pctile", "commute_median_km", "commute_share_le10km", "commute_mean_km_le100"]
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
cm = pd.read_csv(root / WF / "tract_commute.csv", dtype=DTYPES)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(tr) == N_TRACTS and len(cm) == N_TRACTS, f"expected {N_TRACTS} tracts in tracts and tract_commute")
check(cm["tract_geoid"].is_unique and tr["tract_geoid"].is_unique, "tract key not unique")
check(len(tv) == N_TRACTS * len(DECADES), "tract_vintage is not tracts x decades")
t = tr.merge(cm, on="tract_geoid", how="inner", validate="1:1")
t = t[t["resident_jobs"] > 0]
log.info("tracts_with_resident_jobs", n=len(t), of=N_TRACTS)
df = tv.merge(t[["tract_geoid", "access10_mid_pctile", "dist_center_pctile"] + COMMUTE], on="tract_geoid",
              how="inner", validate="m:1")
sample = df[(df["units"] > 0) & df[COMMUTE].notna().all(axis=1)].copy()
sample["decade"] = pd.Categorical(sample["vintage"], categories=DECADES)
EXPECTED_N = len(sample)
log.info("estimation_sample", rows=EXPECTED_N, units=int(sample["units"].sum()))


def wm(g, c, w="units"):
    return (g[c] * g[w]).sum() / g[w].sum()


# == DESCRIPTIVES ============================================================
metro_dec = (sample.groupby(["cbsa_code", "vintage"])
             .apply(lambda g: pd.Series({c: wm(g, c) for c in COMMUTE + ["access10_mid_pctile"]} | {"units": g["units"].sum()}),
                    include_groups=False).reset_index())
pooled = metro_dec.groupby("vintage")[COMMUTE + ["access10_mid_pctile"]].mean().reindex(DECADES).reset_index()
pooled["metros"] = metro_dec.groupby("vintage")["cbsa_code"].nunique().reindex(DECADES).to_numpy()
log.info("pooled", table="\n" + pooled.round(2).to_string(index=False))
write_table(log, pooled, f"empirics/results/{EXERCISE}_pooled.csv")

ts = pd.read_csv(root / TRACT_STRUCTURE, dtype=DTYPES)
TYPES = {("own", "sf"): "owner single-family", ("own", "mobile"): "owner mobile home",
         ("rent", "u5_19"): "renter 5-19 units", ("rent", "u20_49"): "renter 20+ units",
         ("rent", "u50plus"): "renter 20+ units"}
ts["type"] = [TYPES.get((a, b)) for a, b in zip(ts["tenure"], ts["structure"], strict=True)]
ts = ts[ts["type"].notna() & (ts["units"] > 0)].merge(t[["tract_geoid"] + COMMUTE], on="tract_geoid",
                                                      how="inner", validate="m:1")
struct = (ts.groupby(["vintage20", "type"])
          .apply(lambda g: pd.Series({c: wm(g, c) for c in COMMUTE} | {"units": g["units"].sum()}), include_groups=False)
          .reset_index())
log.info("structure", table="\n" + struct.pivot(index="vintage20", columns="type", values="commute_median_km").round(1).to_string())
write_table(log, struct, f"empirics/results/{EXERCISE}_structure.csv", sort_by=["vintage20", "type"])

# == REGRESSIONS =============================================================
results, caught = [], []


def fit(fml, spec, data, weights, label="main"):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m = pf.feols(fml, data=data, vcov=VCOV, weights=weights)
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(m._N), r2=round(float(m._r2), 3))
    results.append(tidy_model(m, spec, sample=label, fe="cbsa_code"))


check(len(sample) == EXPECTED_N, "sample changed")
rhs = "C(decade, contr.treatment(base='1939_earlier'))"
for spec, y in [("s1_pctile", COMMUTE[0]), ("s2_median_km", COMMUTE[1]), ("s3_share_le10km", COMMUTE[2]),
                ("s4_mean_km_le100", COMMUTE[3])]:
    fit(f"{y} ~ {rhs} | cbsa_code", spec, sample, "units", "tract_x_decade")

# how much of actual commuting do the potential-access and centrality measures capture (tract level)
fit("commute_median_close_pctile ~ access10_mid_pctile | cbsa_code", "m1_on_access", t, "units_total", "tract")
fit("commute_median_close_pctile ~ dist_center_pctile | cbsa_code", "m2_on_center", t, "units_total", "tract")
fit("commute_median_close_pctile ~ access10_mid_pctile + dist_center_pctile | cbsa_code", "m3_on_both", t,
    "units_total", "tract")
corr = t[["access10_mid_pctile", "dist_center_pctile", "commute_median_close_pctile"]].corr().round(3)
log.info("correlations", table="\n" + corr.to_string())

res = pd.concat(results, ignore_index=True)
res["term"] = res["term"].str.extract(r"\[T\.(.+)\]", expand=False).fillna(res["term"])
check_sample_consistency(log, res, EXERCISE, warnings_text=caught)
write_table(log, res, f"empirics/results/{EXERCISE}.csv")
log.info("end")
