---
dataset: lodes
collection_type: acquisition
provider: U.S. Census Bureau, LEHD Origin-Destination Employment Statistics (LODES 8)
url: https://lehd.ces.census.gov/data/lodes/LODES8/{st}/wac/{st}_wac_S000_JT00_{year}.csv.gz
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: gzip-compressed CSV
years: 2002-2023 (one early, 2010, and latest year per state; fallbacks below)
geography: 2020 census blocks, 50 states and DC except Alaska
unit: census block of workplace x year (Workplace Area Characteristics, all jobs, all job types)
codebook: https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.pdf
script: data/scripts/collection/acquire_lodes.py
---

# LODES 8 Workplace Area Characteristics (WAC), S000 / JT00

## Description

150 files, `{st}_wac_S000_JT00_{year}.csv.gz`. Column `C000` = total jobs at the workplace block.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

- Missing files (HTTP 404, 2026-11-23): AZ 2002-03, DC 2002-09, MS 2002-03, NH 2002,
  MI 2022-23, AK 2020+. The script falls back to the next available year (log:
  `data/logs/acquire_lodes.log`).
- Massachusetts 2002 and 2010 files exist but contain almost no jobs (7 and 17), and
  Arkansas 2002 is incomplete; MA 2011 is downloaded as an extra year and processing uses
  the first year whose state total is at least half the latest total (ANALYSIS_PLAN.md D3).
- LEHD drops bursts of requests (connections time out); the script pauses between files.
