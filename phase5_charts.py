"""
Phase 5 — Charts
================
Generates 7 editorial-style PNGs from Phase 2–4 outputs.
Dark theme (#1a1a2e), clean sans-serif, easy to read.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Editorial style
BG_COLOR   = "#1a1a2e"
TEXT_COLOR = "#e8e8e8"
GRID_COLOR = "#2a2a4a"
ACCENT_A   = "#00d4aa"   # teal — clutch / primary
ACCENT_B   = "#ff6b6b"   # coral — overall / contrast
ACCENT_C   = "#ffd93d"   # gold — highlight / positive
NEG_COLOR  = "#ff6b6b"
POS_COLOR  = "#00d4aa"

# Chart dimensions
FIG_W = 10
FIG_H = 6
DPI   = 150


def apply_style(ax):
    """Apply shared dark editorial style to an axis."""
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_COLOR, labelsize=10)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.grid(True, axis="y", color=GRID_COLOR, alpha=0.5, linestyle="--")
    ax.set_axisbelow(True)
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")


def chart1_year_over_year_scatter():
    """Scatter: clutch TS% year N vs year N+1; regression line; r."""
    pairs = pd.read_csv(OUTPUT_DIR / "phase2_yoy_pairs.csv")
    with open(OUTPUT_DIR / "phase2_results.json") as f:
        res = json.load(f)

    r = res["test1_yoy"]["pearson_r"]
    n = res["test1_yoy"]["n_pairs"]

    # Drop zeros for cleaner plot
    pairs = pairs[(pairs["clutch_ts_n"] > 0.1) & (pairs["clutch_ts_n1"] > 0.1)]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG_COLOR)
    ax.scatter(pairs["clutch_ts_n"], pairs["clutch_ts_n1"],
               alpha=0.4, s=25, color=ACCENT_A, edgecolors="none")

    # Regression line
    z = np.polyfit(pairs["clutch_ts_n"], pairs["clutch_ts_n1"], 1)
    x_line = np.linspace(pairs["clutch_ts_n"].min(), pairs["clutch_ts_n"].max(), 100)
    ax.plot(x_line, np.poly1d(z)(x_line), color=ACCENT_C, linewidth=2, linestyle="--")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Clutch TS% (Year N)", fontsize=12)
    ax.set_ylabel("Clutch TS% (Year N+1)", fontsize=12)
    ax.set_title("Is Clutch Repeatable?", fontsize=16, fontweight="bold")
    ax.text(0.05, 0.92, f"r = {r:.3f}  (n = {n:,})", fontsize=12, color=ACCENT_C,
            transform=ax.transAxes, fontweight="bold")
    apply_style(ax)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "year_over_year_scatter.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart2_sample_size_bar():
    """Bar: avg clutch possessions vs avg total possessions."""
    with open(OUTPUT_DIR / "phase2_results.json") as f:
        res = json.load(f)

    clutch = res["test2_sample_size"]["avg_clutch_poss"]
    total = res["test2_sample_size"]["avg_overall_poss"]
    ratio = res["test2_sample_size"]["avg_ratio"] * 100

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG_COLOR)
    bars = ax.bar(["Clutch possessions\n(per player per season)", "Total possessions\n(per player per season)"],
                  [clutch, total], color=[ACCENT_A, ACCENT_B], edgecolor="none", width=0.5)

    ax.set_ylabel("Possessions", fontsize=12)
    ax.set_title("How Many Clutch Moments Does a Star Actually Get?", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.95, f"Clutch = {ratio:.1f}% of total", fontsize=12, color=ACCENT_C,
            transform=ax.transAxes, ha="center", fontweight="bold")
    for i, (b, v) in enumerate(zip(bars, [clutch, total])):
        ax.text(b.get_x() + b.get_width() / 2, v + 20, f"{v:.0f}", ha="center", va="bottom",
                color=TEXT_COLOR, fontsize=12, fontweight="bold")
    apply_style(ax)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Clutch\n(per player per season)", "Total\n(per player per season)"])
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "sample_size_bar.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart3_clutch_vs_overall_ts():
    """Grouped bar: clutch TS% vs overall TS% for reputation players."""
    df = pd.read_csv(OUTPUT_DIR / "phase3_test3_ts_comparison.csv")
    # Top 12 by absolute ts_diff (most dramatic) — mix of worse and better
    df = df.sort_values("ts_diff").head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["clutch_ts"], w, label="Clutch TS%", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["overall_ts"], w, label="Overall TS%", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("True Shooting %", fontsize=12)
    ax.set_title("Are Clutch Players Actually Better Under Pressure?", fontsize=16, fontweight="bold")
    ax.set_xlim(0, 0.75)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "clutch_vs_overall_ts.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart4_usage_spike():
    """Grouped bar: clutch FGA share vs overall FGA share."""
    df = pd.read_csv(OUTPUT_DIR / "phase3_test5_usage_spike.csv")
    df = df.sort_values("fga_share_spike_pct", ascending=False).head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["avg_clutch_fga_share"] * 100, w, label="Clutch share", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["avg_overall_fga_share"] * 100, w, label="Overall share", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("Share of team FGA (%)", fontsize=12)
    ax.set_title("The Ball Always Goes to the Star — Is That Clutch or Just Habit?", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 40)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "usage_spike.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart5_ft_stripped():
    """Grouped bar: clutch TS% vs FT-stripped clutch efficiency."""
    df = pd.read_csv(OUTPUT_DIR / "phase3_test4_ft_stripped.csv")
    df = df.sort_values("ft_boost", ascending=False).head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["clutch_ts"], w, label="Clutch TS% (incl. FTs)", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["ft_stripped_eff"], w, label="FT-stripped (FG only)", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("Efficiency", fontsize=12)
    ax.set_title("How Much of Clutch Scoring Is Actually Free Throws?", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 0.7)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "ft_stripped.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart6_home_away_split():
    """Grouped bar: home clutch TS% vs away clutch TS%."""
    df = pd.read_csv(OUTPUT_DIR / "phase4_test7_home_away.csv")
    df = df.sort_values("home_away_diff", ascending=False).head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["home_ts"], w, label="Home", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["road_ts"], w, label="Road", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("Clutch TS%", fontsize=12)
    ax.set_title("Does Clutch Travel?", fontsize=16, fontweight="bold")
    ax.set_xlim(0, 0.75)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "home_away_split.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart7a_clutch_exception_three():
    """The three stars who shoot better in clutch: CP3, Paul George, SGA. Supports 'The One Who Fits the Myth' section."""
    df = pd.read_csv(OUTPUT_DIR / "phase3_test3_ts_comparison.csv")
    # Only the three with positive ts_diff (better in clutch)
    three = df[df["ts_diff"] > 0].sort_values("ts_diff", ascending=False)
    three["player_short"] = three["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(three))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG_COLOR)
    bars_clutch = ax.bar(x - w/2, three["clutch_ts"], w, label="Clutch TS%", color=ACCENT_A, edgecolor="none")
    bars_overall = ax.bar(x + w/2, three["overall_ts"], w, label="Overall TS%", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(three["player_short"], fontsize=11)
    ax.set_ylabel("True Shooting %", fontsize=12)
    ax.set_title("The Exception — Stars Who Shoot Better in Clutch", fontsize=16, fontweight="bold")
    ax.set_ylim(0, 0.75)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    # Highlight CP3 (first row) with gold accent
    if len(bars_clutch) > 0:
        bars_clutch[0].set_color(ACCENT_C)
        bars_overall[0].set_color(ACCENT_B)
        bars_clutch[0].set_alpha(1.0)
    for i, (c, o, d) in enumerate(zip(three["clutch_ts"], three["overall_ts"], three["ts_diff"])):
        ax.text(i, max(c, o) + 0.03, f"+{d*100:.1f}pp", ha="center", va="bottom", color=TEXT_COLOR, fontsize=10)
    apply_style(ax)
    ax.grid(True, axis="y", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "clutch_exception_three.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart8_ball_movement():
    """Grouped bar: assist-to-FGM ratio clutch vs overall — hero-ball collapse."""
    df = pd.read_csv(OUTPUT_DIR / "phase4_test6_assist_ratio.csv")
    df = df.sort_values("ast_fgm_diff").head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["clutch_ast_fgm"], w, label="Clutch", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["overall_ast_fgm"], w, label="Overall", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("Assists per FGM (ball movement)", fontsize=12)
    ax.set_title("Ball Movement Collapses in Clutch — Hero-Ball Takes Over", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 1.8)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "ball_movement_collapse.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart9_turnover_rate():
    """Grouped bar: turnover rate clutch vs overall — stars protect the ball better."""
    tov = pd.read_csv(OUTPUT_DIR / "turnover_rate_clutch.csv")
    rep_ids = set(pd.read_csv(OUTPUT_DIR / "phase3_test3_ts_comparison.csv")["PLAYER_ID"])
    df = tov[tov["PLAYER_ID"].isin(rep_ids)].copy()
    df = df.sort_values("tov_rate_diff").head(12)
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["clutch_tov_rate"] * 100, w, label="Clutch", color=ACCENT_A, edgecolor="none")
    ax.barh(x + w/2, df["overall_tov_rate"] * 100, w, label="Overall", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("Turnover rate (% of possessions)", fontsize=12)
    ax.set_title("They Don't Choke on the Ball — Stars Protect It Better in Clutch", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 20)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "turnover_rate.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart10_hidden_clutch():
    """Grouped bar: non-stars who shot better in clutch — names we never hear."""
    hidden = pd.read_csv(OUTPUT_DIR / "hidden_clutch_better.csv")
    df = hidden.nlargest(10, "ts_diff")
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    x = np.arange(len(df))
    w = 0.35

    fig, ax = plt.subplots(figsize=(FIG_W + 2, FIG_H + 1), facecolor=BG_COLOR)
    ax.barh(x - w/2, df["clutch_ts"], w, label="Clutch TS%", color=ACCENT_C, edgecolor="none")
    ax.barh(x + w/2, df["overall_ts"], w, label="Overall TS%", color=ACCENT_B, edgecolor="none", alpha=0.8)

    ax.set_yticks(x)
    ax.set_yticklabels(df["player_short"], fontsize=10)
    ax.set_xlabel("True Shooting %", fontsize=12)
    ax.set_title("The Narrative Is Selective — 102 Non-Stars Shot Better in Clutch", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 0.85)
    ax.legend(loc="lower right", facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    apply_style(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, alpha=0.5, linestyle="--")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "hidden_clutch.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def chart7_miss_rate():
    """Bar: clutch miss rate for 3 mythology players."""
    df = pd.read_csv(OUTPUT_DIR / "phase4_test8_miss_rate.csv")
    df["player_short"] = df["player_name"].str.replace(" III", "").str.replace(" Jr.", "")

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG_COLOR)
    colors = [ACCENT_A, ACCENT_B, ACCENT_C]
    bars = ax.bar(df["player_short"], df["clutch_miss_rate"] * 100, color=colors, edgecolor="none", width=0.5)

    ax.set_ylabel("Clutch miss rate (%)", fontsize=12)
    ax.set_title("What Fans Forget", fontsize=16, fontweight="bold")
    ax.set_ylim(0, 70)
    for b, v in zip(bars, df["clutch_miss_rate"] * 100):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.1f}%", ha="center", va="bottom",
                color=TEXT_COLOR, fontsize=12, fontweight="bold")
    apply_style(ax)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["player_short"])
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "miss_rate.png", dpi=DPI, facecolor=BG_COLOR,
                edgecolor="none", bbox_inches="tight")
    plt.close()


def main():
    print("Generating Phase 5 charts...")
    chart1_year_over_year_scatter()
    print("  1. year_over_year_scatter.png")
    chart2_sample_size_bar()
    print("  2. sample_size_bar.png")
    chart3_clutch_vs_overall_ts()
    print("  3. clutch_vs_overall_ts.png")
    chart4_usage_spike()
    print("  4. usage_spike.png")
    chart5_ft_stripped()
    print("  5. ft_stripped.png")
    chart6_home_away_split()
    print("  6. home_away_split.png")
    chart7a_clutch_exception_three()
    print("  7a. clutch_exception_three.png")
    chart7_miss_rate()
    print("  7. miss_rate.png")
    chart8_ball_movement()
    print("  8. ball_movement_collapse.png")
    chart9_turnover_rate()
    print("  9. turnover_rate.png")
    chart10_hidden_clutch()
    print("  10. hidden_clutch.png")
    print(f"Done. All charts saved to {CHARTS_DIR}")


if __name__ == "__main__":
    main()
