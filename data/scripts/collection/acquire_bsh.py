"""
acquire_bsh.py
Stage:      collection (A1-A4)
Purpose:    Baum-Snow & Han (JPE 2024) replication package, analysis archive (contains predicted tract supply elasticities) and master readme, from Harvard Dataverse (CC0).
Source:     https://doi.org/10.7910/DVN/LFGAAW (Dataverse file ids 7351376, 7351396)
Reads:      network only (no credentials)
Writes:     data/raw/bsh/<files>, data/logs/acquire_bsh.log
Verified:   every expected file exists, is non-empty and parses as its declared format (A3)
Usage:      uv run python data/scripts/collection/acquire_bsh.py [--force]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from fetch import download  # noqa: E402
from pipeline import get_logger, project_root, verify_files  # noqa: E402

DATASET = "bsh"
RAW_DIR = Path("data/raw") / DATASET
DV = "https://dataverse.harvard.edu/api/access/datafile/"
# The archive is a zip renamed .zipx by the authors so Dataverse would not unpack it.
SOURCES = {"analyze_replication.zipx": (DV + "7351376", "zip"),
           "Master_Readme_Replication.pdf": (DV + "7351396", "pdf")}


def main(force: bool) -> None:
    log = get_logger("acquire_bsh")
    root = project_root()
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)

    # == STEP 1: DOWNLOAD (files already present are kept unless --force) ==
    for name, (url, _fmt) in sorted(SOURCES.items()):
        dest = root / RAW_DIR / name
        if dest.exists() and not force:
            log.info("present", file=name)
            continue
        log.info("download", file=name, url=url)
        download(url, dest)

    # == STEP 2: VERIFY (A3) ==
    verify_files(log, {str(RAW_DIR / n): fmt for n, (_u, fmt) in SOURCES.items()})
    log.info("end", files_verified=len(SOURCES))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    main(parser.parse_args().force)
