---
dataset: tract_xwalk
collection_type: acquisition
provider: U.S. Census Bureau, tract relationship files
url: https://www2.census.gov/geo/docs/maps-data/data/rel/trf_txt/us2010trf.txt; https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: comma-delimited text without header (2000-2010); pipe-delimited text with header (2010-2020)
years: 2000-2010 and 2010-2020 tract relationships
geography: national
unit: 2000 tract x 2010 tract part; 2010 tract x 2020 tract part
codebook: https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/2010-tract-relationship-record-layout.html (2000-2010); header row (2010-2020)
script: data/scripts/collection/acquire_tract_xwalk.py
---

# Census tract relationship files

## Description

- `us2010trf.txt` — 110,854 parts; population, housing-unit and area of each 2000x2010 overlap.
- `tab20_tract20_tract10_natl.txt` — 126,450 parts; land and water area of each 2010x2020 overlap.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

The 2000-2010 file has no header; column names follow the Census record layout (30 fields). The
2010-2020 file starts with a byte-order mark.
