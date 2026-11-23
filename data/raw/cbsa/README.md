---
dataset: cbsa
collection_type: acquisition
provider: U.S. Census Bureau (OMB Bulletin 23-01 delineations)
url: https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: xlsx
years: July 2023 delineation
geography: counties and county equivalents in metropolitan and micropolitan statistical areas
unit: county x CBSA
codebook: header row (row 3) of the file; OMB Bulletin 23-01
script: data/scripts/collection/acquire_cbsa.py
---

# CBSA delineation file, July 2023 (List 1)

## Description

- `list1_2023.xlsx` — 1,915 county rows with CBSA code and title, metro/micro type,
  central/outlying flag. Two title rows on top and footnote rows at the bottom.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

Connecticut appears with its 2022 planning regions, not its old counties.
