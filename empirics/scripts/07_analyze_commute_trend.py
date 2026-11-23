"""
07_analyze_commute_trend.py
Stage:      analysis (descriptive)
Purpose:    Did commutes get longer between 2002 and 2023, and why? Per metro: mean commute of working
            residents (commutes up to 100 km, D11) in both years, and a split of the change into
            (a) within: the same tracts' residents commute farther, (b) between: workers shifted
            toward tracts with longer commutes (where people live), (c) interaction. The between part
            is then split by how much of each tract's housing was built since 2000.
Reproduces: n/a: original analysis
Specs:      shift-share decomposition (exact identity), no regressions
Reads:      data/processed/tract_commute_trend/tract_commute_trend.csv, state_years.csv;
            data/processed/tract_vintage/tracts.csv, tract_vintage.csv, metros.csv
Writes:     empirics/results/analyze_commute_trend.csv (pooled), ..._metros.csv, ..._by_newshare.csv,
            empirics/results/logs/analyze_commute_trend.log
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import DECADES, DTYPES, METROS, N_TRACTS, TRACT_VINTAGE, TRACTS, script_name  # noqa: E402
from pipeline import check, get_logger, project_root, write_table  # noqa: E402

EXERCISE = script_name(__file__)
TREND = Path("data/processed/tract_commute_trend")
log = get_logger(EXERCISE, log_dir="empirics/results/logs")
root = project_root()
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
metros = pd.read_csv(root / METROS, dtype=DTYPES)
ct = pd.read_csv(root / TREND / "tract_commute_trend.csv", dtype=DTYPES)
sy = pd.read_csv(root / TREND / "state_years.csv").set_index("state_abbr")

# == INPUT ASSERTIONS =========================================================
check(len(tr) == N_TRACTS, "tract count changed")
check(not ct.duplicated(["tract_geoid", "role"]).any(), "tract x role not unique")
check(len(tv) == N_TRACTS * len(DECADES), "tract_vintage is not tracts x decades")
# D16: metros whose states all start in the same early year (no mixed years); Phoenix starts 2004
metros["states_list"] = metros["states"].str.split(",")
metros["early_od"] = metros["states_list"].map(lambda ss: sorted({int(sy.loc[s, "early"]) for s in ss}))
metros["late_od"] = metros["states_list"].map(lambda ss: sorted({int(sy.loc[s, "late"]) for s in ss}))
keep = metros[metros["early_od"].map(len).eq(1)]
log.info("sample", metros=len(keep), dropped=metros.loc[~metros.index.isin(keep.index), "cbsa_title"].tolist(),
         nonstandard=keep.loc[keep["early_od"].map(lambda v: v != [2002]) | keep["late_od"].map(lambda v: v != [2023]),
                              "cbsa_title"].tolist())
EXPECTED_N = 44
check(len(keep) == EXPECTED_N, f"expected {EXPECTED_N} metros, got {len(keep)}")

d = ct.merge(tr[["tract_geoid", "cbsa_code"]], on="tract_geoid", how="inner", validate="m:1")
d = d[d["cbsa_code"].isin(keep["cbsa_code"])]
w = d.pivot(index="tract_geoid", columns="role", values=["jobs_le100", "km_sum_le100", "resident_jobs",
                                                       "commute_share_gt100km"]).fillna(0)
w.columns = [f"{a}_{b}" for a, b in w.columns]
w = w.join(tr.set_index("tract_geoid")[["cbsa_code"]], how="left")
for r in ["early", "late"]:
    w[f"c_{r}"] = w[f"km_sum_le100_{r}"] / w[f"jobs_le100_{r}"].replace(0, np.nan)
# a tract with no workers in one year takes the other year's mean (its share that year is zero)
w["c_early"] = w["c_early"].fillna(w["c_late"])
w["c_late"] = w["c_late"].fillna(w["c_early"])
w = w.dropna(subset=["c_early"])

piv = tv.pivot(index="tract_geoid", columns="vintage", values="units")
newshare = piv[["2000_2009", "2010_2019", "2020plus"]].sum(axis=1) / piv.sum(axis=1).replace(0, np.nan)
w["new_share"] = newshare.reindex(w.index)
w["new_group"] = pd.cut(w["new_share"], [-0.01, 0.1, 0.3, 1.01], labels=["<10% built 2000+", "10-30%", ">30%"])

# == DECOMPOSITION PER METRO ==================================================
rows, grp = [], []
for code, g in w.groupby("cbsa_code"):
    s0 = g["jobs_le100_early"] / g["jobs_le100_early"].sum()
    s1 = g["jobs_le100_late"] / g["jobs_le100_late"].sum()
    c0, c1 = g["c_early"], g["c_late"]
    mean0, mean1 = (s0 * c0).sum(), (s1 * c1).sum()
    within, between, inter = (s0 * (c1 - c0)).sum(), ((s1 - s0) * c0).sum(), ((s1 - s0) * (c1 - c0)).sum()
    check(abs(mean1 - mean0 - within - between - inter) < 1e-9, f"{code}: decomposition does not add up")
    rows.append({"cbsa_code": code, "mean_km_early": mean0, "mean_km_late": mean1, "change_km": mean1 - mean0,
                 "within_km": within, "between_km": between, "interaction_km": inter,
                 "workers_early": g["resident_jobs_early"].sum(), "workers_late": g["resident_jobs_late"].sum(),
                 "share_gt100_early": (g["commute_share_gt100km_early"] * g["resident_jobs_early"]).sum() / g["resident_jobs_early"].sum(),
                 "share_gt100_late": (g["commute_share_gt100km_late"] * g["resident_jobs_late"]).sum() / g["resident_jobs_late"].sum()})
    for lab, gg in g.groupby("new_group", observed=False):
        m0, m1 = s0[gg.index], s1[gg.index]
        grp.append({"cbsa_code": code, "new_group": lab, "worker_share_early": m0.sum(), "worker_share_late": m1.sum(),
                    "between_km": ((m1 - m0) * gg["c_early"]).sum(), "within_km": (m0 * (gg["c_late"] - gg["c_early"])).sum(),
                    "mean_km_early": (m0 * gg["c_early"]).sum() / m0.sum() if m0.sum() else np.nan})
m = pd.DataFrame(rows).merge(keep[["cbsa_code", "cbsa_title", "early_od", "late_od"]].astype({"early_od": str, "late_od": str}),
                             on="cbsa_code", validate="1:1")
write_table(log, m, f"empirics/results/{EXERCISE}_metros.csv", sort_by=["cbsa_code"])
log.info("metros", table="\n" + m.sort_values("change_km")[["cbsa_title", "mean_km_early", "mean_km_late", "change_km",
                                                            "within_km", "between_km"]].round(2).to_string(index=False))

COLS = ["mean_km_early", "mean_km_late", "change_km", "within_km", "between_km", "interaction_km",
        "share_gt100_early", "share_gt100_late"]
pooled = pd.DataFrame({"statistic": COLS, "mean_over_metros": m[COLS].mean().to_numpy(),
                       "median_over_metros": m[COLS].median().to_numpy()})
pooled["metros"] = len(m)
pooled["metros_commute_rose"] = int((m["change_km"] > 0).sum())
log.info("pooled", table="\n" + pooled.round(3).to_string(index=False))
write_table(log, pooled, f"empirics/results/{EXERCISE}.csv")

gdf = pd.DataFrame(grp)
gp = gdf.groupby("new_group", observed=False)[["worker_share_early", "worker_share_late", "between_km", "within_km", "mean_km_early"]].mean().reset_index()
log.info("by_newshare", table="\n" + gp.round(3).to_string(index=False))
write_table(log, gp, f"empirics/results/{EXERCISE}_by_newshare.csv")
log.info("end")
