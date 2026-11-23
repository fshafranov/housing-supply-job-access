"""
spatial.py
Stage:      utils (shared by processing scripts)
Purpose:    Great-circle distances and the within-metro, unit-weighted percentile (ANALYSIS_PLAN.md D7).
"""
import numpy as np
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    """Pairwise matrix: rows = points 1, columns = points 2."""
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dlat = p2 - p1
    dlon = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def haversine_pairs_km(lat1, lon1, lat2, lon2):
    """Element-wise distance between aligned arrays."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def unit_pctile(g: pd.DataFrame, col: str, weight: str = "units_total") -> pd.Series:
    """Unit-weighted percentile (0-100, midpoint rule, ties averaged) of col within g."""
    g = g.sort_values(col, kind="mergesort")
    w = g[weight].astype(float)
    cum = w.cumsum() - w / 2
    p = (cum / w.sum() * 100).groupby(g[col]).transform("mean")
    return p.reindex(g.index)
