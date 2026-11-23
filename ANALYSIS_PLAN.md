# Analysis plan: Do new homes get built near jobs? Within-metro job access of US housing by decade

**Status:** exploratory first pass, 2026-11-23. Not pre-registered: the specifications below
were written together with the first run, so every result is descriptive and exploratory.

Decision IDs (D1, D2, ...) and robustness IDs (R1, R2, ...) are referenced from script
comments (`# ANALYSIS_PLAN.md D3`).

## 1. Question and design
Within US metro areas, has new housing (and the cheapest owner housing, a starter-home proxy)
been built progressively farther from jobs, and does new housing go where jobs are being
added? Idea A from the 2026-11-23 brainstorm (housing affordability / where housing gets built).

Design: descriptive. Each 2020 census tract carries (i) the surviving housing stock in
2019-2023 by decade built (ACS B25034) and by tenure x structure type x 20-year vintage
(B25127), and (ii) its job access: the share of the metro's jobs within 10 km straight-line
(LODES WAC). Job access is converted to a within-metro, unit-weighted percentile (D7), so 50
means "as close to jobs as the metro's median home" and metros of different size compare.
The estimand is the unit-weighted mean percentile of homes of each vintage.

## 2. Data and sample
Sources: `acs`, `lodes`, `gazetteer`, `cbsa` (see `data/raw/*/README.md`). Sample: tracts of
the 50 largest metropolitan CBSAs by housing units (D1), minus Hartford and San Juan (D2):
48 metros, 43,370 tracts.

## 3. Main specification
- `01_analyze_access_by_vintage`: tract x decade cells weighted by units;
  percentile ~ decade dummies (pre-1940 reference), s1 pooled, s2 + metro FE (main), s3/s4
  5 and 20 km radius, s5 distance to job center, s6/s7 2002 and 2023 job geography. SEs
  clustered by metro (D8). Plus a contemporaneous comparison: homes of each recent decade
  against jobs at the start of that decade, relative to the stock built before it.
- `02_analyze_jobs_housing_growth`: per metro, homes built 2000+ minus older homes in the
  percentile of access to 2002-2023 job gains (D6); regressed on the metro's share of new homes.
- `03_analyze_structure_type`: tenure x structure cells, metro FE and metro x vintage FE,
  20+ unit rentals as reference.

## 4. Decisions

### D1 Sample: 50 largest metros by housing units
- **Stage / script:** `data/scripts/processing/process_tract_vintage.py`, phase 2
- **Decision:** metropolitan CBSAs (2023 delineation) ranked by ACS 2019-2023 total housing
  units; top 50 kept (smallest: Rochester, NY).
- **Alternatives considered:** all metros; population cutoff of 1 million.
- **Evidence / rationale:** cheap first pass; large metros have enough tracts for a
  within-metro gradient and are where the affordability debate is.
- **Downstream implications:** says nothing about small metros or rural areas.
- **Status:** open

### D2 Exclusions: Connecticut and Puerto Rico metros
- **Stage / script:** `process_tract_vintage.py`, phase 2
- **Decision:** drop Hartford (Connecticut tracts renumbered to planning regions in 2022, so
  2023 ACS tracts do not match 2020 job geography) and San Juan (no LODES).
- **Alternatives considered:** a 2020-2022 Connecticut tract crosswalk.
- **Evidence / rationale:** 884 ACS tracts fail to match the 2020 Gazetteer (log), all in CT.
- **Downstream implications:** 48 metros.
- **Status:** settled (2026-11-23)

### D3 Job years and fallbacks
- **Stage / script:** `acquire_lodes.py`; `process_tract_vintage.py`, phase 3
- **Decision:** per state, early = first year whose job total is at least half the state's
  latest total (2002 where possible), mid = first such year from 2010, late = latest year
  (2023 where possible). Metros whose states have different early years are flagged
  (`early_year_mixed`) and excluded from 02.
- **Alternatives considered:** a common start year of 2010 for all states.
- **Evidence / rationale:** missing or near-empty files (`data/raw/lodes/README.md`).
  Nonstandard years: AZ 2004, DC 2010, AR 2010, MA 2011, MS 2004, NH 2003, MI late 2021.
