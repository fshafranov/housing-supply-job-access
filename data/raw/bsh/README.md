---
dataset: bsh
collection_type: acquisition
provider: Nathaniel Baum-Snow and Lu Han, replication package for "The Microgeography of Housing Supply" (JPE 2024), Harvard Dataverse
url: https://doi.org/10.7910/DVN/LFGAAW (files https://dataverse.harvard.edu/api/access/datafile/7351376 and /7351396)
date_retrieved: 2026-11-23
license: CC0 1.0
format: zip archive (renamed .zipx by the authors), PDF readme
years: elasticities predicted with 2001 and 2011 tract traits; this project uses the 2011 linear IV prediction
geography: 2000 census tracts in 306 metro regions (50,410 tracts; 63,897 tract x region rows)
unit: 2000 census tract x BSH metro region
codebook: Stata variable labels in analyze_replication/datasets/gammas_hat_all.dta; prediction code analyze_replication/step4b_predgam_inter.do; Master_Readme_Replication.pdf
script: data/scripts/collection/acquire_bsh.py
---

# Baum-Snow & Han (2024): predicted tract housing supply elasticities

## Description

- `analyze_replication.zipx` — the authors' analysis archive (zip). Cleaning reads only
  `analyze_replication/datasets/gammas_hat_all.dta`: predicted supply elasticities (units, new units,
  floorspace, land development; IV and finite-mixture versions) and the tract traits they are built
  from (fraction of the way from the CBD to the region edge, fraction of land flat, fraction
  developed in 2001 and 2011).
- `Master_Readme_Replication.pdf` — the authors' readme.

Checksums: `data/raw/MANIFEST.sha256`.

## Access quirks

The authors renamed zip files to `.zipx` so Dataverse would not unpack them; the file is an ordinary
zip. Within a metro region, the IV predictions are an exact function of the CBD-distance, flatness
and developed-share traits (metro regulation enters only through interactions), and about 20% of
predicted unit elasticities are negative (linear specification).
