"""
analysis_config.py
Stage:      analysis: shared setup imported by every Python empirics script (like 00_setup.R).
Purpose:    One place for paths and global analysis choices, each with its ANALYSIS_PLAN.md ID.
Reads:      nothing
Writes:     nothing
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data" / "scripts" / "utils"))

WF = Path("data/processed/tract_vintage")
TRACTS = WF / "tracts.csv"
TRACT_VINTAGE = WF / "tract_vintage.csv"
TRACT_STRUCTURE = WF / "tract_structure.csv"
METROS = WF / "metros.csv"
N_TRACTS = 43370           # exact N of tracts.csv (D1, D2)
N_METROS = 48
DECADES = ["1939_earlier", "1940_1949", "1950_1959", "1960_1969", "1970_1979", "1980_1989",
           "1990_1999", "2000_2009", "2010_2019", "2020plus"]
MAIN_ACCESS = "access10_mid_pctile"   # ANALYSIS_PLAN.md D4, D7: fixed 2010 job geography
VCOV = {"CRV1": "cbsa_code"}         # ANALYSIS_PLAN.md D8: tracts in a metro share job geography
DTYPES = {"tract_geoid": str, "cbsa_code": str}


def script_name(file: str) -> str:
    """04_analyze_reaction_functions.py -> analyze_reaction_functions (results/log name)."""
    stem = Path(file).stem
    return stem.split("_", 1)[1] if stem[:2].isdigit() else stem


def wmean(df, col, w):
    return (df[col] * df[w]).sum() / df[w].sum()
