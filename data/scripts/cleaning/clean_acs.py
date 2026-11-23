"""
clean_acs.py
Stage:      cleaning (B1-B4)
Purpose:    Census-tract rows of ACS 2019-2023 5-year tables B25034 (housing units by year
            structure built) and B25127 (occupied units by tenure x year built x units in
            structure), with descriptive column names built from the Census variable labels.
Codebook:   data/raw/acs/labels_b25034.json, labels_b25127.json (Census API group metadata)
Reads:      data/raw/acs/acsdt5y2023-b25034.dat, acsdt5y2023-b25127.dat, labels_*.json
Writes:     data/clean/acs/b25034.csv, b25127.csv, discrepancies.csv, data/logs/clean_acs.log
Unit:       2020 census tract (summary level 140); other summary levels are not tract data
            and are set aside by summary level with counts (B3)
Decisions:  none
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from pipeline import Discrepancies, check, get_logger, log_shape, project_root, write_table  # noqa: E402

RAW = Path("data/raw/acs")
OUT = Path("data/clean/acs")
VINTAGE = {"Built 2020 or later": "2020plus", "Built 2010 to 2019": "2010_2019",
           "Built 2000 to 2009": "2000_2009", "Built 1990 to 1999": "1990_1999",
           "Built 1980 to 1989": "1980_1989", "Built 1970 to 1979": "1970_1979",
           "Built 1960 to 1969": "1960_1969", "Built 1950 to 1959": "1950_1959",
           "Built 1940 to 1949": "1940_1949", "Built 1939 or earlier": "1939_earlier",
           "Built 2000 to 2019": "2000_2019", "Built 1980 to 1999": "1980_1999",
           "Built 1960 to 1979": "1960_1979", "Built 1940 to 1959": "1940_1959"}
STRUCTURE = {"1, detached or attached": "sf", "2 to 4": "u2_4", "5 to 19": "u5_19",
             "20 to 49": "u20_49", "50 or more": "u50plus", "Mobile home, boat, RV, van, etc.": "mobile"}
TENURE = {"Owner occupied": "own", "Renter occupied": "rent"}

log = get_logger("clean_acs")
disc = Discrepancies(log)
root = project_root()


def names_from_labels(table: str) -> dict:
    """Map summary-file column (B25034_E002) to a descriptive name from the label path."""
    meta = json.loads((root / RAW / f"labels_{table.lower()}.json").read_text())["variables"]
    out = {}
    for var, info in meta.items():
        m = re.fullmatch(rf"{table}_(\d{{3}})E", var)
        if not m:
            continue
        parts = [p.rstrip(":") for p in info["label"].split("!!")[2:]]  # drop "Estimate", "Total:"
        if not parts:
            name = "units_total" if table == "B25034" else "occupied_total"
        else:
            mapped = [TENURE.get(p) or VINTAGE.get(p) or STRUCTURE.get(p) for p in parts]
            check(all(mapped), f"{var}: unmapped label part in {parts}")
            name = "units_" + "_".join(mapped)
        out[f"{table}_E{m.group(1)}"] = name
    return out


for table in ("B25034", "B25127"):
    # == PHASE 1: LOAD AND PROFILE ==============================================
    df = pd.read_csv(root / RAW / f"acsdt5y2023-{table.lower()}.dat", sep="|", dtype=str)
    log_shape(log, df, f"{table} raw (all summary levels)")
    level = df["GEO_ID"].str[:3]
    log.info("summary_levels", table=table, counts=level.value_counts().head(15).to_dict())

    # == PHASE 2: PRE-CLEANING ASSERTIONS (data vs documentation) ===============
    mapping = names_from_labels(table)
    est_cols = [c for c in df.columns if re.fullmatch(rf"{table}_E\d{{3}}", c)]
    check(set(est_cols) == set(mapping), f"{table}: estimate columns differ from codebook: "
          f"{set(est_cols) ^ set(mapping)}")
    check(df["GEO_ID"].is_unique, f"{table}: GEO_ID not unique")

    # == PHASE 3: TRANSFORMATIONS ================================================
    is_tract = df["GEO_ID"].str.startswith("1400000US")
    log.info("set_aside_non_tract", table=table, n_rows=int((~is_tract).sum()),
             reason="other summary levels (nation, state, county, ...): not the tract unit")
    df = df.loc[is_tract, ["GEO_ID"] + est_cols].copy()
    n_in = len(df)
    df["tract_geoid"] = df.pop("GEO_ID").str[9:]
    for c in est_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        neg = df[c] < 0
        if neg.any():  # Census annotation sentinels (e.g. -666666666) mark unavailable estimates
            disc.add(c, ">= 0 count", sorted(df.loc[neg, c].unique().tolist())[:5], int(neg.sum()),
                     "sentinel set to missing")
            df.loc[neg, c] = pd.NA
    df = df.rename(columns=mapping)

    # == PHASE 4: POST-CLEANING ASSERTIONS =======================================
    check(len(df) == n_in, "row count changed")
    check(df["tract_geoid"].str.fullmatch(r"\d{11}").all(), "tract GEOID not 11 digits")
    check(df["tract_geoid"].is_unique, "tract GEOID not unique")
    total = "units_total" if table == "B25034" else "occupied_total"
    if table == "B25034":
        leaves = [c for c in df.columns if c.startswith("units_") and c != total]
    else:  # leaf cells end in a structure type
        leaves = [c for c in df.columns if c.endswith(tuple("_" + v for v in STRUCTURE.values()))]
    gap = (df[leaves].sum(axis=1) - df[total]).abs()
    check(int((gap > 0).sum()) == 0, f"{table}: leaf cells do not sum to total in {int((gap > 0).sum())} tracts")
    log.info("leaf_cells_sum_to_total", table=table, n_leaves=len(leaves))

    # == PHASE 5: FINAL PROFILE AND WRITE ========================================
    log_shape(log, df, f"{table} clean")
    log.info("totals", table=table, sum_total=int(df[total].sum()))
    write_table(log, df[["tract_geoid"] + [c for c in df.columns if c != "tract_geoid"]],
                str(OUT / f"{table.lower()}.csv"), sort_by=["tract_geoid"])

disc.write(str(OUT / "discrepancies.csv"))
log.info("end")
