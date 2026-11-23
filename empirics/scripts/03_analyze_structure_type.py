"""
03_analyze_structure_type.py
Stage:      analysis (D1-D4)
Purpose:    Starter-home proxy: is owner-occupied single-family and mobile-home housing built
            farther from jobs than rental apartments of the same 20-year vintage? Estimand:
            unit-weighted mean percentile of job access (2010 jobs, 10 km) by tenure x structure
            x vintage; then the within-tract-free regression gap with metro FE.
Reproduces: n/a: original analysis
Specs:      s1 metro FE, vintage x type cells (no tract FE) -> s2 + vintage-specific metro FE
SEs:        clustered by metro (ANALYSIS_PLAN.md D8)
Reads:      data/processed/tract_vintage/tracts.csv, tract_structure.csv
Writes:     empirics/results/analyze_structure_type.csv, ..._means.csv,
            empirics/results/warnings/analyze_structure_type.md, logs/analyze_structure_type.log
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import (  # noqa: E402
    DTYPES,
    MAIN_ACCESS,
    N_TRACTS,
    TRACT_STRUCTURE,
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
V20 = ["1939_earlier", "1940_1959", "1960_1979", "1980_1999", "2000_2019", "2020plus"]
TYPES = {("own", "sf"): "owner single-family", ("own", "mobile"): "owner mobile home",
         ("rent", "sf"): "renter single-family", ("rent", "u2_4"): "renter 2-4 units",
         ("rent", "u5_19"): "renter 5-19 units", ("rent", "u20_49"): "renter 20+ units",
         ("rent", "u50plus"): "renter 20+ units"}
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
ts = pd.read_csv(root / TRACT_STRUCTURE, dtype=DTYPES)

# == INPUT ASSERTIONS (D2) ==================================================
check(len(tr) == N_TRACTS, "tract count changed")
check(set(ts["vintage20"]) == set(V20), f"unexpected 20-year bins {set(ts['vintage20'])}")
check(tr["tract_geoid"].is_unique, "tracts: tract_geoid not unique")
check(len(ts) == N_TRACTS * 72, f"tract_structure: expected {N_TRACTS * 72} rows (72 cells), got {len(ts)}")
check(not ts.duplicated(["tract_geoid", "tenure", "vintage20", "structure"]).any(), "structure cell key not unique")
ts["type"] = [TYPES.get((t, s)) for t, s in zip(ts["tenure"], ts["structure"], strict=True)]
log.info("types_not_used", units=int(ts.loc[ts["type"].isna(), "units"].sum()),
         share=round(float(ts.loc[ts["type"].isna(), "units"].sum() / ts["units"].sum()), 3))
df = ts[ts["type"].notna() & (ts["units"] > 0)].merge(tr[["tract_geoid", MAIN_ACCESS]], on="tract_geoid",
                                                      how="inner", validate="m:1")
df = df.groupby(["tract_geoid", "cbsa_code", "vintage20", "type", MAIN_ACCESS], as_index=False)["units"].sum()
check(len(df) == 555576, f"expected 555576 tract x vintage x type cells with units, got {len(df)}")

# == MEANS ==================================================================
means = (df.groupby(["vintage20", "type"])
         .apply(lambda g: pd.Series({"units": g["units"].sum(),
                                     "access10_pctile": (g[MAIN_ACCESS] * g["units"]).sum() / g["units"].sum()}),
                include_groups=False).reset_index())
log.info("means", table="\n" + means.pivot(index="vintage20", columns="type", values="access10_pctile")
         .reindex(V20).round(1).to_string())
write_table(log, means, f"empirics/results/{EXERCISE}_means.csv", sort_by=["vintage20", "type"])

# == REGRESSIONS ============================================================
results, caught = [], []
df["vt"] = df["vintage20"] + ":" + df["type"]
df["cbsa_v"] = df["cbsa_code"] + ":" + df["vintage20"]


def fit(fml, spec):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = pf.feols(fml, data=df, vcov=VCOV, weights="units")
    caught.extend(f"{spec}: {x.message}" for x in w)
    log.info("spec", spec=spec, formula=fml, nobs=int(r._N))
    results.append(tidy_model(r, spec, fe=fml.split("|")[-1].strip()))


ref = "C(type, contr.treatment(base='renter 20+ units'))"
fit(f"{MAIN_ACCESS} ~ {ref} | cbsa_code", "s1_type_metro_fe")
fit(f"{MAIN_ACCESS} ~ {ref} | cbsa_v", "s2_type_metro_by_vintage_fe")
for v in ["1960_1979", "2000_2019"]:
    sub = df[df["vintage20"] == v]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = pf.feols(f"{MAIN_ACCESS} ~ {ref} | cbsa_code", data=sub, vcov=VCOV, weights="units")
    caught.extend(f"s3_{v}: {x.message}" for x in w)
    results.append(tidy_model(r, f"s3_built_{v}", sample=v, fe="cbsa_code"))
res = pd.concat(results, ignore_index=True)
res["term"] = res["term"].str.extract(r"\[T\.(.+)\]", expand=False).fillna(res["term"])
check_sample_consistency(log, res, EXERCISE, warnings_text=caught)
write_table(log, res, f"empirics/results/{EXERCISE}.csv")
log.info("end")
