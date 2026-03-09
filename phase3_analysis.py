"""
Phase 3 — Reputation Players & Tests 3, 4, 5
=============================================
Reads merged_clutch_overall.csv + team totals.
Runs:
  • Test 3 — Clutch TS% vs Overall TS% for 22 reputation players
  • Test 4 — FT-stripped clutch efficiency
  • Test 5 — Usage spike (clutch vs overall share of team possessions)

Outputs:
  outputs/phase3_test3_ts_comparison.csv
  outputs/phase3_test4_ft_stripped.csv
  outputs/phase3_test5_usage_spike.csv
  outputs/phase3_reputation_seasons.csv   (full per-season detail)
  outputs/phase3_results.json
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

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

REPUTATION_PLAYERS = {
    # --- Original 10 ("clutch gods" + established) ---
    2544:    "LeBron James",
    203081:  "Damian Lillard",
    202695:  "Kawhi Leonard",
    202681:  "Kyrie Irving",
    202710:  "Jimmy Butler",
    101108:  "Chris Paul",
    201939:  "Stephen Curry",
    1629029: "Luka Doncic",
    1626164: "Devin Booker",
    202331:  "Paul George",
    # --- New additions ---
    201142:  "Kevin Durant",
    203507:  "Giannis Antetokounmpo",
    1628369: "Jayson Tatum",
    1628378: "Donovan Mitchell",
    1628983: "Shai Gilgeous-Alexander",
    1629027: "Trae Young",
    1629630: "Ja Morant",
    203954:  "Joel Embiid",
    1630162: "Anthony Edwards",
    1628368: "De'Aaron Fox",
    # --- Contrast / debated ---
    201566:  "Russell Westbrook",
    203999:  "Nikola Jokic",
}


def ts_pct(pts, fga, fta):
    denom = 2.0 * (fga + 0.44 * fta)
    return np.where(denom > 0, pts / denom, np.nan)


def ft_stripped_eff(fgm, fg3m, fga):
    """Points from field goals only / (2 * FGA). Removes FT contribution."""
    pts_fg = 2 * (fgm - fg3m) + 3 * fg3m
    denom = 2.0 * fga
    return np.where(denom > 0, pts_fg / denom, np.nan)


def load_team_totals(kind: str) -> pd.DataFrame:
    """Load all 8 season files for team_overall or team_clutch."""
    frames = []
    for s in SEASONS:
        path = DATA_DIR / f"team_{kind}_{s}.csv"
        if path.exists():
            t = pd.read_csv(path)
            if "SEASON" not in t.columns:
                t["SEASON"] = s
            frames.append(t)
    return pd.concat(frames, ignore_index=True)


def main():
    # ------------------------------------------------------------------
    # Load merged player data
    # ------------------------------------------------------------------
    df = pd.read_csv(DATA_DIR / "merged_clutch_overall.csv")
    log.info("Loaded merged data: %d rows", len(df))

    # ------------------------------------------------------------------
    # Step 1: Filter to reputation players
    # ------------------------------------------------------------------
    rep_ids = set(REPUTATION_PLAYERS.keys())
    rep = df[df["PLAYER_ID"].isin(rep_ids)].copy()
    log.info("Reputation player-seasons found: %d", len(rep))

    found_ids = set(rep["PLAYER_ID"].unique())
    missing = rep_ids - found_ids
    if missing:
        for mid in missing:
            log.warning("  NOT FOUND in data: %s (id=%d)", REPUTATION_PLAYERS[mid], mid)

    for pid in sorted(found_ids):
        seasons = sorted(rep.loc[rep["PLAYER_ID"] == pid, "SEASON"].unique())
        log.info("  %-20s  %d seasons: %s", REPUTATION_PLAYERS[pid], len(seasons),
                 ", ".join(seasons))

    # ------------------------------------------------------------------
    # Step 2: Compute TS% columns
    # ------------------------------------------------------------------
    rep["clutch_ts"]  = ts_pct(rep["CLUTCH_PTS"], rep["CLUTCH_FGA"], rep["CLUTCH_FTA"])
    rep["overall_ts"] = ts_pct(rep["OVERALL_PTS"], rep["OVERALL_FGA"], rep["OVERALL_FTA"])

    # ------------------------------------------------------------------
    # TEST 3 — Clutch vs Overall TS%
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 3 — Clutch TS%% vs Overall TS%% (reputation players)")

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
    t3["clutch_ts"]  = ts_pct(t3["clutch_pts"], t3["clutch_fga"], t3["clutch_fta"])
    t3["overall_ts"] = ts_pct(t3["overall_pts"], t3["overall_fga"], t3["overall_fta"])
    t3["ts_diff"]    = t3["clutch_ts"] - t3["overall_ts"]
    t3 = t3.sort_values("ts_diff")

    log.info("  %-20s  %7s  %7s  %7s  %s", "Player", "Clutch", "Overall", "Diff", "Verdict")
    log.info("  " + "-" * 65)
    for _, r in t3.iterrows():
        verdict = "BETTER in clutch" if r["ts_diff"] > 0.005 else (
            "WORSE in clutch" if r["ts_diff"] < -0.005 else "~same")
        log.info("  %-20s  %7.3f  %7.3f  %+7.3f  %s",
                 r["player_name"], r["clutch_ts"], r["overall_ts"], r["ts_diff"], verdict)

    t3_out = t3[["PLAYER_ID", "player_name", "seasons", "clutch_ts", "overall_ts", "ts_diff"]]
    t3_out.to_csv(OUTPUT_DIR / "phase3_test3_ts_comparison.csv", index=False)
    log.info("  Saved phase3_test3_ts_comparison.csv")

    # ------------------------------------------------------------------
    # TEST 4 — FT-stripped clutch efficiency
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 4 — FT-Stripped Clutch Efficiency")

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
    t4["clutch_ts"]       = ts_pct(t4["clutch_pts"], t4["clutch_fga"], t4["clutch_fta"])
    t4["ft_stripped_eff"]  = ft_stripped_eff(t4["clutch_fgm"], t4["clutch_fg3m"], t4["clutch_fga"])
    t4["ft_boost"]         = t4["clutch_ts"] - t4["ft_stripped_eff"]
    t4["ft_pts"]           = t4["clutch_ftm"]
    t4["fg_pts"]           = 2 * (t4["clutch_fgm"] - t4["clutch_fg3m"]) + 3 * t4["clutch_fg3m"]
    t4["ft_share_of_pts"]  = np.where(t4["clutch_pts"] > 0,
                                      t4["ft_pts"] / t4["clutch_pts"], np.nan)
    t4 = t4.sort_values("ft_boost", ascending=False)

    log.info("  %-20s  %7s  %7s  %7s  %8s", "Player", "ClutchTS", "FTStrip", "FTBoost", "FT%%ofPts")
    log.info("  " + "-" * 60)
    for _, r in t4.iterrows():
        log.info("  %-20s  %7.3f  %7.3f  %+7.3f  %7.1f%%",
                 r["player_name"], r["clutch_ts"], r["ft_stripped_eff"],
                 r["ft_boost"], r["ft_share_of_pts"] * 100)

    t4_out = t4[["PLAYER_ID", "player_name", "clutch_ts", "ft_stripped_eff",
                 "ft_boost", "ft_share_of_pts"]]
    t4_out.to_csv(OUTPUT_DIR / "phase3_test4_ft_stripped.csv", index=False)
    log.info("  Saved phase3_test4_ft_stripped.csv")

    # ------------------------------------------------------------------
    # TEST 5 — Usage Spike
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("TEST 5 — Usage Spike (Clutch vs Overall)")

    team_overall = load_team_totals("overall")
    team_clutch  = load_team_totals("clutch")
    log.info("  Team overall rows: %d   Team clutch rows: %d",
             len(team_overall), len(team_clutch))

    team_overall = team_overall.rename(columns={
        "FGA": "TEAM_OVR_FGA", "FTA": "TEAM_OVR_FTA",
        "TOV": "TEAM_OVR_TOV", "MIN": "TEAM_OVR_MIN",
    })
    team_clutch = team_clutch.rename(columns={
        "FGA": "TEAM_CLU_FGA", "FTA": "TEAM_CLU_FTA",
        "TOV": "TEAM_CLU_TOV", "MIN": "TEAM_CLU_MIN",
    })

    rep_usage = rep.copy()

    rep_usage = rep_usage.merge(
        team_overall[["TEAM_ID", "SEASON", "TEAM_OVR_FGA", "TEAM_OVR_FTA",
                       "TEAM_OVR_TOV", "TEAM_OVR_MIN"]],
        left_on=["TEAM_ID", "SEASON"],
        right_on=["TEAM_ID", "SEASON"],
        how="left",
    )
    rep_usage = rep_usage.merge(
        team_clutch[["TEAM_ID", "SEASON", "TEAM_CLU_FGA", "TEAM_CLU_FTA",
                      "TEAM_CLU_TOV", "TEAM_CLU_MIN"]],
        left_on=["TEAM_ID", "SEASON"],
        right_on=["TEAM_ID", "SEASON"],
        how="left",
    )

    # Player possessions (approx)
    rep_usage["player_clutch_poss"]  = rep_usage["CLUTCH_FGA"]  + 0.44 * rep_usage["CLUTCH_FTA"]  + rep_usage["CLUTCH_TOV"]
    rep_usage["player_overall_poss"] = rep_usage["OVERALL_FGA"] + 0.44 * rep_usage["OVERALL_FTA"] + rep_usage["OVERALL_TOV"]

    # Team possessions (approx)
    rep_usage["team_clutch_poss"]  = rep_usage["TEAM_CLU_FGA"]  + 0.44 * rep_usage["TEAM_CLU_FTA"]  + rep_usage["TEAM_CLU_TOV"]
    rep_usage["team_overall_poss"] = rep_usage["TEAM_OVR_FGA"] + 0.44 * rep_usage["TEAM_OVR_FTA"] + rep_usage["TEAM_OVR_TOV"]

    # Usage % = player poss / team poss (minutes-adjusted)
    # Simpler & more intuitive: player's FGA share of team FGA
    rep_usage["clutch_fga_share"]  = np.where(rep_usage["TEAM_CLU_FGA"] > 0,
                                              rep_usage["CLUTCH_FGA"] / rep_usage["TEAM_CLU_FGA"], np.nan)
    rep_usage["overall_fga_share"] = np.where(rep_usage["TEAM_OVR_FGA"] > 0,
                                              rep_usage["OVERALL_FGA"] / rep_usage["TEAM_OVR_FGA"], np.nan)

    # Possession-based usage share
    rep_usage["clutch_usg"]  = np.where(rep_usage["team_clutch_poss"] > 0,
                                        rep_usage["player_clutch_poss"] / rep_usage["team_clutch_poss"], np.nan)
    rep_usage["overall_usg"] = np.where(rep_usage["team_overall_poss"] > 0,
                                        rep_usage["player_overall_poss"] / rep_usage["team_overall_poss"], np.nan)

    # Save full per-season detail
    detail_cols = [
        "PLAYER_ID", "PLAYER_NAME", "SEASON", "TEAM_ABBREVIATION",
        "clutch_ts", "overall_ts",
        "CLUTCH_FGA", "OVERALL_FGA",
        "clutch_fga_share", "overall_fga_share",
        "clutch_usg", "overall_usg",
        "player_clutch_poss", "player_overall_poss",
    ]
    rep_usage[detail_cols].to_csv(OUTPUT_DIR / "phase3_reputation_seasons.csv", index=False)

    # Aggregate per player
    t5 = (
        rep_usage.groupby("PLAYER_ID")
        .agg(
            player_name=("PLAYER_NAME", "first"),
            seasons=("SEASON", "count"),
            avg_clutch_fga_share=("clutch_fga_share", "mean"),
            avg_overall_fga_share=("overall_fga_share", "mean"),
            avg_clutch_usg=("clutch_usg", "mean"),
            avg_overall_usg=("overall_usg", "mean"),
        )
        .reset_index()
    )
    t5["fga_share_spike"]     = t5["avg_clutch_fga_share"] - t5["avg_overall_fga_share"]
    t5["fga_share_spike_pct"] = np.where(t5["avg_overall_fga_share"] > 0,
                                         t5["fga_share_spike"] / t5["avg_overall_fga_share"] * 100, np.nan)
    t5["usg_spike"]           = t5["avg_clutch_usg"] - t5["avg_overall_usg"]
    t5["usg_spike_pct"]       = np.where(t5["avg_overall_usg"] > 0,
                                         t5["usg_spike"] / t5["avg_overall_usg"] * 100, np.nan)
    t5 = t5.sort_values("fga_share_spike_pct", ascending=False)

    log.info("  %-20s  %8s  %8s  %8s  %8s", "Player", "Clu FGA%", "Ovr FGA%", "Spike", "Spike%")
    log.info("  " + "-" * 60)
    for _, r in t5.iterrows():
        log.info("  %-20s  %7.1f%%  %7.1f%%  %+7.1fpp  %+7.1f%%",
                 r["player_name"],
                 r["avg_clutch_fga_share"] * 100,
                 r["avg_overall_fga_share"] * 100,
                 r["fga_share_spike"] * 100,
                 r["fga_share_spike_pct"])

    t5.to_csv(OUTPUT_DIR / "phase3_test5_usage_spike.csv", index=False)
    log.info("  Saved phase3_test5_usage_spike.csv")

    # ------------------------------------------------------------------
    # Summary JSON
    # ------------------------------------------------------------------
    log.info("=" * 60)

    # Build summary dicts
    test3_summary = {}
    for _, r in t3.iterrows():
        test3_summary[r["player_name"]] = {
            "clutch_ts": round(float(r["clutch_ts"]), 4),
            "overall_ts": round(float(r["overall_ts"]), 4),
            "diff": round(float(r["ts_diff"]), 4),
        }

    test4_summary = {}
    for _, r in t4.iterrows():
        test4_summary[r["player_name"]] = {
            "clutch_ts": round(float(r["clutch_ts"]), 4),
            "ft_stripped_eff": round(float(r["ft_stripped_eff"]), 4),
            "ft_boost": round(float(r["ft_boost"]), 4),
            "ft_share_of_pts": round(float(r["ft_share_of_pts"]), 4),
        }

    test5_summary = {}
    for _, r in t5.iterrows():
        test5_summary[r["player_name"]] = {
            "avg_clutch_fga_share": round(float(r["avg_clutch_fga_share"]), 4),
            "avg_overall_fga_share": round(float(r["avg_overall_fga_share"]), 4),
            "fga_share_spike_pct": round(float(r["fga_share_spike_pct"]), 1),
        }

    results = {
        "test3_ts_comparison": test3_summary,
        "test4_ft_stripped": test4_summary,
        "test5_usage_spike": test5_summary,
    }

    results_path = OUTPUT_DIR / "phase3_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("PHASE 3 RESULTS saved to %s", results_path.name)
    log.info("Phase 3 done.")


if __name__ == "__main__":
    main()
