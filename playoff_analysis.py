"""
Playoff Analysis — Clutch Metrics (Phase 2 + Phase 3 style)
============================================================
Reads merged_clutch_overall_playoffs.csv.
Computes:
  • TS% summary (clutch vs overall)
  • Test 1 — YoY clutch TS% consistency (Pearson r)
  • Test 2 — Sample size (clutch possessions, ratio)
  • Test 3 — Clutch vs Overall TS% for reputation players
  • Test 4 — FT-stripped clutch efficiency (reputation players)

Note: No usage spike (Test 5) — playoff team totals not pulled.
"""

import json
import logging
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25",
]

REPUTATION_PLAYERS = {
    2544: "LeBron James",
    203081: "Damian Lillard",
    202695: "Kawhi Leonard",
    202681: "Kyrie Irving",
    202710: "Jimmy Butler",
    101108: "Chris Paul",
    201939: "Stephen Curry",
    1629029: "Luka Doncic",
    1626164: "Devin Booker",
    202331: "Paul George",
    201142: "Kevin Durant",
    203507: "Giannis Antetokounmpo",
    1628369: "Jayson Tatum",
    1628378: "Donovan Mitchell",
    1628983: "Shai Gilgeous-Alexander",
    1629027: "Trae Young",
    1629630: "Ja Morant",
    203954: "Joel Embiid",
    1630162: "Anthony Edwards",
    1628368: "De'Aaron Fox",
    201566: "Russell Westbrook",
    203999: "Nikola Jokic",
}


def ts_pct(pts, fga, fta):
    denom = 2.0 * (fga + 0.44 * fta)
    return np.where(denom > 0, pts / denom, np.nan)


def ft_stripped_eff(fgm, fg3m, fga):
    pts_fg = 2 * (fgm - fg3m) + 3 * fg3m
    denom = 2.0 * fga
    return np.where(denom > 0, pts_fg / denom, np.nan)


