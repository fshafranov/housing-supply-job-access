"""
91_build_figures.py
Stage:      analysis (figures)
Purpose:    First-pass figures, built only from results files and the workfile (no estimation).
            Palette: reference dataviz palette, light mode (validated 2026-11-23: adjacent CVD
            dE 9.1, normal-vision 22.9; aqua/yellow below 3:1 contrast, so lines are direct-labeled).
Reads:      empirics/results/analyze_access_by_vintage_pooled.csv, analyze_access_by_vintage_contemporaneous.csv,
            analyze_structure_type_means.csv, analyze_jobs_housing_growth_metros.csv,
            analyze_commute_by_vintage_structure.csv, analyze_elasticity_description_by_access.csv,
            analyze_elasticity_description_metros.csv, analyze_elasticity_description.csv,
            explore_job_growth_location.csv, analyze_commute_trend_metros.csv,
            data/processed/tract_vintage/tracts.csv, tract_vintage.csv, metros.csv
Writes:     empirics/results/figures/fig1_decades.png, fig2_structure.png, fig3_metro_gaps.png,
            fig4_maps.png, fig5_commute_structure.png, fig6_elasticity_access.png,
            fig7_elasticity_metros.png, fig8_jobs_vs_homes_rings.png, fig9_commute_trend.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_config import DECADES, DTYPES, METROS, TRACT_VINTAGE, TRACTS  # noqa: E402
from pipeline import check, get_logger, project_root  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SEQ = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
LABEL = {"1939_earlier": "<1940", "1940_1949": "1940s", "1950_1959": "1950s", "1960_1969": "1960s",
         "1970_1979": "1970s", "1980_1989": "1980s", "1990_1999": "1990s", "2000_2009": "2000s",
         "2010_2019": "2010s", "2020plus": "2020+"}

log = get_logger("build_figures", log_dir="empirics/results/logs")
root = project_root()
R = root / "empirics/results"
OUT = R / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK,
                     "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left"})


def style(ax, ygrid=True):
    ax.tick_params(length=0)
    if ygrid:
        ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def note(fig, text):
    fig.text(0.01, 0.01, text, color=MUTED, fontsize=8, ha="left", va="bottom")


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, metadata={"Software": None})  # no timestamps (G4)
    plt.close(fig)
    log.info("wrote", file=f"empirics/results/figures/{name}")


# == FIGURE 1: decade gradient ================================================
p = pd.read_csv(R / "analyze_access_by_vintage_pooled.csv").set_index("vintage").reindex(DECADES)
c = pd.read_csv(R / "analyze_access_by_vintage_contemporaneous.csv")
check(p["metros"].eq(48).all(), "pooled table not 48 metros")
x = np.arange(len(DECADES))
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.fill_between(x, p["access10_pctile_p10"], p["access10_pctile_p90"], color="#cde2fb", linewidth=0)
ax.axhline(50, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
ax.text(len(DECADES) - 0.6, 50.8, "metro median home", color=MUTED, fontsize=8, ha="right")
ax.plot(x, p["access10_pctile_mean"], color=BLUE, linewidth=2, marker="o", markersize=5,
        markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
for v in ["1939_earlier", "2000_2009", "2010_2019"]:
    i = DECADES.index(v)
    ax.annotate(f"{p.loc[v, 'access10_pctile_mean']:.0f}", (i, p.loc[v, "access10_pctile_mean"]),
                xytext=(0, 9), textcoords="offset points", ha="center", color=INK, fontsize=9)
ax.text(0.15, p["access10_pctile_p90"].iloc[0] + 1.5, "10th–90th percentile of metros", color=INK2, fontsize=8)
ax.set_xticks(x, [LABEL[d] for d in DECADES])
ax.set_ylim(25, 80)
ax.set_ylabel("Job-access percentile (50 = median home)")
ax.set_title("Each decade's homes were built farther from jobs, with a pause in the 2010s")
style(ax)
note(fig, "Mean over 48 large metros of the unit-weighted percentile of jobs within 10 km (2010 jobs). "
          "Surviving stock in ACS 2019–2023.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig1_decades.png")

# == FIGURE 2: structure types ================================================
s = pd.read_csv(R / "analyze_structure_type_means.csv")
V20 = ["1939_earlier", "1940_1959", "1960_1979", "1980_1999", "2000_2019", "2020plus"]
V20L = ["<1940", "1940–59", "1960–79", "1980–99", "2000–19", "2020+"]
TYPES = [("renter 20+ units", "Rental, 20+ units", BLUE), ("renter 5-19 units", "Rental, 5–19 units", AQUA),
         ("owner single-family", "Owner, single-family", ORANGE), ("owner mobile home", "Owner, mobile home", YELLOW)]
pv = s.pivot(index="vintage20", columns="type", values="access10_pctile").reindex(V20)
x = np.arange(len(V20))
fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.axhline(50, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
for t, lab, col in TYPES:
    ax.plot(x, pv[t], color=col, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE,
            markeredgewidth=1.5, label=lab)
    ax.annotate(f"{lab}  {pv[t].iloc[-1]:.0f}", (x[-1], pv[t].iloc[-1]), xytext=(8, 0),
                textcoords="offset points", va="center", color=INK, fontsize=9,
                bbox={"boxstyle": "square,pad=0.15", "fc": SURFACE, "ec": "none"})
ax.set_xticks(x, V20L)
ax.set_xlim(-0.3, len(V20) + 1.6)
ax.set_ylim(15, 85)
ax.set_ylabel("Job-access percentile (50 = median home)")
ax.set_title("Owner homes, the starter-home proxy, sit farthest from jobs;\nlarge rental buildings stayed close")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False, fontsize=8.5,
          labelcolor=INK2, handlelength=1.5)
style(ax)
note(fig, "Occupied units, ACS B25127, 48 large metros pooled; 2010 jobs within 10 km. Year = year built.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig2_structure.png")

# == FIGURE 3: metro gaps =====================================================
m = pd.read_csv(R / "analyze_jobs_housing_growth_metros.csv").sort_values("growth_gap")
check(len(m) == 48, "metro table not 48 rows")
m["short"] = m["cbsa_title"].str.split(r"[-,/]").str[0].str.replace(" Beach", " Bch.")
y = np.arange(len(m))
fig, ax = plt.subplots(figsize=(7.5, 10))
ax.axvline(0, color=MUTED, linewidth=1)
for flag, face in [(False, BLUE), (True, SURFACE)]:
    sub = m[m["early_year_mixed"] == flag]
    yy = y[m["early_year_mixed"].to_numpy() == flag]
    ax.hlines(yy, 0, sub["growth_gap"], color="#b7d3f6", linewidth=2)
    ax.scatter(sub["growth_gap"], yy, s=40, color=face, edgecolor=BLUE, linewidth=1.5, zorder=3,
               label="job years differ across states (not in regressions)" if flag else "metro")
ax.set_yticks(y, m["short"], fontsize=8.5)
ax.set_xlabel("Homes built 2000+ minus older homes: percentile of access to 2002–2023 job gains")
ax.set_title("New homes sit farthest from new jobs in Phoenix, Las Vegas and San Antonio;\nin most coastal metros the gap is near zero")
ax.text(-17.5, len(m) - 0.5, "new homes farther from\nnew jobs than older homes", color=INK2, fontsize=8, va="top")
ax.text(1, 2.5, "new homes closer", color=INK2, fontsize=8, va="center")
ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK2)
ax.tick_params(length=0)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
note(fig, "Access to job gains: share of the metro's tract-level job gains 2002–2023 within 10 km, as a "
          "within-metro percentile.")
fig.tight_layout(rect=(0, 0.02, 1, 1))
save(fig, "fig3_metro_gaps.png")

# == FIGURE 4: two metros on a map ============================================
tr = pd.read_csv(root / TRACTS, dtype=DTYPES)
tv = pd.read_csv(root / TRACT_VINTAGE, dtype=DTYPES)
metros = pd.read_csv(root / METROS, dtype=DTYPES)
new = tv[tv["vintage"].isin(["2000_2009", "2010_2019", "2020plus"])].groupby("tract_geoid")["units"].sum()
tr["new_share"] = tr["tract_geoid"].map(new) / tr["units_total"].where(tr["units_total"] > 0)
PICK = [("38060", "Phoenix: new homes on the edge", 45), ("41940", "San Jose: new homes among the jobs", 45)]
fig, axes = plt.subplots(1, 2, figsize=(9, 5.8))
fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.24, wspace=0.05)
for ax, (code, title, half_km) in zip(axes, PICK, strict=True):
    g = tr[(tr["cbsa_code"] == code) & tr["new_share"].notna()].sort_values("new_share")
    mm = metros[metros["cbsa_code"] == code].iloc[0]
    kx = 111.32 * np.cos(np.radians(mm["center_lat"]))
    gx, gy = (g["lon"] - mm["center_lon"]) * kx, (g["lat"] - mm["center_lat"]) * 110.57
    keep = (gx.abs() <= half_km) & (gy.abs() <= half_km)
    sc = ax.scatter(gx[keep], gy[keep], c=g.loc[keep, "new_share"], cmap=SEQ, vmin=0, vmax=1, s=9, linewidths=0)
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(10 * np.cos(th), 10 * np.sin(th), color=INK, linewidth=1, linestyle=(0, (3, 2)))
    ax.plot(0, 0, marker="*", markersize=12, color=ORANGE, markeredgecolor=SURFACE)
    ax.text(10 * np.cos(0.8) + 1, 10 * np.sin(0.8) + 1, "10 km from\njob center", fontsize=7.5, color=INK,
            bbox={"boxstyle": "square,pad=0.2", "fc": SURFACE, "ec": "none", "alpha": 0.85})
    ax.plot([-half_km + 2, -half_km + 22], [-half_km + 2] * 2, color=INK, linewidth=1.5)
    ax.text(-half_km + 12, -half_km + 3.5, "20 km", ha="center", fontsize=7.5, color=INK2)
    ax.set_xlim(-half_km, half_km)
    ax.set_ylim(-half_km, half_km)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
cb = fig.colorbar(sc, cax=fig.add_axes((0.2, 0.15, 0.6, 0.025)), orientation="horizontal")
cb.set_label("Share of a tract's homes built 2000 or later", color=INK2)
cb.outline.set_visible(False)
cb.ax.tick_params(length=0, colors=INK2)
cb.ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
fig.text(0.02, 0.01, "Both maps 90 x 90 km around the job center (star: most 2010 jobs within 3 km). One dot "
         "per census tract.\nGap between new and older homes in access to job gains: Phoenix −17.9, "
         "San Jose +8.0.", color=MUTED, fontsize=8, ha="left", va="bottom")
save(fig, "fig4_maps.png")
# == FIGURE 5: actual commutes by structure type ==============================
cs = pd.read_csv(R / "analyze_commute_by_vintage_structure.csv")
pv = cs.pivot(index="vintage20", columns="type", values="commute_median_km").reindex(V20)
x = np.arange(len(V20))
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for t, lab, col in TYPES:
    ax.plot(x, pv[t], color=col, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE,
            markeredgewidth=1.5, label=lab)
    ax.annotate(f"{lab}  {pv[t].iloc[-1]:.0f} km", (x[-1], pv[t].iloc[-1]), xytext=(8, 0),
                textcoords="offset points", va="center", color=INK, fontsize=9,
                bbox={"boxstyle": "square,pad=0.15", "fc": SURFACE, "ec": "none"})
ax.set_xticks(x, V20L)
ax.set_xlim(-0.3, len(V20) + 1.9)
ax.set_ylim(0, 36)
ax.set_ylabel("Median commute of the tract's residents (km)")
ax.set_title("Actual commutes tell the same story: residents of new owner homes\ncommute 25–33 km, of big rental buildings about 15 km")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False, fontsize=8.5,
          labelcolor=INK2, handlelength=1.5)
style(ax)
note(fig, "LODES 2023 home-to-work flows, straight-line tract-to-tract km; tract median weighted by units "
          "of each type; 48 metros.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig5_commute_structure.png")
# == FIGURE 6: elasticity by job-access decile =================================
ba = pd.read_csv(R / "analyze_elasticity_description_by_access.csv").sort_values("access_decile")
x = ba["access_decile"].to_numpy()
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.2))
a1.plot(x, ba["elast_units"], color=BLUE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5)
for i in [0, 9]:
    a1.annotate(f"{ba['elast_units'].iloc[i]:.2f}", (x[i], ba["elast_units"].iloc[i]), xytext=(0, 9),
                textcoords="offset points", ha="center", color=INK, fontsize=9)
a1.set_ylim(0, 0.7)
a1.set_title("Supply elasticity (housing units)", fontsize=10)
a2.plot(x, ba["bsh_frac_developed_2011"] * 100, color=ORANGE, linewidth=2, marker="o", markersize=5,
        markeredgecolor=SURFACE, markeredgewidth=1.5)
a2.plot(x, ba["bsh_frac_flat"] * 100, color=AQUA, linewidth=2, marker="o", markersize=5,
        markeredgecolor=SURFACE, markeredgewidth=1.5)
a2.annotate("land already developed", (x[-1], ba["bsh_frac_developed_2011"].iloc[-1] * 100), xytext=(-4, 10),
            textcoords="offset points", ha="right", color=INK, fontsize=9)
a2.annotate("land that is flat", (x[2], ba["bsh_frac_flat"].iloc[2] * 100), xytext=(0, 10),
            textcoords="offset points", ha="center", color=INK, fontsize=9)
a2.set_ylim(0, 70)
a2.set_title("Share of the tract's land (%)", fontsize=10)
for a in (a1, a2):
    a.set_xticks(x)
    a.set_xlabel("Job-access decile within the metro (10 = closest to jobs)")
    style(a)
fig.suptitle("Near jobs, housing supply is inelastic because the land is already built up, not because of terrain",
             x=0.01, ha="left", fontsize=11, fontweight="semibold", color=INK)
note(fig, "Baum-Snow & Han (JPE 2024) predicted tract unit supply elasticities (2011), carried to 2020 tracts; "
          "unit-weighted means, 48 metros.")
fig.tight_layout(rect=(0, 0.04, 1, 0.94))
save(fig, "fig6_elasticity_access.png")

# == FIGURE 7: metro scatter, edge elasticity vs gap ===========================
mt = pd.read_csv(R / "analyze_elasticity_description_metros.csv")
er = pd.read_csv(R / "analyze_elasticity_description.csv")
check(len(mt) == 48, "metro table not 48 rows")
mt["short"] = mt["cbsa_title"].str.split(r"[-,/]").str[0]
fig, ax = plt.subplots(figsize=(7.5, 5.2))
ax.axhline(0, color=MUTED, linewidth=1)
ax.scatter(mt["elast_far"], mt["new_minus_old_access_pctile"], s=36, color=BLUE, edgecolor=SURFACE, linewidth=1, zorder=3)
b = np.polyfit(mt["elast_far"], mt["new_minus_old_access_pctile"], 1)
xx = np.linspace(mt["elast_far"].min(), mt["elast_far"].max(), 50)
ax.plot(xx, np.polyval(b, xx), color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
LAB = ["San Jose", "New York", "Seattle", "San Francisco", "Los Angeles", "San Diego", "Boston", "Phoenix",
       "Las Vegas", "San Antonio", "Houston", "Jacksonville", "Orlando", "Charlotte", "Detroit", "St. Louis"]
OFFSET = {"Las Vegas": (-5, 3, "right"), "Houston": (0, -13, "center")}
for _, r in mt[mt["short"].isin(LAB)].iterrows():
    dx, dy, ha = OFFSET.get(r["short"], (5, 3, "left"))
    ax.annotate(r["short"], (r["elast_far"], r["new_minus_old_access_pctile"]), xytext=(dx, dy),
                ha=ha, textcoords="offset points", fontsize=8, color=INK2)
e5 = er[(er["spec"] == "e5_access_gap_levels")].set_index("term")
ax.set_xlabel("Supply elasticity of tracts far from jobs (bottom 20% of job access)")
ax.set_ylabel("Homes built 2010+ minus older homes:\njob-access percentile")
ax.set_title("Where the edge is easy to build on, new homes end up far from jobs")
style(ax)
ax.grid(axis="x", color=GRID, linewidth=0.8)
note(fig, f"48 metros; dashed: simple fit. Holding core elasticity fixed, slope {e5.loc['elast_far', 'estimate']:.1f} "
          f"(SE {e5.loc['elast_far', 'std_error']:.1f}); core elasticity itself: {e5.loc['elast_near_jobs', 'estimate']:.1f} "
          f"(SE {e5.loc['elast_near_jobs', 'std_error']:.1f}). Descriptive.")
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig7_elasticity_metros.png")
# == FIGURE 8: where jobs and homes were added, by distance ring ===============
jr = pd.read_csv(R / "explore_job_growth_location.csv")
SERIES = [("share_jobs_early", "Jobs in 2002", BLUE), ("share_job_change", "Net job growth 2002–2023", ORANGE),
          ("share_homes_2010plus", "Homes built 2010+", AQUA)]
x = np.arange(len(jr))
bw = 0.26
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, (col, lab, colr) in enumerate(SERIES):
    v = jr[col].to_numpy() * 100
    ax.bar(x + (k - 1) * bw, v, width=bw - 0.03, color=colr, label=lab, edgecolor=SURFACE, linewidth=0)
    for xi, vi in zip(x + (k - 1) * bw, v, strict=True):
        ax.text(xi, vi + 0.6, f"{vi:.0f}", ha="center", fontsize=7.5, color=INK2)
ax.set_xticks(x, jr["ring"])
ax.set_xlabel("Distance from the metro's job center")
ax.set_ylabel("Share of the metro total (%)")
ax.set_ylim(0, 36)
ax.set_title("New jobs did not stay in the centers: they moved out too,\njust not quite as far as new homes")
ax.legend(loc="upper right", frameon=False, fontsize=8.5, labelcolor=INK2)
style(ax)
note(fig, f"Mean over {int(jr['metros'].iloc[0])} metros whose jobs grew at least 10% (each weighted equally; mixed LODES "
          "start years excluded).")
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig8_jobs_vs_homes_rings.png")
# == FIGURE 9: commute change 2002-2023, within vs between =====================
ctm = pd.read_csv(R / "analyze_commute_trend_metros.csv").sort_values("change_km")
check(len(ctm) == 44, "commute trend table not 44 metros")
ctm["short"] = ctm["cbsa_title"].str.split(r"[-,/]").str[0].str.replace(" Beach", " Bch.")
y = np.arange(len(ctm))
fig, ax = plt.subplots(figsize=(7.5, 10))
wv, bv = ctm["within_km"].to_numpy(), ctm["between_km"].to_numpy()
ax.barh(y, wv, height=0.7, color=BLUE, label="Within: same tracts, residents commute farther", edgecolor=SURFACE, linewidth=1)
ax.barh(y, bv, left=np.where(bv >= 0, np.maximum(wv, 0), 0), height=0.7, color=ORANGE,
        label="Between: more workers live in far-out tracts", edgecolor=SURFACE, linewidth=1)
ax.scatter(ctm["change_km"], y, s=18, color=INK, zorder=3, label="Total change (incl. small interaction)")
ax.axvline(0, color=MUTED, linewidth=1)
ax.set_yticks(y, ctm["short"], fontsize=8.5)
ax.set_xlabel("Change in mean commute of residents, 2002 to 2023 (km)")
n_between = int((ctm["between_km"] > ctm["within_km"]).sum())
ax.set_title(f"Commutes rose in {int((ctm['change_km'] > 0).sum())} of {len(ctm)} metros; where people live explains most\n"
             f"of the rise in only {n_between}, mostly fast-growing Sunbelt metros")
ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK2)
ax.tick_params(length=0)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
note(fig, "LODES OD, commutes up to 100 km, straight-line. Phoenix starts 2004, Detroit ends 2021; "
          "federal jobs enter LODES only in 2010.")
fig.tight_layout(rect=(0, 0.02, 1, 1))
save(fig, "fig9_commute_trend.png")
log.info("end", figures=9)
