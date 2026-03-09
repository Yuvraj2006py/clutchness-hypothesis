"""
Phase 1 — Data Pull, Merge, and Filter
=======================================
Pulls 8 seasons (2017-18 through 2024-25) of:
  1. LeagueDashPlayerClutch (Base)   -> clutch box-score stats
  2. LeagueDashPlayerStats  (Base)   -> overall season stats

USG% is computed from base box-score stats in Phase 3 (no separate API call).

Merges on PLAYER_ID + SEASON, filters to GP >= 10 clutch games,
logs dropped player-seasons, and caches everything as per-season CSVs.
Re-run safe: skips any season already cached.
"""

import sys
import time
import logging
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueDashPlayerClutch, LeagueDashPlayerStats

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25",
]
MIN_CLUTCH_GP = 10
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

SLEEP_AFTER_SUCCESS = 15         # seconds after a successful API call
MAX_RETRIES = 3
RETRY_WAITS = [45, 90, 180]     # fixed wait schedule (not exponential)
API_TIMEOUT = 45                 # short timeout — if NBA blocks, fail fast

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / "phase1.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_call_with_retry(endpoint_cls, description: str, **kwargs) -> pd.DataFrame:
    """Call an nba_api endpoint with fixed-schedule retries."""
    for attempt in range(MAX_RETRIES):
        try:
            log.info("API [%s] attempt %d/%d", description, attempt + 1, MAX_RETRIES)
            result = endpoint_cls(**kwargs, timeout=API_TIMEOUT)
            df = result.get_data_frames()[0]
            log.info("  -> OK  shape=%s", df.shape)
            time.sleep(SLEEP_AFTER_SUCCESS)
            return df
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                log.error("  All retries exhausted for [%s]: %s", description, exc)
                raise RuntimeError(f"Failed: {description}") from exc
            wait = RETRY_WAITS[attempt]
            log.warning("  -> FAIL (%s). Waiting %ds...", type(exc).__name__, wait)
            time.sleep(wait)


def pull_dataset(endpoint_cls, tag: str, seasons: list[str],
                 extra_params: dict) -> pd.DataFrame:
    """
    Pull data season-by-season with per-season CSV caching.
    Skips cached seasons. On failure, logs and continues.
    """
    frames = []
    failed = []
    for season in seasons:
        csv_path = DATA_DIR / f"{tag}_{season}.csv"
        if csv_path.exists():
            log.info("  Cached: %s", csv_path.name)
            frames.append(pd.read_csv(csv_path))
            continue
        try:
            df = api_call_with_retry(
                endpoint_cls, f"{tag} {season}",
                season=season, **extra_params,
            )
            df["SEASON"] = season
            df.to_csv(csv_path, index=False)
            log.info("  Saved %s", csv_path.name)
            frames.append(df)
        except RuntimeError:
            log.error("  SKIPPING %s %s — re-run to retry.", tag, season)
            failed.append(season)

    if failed:
        log.warning("  Failed seasons for %s: %s", tag, failed)
    if not frames:
        raise RuntimeError(f"No data at all for {tag}")
    return pd.concat(frames, ignore_index=True)

# ---------------------------------------------------------------------------
# Merge & filter
# ---------------------------------------------------------------------------

