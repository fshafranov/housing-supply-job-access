---
dataset: gazetteer
collection_type: acquisition
provider: U.S. Census Bureau, Gazetteer Files
url: https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_tracts_national.zip
date_retrieved: 2026-11-23
license: U.S. government work, public domain
format: zip containing a tab-delimited text file
years: 2020
geography: 2020 census tracts, national (85,395 tracts incl. Puerto Rico)
unit: census tract
codebook: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2020.html
script: data/scripts/collection/acquire_gazetteer.py
---

# 2020 Census tract Gazetteer

## Description

- `2020_Gaz_tracts_national.zip` — GEOID, land and water area, internal point (INTPTLAT, INTPTLONG).

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

The last header field carries trailing spaces; cleaning strips them. Connecticut tracts use
pre-2022 county codes, so they do not match 2023 ACS Connecticut tract GEOIDs.
