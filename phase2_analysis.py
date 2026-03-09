"""
Phase 2 — Core Metrics & Tests 1-2
===================================
Reads merged_clutch_overall.csv (from Phase 1).
Computes:
  • Clutch TS% and Overall TS%
  • Test 1 — YoY clutch TS% consistency  (Pearson r)
  • Test 2 — Sample-size analysis         (clutch vs total possessions)

Outputs:
  outputs/phase2_results.json   — key numbers for downstream phases
  outputs/phase2_yoy_pairs.csv  — year-N / year-N+1 pairs for Chart 1
  outputs/phase2_sample_size.csv — per player-season possession counts
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
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


def ts_pct(pts, fga, fta):
    """True Shooting %: PTS / (2 * (FGA + 0.44 * FTA)). Returns NaN when denominator is 0."""
    denom = 2.0 * (fga + 0.44 * fta)
    return np.where(denom > 0, pts / denom, np.nan)


def main():
    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    merged_path = DATA_DIR / "merged_clutch_overall.csv"
    df = pd.read_csv(merged_path)
    log.info("Loaded %s  (%d rows, %d cols)", merged_path.name, *df.shape)

    # ------------------------------------------------------------------
    # 1. True Shooting %
    # ------------------------------------------------------------------
    df["clutch_ts"] = ts_pct(df["CLUTCH_PTS"], df["CLUTCH_FGA"], df["CLUTCH_FTA"])
    df["overall_ts"] = ts_pct(df["OVERALL_PTS"], df["OVERALL_FGA"], df["OVERALL_FTA"])

    valid = df["clutch_ts"].notna() & df["overall_ts"].notna()
    log.info("TS%% computed — %d valid rows (%.1f%% of total)",
             valid.sum(), 100.0 * valid.sum() / len(df))
    log.info("  Clutch TS%%  mean=%.3f  median=%.3f  std=%.3f",
             df.loc[valid, "clutch_ts"].mean(),
             df.loc[valid, "clutch_ts"].median(),
             df.loc[valid, "clutch_ts"].std())
    log.info("  Overall TS%% mean=%.3f  median=%.3f  std=%.3f",
             df.loc[valid, "overall_ts"].mean(),
             df.loc[valid, "overall_ts"].median(),
             df.loc[valid, "overall_ts"].std())

    # ------------------------------------------------------------------
    # 2. Test 1 — Year-over-Year clutch TS% consistency
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 1 — Year-over-Year Clutch TS%% Consistency")

    season_order = {s: i for i, s in enumerate(SEASONS)}
    df["_season_idx"] = df["SEASON"].map(season_order)

    pairs = []
    for pid, grp in df[valid].groupby("PLAYER_ID"):
        grp = grp.sort_values("_season_idx")
        rows = grp[["SEASON", "_season_idx", "clutch_ts", "PLAYER_NAME"]].values
        for i in range(len(rows) - 1):
            s1, idx1, ts1, name = rows[i]
            s2, idx2, ts2, _    = rows[i + 1]
            if idx2 - idx1 == 1:
                pairs.append(dict(
                    player_id=pid, player_name=name,
                    season_n=s1, season_n1=s2,
                    clutch_ts_n=ts1, clutch_ts_n1=ts2,
                ))

    pairs_df = pd.DataFrame(pairs)
    log.info("  Adjacent-season pairs: %d", len(pairs_df))

    r, p = stats.pearsonr(pairs_df["clutch_ts_n"], pairs_df["clutch_ts_n1"])
    log.info("  Pearson r = %.4f    p = %.4e", r, p)
    log.info("  Interpretation: %s",
             "weak (< 0.3) — clutch TS%% is NOT a repeatable skill" if abs(r) < 0.3
             else "moderate" if abs(r) < 0.5
             else "strong — clutch TS%% IS repeatable")

    pairs_csv = OUTPUT_DIR / "phase2_yoy_pairs.csv"
    pairs_df.to_csv(pairs_csv, index=False)
    log.info("  Saved %s  (%d rows)", pairs_csv.name, len(pairs_df))

    # Also compute per-player r (for players with >= 3 pairs → outlier detection later)
    player_rs = []
    for pid, grp in pairs_df.groupby("player_id"):
        if len(grp) >= 3:
            pr, pp = stats.pearsonr(grp["clutch_ts_n"], grp["clutch_ts_n1"])
            player_rs.append(dict(
                player_id=pid,
                player_name=grp["player_name"].iloc[0],
                n_pairs=len(grp),
                r=pr, p=pp,
            ))
    player_rs_df = pd.DataFrame(player_rs)
    if not player_rs_df.empty:
        outliers = player_rs_df[player_rs_df["r"] > 0.5]
        log.info("  Players with individual r > 0.5 (potential repeatable clutch):")
        if outliers.empty:
            log.info("    (none)")
        else:
            for _, row in outliers.iterrows():
                log.info("    %s  r=%.3f  pairs=%d", row["player_name"], row["r"], row["n_pairs"])
        player_rs_csv = OUTPUT_DIR / "phase2_player_yoy_r.csv"
        player_rs_df.to_csv(player_rs_csv, index=False)
        log.info("  Saved %s", player_rs_csv.name)

    # ------------------------------------------------------------------
    # 3. Test 2 — Sample Size
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 2 — Sample Size (Clutch vs Total Possessions)")

    # Possessions ≈ FGA + 0.44*FTA + TOV
    df["clutch_poss"]  = df["CLUTCH_FGA"]  + 0.44 * df["CLUTCH_FTA"]  + df["CLUTCH_TOV"]
    df["overall_poss"] = df["OVERALL_FGA"] + 0.44 * df["OVERALL_FTA"] + df["OVERALL_TOV"]
    df["poss_ratio"]   = np.where(df["overall_poss"] > 0,
                                  df["clutch_poss"] / df["overall_poss"], np.nan)

    avg_clutch  = df["clutch_poss"].mean()
    med_clutch  = df["clutch_poss"].median()
    avg_overall = df["overall_poss"].mean()
    med_overall = df["overall_poss"].median()
    avg_ratio   = df["poss_ratio"].mean()
    med_ratio   = df["poss_ratio"].median()

    log.info("  Per player-season (N=%d):", len(df))
    log.info("    Clutch possessions:  mean=%.1f  median=%.1f", avg_clutch, med_clutch)
    log.info("    Overall possessions: mean=%.1f  median=%.1f", avg_overall, med_overall)
    log.info("    Clutch/Overall ratio: mean=%.4f  median=%.4f  (%.2f%% / %.2f%%)",
             avg_ratio, med_ratio, avg_ratio * 100, med_ratio * 100)

    # Clutch minutes for context
    avg_clutch_min = df["CLUTCH_MIN"].mean()
    avg_clutch_gp  = df["CLUTCH_GP"].mean()
    log.info("    Avg clutch GP: %.1f   Avg clutch MIN: %.1f", avg_clutch_gp, avg_clutch_min)

    sample_csv = OUTPUT_DIR / "phase2_sample_size.csv"
    df[["PLAYER_ID", "PLAYER_NAME", "SEASON",
        "clutch_poss", "overall_poss", "poss_ratio",
        "CLUTCH_GP", "CLUTCH_MIN",
        "clutch_ts", "overall_ts"]].to_csv(sample_csv, index=False)
    log.info("  Saved %s", sample_csv.name)

    # ------------------------------------------------------------------
    # 4. Summary — save results JSON for downstream phases
    # ------------------------------------------------------------------
    results = {
        "test1_yoy": {
            "pearson_r": round(r, 4),
            "p_value": float(f"{p:.4e}"),
            "n_pairs": len(pairs_df),
            "interpretation": (
                "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.5 else "strong"
            ),
        },
        "test2_sample_size": {
            "avg_clutch_poss": round(avg_clutch, 1),
            "median_clutch_poss": round(med_clutch, 1),
            "avg_overall_poss": round(avg_overall, 1),
            "median_overall_poss": round(med_overall, 1),
            "avg_ratio": round(avg_ratio, 4),
            "median_ratio": round(med_ratio, 4),
            "avg_clutch_gp": round(avg_clutch_gp, 1),
            "avg_clutch_min": round(avg_clutch_min, 1),
        },
        "ts_summary": {
            "clutch_ts_mean": round(df.loc[valid, "clutch_ts"].mean(), 4),
            "clutch_ts_median": round(df.loc[valid, "clutch_ts"].median(), 4),
            "overall_ts_mean": round(df.loc[valid, "overall_ts"].mean(), 4),
            "overall_ts_median": round(df.loc[valid, "overall_ts"].median(), 4),
            "n_player_seasons": int(valid.sum()),
        },
    }

    results_path = OUTPUT_DIR / "phase2_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("=" * 60)
    log.info("PHASE 2 RESULTS saved to %s", results_path.name)
    log.info(json.dumps(results, indent=2))
    log.info("Phase 2 done.")


if __name__ == "__main__":
    main()
