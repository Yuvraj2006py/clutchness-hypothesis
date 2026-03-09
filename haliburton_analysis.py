"""
Tyrese Haliburton Clutch Deep Dive
==================================
Analyzes Haliburton's 2024-25 playoff run (described as "one of the clutchest")
against our clutch hypothesis framework.
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUTPUT = BASE / "outputs"

HALIBURTON_ID = 1630169


def ts_pct(pts, fga, fta):
    denom = 2.0 * (fga + 0.44 * fta)
    return pts / denom if denom > 0 else np.nan


def main():
    # Load data
    reg = pd.read_csv(DATA / "merged_clutch_overall.csv")
    play = pd.read_csv(DATA / "merged_clutch_overall_playoffs.csv")

    h_reg = reg[reg["PLAYER_ID"] == HALIBURTON_ID]
    h_play = play[play["PLAYER_ID"] == HALIBURTON_ID]

    print("=" * 70)
    print("TYRESE HALIBURTON — Clutch Analysis")
    print("=" * 70)

    # 2024-25 Regular Season
    r24 = h_reg[h_reg["SEASON"] == "2024-25"].iloc[0]
    r_clutch_ts = ts_pct(r24["CLUTCH_PTS"], r24["CLUTCH_FGA"], r24["CLUTCH_FTA"])
    r_overall_ts = ts_pct(r24["OVERALL_PTS"], r24["OVERALL_FGA"], r24["OVERALL_FTA"])
    r_diff = r_clutch_ts - r_overall_ts
    print("\n2024-25 REGULAR SEASON")
    print(f"  Clutch:  {r_clutch_ts:.1%} TS%  ({r24['CLUTCH_PTS']} pts, {r24['CLUTCH_FGA']} FGA, {r24['CLUTCH_FTA']} FTA)")
    print(f"  Overall: {r_overall_ts:.1%} TS%  ({r24['OVERALL_PTS']} pts)")
    print(f"  Diff:    {r_diff:+.1%}  {'BETTER in clutch' if r_diff > 0.005 else 'worse in clutch'}")
    print(f"  Clutch GP: {r24['CLUTCH_GP']}  |  Clutch poss: ~{r24['CLUTCH_FGA'] + 0.44*r24['CLUTCH_FTA'] + r24['CLUTCH_TOV']:.0f}")

    # 2024-25 Playoffs
    p24 = h_play[h_play["SEASON"] == "2024-25"].iloc[0]
    p_clutch_ts = ts_pct(p24["CLUTCH_PTS"], p24["CLUTCH_FGA"], p24["CLUTCH_FTA"])
    p_overall_ts = ts_pct(p24["OVERALL_PTS"], p24["OVERALL_FGA"], p24["OVERALL_FTA"])
    p_diff = p_clutch_ts - p_overall_ts
    p_poss = p24["CLUTCH_FGA"] + 0.44 * p24["CLUTCH_FTA"] + p24["CLUTCH_TOV"]
    print("\n2024-25 PLAYOFFS (the 'clutchest' run)")
    print(f"  Clutch:  {p_clutch_ts:.1%} TS%  ({p24['CLUTCH_PTS']} pts, {p24['CLUTCH_FGA']} FGA, {p24['CLUTCH_FTA']} FTA)")
    print(f"  Overall: {p_overall_ts:.1%} TS%  ({p24['OVERALL_PTS']} pts)")
    print(f"  Diff:    {p_diff:+.1%}  {'BETTER in clutch' if p_diff > 0.005 else 'worse in clutch'}")
    print(f"  Clutch GP: {p24['CLUTCH_GP']}  |  Clutch poss: ~{p_poss:.0f}")

    # 2023-24 Playoffs (contrast)
    if "2023-24" in h_play["SEASON"].values:
        p23 = h_play[h_play["SEASON"] == "2023-24"].iloc[0]
        p23_clutch = ts_pct(p23["CLUTCH_PTS"], p23["CLUTCH_FGA"], p23["CLUTCH_FTA"])
        p23_overall = ts_pct(p23["OVERALL_PTS"], p23["OVERALL_FGA"], p23["OVERALL_FTA"])
        print("\n2023-24 PLAYOFFS (for contrast)")
        print(f"  Clutch:  {p23_clutch:.1%} TS%  ({p23['CLUTCH_PTS']} pts, {p23['CLUTCH_FGA']} FGA)")
        print(f"  Overall: {p23_overall:.1%} TS%")
        print(f"  Diff:    {p23_clutch - p23_overall:+.1%}  (tiny sample: {p23['CLUTCH_GP']} GP)")

    # Career regular-season clutch
    r_all = h_reg.groupby("PLAYER_ID").agg(
        clutch_pts=("CLUTCH_PTS", "sum"),
        clutch_fga=("CLUTCH_FGA", "sum"),
        clutch_fta=("CLUTCH_FTA", "sum"),
        overall_pts=("OVERALL_PTS", "sum"),
        overall_fga=("OVERALL_FGA", "sum"),
        overall_fta=("OVERALL_FTA", "sum"),
    ).iloc[0]
    r_career_clutch = ts_pct(r_all["clutch_pts"], r_all["clutch_fga"], r_all["clutch_fta"])
    r_career_overall = ts_pct(r_all["overall_pts"], r_all["overall_fga"], r_all["overall_fta"])
    print("\nCAREER REGULAR SEASON (all seasons)")
    print(f"  Clutch:  {r_career_clutch:.1%}  |  Overall: {r_career_overall:.1%}  |  Diff: {r_career_clutch - r_career_overall:+.1%}")

    # YoY playoff pair
    pairs = pd.read_csv(OUTPUT / "playoff_yoy_pairs.csv")
    h_pairs = pairs[pairs["player_id"] == HALIBURTON_ID]
    if not h_pairs.empty:
        print("\nPLAYOFF YoY PAIR (2023-24 -> 2024-25)")
        for _, row in h_pairs.iterrows():
            print(f"  {row['season_n']} clutch TS%: {row['clutch_ts_n']:.1%}")
            print(f"  {row['season_n1']} clutch TS%: {row['clutch_ts_n1']:.1%}")
            print(f"  (One pair — can't infer repeatability)")

    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("""
Haliburton's 2024-25 playoff clutch run was genuinely strong by the numbers:
  • 59.8% clutch TS% vs 58.1% overall (+1.7 pp) — he shot BETTER in clutch
  • 11 clutch games, ~32 possessions — small but not trivial
  • Contrast: 2023-24 playoffs he was 32.8% clutch (5 GP, 15 FGA) — noise

The hypothesis isn't "nobody ever shoots well in clutch." It's that clutch TS%
doesn't *repeat* year-over-year. Haliburton had one great playoff clutch run.
We'd need multiple seasons of playoff clutch data to say it's a skill — and
he only has 2 playoff years, with wildly different results (32.8% vs 59.8%).

So: 2024-25 was legitimately clutch by the numbers. Whether it's repeatable?
The data can't tell us yet. He's a good case study for "one run can build
a narrative" — if he regresses next playoffs, we'll forget this one.
""")


if __name__ == "__main__":
    main()
