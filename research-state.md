# Research state: Do new homes get built near jobs?

<!-- Protocol. Start of a session: read "Current state" and the last three entries of
"Session history" only. Before stopping for any reason: rewrite "Current state" (present
only, never appended to) and append one dated entry to "Session history" (never edit or
delete earlier entries). Code, results files and the registers are the source of truth:
if this file contradicts them, trust them and flag the contradiction. -->

## Current state
Last updated: 2026-11-23

- **Done:** first pass, idea A (within-metro job access of new housing). Data: ACS 2019-2023
  year built (tracts), LODES jobs 2002/2010/2023, 48 of the 50 largest metros. Pipeline runs
  end to end from `data/raw/` (`uv run python run_all.py`). Four figures in
  `empirics/results/figures/` (`91_build_figures.py`): decade gradient, structure types,
  metro gaps, Phoenix vs San Jose maps, commutes by structure type, elasticity by job access,
  metro scatter of edge elasticity vs gap.
- **Results so far (all descriptive):**
  - Each decade's homes sit lower in the metro's job-access distribution: 64.2 percentile for
    pre-1940 homes, 40.4 for 2000s homes, 44.9 for 2010s, 41.2 for 2020+
    (`empirics/results/analyze_access_by_vintage_pooled.csv`). Metro-FE gap vs pre-1940 for
    2000s homes: -27.3 (s2 in `analyze_access_by_vintage.csv`). Same at 5/20 km and with 2002 or 2023 jobs.
  - Against jobs at the time: 2000s homes 40.1 vs 53.0 for older stock (gap -13.0); 2010s
    gap -5.9; 2020+ gap -8.2 (`analyze_access_by_vintage_contemporaneous.csv`, means over metros).
  - Starter-home proxy: owner single-family built 2000-2019 at 32.6 vs 66.6 for 20+ unit
    rentals; owner mobile homes 25.7 (`analyze_structure_type_means.csv`). Gap of owner
    single-family vs big rentals, metro FE: -23.9 for 1960-79, -34.8 for 2000-19
    (`analyze_structure_type.csv`, s3).
  - New homes vs job gains: mean gap -7.0 across 44 metros (s1 in
    `analyze_jobs_housing_growth.csv`); biggest in Phoenix, Las Vegas, San Antonio; near zero or
    positive in San Jose, Charlotte, New York, Seattle, LA, SF.
- **Interpretation caution:** regulated coastal metros show small gaps because little gets
  built there and what does is infill; the displacement in those regions likely crosses metro
  borders (Inland Empire, Central Valley), which a within-metro measure cannot see (R4).
  - Actual commutes (LODES OD 2023, script 04): median commute of residents of tracts with
    pre-1940 homes 17.13 km, 2000s homes 22.25 km (`analyze_commute_by_vintage_pooled.csv`);
    metro-FE gap 6.675 km (s2 in `analyze_commute_by_vintage.csv`). Owner single-family built
    2000-2019: 25.5 km vs 15.0 km for 20+ unit rentals (`analyze_commute_by_vintage_structure.csv`).
    The 10 km access percentile predicts the commute percentile well (within-metro R2 0.816, m1);
    distance to center alone less so (0.683, m2), so access is not just centrality.
- **Not verified:** survival bias in year built (R3); whether this already exists in the
  literature (Kneebone & Holmes 2015 Brookings on jobs-people distance; job sprawl papers);
  no home size or price data, so "starter home" is only a structure/tenure proxy.
- **Blocked:** Wharton regulation index 2018 page moved (404), no regulation split yet.
- **Supply elasticity, descriptive (script 05, D12-D14):** Baum-Snow & Han 2011 unit elasticities
  on 42,156 sample tracts. Elasticity falls from 0.567 in the least job-accessible decile to 0.125 in
  the most (`analyze_elasticity_description_by_access.csv`), tracking land already developed
  (0.12 to 0.585), not flatness. The most elastic fifth of tracts got 0.294 of homes built 2010+, at
  job-access percentile 24.034 (`..._new_homes.csv`). Across metros, the gap between new and older
  homes tracks the elasticity of the edge (slope -29.193, SE 9.773), not of the core (-4.005, SE 5.897)
  (e5 in `analyze_elasticity_description.csv`): new homes go far where the edge is easy to build on.
- **Where job growth went (script 06, D15):** new jobs did not stay in the centers. In 38 growing
  metros the 0-5 km ring held 0.195 of 2002 jobs but got 0.112 of net job growth and 0.101 of homes
  built 2010+; 20-30 km got 0.252 of job growth and 0.228 of new homes; 30-50 km 0.188 vs 0.24
  (`explore_job_growth_location.csv`). Jobs moved out too, homes somewhat further.