- **Downstream implications:** Boston, Providence, Washington and Memphis are flagged.
- **Status:** open

### D4 Job access measure
- **Stage / script:** `process_tract_vintage.py`, phase 4
- **Decision:** share of the metro's jobs whose tract internal point lies within 10 km
  straight-line of the home tract's internal point; 5 and 20 km as checks. Main analysis uses
  2010 jobs as a fixed geography for all decades.
- **Alternatives considered:** gravity weights; travel-time isochrones; commuting flows (LODES OD).
- **Evidence / rationale:** simple, no routing data; results are almost identical at 5 and
  20 km (s3, s4 in `analyze_access_by_vintage.csv`).
- **Downstream implications:** ignores jobs outside the metro and travel speed differences
  (freeway suburbs vs dense cores).
- **Status:** open

### D5 Job center
- **Decision:** tract with the most 2010 jobs within 3 km. Checked by eye in `metros.csv`
  (Boston center sat in Portsmouth, NH until the Massachusetts job-year fix in D3).
- **Status:** open

### D6 Access to job growth
- **Decision:** share of the metro's gross tract-level job gains (early to late, gaining tracts
  only) within 10 km. Net change was unstable (negative or above 1) where metros barely grew.
- **Status:** open

### D7 Within-metro percentiles
- **Decision:** unit-weighted percentile (midpoint rule, ties averaged) of each access measure
  among all housing units of the metro in 2019-2023.
- **Downstream implications:** older homes score high partly by construction (cities grow
  outward); the benchmark that matters is the comparison with older stock under the same job
  geography and the comparison across structure types within a vintage.
- **Status:** open

### D8 Standard errors
- **Decision:** cluster by metro: all tracts in a metro share one job geography and one
  percentile scale.
- **Status:** open

### D9 Actual commutes: data and year
- **Stage / script:** `acquire_lodes_od.py`, `process_tract_commute.py`
- **Decision:** LODES 8 OD "main" plus "aux" files (aux adds residents who work in another state),
  all jobs (JT00), latest available year per state (2023; Michigan 2021 as in D3). Home and work
  locations at the 2020 tract internal point; straight-line distance.
- **Alternatives considered:** 2010 OD to match the fixed job geography; network distances.
- **Evidence / rationale:** the access measure in D4 is potential access and turned out to track
  centrality closely (s2 vs s5 in `analyze_access_by_vintage.csv`); actual commutes say where
  residents really work.
- **Downstream implications:** measures commutes of today's residents of a tract, not of a home's
  first buyers; tract-level, so homes of different vintages in one tract share one value. Covers
  wage and salary jobs in LODES (no self-employed); jobs in Alaska are missing (no files used).
- **Status:** open

### D10 Within-tract commutes
- **Decision:** home and work in the same tract get 0.52 x sqrt(land area), the mean distance
  between two random points in a square of that area, instead of zero.
- **Status:** open

### D11 Long-distance commutes
- **Decision:** the main outcome is the median, which needs no cap; the mean is computed over
  commutes up to 100 km, and the share beyond 100 km is reported separately. Very long "commutes"
  in LODES are mostly remote work or jobs assigned to a firm's reporting address.
- **Status:** open

### D12 Putting 2000-tract elasticities on 2020 tracts
- **Stage / script:** `process_tract_elasticity.py`
- **Decision:** (1) a 2000 tract in two BSH regions gets the weighted mean of its rows (BSH weights);
  (2) 2000 to 2010 by 2010 housing units in each overlap (land area where a 2010 tract has no
  housing); (3) 2010 to 2020 by land area of each overlap (the 2020 file has no housing counts).
  Uses the 2011 linear IV unit elasticity (`gamma11a_units_IV`) as the main measure.
- **Alternatives considered:** NHGIS crosswalks (need a login); population weights.
- **Downstream implications:** elasticities are smoothed across tract splits.
- **Status:** open

