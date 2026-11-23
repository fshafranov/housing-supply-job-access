"""
clean_bsh.py
Stage:      cleaning (B1-B4)
Purpose:    Baum-Snow & Han (JPE 2024) predicted tract supply elasticities and the tract traits they
            are built from, read from gammas_hat_all.dta inside the authors' analysis archive.
Codebook:   Stata variable labels in gammas_hat_all.dta; analyze_replication/step4b_predgam_inter.do
            and step4d_gamma_estimates.do (prediction code); Master_Readme_Replication.pdf
Reads:      data/raw/bsh/analyze_replication.zipx
Writes:     data/clean/bsh/tract_elasticity_2000.csv, data/clean/bsh/discrepancies.csv, data/logs/clean_bsh.log
Unit:       2000 census tract x BSH metro region (a tract in two regions appears twice, weight 1/2), unchanged (B3)
Decisions:  none
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import (  # noqa: E402
    Discrepancies,
    check,
    get_logger,
    log_shape,
    project_root,
    rename_logged,
    write_table,
)

MEMBER = "analyze_replication/datasets/gammas_hat_all.dta"
RENAME = {"ctracts2000": "tract2000", "region_all": "bsh_region", "cbdname": "bsh_cbd_name",
          "wgt": "bsh_weight", "primary_sample": "bsh_primary_sample",
          "pctdis": "bsh_frac_to_edge",  # fraction of the way from the region's CBD to its edge
          "lsf_1_flat_plains": "bsh_frac_flat", "Trct_FrcDev_01": "bsh_frac_developed_2001",
          "Trct_FrcDev_11": "bsh_frac_developed_2011",
          "gamma11a_units_IV": "elast_units", "sd_gamma11a_units_IV": "elast_units_sd",
          "gamma11a_newunits_IV": "elast_newunits", "gamma11a_space_IV": "elast_floorspace",
          "gamma11a_devl_IV": "elast_land_dev", "gamma11b_units_FMM": "elast_units_fmm"}

log = get_logger("clean_bsh")
disc = Discrepancies(log)
root = project_root()

# == PHASE 1: LOAD AND PROFILE ==============================================
with zipfile.ZipFile(root / "data/raw/bsh/analyze_replication.zipx") as z:
    raw = z.read(MEMBER)
reader = pd.read_stata(io.BytesIO(raw), iterator=True)
labels = reader.variable_labels()
df = reader.read()
log_shape(log, df, "raw")
log.info("labels_used", **{k: labels.get(k, "") for k in RENAME})

# == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
check(set(RENAME) <= set(df.columns), f"missing columns {set(RENAME) - set(df.columns)}")
check(labels["gamma11a_units_IV"].startswith("IV pred., units, linear spec, 2011"), "label of main elasticity changed")
check(df["ctracts2000"].str.fullmatch(r"\d{11}").all(), "2000 tract codes not 11 digits")
check(not df.duplicated(["ctracts2000", "region_all"]).any(), "tract x region not unique")
n_in = len(df)

# == PHASE 3: TRANSFORMATIONS ================================================
df = rename_logged(log, df[list(RENAME)], RENAME)
df["bsh_region"] = df["bsh_region"].astype("int64")
df["bsh_primary_sample"] = df["bsh_primary_sample"].astype("int64").astype(bool)
miss = df["elast_units"].isna()
if miss.any():
    disc.add("elast_units", "non-missing", "missing", int(miss.sum()), "kept as missing (one tract in source)")

# == PHASE 4: POST-CLEANING ASSERTIONS =======================================
check(len(df) == n_in, "row count changed")
check(df["bsh_weight"].between(0, 1).all(), "weights outside (0, 1]")
wsum = df.groupby("tract2000")["bsh_weight"].sum()
check(((wsum - 1).abs() < 1e-4).all(), "weights of a tract across regions do not sum to 1")
for c in ["bsh_frac_to_edge", "bsh_frac_flat", "bsh_frac_developed_2001", "bsh_frac_developed_2011"]:
    check(df[c].dropna().between(0, 1.0001).all(), f"{c} outside [0, 1]")

# == PHASE 5: FINAL PROFILE AND WRITE ========================================
log.info("profile", tracts=int(df["tract2000"].nunique()), rows=len(df),
         elast_units_mean=round(float(df["elast_units"].mean()), 4))
write_table(log, df, "data/clean/bsh/tract_elasticity_2000.csv", sort_by=["tract2000", "bsh_region"])
disc.write("data/clean/bsh/discrepancies.csv")
log.info("end")
