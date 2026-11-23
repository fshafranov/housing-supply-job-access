---
dataset: lodes_od
collection_type: acquisition
provider: U.S. Census Bureau, LEHD Origin-Destination Employment Statistics (LODES 8)
url: https://lehd.ces.census.gov/data/lodes/LODES8/{st}/od/{st}_od_{main|aux}_JT00_{year}.csv.gz
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: gzip-compressed CSV
years: 2023 and 2002 (latest and earliest available per state, plus MA 2011 and AR 2010; see data/logs/acquire_lodes_od.log)
geography: 2020 census blocks, 50 states and DC except Alaska
unit: work block x home block (all jobs, JT00); main = both in the file's state, aux = work in the state, home elsewhere
codebook: https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.pdf
script: data/scripts/collection/acquire_lodes_od.py
---

# LODES 8 Origin-Destination files (main and aux), all jobs

## Description

204 files, `{st}_od_{part}_JT00_{year}.csv.gz`. Columns used: `w_geocode`, `h_geocode`, `S000`
(total jobs for the pair). About 1.4 GB compressed in total.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

LEHD drops bursts of requests and serves one connection at about 0.5 MB/s; the script downloads six
states at a time and pauses between files (about 4 minutes for the second year).
Home locations come from administrative records and some jobs are assigned to a firm's
reporting address rather than the worksite, so very long "commutes" exist (ANALYSIS_PLAN.md D11).