def merge_and_filter(clutch_base: pd.DataFrame,
                     league_stats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    clutch_cols = [c for c in clutch_base.columns if c != "GROUP_SET"]
    league_cols = [c for c in league_stats.columns if c != "GROUP_SET"]

    clutch_sub = clutch_base[clutch_cols].copy()
    league_sub = league_stats[league_cols].copy()

    clutch_sub = clutch_sub.add_prefix("CLUTCH_")
    clutch_sub.rename(columns={
        "CLUTCH_PLAYER_ID": "PLAYER_ID",
        "CLUTCH_PLAYER_NAME": "PLAYER_NAME",
        "CLUTCH_SEASON": "SEASON",
        "CLUTCH_TEAM_ID": "TEAM_ID",
        "CLUTCH_TEAM_ABBREVIATION": "TEAM_ABBREVIATION",
    }, inplace=True)

    league_sub = league_sub.add_prefix("OVERALL_")
    league_sub.rename(columns={
        "OVERALL_PLAYER_ID": "PLAYER_ID",
        "OVERALL_PLAYER_NAME": "PLAYER_NAME",
        "OVERALL_SEASON": "SEASON",
        "OVERALL_TEAM_ID": "TEAM_ID",
        "OVERALL_TEAM_ABBREVIATION": "TEAM_ABBREVIATION",
    }, inplace=True)

    merged = pd.merge(
        clutch_sub, league_sub,
        on=["PLAYER_ID", "PLAYER_NAME", "SEASON"],
        how="inner",
        suffixes=("", "_OVR"),
    )
    log.info("Inner merge: %d rows", len(merged))

    mask = merged["CLUTCH_GP"] >= MIN_CLUTCH_GP
    dropped = merged[~mask].copy()
    merged = merged[mask].copy()
    log.info("After GP >= %d filter: kept %d, dropped %d",
             MIN_CLUTCH_GP, len(merged), len(dropped))
    return merged, dropped

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(df: pd.DataFrame, name: str):
    log.info("=== %s ===", name)
    log.info("  Shape: %s", df.shape)
    nulls = df.isnull().sum()
    bad = nulls[nulls > 0]
    if len(bad):
        log.warning("  Nulls:\n%s", bad.to_string())
    else:
        log.info("  No nulls")
    if "SEASON" in df.columns:
        log.info("  Seasons: %s", sorted(df["SEASON"].unique()))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("PHASE 1 — Data Pull, Merge & Filter")
    log.info("Seasons: %s", SEASONS)
    log.info("=" * 60)

    # -- Clutch base (all 8 cached from prior runs) -------------------------
    log.info("Step 1: LeagueDashPlayerClutch (Base)...")
    clutch_base = pull_dataset(
        LeagueDashPlayerClutch, "clutch_base", SEASONS,
        dict(
            clutch_time="Last 5 Minutes",
            ahead_behind="Ahead or Behind",
            point_diff=5,
            measure_type_detailed_defense="Base",
            per_mode_detailed="Totals",
            season_type_all_star="Regular Season",
        ),
    )
    required = ["PLAYER_ID", "PLAYER_NAME", "GP", "FGM", "FGA",
                 "FG3M", "FG3A", "FTM", "FTA", "PTS", "AST", "TOV", "MIN"]
    missing = [c for c in required if c not in clutch_base.columns]
    if missing:
        raise ValueError(f"Missing clutch columns: {missing}")
    verify(clutch_base, "Clutch Base")

    # -- League stats -------------------------------------------------------
    log.info("Step 2: LeagueDashPlayerStats...")
    league_stats = pull_dataset(
        LeagueDashPlayerStats, "league_stats", SEASONS,
        dict(
            per_mode_detailed="Totals",
            season_type_all_star="Regular Season",
        ),
    )
    verify(league_stats, "League Stats")

    # -- Merge & filter -----------------------------------------------------
    log.info("Step 3: Merge & filter...")
    merged, dropped = merge_and_filter(clutch_base, league_stats)

    merged.to_csv(DATA_DIR / "merged_clutch_overall.csv", index=False)
    log.info("Saved merged -> %s", DATA_DIR / "merged_clutch_overall.csv")

    if len(dropped):
        dropped.to_csv(OUTPUT_DIR / "dropped_insufficient_sample.csv", index=False)
        log.info("Saved %d dropped rows -> %s",
                 len(dropped), OUTPUT_DIR / "dropped_insufficient_sample.csv")

    verify(merged, "Merged (GP >= 10)")

    # -- Summary ------------------------------------------------------------
    log.info("=" * 60)
    log.info("PHASE 1 SUMMARY")
    log.info("=" * 60)
    log.info("Clutch Base:  %d rows", len(clutch_base))
    log.info("League Stats: %d rows", len(league_stats))
    log.info("Merged:       %d rows  (%d players)",
             len(merged), merged["PLAYER_ID"].nunique())
    log.info("Dropped:      %d rows", len(dropped))

    for season in SEASONS:
        sc = len(clutch_base[clutch_base["SEASON"] == season])
        sl = len(league_stats[league_stats["SEASON"] == season])
        sm = len(merged[merged["SEASON"] == season])
        log.info("  %s  clutch=%d  league=%d  merged=%d", season, sc, sl, sm)

    lebron = merged[merged["PLAYER_NAME"].str.contains("LeBron", case=False, na=False)]
    if len(lebron):
        log.info("Spot check — LeBron seasons: %s", sorted(lebron["SEASON"].unique()))
        log.info("  Clutch GP:\n%s", lebron[["SEASON", "CLUTCH_GP"]].to_string(index=False))

    # -- Completeness check -------------------------------------------------
    missing_files = {"clutch_base": [], "league_stats": []}
    for season in SEASONS:
        for tag in missing_files:
            if not (DATA_DIR / f"{tag}_{season}.csv").exists():
                missing_files[tag].append(season)
    any_missing = any(v for v in missing_files.values())
    if any_missing:
        log.warning("INCOMPLETE — missing: %s. Re-run to retry.", missing_files)
    else:
        log.info("ALL DATA COMPLETE — 8 seasons cached for both datasets.")

    log.info("Phase 1 done.")


if __name__ == "__main__":
    main()
