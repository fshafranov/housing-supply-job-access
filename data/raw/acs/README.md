---
dataset: acs
collection_type: acquisition
provider: U.S. Census Bureau, American Community Survey
url: https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/ (files acsdt5y2023-b25034.dat, acsdt5y2023-b25127.dat); labels from https://api.census.gov/data/2023/acs/acs5/groups/{B25034,B25127}.json
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: pipe-delimited text (.dat); JSON (labels)
years: 2019-2023 5-year estimates
geography: all summary levels, national; tracts are 2020 census tracts (Connecticut uses 2022 planning-region codes)
unit: geography (GEO_ID) x table; estimates (E) and margins of error (M)
codebook: labels_b25034.json, labels_b25127.json (Census API group metadata, 2023 ACS 5-year)
script: data/scripts/collection/acquire_acs.py
---

# ACS 2019-2023 table-based summary files: year structure built

## Description

- `acsdt5y2023-b25034.dat` — B25034 Year Structure Built: all housing units by decade built
  (2020 or later ... 1939 or earlier), one row per geography (543,541 rows; 85,381 tracts).
- `acsdt5y2023-b25127.dat` — B25127 Tenure by Year Structure Built by Units in Structure
  (occupied units; 20-year bins; 1, 2-4, 5-19, 20-49, 50+, mobile home).
- `labels_*.json` — variable labels used to name columns in cleaning.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

The Census data API now requires a key for tract queries (it redirects to `missing_key.html`);
the bulk table-based summary files need none. Year built is self-reported by respondents
and refers to the surviving stock in 2019-2023, not to all units ever built.
