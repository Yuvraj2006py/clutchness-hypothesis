"""
Shot Mix (3PA Rate) & Turnover Rate Analysis
============================================
Tests whether stars change shot selection or turnover rate in clutch:
  • 3PA rate = FG3A / FGA (share of shots that are 3s)
  • TOV rate = TOV / possessions (possessions = FGA + 0.44*FTA + TOV)

Outputs:
  outputs/shot_mix_3pa_rate.csv
  outputs/turnover_rate_clutch.csv
  outputs/shot_mix_tov_summary.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def safe_name(s):
    return str(s).replace("\u010d", "c").replace("\u0107", "c").replace("\u0106", "C")


REPUTATION_IDS = {
    2544, 203081, 202695, 202681, 202710, 101108, 201939,
    1629029, 1626164, 202331, 201142, 203507, 1628369,
    1628378, 1628983, 1629027, 1629630, 203954, 1630162,
    1628368, 201566, 203999,
}


def main():
    df = pd.read_csv(DATA_DIR / "merged_clutch_overall.csv")

    # Aggregate by player
    agg = df.groupby("PLAYER_ID").agg(
        player_name=("PLAYER_NAME", "first"),
        clutch_fga=("CLUTCH_FGA", "sum"),
        clutch_fg3a=("CLUTCH_FG3A", "sum"),
        clutch_fg3m=("CLUTCH_FG3M", "sum"),
        clutch_fg3_pct=("CLUTCH_FG3_PCT", "mean"),  # weighted avg would be better but mean is ok
        overall_fga=("OVERALL_FGA", "sum"),
        overall_fg3a=("OVERALL_FG3A", "sum"),
        overall_fg3m=("OVERALL_FG3M", "sum"),
        overall_fg3_pct=("OVERALL_FG3_PCT", "mean"),
        clutch_tov=("CLUTCH_TOV", "sum"),
        clutch_fta=("CLUTCH_FTA", "sum"),
        overall_tov=("OVERALL_TOV", "sum"),
        overall_fta=("OVERALL_FTA", "sum"),
        clutch_pts=("CLUTCH_PTS", "sum"),
        overall_pts=("OVERALL_PTS", "sum"),
        clutch_gp=("CLUTCH_GP", "sum"),
        seasons=("SEASON", "count"),
    ).reset_index()

    # ------------------------------------------------------------------
    # 1. Shot mix (3PA rate)
    # ------------------------------------------------------------------
    agg["clutch_3pa_rate"]  = np.where(agg["clutch_fga"] > 0,
                                        agg["clutch_fg3a"] / agg["clutch_fga"], np.nan)
    agg["overall_3pa_rate"] = np.where(agg["overall_fga"] > 0,
                                        agg["overall_fg3a"] / agg["overall_fga"], np.nan)
    agg["3pa_rate_diff"]    = agg["clutch_3pa_rate"] - agg["overall_3pa_rate"]

    # True 3P% from makes/attempts (not the API's FG3_PCT which can have quirks)
    agg["clutch_3p_pct"]  = np.where(agg["clutch_fg3a"] > 0,
                                      agg["clutch_fg3m"] / agg["clutch_fg3a"], np.nan)
    agg["overall_3p_pct"] = np.where(agg["overall_fg3a"] > 0,
                                      agg["overall_fg3m"] / agg["overall_fg3a"], np.nan)
    agg["3p_pct_diff"]    = agg["clutch_3p_pct"] - agg["overall_3p_pct"]

    shot_mix = agg[["PLAYER_ID", "player_name", "seasons", "clutch_gp",
                    "clutch_3pa_rate", "overall_3pa_rate", "3pa_rate_diff",
                    "clutch_3p_pct", "overall_3p_pct", "3p_pct_diff"]].copy()
    shot_mix = shot_mix.sort_values("3pa_rate_diff", ascending=False)

    rep_shot = shot_mix[shot_mix["PLAYER_ID"].isin(REPUTATION_IDS)].copy()
    rep_shot = rep_shot.sort_values("3pa_rate_diff", ascending=False)

    shot_mix.to_csv(OUTPUT_DIR / "shot_mix_3pa_rate.csv", index=False)

    # ------------------------------------------------------------------
    # 2. Turnover rate
    # ------------------------------------------------------------------
    agg["clutch_poss"]   = agg["clutch_fga"] + 0.44 * agg["clutch_fta"] + agg["clutch_tov"]
    agg["overall_poss"]  = agg["overall_fga"] + 0.44 * agg["overall_fta"] + agg["overall_tov"]
    agg["clutch_tov_rate"]  = np.where(agg["clutch_poss"] > 0,
                                        agg["clutch_tov"] / agg["clutch_poss"], np.nan)
    agg["overall_tov_rate"] = np.where(agg["overall_poss"] > 0,
                                        agg["overall_tov"] / agg["overall_poss"], np.nan)
    agg["tov_rate_diff"]    = agg["clutch_tov_rate"] - agg["overall_tov_rate"]

    tov = agg[["PLAYER_ID", "player_name", "seasons", "clutch_gp",
               "clutch_tov", "overall_tov",
               "clutch_tov_rate", "overall_tov_rate", "tov_rate_diff"]].copy()
    tov = tov.sort_values("tov_rate_diff", ascending=False)

    rep_tov = tov[tov["PLAYER_ID"].isin(REPUTATION_IDS)].copy()
    rep_tov = rep_tov.sort_values("tov_rate_diff", ascending=False)

    tov.to_csv(OUTPUT_DIR / "turnover_rate_clutch.csv", index=False)

    # ------------------------------------------------------------------
    # Summary for reputation players
    # ------------------------------------------------------------------
    print("=" * 65)
    print("SHOT MIX (3PA RATE) — Clutch vs Overall")
    print("=" * 65)
    print("  Positive diff = more 3s in clutch (harder shots, more variance)")
    print()
    print("  %-24s  %8s  %8s  %8s  %8s" % ("Player", "Clu 3PA%", "Ovr 3PA%", "Diff", "3P% Diff"))
    print("  " + "-" * 60)
    for _, r in rep_shot.iterrows():
        pct = r["3p_pct_diff"] * 100 if pd.notna(r["3p_pct_diff"]) else 0
        print(f"  {safe_name(r['player_name']):24}  {r['clutch_3pa_rate']*100:7.1f}%  {r['overall_3pa_rate']*100:7.1f}%  {r['3pa_rate_diff']*100:+7.1f}%  {pct:+6.1f}pp")

    avg_3pa_diff = rep_shot["3pa_rate_diff"].mean() * 100
    n_more_3s = (rep_shot["3pa_rate_diff"] > 0.01).sum()
    n_fewer_3s = (rep_shot["3pa_rate_diff"] < -0.01).sum()
    print()
    print(f"  League-wide (reputation): avg 3PA rate diff = {avg_3pa_diff:+.1f}%")
    print(f"  More 3s in clutch: {n_more_3s} players | Fewer 3s: {n_fewer_3s} players")
    print()

    print("=" * 65)
    print("TURNOVER RATE — Clutch vs Overall")
    print("=" * 65)
    print("  Positive diff = more turnovers in clutch (pressure hurts)")
    print()
    print("  %-24s  %8s  %8s  %8s" % ("Player", "Clu TOV%", "Ovr TOV%", "Diff"))
    print("  " + "-" * 55)
    for _, r in rep_tov.iterrows():
        print(f"  {safe_name(r['player_name']):24}  {r['clutch_tov_rate']*100:7.1f}%  {r['overall_tov_rate']*100:7.1f}%  {r['tov_rate_diff']*100:+7.1f}%")

    avg_tov_diff = rep_tov["tov_rate_diff"].mean() * 100
    n_more_tov = (rep_tov["tov_rate_diff"] > 0.005).sum()
    n_fewer_tov = (rep_tov["tov_rate_diff"] < -0.005).sum()
    print()
    print(f"  League-wide (reputation): avg TOV rate diff = {avg_tov_diff:+.1f}%")
    print(f"  More TOV in clutch: {n_more_tov} players | Fewer TOV: {n_fewer_tov} players")
    print()

    # ------------------------------------------------------------------
    # Save summary JSON
    # ------------------------------------------------------------------
    summary = {
        "shot_mix": {
            "avg_3pa_rate_diff_pct": round(avg_3pa_diff, 2),
            "n_more_3s_in_clutch": int(n_more_3s),
            "n_fewer_3s_in_clutch": int(n_fewer_3s),
            "interpretation": (
                "Stars shoot MORE 3s in clutch — harder shots explain some TS% drop"
                if avg_3pa_diff > 1 else
                "Stars shoot FEWER 3s in clutch — shot mix doesn't explain TS% drop"
                if avg_3pa_diff < -1 else
                "Shot mix roughly similar — 3PA rate change doesn't explain TS% drop"
            ),
        },
        "turnover_rate": {
            "avg_tov_rate_diff_pct": round(avg_tov_diff, 2),
            "n_more_tov_in_clutch": int(n_more_tov),
            "n_fewer_tov_in_clutch": int(n_fewer_tov),
            "interpretation": (
                "Stars turn it over MORE in clutch — pressure hurts beyond shooting"
                if avg_tov_diff > 0.5 else
                "Stars turn it over LESS in clutch — no added pressure effect"
                if avg_tov_diff < -0.5 else
                "TOV rate roughly similar — no strong pressure effect on ball security"
            ),
        },
    }

    with open(OUTPUT_DIR / "shot_mix_tov_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("Saved: shot_mix_3pa_rate.csv, turnover_rate_clutch.csv, shot_mix_tov_summary.json")


if __name__ == "__main__":
    main()