def main():
    merged_path = DATA_DIR / "merged_clutch_overall_playoffs.csv"
    df = pd.read_csv(merged_path)
    log.info("Loaded %s  (%d rows)", merged_path.name, len(df))

    # ------------------------------------------------------------------
    # 1. TS%
    # ------------------------------------------------------------------
    df["clutch_ts"] = ts_pct(df["CLUTCH_PTS"], df["CLUTCH_FGA"], df["CLUTCH_FTA"])
    df["overall_ts"] = ts_pct(df["OVERALL_PTS"], df["OVERALL_FGA"], df["OVERALL_FTA"])
    valid = df["clutch_ts"].notna() & df["overall_ts"].notna()
    log.info("TS%% — %d valid rows", valid.sum())
    log.info("  Clutch TS%%  mean=%.3f  median=%.3f",
             df.loc[valid, "clutch_ts"].mean(), df.loc[valid, "clutch_ts"].median())
    log.info("  Overall TS%% mean=%.3f  median=%.3f",
             df.loc[valid, "overall_ts"].mean(), df.loc[valid, "overall_ts"].median())

    # ------------------------------------------------------------------
    # 2. Test 1 — YoY clutch TS% consistency
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 1 — Year-over-Year Clutch TS%% (Playoffs)")

    season_order = {s: i for i, s in enumerate(SEASONS)}
    df["_season_idx"] = df["SEASON"].map(season_order)

    pairs = []
    for pid, grp in df[valid].groupby("PLAYER_ID"):
        grp = grp.sort_values("_season_idx")
        rows = grp[["SEASON", "_season_idx", "clutch_ts", "PLAYER_NAME"]].values
        for i in range(len(rows) - 1):
            s1, idx1, ts1, name = rows[i]
            s2, idx2, ts2, _ = rows[i + 1]
            if idx2 - idx1 == 1:
                pairs.append(dict(
                    player_id=pid, player_name=name,
                    season_n=s1, season_n1=s2,
                    clutch_ts_n=ts1, clutch_ts_n1=ts2,
                ))

    pairs_df = pd.DataFrame(pairs)
    log.info("  Adjacent-season pairs: %d", len(pairs_df))

    if len(pairs_df) >= 3:
        r_raw, p_raw = stats.pearsonr(pairs_df["clutch_ts_n"], pairs_df["clutch_ts_n1"])
        r, p = float(r_raw), float(p_raw)
        log.info("  Pearson r = %.4f    p = %.4e", r, p)
        interp = "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.5 else "strong"
        log.info("  Interpretation: %s", interp)
    else:
        r, p = float("nan"), float("nan")
        log.info("  Too few pairs (%d) for Pearson r", len(pairs_df))

    pairs_df.to_csv(OUTPUT_DIR / "playoff_yoy_pairs.csv", index=False)
    log.info("  Saved playoff_yoy_pairs.csv")

    # ------------------------------------------------------------------
    # 3. Test 2 — Sample size
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 2 — Sample Size (Playoffs)")

    df["clutch_poss"] = df["CLUTCH_FGA"] + 0.44 * df["CLUTCH_FTA"] + df["CLUTCH_TOV"]
    df["overall_poss"] = df["OVERALL_FGA"] + 0.44 * df["OVERALL_FTA"] + df["OVERALL_TOV"]
    df["poss_ratio"] = np.where(df["overall_poss"] > 0,
                                df["clutch_poss"] / df["overall_poss"], np.nan)

    avg_clutch = df["clutch_poss"].mean()
    avg_ratio = df["poss_ratio"].mean()
    avg_gp = df["CLUTCH_GP"].mean()
    avg_min = df["CLUTCH_MIN"].mean()

    log.info("  Clutch poss: mean=%.1f  |  Clutch/Overall ratio: %.2f%%",
             avg_clutch, avg_ratio * 100)
    log.info("  Avg clutch GP: %.1f   Avg clutch MIN: %.1f", avg_gp, avg_min)

    df[["PLAYER_ID", "PLAYER_NAME", "SEASON", "clutch_poss", "overall_poss",
        "poss_ratio", "CLUTCH_GP", "CLUTCH_MIN", "clutch_ts", "overall_ts"]].to_csv(
        OUTPUT_DIR / "playoff_sample_size.csv", index=False)
    log.info("  Saved playoff_sample_size.csv")

    # ------------------------------------------------------------------
    # 4. Test 3 & 4 — Reputation players
    # ------------------------------------------------------------------
    rep_ids = set(REPUTATION_PLAYERS.keys())
    rep = df[df["PLAYER_ID"].isin(rep_ids)].copy()
    log.info("=" * 60)
    log.info("Reputation players in playoffs: %d player-seasons", len(rep))

    if rep.empty:
        log.warning("  No reputation players found in playoff data.")
        t3 = pd.DataFrame()
        t4 = pd.DataFrame()
    else:
        # Test 3 — Clutch vs Overall TS%
        t3 = (
            rep.groupby("PLAYER_ID")
            .agg(
                player_name=("PLAYER_NAME", "first"),
                seasons=("SEASON", "count"),
                clutch_pts=("CLUTCH_PTS", "sum"),
                clutch_fga=("CLUTCH_FGA", "sum"),
                clutch_fta=("CLUTCH_FTA", "sum"),
                overall_pts=("OVERALL_PTS", "sum"),
                overall_fga=("OVERALL_FGA", "sum"),
                overall_fta=("OVERALL_FTA", "sum"),
            )
            .reset_index()
        )
        t3["clutch_ts"] = ts_pct(t3["clutch_pts"], t3["clutch_fga"], t3["clutch_fta"])
        t3["overall_ts"] = ts_pct(t3["overall_pts"], t3["overall_fga"], t3["overall_fta"])
        t3["ts_diff"] = t3["clutch_ts"] - t3["overall_ts"]
        t3 = t3.sort_values("ts_diff")

        def safe_name(s):
            return str(s).encode("ascii", "replace").decode("ascii") if s else ""

        log.info("TEST 3 — Clutch vs Overall TS%% (playoffs)")
        for _, row in t3.iterrows():
            verdict = "BETTER" if row["ts_diff"] > 0.005 else "WORSE" if row["ts_diff"] < -0.005 else "~same"
            log.info("  %-20s  clutch=%.3f  overall=%.3f  diff=%+.3f  %s",
                     safe_name(row["player_name"]), row["clutch_ts"], row["overall_ts"], row["ts_diff"], verdict)

        t3[["PLAYER_ID", "player_name", "seasons", "clutch_ts", "overall_ts", "ts_diff"]].to_csv(
            OUTPUT_DIR / "playoff_reputation_ts.csv", index=False)

        # Test 4 — FT-stripped
        t4 = (
            rep.groupby("PLAYER_ID")
            .agg(
                player_name=("PLAYER_NAME", "first"),
                clutch_fgm=("CLUTCH_FGM", "sum"),
                clutch_fg3m=("CLUTCH_FG3M", "sum"),
                clutch_fga=("CLUTCH_FGA", "sum"),
                clutch_fta=("CLUTCH_FTA", "sum"),
                clutch_ftm=("CLUTCH_FTM", "sum"),
                clutch_pts=("CLUTCH_PTS", "sum"),
            )
            .reset_index()
        )
        t4["clutch_ts"] = ts_pct(t4["clutch_pts"], t4["clutch_fga"], t4["clutch_fta"])
        t4["ft_stripped_eff"] = ft_stripped_eff(t4["clutch_fgm"], t4["clutch_fg3m"], t4["clutch_fga"])
        t4["ft_boost"] = t4["clutch_ts"] - t4["ft_stripped_eff"]
        t4["ft_share_of_pts"] = np.where(t4["clutch_pts"] > 0,
                                         t4["clutch_ftm"] / t4["clutch_pts"], np.nan)
        t4 = t4.sort_values("ft_boost", ascending=False)

        log.info("TEST 4 — FT-stripped clutch (playoffs)")
        for _, row in t4.iterrows():
            log.info("  %-20s  clutch=%.3f  ft_strip=%.3f  ft_boost=%+.3f",
                     safe_name(row["player_name"]), row["clutch_ts"], row["ft_stripped_eff"], row["ft_boost"])

        t4.to_csv(OUTPUT_DIR / "playoff_reputation_ft_stripped.csv", index=False)

    # ------------------------------------------------------------------
    # 5. Summary JSON
    # ------------------------------------------------------------------
    results = {
        "test1_yoy": {
            "pearson_r": round(r, 4) if not math.isnan(r) else None,
            "p_value": float(f"{p:.4e}") if not math.isnan(p) else None,
            "n_pairs": len(pairs_df),
            "interpretation": (
                "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.5 else "strong"
            ) if not math.isnan(r) and len(pairs_df) >= 3 else None,
        },
        "test2_sample_size": {
            "avg_clutch_poss": round(avg_clutch, 1),
            "avg_ratio": round(avg_ratio, 4),
            "avg_clutch_gp": round(avg_gp, 1),
            "avg_clutch_min": round(avg_min, 1),
        },
        "ts_summary": {
            "clutch_ts_mean": round(df.loc[valid, "clutch_ts"].mean(), 4),
            "overall_ts_mean": round(df.loc[valid, "overall_ts"].mean(), 4),
            "n_player_seasons": int(valid.sum()),
        },
    }

    results_path = OUTPUT_DIR / "playoff_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("=" * 60)
    log.info("PLAYOFF RESULTS saved to %s", results_path.name)
    log.info(json.dumps(results, indent=2))
    log.info("Playoff analysis done.")


if __name__ == "__main__":
    main()