- **Commute trend 2002-2023 (script 07, D16):** in 44 metros the mean commute (up to 100 km) rose from
  18.546 to 20.985 km; it rose in 43 metros. Of the 2.439 km rise, 1.74 km is within (same tracts'
  residents commute farther) and 0.831 km between (more workers live in far-out tracts)
  (`analyze_commute_trend.csv`). Tracts with over 30% of homes built since 2000 went from 0.223 to
  0.343 of workers (`analyze_commute_trend_by_newshare.csv`). Between exceeds within in 7 metros
  (Phoenix, Austin, Houston, Las Vegas, San Antonio, Riverside, Baltimore; `..._metros.csv`).
- **Next step:** minimum-commute split (location vs matching), or decide between (a) the causal version (job-growth shocks x elasticity, proposed
  2026-11-23), (b) literature check, (c) CSA version, (d) R6 robustness with the FMM elasticity.

## Session history

### 2026-11-23
- Done: scaffolded; acquisition, cleaning, processing, three analyses and tables; first results.
- Succeeded: Census bulk summary files replace the keyed API; LODES with year fallbacks.
- Failed: Census API needs a key now; LODES MA 2002/2010 files are near-empty (Boston job
  center landed in Portsmouth, NH until fixed, D3); Wharton index URL 404.
- Key decisions: D1-D8 in `ANALYSIS_PLAN.md`, all exploratory.
- Commit: no-git

### 2026-11-23 (figures)
- Done: `91_build_figures.py` (four PNGs from results files and the workfile), added to `run_all.py`.
- Succeeded: palette validated (dataviz validator, light mode); every figure rendered and checked by eye.
- Failed: constrained layout clipped the map panel titles; switched to a manual layout.
- Key decisions: none (presentation only).
- Commit: no-git

### 2026-11-23 (actual commutes)
- Done: LODES OD 2023 main + aux (100 files, 824 MB), `clean_lodes_od.py`, `process_tract_commute.py`,
  `04_analyze_commute_by_vintage.py`, table 4, figure 5; spatial helpers moved to `utils/spatial.py`
  (processed outputs byte-identical before and after).
- Succeeded: OD job total equals the WAC late-year total (`clean_lodes_od.log` totals vs `process_tract_vintage.log` jobs_role late).
- Failed: first processing run lost every tract key (index name dropped on reset); fixed. Distance
  bound of 6,000 km too low for Hawaii-Maine pairs.
- Key decisions: D9-D11, R5 in `ANALYSIS_PLAN.md`.
- Commit: no-git

### 2026-11-23 (elasticity screen)
- Done: located Baum-Snow & Han tract elasticities and read their prediction code; checked how much of
  the within-metro elasticity is distance to CBD (alone: within R2 0.03-0.13; with developed share and
  flatness: 1.0 for the IV predictions). Literature: Baum-Snow (JEP 2023) already documents growth at
  the fringe and rising core construction costs.
- Key decisions: none yet; design choice pending with the user.
- Commit: no-git

### 2026-11-23 (elasticity description)
- Done: acquired BSH replication archive and Census tract relationship files; `clean_bsh.py`,
  `clean_tract_xwalk.py`, `process_tract_elasticity.py`, `05_analyze_elasticity_description.py`,
  table 5, figures 6-7.
- Succeeded: cleaned BSH tract count matches the paper (`clean_bsh.log`, profile tracts).
- Failed: guessed elasticity bound (-0.5) too tight; source has negative predictions (about 20%).
- Key decisions: D12-D14 in `ANALYSIS_PLAN.md`.
- Commit: no-git

### 2026-11-23 (job growth location)
- Done: `06_explore_job_growth_location.py`, figure 8.
- Failed: first version averaged ring shares over all 44 metros; Rochester and Cleveland (tiny net
  growth) pushed the downtown share of job growth to 0.24; fixed with the 10% growth filter (D15).
- Commit: no-git

### 2026-11-23 (2002 commute data)
- Done: `acquire_lodes_od.py` now downloads the earliest year too, six states at a time (3 min 45 s
  instead of about 25 min); cleaning handles both years; processing keeps the latest year.
- Succeeded: `tract_commute.csv` unchanged (byte-compare).
- Commit: no-git

### 2026-11-23 (commute trend)
- Done: `process_tract_commute_trend.py`, `07_analyze_commute_trend.py`, figure 9.
- Succeeded: decomposition adds up exactly in every metro (asserted).
- Key decisions: D16.
- Commit: no-git
