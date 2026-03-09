"""
Phase 4 — Tests 6, 7, 8, outliers, and caveats
================================================
Reads:
  data/merged_clutch_overall.csv          (Tests 6 & 8)
  data/clutch_home_YYYY-YY.csv            (Test 7)
  data/clutch_road_YYYY-YY.csv            (Test 7)
  outputs/phase2_player_yoy_r.csv         (Outliers)

Runs:
  • Test 6 — Assisted-to-FGM ratio (clutch vs overall) — isolation proxy
  • Test 7 — Home vs Away clutch TS%
  • Test 8 — Miss rate for 3 mythology players
  • Outlier flagging (r > 0.5 from Phase 2)
  • Caveats documentation

Outputs:
  outputs/phase4_test6_assist_ratio.csv
  outputs/phase4_test7_home_away.csv
  outputs/phase4_test8_miss_rate.csv
  outputs/phase4_outliers.csv
  outputs/phase4_results.json
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
    201566:  "Russell Westbrook",
    203999:  "Nikola Jokic",
}

MYTHOLOGY_PLAYERS = {
    203081: "Damian Lillard",
    2544:   "LeBron James",
    202681: "Kyrie Irving",
}


def ts_pct(pts, fga, fta):
    denom = 2.0 * (fga + 0.44 * fta)
    return np.where(denom > 0, pts / denom, np.nan)


def load_split_files(location: str) -> pd.DataFrame:
    """Load all 8 season files for clutch_home or clutch_road."""
    frames = []
    tag = "home" if location == "Home" else "road"
    for s in SEASONS:
        path = DATA_DIR / f"clutch_{tag}_{s}.csv"
        if path.exists():
            t = pd.read_csv(path)
            if "SEASON" not in t.columns:
                t["SEASON"] = s
            frames.append(t)
        else:
            log.warning("  Missing %s", path.name)
    return pd.concat(frames, ignore_index=True)


def main():
    # ------------------------------------------------------------------
    # Load merged data
    # ------------------------------------------------------------------
    df = pd.read_csv(DATA_DIR / "merged_clutch_overall.csv")
    log.info("Loaded merged data: %d rows", len(df))

    rep_ids = set(REPUTATION_PLAYERS.keys())

    # ==================================================================
    # TEST 6 — Assisted-to-FGM ratio (isolation proxy)
    # ==================================================================
    log.info("=" * 60)
    log.info("TEST 6 -- Assist-to-FGM Ratio (clutch vs overall)")

    # League-wide averages first (all player-seasons)
    valid_clutch = df["CLUTCH_FGM"] > 0
    valid_overall = df["OVERALL_FGM"] > 0

    df.loc[valid_clutch, "clutch_ast_fgm"]  = df.loc[valid_clutch, "CLUTCH_AST"]  / df.loc[valid_clutch, "CLUTCH_FGM"]
    df.loc[valid_overall, "overall_ast_fgm"] = df.loc[valid_overall, "OVERALL_AST"] / df.loc[valid_overall, "OVERALL_FGM"]

    league_clutch_ast_fgm  = df.loc[valid_clutch, "clutch_ast_fgm"].mean()
    league_overall_ast_fgm = df.loc[valid_overall, "overall_ast_fgm"].mean()
    log.info("  League-wide avg AST/FGM:")
    log.info("    Clutch:  %.3f", league_clutch_ast_fgm)
    log.info("    Overall: %.3f", league_overall_ast_fgm)
    log.info("    Drop:    %+.3f  (%.1f%%)",
             league_clutch_ast_fgm - league_overall_ast_fgm,
             (league_clutch_ast_fgm - league_overall_ast_fgm) / league_overall_ast_fgm * 100)

    # Reputation players
    rep = df[df["PLAYER_ID"].isin(rep_ids)].copy()

    t6 = (
        rep.groupby("PLAYER_ID")
        .agg(
            player_name=("PLAYER_NAME", "first"),
            seasons=("SEASON", "count"),
            clutch_ast=("CLUTCH_AST", "sum"),
            clutch_fgm=("CLUTCH_FGM", "sum"),
            overall_ast=("OVERALL_AST", "sum"),
            overall_fgm=("OVERALL_FGM", "sum"),
        )
        .reset_index()
    )
    t6["clutch_ast_fgm"]  = np.where(t6["clutch_fgm"] > 0,
                                      t6["clutch_ast"] / t6["clutch_fgm"], np.nan)
    t6["overall_ast_fgm"] = np.where(t6["overall_fgm"] > 0,
                                      t6["overall_ast"] / t6["overall_fgm"], np.nan)
    t6["ast_fgm_diff"]    = t6["clutch_ast_fgm"] - t6["overall_ast_fgm"]
    t6["ast_fgm_pct_change"] = np.where(t6["overall_ast_fgm"] > 0,
                                         t6["ast_fgm_diff"] / t6["overall_ast_fgm"] * 100, np.nan)
    t6 = t6.sort_values("ast_fgm_diff")

    log.info("\n  %-24s  %8s  %8s  %8s  %8s", "Player", "Clu A/F", "Ovr A/F", "Diff", "Chg%")
    log.info("  " + "-" * 65)
    for _, r in t6.iterrows():
        log.info("  %-24s  %8.3f  %8.3f  %+8.3f  %+7.1f%%",
                 r["player_name"],
                 r["clutch_ast_fgm"], r["overall_ast_fgm"],
                 r["ast_fgm_diff"], r["ast_fgm_pct_change"])

    t6_out = t6[["PLAYER_ID", "player_name", "seasons",
                  "clutch_ast_fgm", "overall_ast_fgm", "ast_fgm_diff", "ast_fgm_pct_change"]]
    t6_out.to_csv(OUTPUT_DIR / "phase4_test6_assist_ratio.csv", index=False)
    log.info("  Saved phase4_test6_assist_ratio.csv")

    # ==================================================================
    # TEST 7 — Home vs Away clutch TS%
    # ==================================================================
    log.info("=" * 60)
    log.info("TEST 7 -- Home vs Away Clutch TS%%")

    home_df = load_split_files("Home")
    road_df = load_split_files("Road")
    log.info("  Home rows: %d   Road rows: %d", len(home_df), len(road_df))

    # Filter to reputation players
    home_rep = home_df[home_df["PLAYER_ID"].isin(rep_ids)].copy()
    road_rep = road_df[road_df["PLAYER_ID"].isin(rep_ids)].copy()

    # Aggregate per player
    def agg_split(split_df, prefix):
        agg = (
            split_df.groupby("PLAYER_ID")
            .agg(
                player_name=("PLAYER_NAME", "first"),
                seasons=("SEASON", "count"),
                pts=("PTS", "sum"),
                fga=("FGA", "sum"),
                fta=("FTA", "sum"),
                fgm=("FGM", "sum"),
                gp=("GP", "sum"),
            )
            .reset_index()
        )
        agg[f"{prefix}_ts"] = ts_pct(agg["pts"], agg["fga"], agg["fta"])
        agg[f"{prefix}_fga"] = agg["fga"]
        agg[f"{prefix}_gp"]  = agg["gp"]
        return agg[["PLAYER_ID", "player_name", f"{prefix}_ts", f"{prefix}_fga", f"{prefix}_gp"]]

    home_agg = agg_split(home_rep, "home")
    road_agg = agg_split(road_rep, "road")

    t7 = home_agg.merge(road_agg, on="PLAYER_ID", suffixes=("", "_road"))
    t7["home_away_diff"] = t7["home_ts"] - t7["road_ts"]
    t7 = t7.sort_values("home_away_diff", ascending=False)

    log.info("  %-24s  %8s  %8s  %8s", "Player", "Home TS", "Road TS", "Diff")
    log.info("  " + "-" * 55)
    for _, r in t7.iterrows():
        log.info("  %-24s  %8.3f  %8.3f  %+8.3f",
                 r["player_name"], r["home_ts"], r["road_ts"], r["home_away_diff"])

    # League-wide home vs road
    home_all = home_df.copy()
    road_all = road_df.copy()
    home_all_ts = ts_pct(home_all["PTS"].sum(), home_all["FGA"].sum(), home_all["FTA"].sum())
    road_all_ts = ts_pct(road_all["PTS"].sum(), road_all["FGA"].sum(), road_all["FTA"].sum())
    log.info("\n  League-wide clutch TS%%:  Home=%.3f   Road=%.3f   Diff=%+.3f",
             float(home_all_ts), float(road_all_ts), float(home_all_ts - road_all_ts))

    t7_out = t7[["PLAYER_ID", "player_name", "home_ts", "road_ts",
                  "home_away_diff", "home_fga", "road_fga", "home_gp", "road_gp"]]
    t7_out.to_csv(OUTPUT_DIR / "phase4_test7_home_away.csv", index=False)
    log.info("  Saved phase4_test7_home_away.csv")

    # ==================================================================
    # TEST 8 — Miss rate / memory bias
    # ==================================================================
    log.info("=" * 60)
    log.info("TEST 8 -- Miss Rate (Memory Bias) for Mythology Players")

    myth_ids = set(MYTHOLOGY_PLAYERS.keys())
    myth = df[df["PLAYER_ID"].isin(myth_ids)].copy()

    t8 = (
        myth.groupby("PLAYER_ID")
        .agg(
            player_name=("PLAYER_NAME", "first"),
            seasons=("SEASON", "count"),
            clutch_fga=("CLUTCH_FGA", "sum"),
            clutch_fgm=("CLUTCH_FGM", "sum"),
            clutch_fg3a=("CLUTCH_FG3A", "sum"),
            clutch_fg3m=("CLUTCH_FG3M", "sum"),
            clutch_pts=("CLUTCH_PTS", "sum"),
            overall_fga=("OVERALL_FGA", "sum"),
            overall_fgm=("OVERALL_FGM", "sum"),
        )
        .reset_index()
    )
    t8["clutch_misses"]    = t8["clutch_fga"] - t8["clutch_fgm"]
    t8["clutch_miss_rate"] = np.where(t8["clutch_fga"] > 0,
                                       t8["clutch_misses"] / t8["clutch_fga"], np.nan)
    t8["clutch_fg_pct"]    = np.where(t8["clutch_fga"] > 0,
                                       t8["clutch_fgm"] / t8["clutch_fga"], np.nan)
    t8["overall_fg_pct"]   = np.where(t8["overall_fga"] > 0,
                                       t8["overall_fgm"] / t8["overall_fga"], np.nan)
    t8["fg_pct_diff"]      = t8["clutch_fg_pct"] - t8["overall_fg_pct"]

    log.info("  %-20s  %6s  %6s  %6s  %8s  %8s  %8s  %8s",
             "Player", "FGA", "FGM", "Miss", "MissRate", "CluFG%", "OvrFG%", "FG%Diff")
    log.info("  " + "-" * 85)
    for _, r in t8.iterrows():
        log.info("  %-20s  %6d  %6d  %6d  %7.1f%%  %7.1f%%  %7.1f%%  %+7.1fpp",
                 r["player_name"],
                 int(r["clutch_fga"]), int(r["clutch_fgm"]), int(r["clutch_misses"]),
                 r["clutch_miss_rate"] * 100,
                 r["clutch_fg_pct"] * 100,
                 r["overall_fg_pct"] * 100,
                 r["fg_pct_diff"] * 100)

    t8.to_csv(OUTPUT_DIR / "phase4_test8_miss_rate.csv", index=False)
    log.info("  Saved phase4_test8_miss_rate.csv")

    # ==================================================================
    # OUTLIERS — repeatable clutch from Phase 2
    # ==================================================================
    log.info("=" * 60)
    log.info("OUTLIERS -- Players with r > 0.5 (potential repeatable clutch)")

    yoy_path = OUTPUT_DIR / "phase2_player_yoy_r.csv"
    if yoy_path.exists():
        yoy = pd.read_csv(yoy_path)
        outliers = yoy[yoy["r"] > 0.5].sort_values("r", ascending=False).copy()
        log.info("  %d players with r > 0.5 (out of %d tested):", len(outliers), len(yoy))
        log.info("  %-24s  %6s  %6s  %10s", "Player", "r", "pairs", "p-value")
        log.info("  " + "-" * 55)
        for _, r in outliers.iterrows():
            log.info("  %-24s  %6.3f  %6d  %10.4f",
                     r["player_name"], r["r"], int(r["n_pairs"]), r["p"])

        # Flag which ones are reputation players
        outliers["is_reputation"] = outliers["player_id"].isin(rep_ids)
        rep_outliers = outliers[outliers["is_reputation"]]
        if not rep_outliers.empty:
            log.info("\n  Reputation players in outlier list:")
            for _, r in rep_outliers.iterrows():
                log.info("    %s  r=%.3f", r["player_name"], r["r"])

        outliers.to_csv(OUTPUT_DIR / "phase4_outliers.csv", index=False)
        log.info("  Saved phase4_outliers.csv")
    else:
        log.warning("  phase2_player_yoy_r.csv not found — skipping outlier analysis")
        outliers = pd.DataFrame()

    # ==================================================================
    # CAVEATS
    # ==================================================================
    log.info("=" * 60)
    log.info("CAVEATS")

    caveats = [
        {
            "id": "era_effects",
            "title": "Era and rule changes (2017-2025)",
            "detail": (
                "The 8-season window spans significant rule changes: "
                "the 2018-19 freedom-of-movement emphasis, the 2020 bubble, "
                "and the 2023 take-foul rule. Pace increased ~5%% across this span. "
                "Clutch behavior may shift with rules, not just player skill."
            ),
        },
        {
            "id": "survivorship_bias",
            "title": "Survivorship bias",
            "detail": (
                "Only players who remained in the league and met the 10-game "
                "clutch filter appear in the data. Players who were benched or "
                "cut partly due to poor clutch play are excluded, which could "
                "artificially narrow the TS%% distribution."
            ),
        },
        {
            "id": "sample_size",
            "title": "Small clutch sample sizes",
            "detail": (
                "The median player-season has only ~25 clutch possessions "
                "(~3.6%% of total). Individual player conclusions are unreliable; "
                "aggregate patterns are more trustworthy."
            ),
        },
        {
            "id": "defensive_context",
            "title": "Defensive attention in clutch",
            "detail": (
                "Stars face tighter defensive schemes in clutch situations. "
                "A TS%% drop may reflect elevated defensive pressure rather than "
                "a player 'choking.' This is a confound, not a rebuttal."
            ),
        },
        {
            "id": "ast_fgm_limitation",
            "title": "AST/FGM is a rough isolation proxy",
            "detail": (
                "True isolation rate requires play-by-play data. AST/FGM captures "
                "ball-movement collapse but does not distinguish between unassisted "
                "pull-ups and post-ups, nor does it account for hockey assists."
            ),
        },
    ]

    for c in caveats:
        log.info("  [%s] %s", c["id"], c["title"])

    # ==================================================================
    # Summary JSON
    # ==================================================================
    log.info("=" * 60)

    test6_summary = {
        "league_clutch_ast_fgm": round(league_clutch_ast_fgm, 4),
        "league_overall_ast_fgm": round(league_overall_ast_fgm, 4),
        "league_drop_pct": round(
            (league_clutch_ast_fgm - league_overall_ast_fgm) / league_overall_ast_fgm * 100, 1
        ),
        "players": {},
    }
    for _, r in t6.iterrows():
        test6_summary["players"][r["player_name"]] = {
            "clutch_ast_fgm": round(float(r["clutch_ast_fgm"]), 4),
            "overall_ast_fgm": round(float(r["overall_ast_fgm"]), 4),
            "diff": round(float(r["ast_fgm_diff"]), 4),
            "pct_change": round(float(r["ast_fgm_pct_change"]), 1),
        }

    test7_summary = {
        "league_home_ts": round(float(home_all_ts), 4),
        "league_road_ts": round(float(road_all_ts), 4),
        "players": {},
    }
    for _, r in t7.iterrows():
        test7_summary["players"][r["player_name"]] = {
            "home_ts": round(float(r["home_ts"]), 4),
            "road_ts": round(float(r["road_ts"]), 4),
            "diff": round(float(r["home_away_diff"]), 4),
        }

    test8_summary = {}
    for _, r in t8.iterrows():
        test8_summary[r["player_name"]] = {
            "clutch_fga": int(r["clutch_fga"]),
            "clutch_fgm": int(r["clutch_fgm"]),
            "clutch_misses": int(r["clutch_misses"]),
            "miss_rate": round(float(r["clutch_miss_rate"]), 4),
            "clutch_fg_pct": round(float(r["clutch_fg_pct"]), 4),
            "overall_fg_pct": round(float(r["overall_fg_pct"]), 4),
        }

    outlier_summary = []
    if not outliers.empty:
        for _, r in outliers.head(10).iterrows():
            outlier_summary.append({
                "player_name": r["player_name"],
                "r": round(float(r["r"]), 4),
                "n_pairs": int(r["n_pairs"]),
                "is_reputation": bool(r["is_reputation"]),
            })

    results = {
        "test6_assist_ratio": test6_summary,
        "test7_home_away": test7_summary,
        "test8_miss_rate": test8_summary,
        "outliers": outlier_summary,
        "caveats": caveats,
    }

    results_path = OUTPUT_DIR / "phase4_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log.info("PHASE 4 RESULTS saved to %s", results_path.name)
    log.info("Phase 4 done.")


if __name__ == "__main__":
    main()
