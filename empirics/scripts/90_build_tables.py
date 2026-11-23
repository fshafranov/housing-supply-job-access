"""
90_build_tables.py
Stage:      analysis (tables)
Purpose:    Build the first-pass tables (markdown) from the results CSVs only.
Reads:      empirics/results/analyze_access_by_vintage_pooled.csv, analyze_access_by_vintage.csv,
            analyze_structure_type_means.csv, analyze_jobs_housing_growth.csv, ..._metros.csv,
            analyze_commute_by_vintage.csv, analyze_commute_by_vintage_pooled.csv,
            analyze_elasticity_description*.csv
Writes:     empirics/results/tables/table1_decades.md, table2_structure.md, table3_metros.md,
            table4_commutes.md, table5_elasticity.md
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import DECADES  # noqa: E402
from pipeline import check, get_logger, project_root  # noqa: E402

log = get_logger("build_tables", log_dir="empirics/results/logs")
root = project_root()
R = root / "empirics/results"
(R / "tables").mkdir(parents=True, exist_ok=True)

# Table 1: decade gradient
pooled = pd.read_csv(R / "analyze_access_by_vintage_pooled.csv")
reg = pd.read_csv(R / "analyze_access_by_vintage.csv")
s2 = reg[reg["spec"] == "s2_metro_fe"].set_index("term")
check(len(pooled) == len(DECADES), "pooled table incomplete")
t1 = pooled[["vintage", "units", "access10_pctile_mean", "access10_pctile_p10", "access10_pctile_p90",
             "dist_center_km_median"]].copy()
t1["vs_pre1940 (s2)"] = t1["vintage"].map(lambda v: "ref" if v == "1939_earlier" else
                                         f"{s2.loc[v, 'estimate']:.1f} ({s2.loc[v, 'std_error']:.1f})")
t1["units"] = (t1["units"] / 1e6).round(2)
(R / "tables/table1_decades.md").write_text(
    "Table 1. Job access of housing by decade built, 48 largest metros (percentile of metro housing "
    "stock; 50 = median home). Units in millions. Last column: metro-FE regression vs pre-1940, SE "
    "clustered by metro.\n\n" + t1.round(1).to_markdown(index=False) + "\n")

# Table 2: structure types
st = pd.read_csv(R / "analyze_structure_type_means.csv")
t2 = st.pivot(index="vintage20", columns="type", values="access10_pctile").round(1)
(R / "tables/table2_structure.md").write_text(
    "Table 2. Job access percentile by tenure x structure type x 20-year vintage (occupied units).\n\n"
    + t2.to_markdown() + "\n")

# Table 3: metros
m = pd.read_csv(R / "analyze_jobs_housing_growth_metros.csv")
t3 = m.sort_values("growth_gap")[["cbsa_title", "new_share", "level_gap", "growth_gap", "early_year_mixed"]]
(R / "tables/table3_metros.md").write_text(
    "Table 3. Homes built 2000+ vs older homes: gap in percentile of access to 2002 jobs (level_gap) and "
    "to 2002-2023 job gains (growth_gap). Negative = new homes farther.\n\n"
    + t3.round(2).to_markdown(index=False) + "\n")
# Table 4: actual commutes by decade
cp = pd.read_csv(R / "analyze_commute_by_vintage_pooled.csv")
cr = pd.read_csv(R / "analyze_commute_by_vintage.csv")
s2 = cr[cr["spec"] == "s2_median_km"].set_index("term")
t4 = cp[["vintage", "commute_median_km", "commute_share_le10km", "commute_median_close_pctile", "access10_mid_pctile"]].copy()
t4["median km vs pre-1940 (s2)"] = t4["vintage"].map(lambda v: "ref" if v == "1939_earlier" else
                                                    f"{s2.loc[v, 'estimate']:.1f} ({s2.loc[v, 'std_error']:.1f})")
m = cr[cr["spec"].str.startswith("m")][["spec", "term", "estimate", "std_error", "r2_within"]]
(R / "tables/table4_commutes.md").write_text(
    "Table 4. Actual commutes (LODES 2023) of residents of tracts, by decade built (means over 48 metros). "
    "Last column: metro-FE regression, SE clustered by metro.\n\n" + t4.round(2).to_markdown(index=False)
    + "\n\nHow well potential access and centrality predict the commute percentile (tract level, metro FE):\n\n"
    + m.round(3).to_markdown(index=False) + "\n")
# Table 5: elasticity by job access and where new homes went
ba = pd.read_csv(R / "analyze_elasticity_description_by_access.csv")
nh = pd.read_csv(R / "analyze_elasticity_description_new_homes.csv")
er = pd.read_csv(R / "analyze_elasticity_description.csv")
(R / "tables/table5_elasticity.md").write_text(
    "Table 5. Baum-Snow & Han tract supply elasticities (2011, units) and job access. Descriptive.\n\n"
    "A. By within-metro job-access decile (10 = closest to jobs), unit-weighted:\n\n"
    + ba.round(3).to_markdown(index=False)
    + "\n\nB. Homes built 2010+ by within-metro elasticity quintile (5 = most elastic):\n\n"
    + nh.round(3).to_markdown(index=False)
    + "\n\nC. Regressions (e1: tracts, metro FE, SE by metro; e2-e5: metros, robust SE):\n\n"
    + er[["spec", "term", "estimate", "std_error", "p_value", "nobs", "r2"]].round(3).to_markdown(index=False) + "\n")
log.info("end", tables=5)