### D13 Elasticity coverage
- **Decision:** keep a 2020 tract if at least 50% of its crosswalk weight comes from tracts with a BSH
  elasticity. 42,156 of 43,370 sample tracts (97% of units) pass (`process_tract_elasticity.log`).
- **Downstream implications:** BSH covers urban tracts only; the dropped tracts sit at the outer edge.
- **Status:** open

### D14 Elasticity analysis is descriptive
- **Decision:** script 05 describes how elasticity lines up with job access and with where homes built
  since 2010 went; it makes no causal claim. Homes built 2010+ are used because the elasticity uses
  2011 tract traits, and 2000s construction itself lowers a tract's undeveloped share.
- **Downstream implications:** within a metro, BSH elasticity is a function of built-up share,
  flatness and CBD distance, so "elastic tracts got more new homes" is partly by construction. The
  metro comparison (core versus edge elasticity) is less mechanical but has 48 observations.
- **Status:** open

### D15 Where job growth went: sample
- **Stage / script:** `06_explore_job_growth_location.py`
- **Decision:** ring shares of net job change 2002-2023 use metros with consistent LODES start
  years (D3) and total job growth of at least 10% (38 metros; six slow-growing metros dropped).
- **Alternatives considered:** all 44 consistent metros (mean 0-5 km share of net growth was pulled
  up by Rochester and Cleveland, whose small totals make ring shares exceed 100%); medians.
- **Evidence / rationale:** with all 44 metros the mean and median 0-5 km shares disagreed sharply;
  with the growth filter they agree (both columns in `explore_job_growth_location.csv`).
- **Status:** open

### D16 Commute trend 2002-2023: sample and split
- **Stage / script:** `process_tract_commute_trend.py`, `07_analyze_commute_trend.py`
- **Decision:** early year per state = first LODES OD year whose job total is at least half the
  latest (D3 rule); metros whose states start in different years are dropped (Washington, Boston,
  Providence, Memphis), leaving 44; Phoenix starts in 2004 and Detroit ends in 2021. Outcome: mean
  commute of working residents over commutes up to 100 km (D11), split exactly into within (same
  tracts' commutes change, early worker shares), between (worker shares shift, early commutes) and
  interaction. Home geography is 2020 tracts in both years (LODES 8 uses 2020 blocks throughout).
- **Alternatives considered:** medians (not additive); including commutes beyond 100 km (their share
  rises from 6.9% to 10.5% of jobs, mostly remote work or firm-address assignment).
- **Downstream implications:** federal jobs enter LODES only in 2010, so 2002 lacks them; LODES
  residence imputation also changed over time, which can move the within part.
- **Status:** open

## 5. Robustness checks
| ID | Check | Script | Status |
|---|---|---|---|
| R1 | Radius 5 km and 20 km | `01_analyze_access_by_vintage` s3, s4 | done |
| R2 | 2002 and 2023 job geography | `01_analyze_access_by_vintage` s6, s7 | done |
| R3 | Survival bias: compare with decennial-census year-built counts from earlier censuses (NHGIS) | not written | planned |
| R4 | Commuting-zone or CSA scale (spillover into neighbouring metros) | not written | planned |
| R5 | Actual commutes instead of potential access | `04_analyze_commute_by_vintage` | done |
| R6 | Finite-mixture (FMM) elasticity instead of IV prediction | `05_analyze_elasticity_description` | planned |

## 6. Change log
| Date | Change | Reason | Pre-specified? |
|---|---|---|---|
| 2026-11-23 | Plan written with the first run | exploratory first pass | no |
| 2026-11-23 | Added actual commutes (D9-D11, R5, script 04) | access measure tracks centrality; user asked for actual commutes | no |
| 2026-11-23 | Added supply elasticity description (D12-D14, script 05) | user chose the elasticity direction, descriptive first | no |
| 2026-11-23 | Added where-job-growth-went description (D15, script 06) | user asked whether new jobs stayed in the centers | no |
| 2026-11-23 | Added commute trend 2002-2023 and within/between split (D16, script 07) | user asked whether commutes grew over time | no |
