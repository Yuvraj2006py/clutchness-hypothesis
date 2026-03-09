"""
Hidden Clutch Analysis
======================
Identifies players who are "clutch by the numbers" but lack the narrative:
  • Non-reputation players with r > 0.5 (repeatable clutch)
  • Non-reputation players with clutch TS% > overall TS% (better in clutch)
  • Sample-size sanity check
  • Reputation vs. stats 2x2 matrix

Outputs:
  outputs/hidden_clutch_repeatable.csv   — high r, not reputation
  outputs/hidden_clutch_better.csv       — clutch > overall, not reputation
  outputs/hidden_clutch_matrix.json      — 2x2 summary for writeup
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

REPUTATION_IDS = {
    2544, 203081, 202695, 202681, 202710, 101108, 201939,
    1629029, 1626164, 202331, 201142, 203507, 1628369,
    1628378, 1628983, 1629027, 1629630, 203954, 1630162,
    1628368, 201566, 203999,
}


def ts_pct(pts, fga, fta):
    denom = 2.0 * (fga + 0.44 * fta)
    return np.where(denom > 0, pts / denom, np.nan)


def main():
    # ------------------------------------------------------------------
    # 1. Hidden repeatable (r > 0.5, non-reputation)
    # ------------------------------------------------------------------
    outliers = pd.read_csv(OUTPUT_DIR / "phase4_outliers.csv")
    hidden_repeatable = outliers[
        (outliers["is_reputation"] == False) &
        (outliers["n_pairs"] >= 4)  # avoid 3-pair noise
    ].copy()
    hidden_repeatable = hidden_repeatable.sort_values("r", ascending=False)

    hidden_repeatable.to_csv(OUTPUT_DIR / "hidden_clutch_repeatable.csv", index=False)

    # ------------------------------------------------------------------
    # 2. Hidden "better in clutch" (clutch TS% > overall, non-reputation)
    # ------------------------------------------------------------------
    merged = pd.read_csv(DATA_DIR / "merged_clutch_overall.csv")
    merged["clutch_ts"]  = ts_pct(merged["CLUTCH_PTS"], merged["CLUTCH_FGA"], merged["CLUTCH_FTA"])
    merged["overall_ts"] = ts_pct(merged["OVERALL_PTS"], merged["OVERALL_FGA"], merged["OVERALL_FTA"])

    agg = merged.groupby("PLAYER_ID").agg(
        player_name=("PLAYER_NAME", "first"),
        clutch_pts=("CLUTCH_PTS", "sum"),
        clutch_fga=("CLUTCH_FGA", "sum"),
        clutch_fta=("CLUTCH_FTA", "sum"),
        overall_pts=("OVERALL_PTS", "sum"),
        overall_fga=("OVERALL_FGA", "sum"),
        overall_fta=("OVERALL_FTA", "sum"),
        clutch_gp=("CLUTCH_GP", "sum"),
        seasons=("SEASON", "count"),
    ).reset_index()

    agg["clutch_ts"]  = ts_pct(agg["clutch_pts"], agg["clutch_fga"], agg["clutch_fta"])
    agg["overall_ts"] = ts_pct(agg["overall_pts"], agg["overall_fga"], agg["overall_fta"])
    agg["ts_diff"]    = agg["clutch_ts"] - agg["overall_ts"]

    # Non-reputation, clutch better by at least 0.02, min 40 clutch games
    hidden_better = agg[
        (~agg["PLAYER_ID"].isin(REPUTATION_IDS)) &
        (agg["ts_diff"] >= 0.02) &
        (agg["clutch_gp"] >= 40)
    ].copy()
    hidden_better = hidden_better.sort_values("ts_diff", ascending=False)

    hidden_better.to_csv(OUTPUT_DIR / "hidden_clutch_better.csv", index=False)

    # ------------------------------------------------------------------
    # 3. Build 2x2 matrix (counts for writeup)
    # ------------------------------------------------------------------
    rep_ts = merged[merged["PLAYER_ID"].isin(REPUTATION_IDS)]
    rep_agg = rep_ts.groupby("PLAYER_ID").agg(
        clutch_pts=("CLUTCH_PTS", "sum"),
        clutch_fga=("CLUTCH_FGA", "sum"),
        clutch_fta=("CLUTCH_FTA", "sum"),
        overall_pts=("OVERALL_PTS", "sum"),
        overall_fga=("OVERALL_FGA", "sum"),
        overall_fta=("OVERALL_FTA", "sum"),
        clutch_gp=("CLUTCH_GP", "sum"),
    ).reset_index()
    rep_agg["clutch_ts"]  = ts_pct(rep_agg["clutch_pts"], rep_agg["clutch_fga"], rep_agg["clutch_fta"])
    rep_agg["overall_ts"] = ts_pct(rep_agg["overall_pts"], rep_agg["overall_fga"], rep_agg["overall_fta"])
    rep_agg["ts_diff"]    = rep_agg["clutch_ts"] - rep_agg["overall_ts"]

    rep_better = (rep_agg["ts_diff"] >= 0.02).sum()
    rep_worse  = (rep_agg["ts_diff"] < -0.02).sum()
    rep_same   = len(rep_agg) - rep_better - rep_worse

    nonrep_better = len(hidden_better)
    nonrep_total  = len(agg[~agg["PLAYER_ID"].isin(REPUTATION_IDS)])
    nonrep_worse  = len(agg[
        (~agg["PLAYER_ID"].isin(REPUTATION_IDS)) &
        (agg["ts_diff"] <= -0.02) &
        (agg["clutch_gp"] >= 40)
    ])

    matrix = {
        "reputation_better": int(rep_better),
        "reputation_worse": int(rep_worse),
        "reputation_same": int(rep_same),
        "reputation_total": len(rep_agg),
        "non_reputation_better": int(nonrep_better),
        "non_reputation_worse": int(nonrep_worse),
        "non_reputation_total": int(nonrep_total),
        "hidden_repeatable_count": len(hidden_repeatable),
        "hidden_repeatable_top5": hidden_repeatable.head(5)[["player_name", "r", "n_pairs"]].to_dict("records"),
        "hidden_better_top5": hidden_better.head(5)[["player_name", "ts_diff", "clutch_gp"]].to_dict("records"),
    }

    with open(OUTPUT_DIR / "hidden_clutch_matrix.json", "w") as f:
        json.dump(matrix, f, indent=2)

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    print("Hidden Clutch Analysis")
    print("=" * 50)
    print(f"Non-reputation players with r > 0.5 (n_pairs >= 4): {len(hidden_repeatable)}")
    print("Top 5:")
    for _, r in hidden_repeatable.head(5).iterrows():
        print(f"  {r['player_name']:25} r={r['r']:.3f}  pairs={int(r['n_pairs'])}")
    print()
    print(f"Non-reputation players with clutch > overall (ts_diff >= 0.02, 40+ GP): {len(hidden_better)}")
    print("Top 5:")
    for _, r in hidden_better.head(5).iterrows():
        print(f"  {r['player_name']:25} diff={r['ts_diff']:+.3f}  clutch_GP={int(r['clutch_gp'])}")
    print()
    print("2x2 Matrix (clutch better vs worse):")
    print(f"  Reputation:    {rep_better} better, {rep_worse} worse")
    print(f"  Non-reputation: {nonrep_better} better, {nonrep_worse} worse (min 40 GP)")
    print()
    print("Saved: hidden_clutch_repeatable.csv, hidden_clutch_better.csv, hidden_clutch_matrix.json")


if __name__ == "__main__":
    main()
