"""
Playoff Data Pull
==================
Pulls playoff clutch + overall stats for 8 seasons (2017-18 through 2024-25).
Same structure as Phase 1, but season_type_all_star="Playoffs".
Uses Phase 2's robust rate limiting, headers, and retries.

Outputs:
  data/clutch_base_playoffs_YYYY-YY.csv
  data/league_stats_playoffs_YYYY-YY.csv
  data/merged_clutch_overall_playoffs.csv
  outputs/dropped_insufficient_sample_playoffs.csv
"""

import logging
import random
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from nba_api.stats import endpoints as _nba_endpoints
from nba_api.stats.endpoints import LeagueDashPlayerClutch, LeagueDashPlayerStats

# Same browser headers as Phase 2 — stats.nba.com throttles without these
_nba_endpoints.headers = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25",
]
MIN_CLUTCH_GP = 5  # Lower for playoffs — smaller samples

CALL_INTERVAL = 20   # seconds between API calls (conservative for playoffs)
JITTER_MAX = 5      # extra random 0–5 sec to avoid robotic pattern
COOLDOWN_AFTER_FAIL = 90  # seconds to wait after a failed season before next
MAX_RETRIES = 6
RETRY_WAITS = [30, 60, 120, 180, 300, 420]  # 7 min max wait before final attempt
TIMEOUT = 180

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / "playoff_pull.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, interval: float):
        self._lock = threading.Lock()
        self._last_ts = 0.0
        self.interval = interval

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self.interval - (now - self._last_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_ts = time.monotonic()


limiter = RateLimiter(CALL_INTERVAL)


def api_call(endpoint_cls, description: str, **kwargs) -> pd.DataFrame:
    for attempt in range(MAX_RETRIES):
        limiter.acquire()
        time.sleep(random.uniform(0, JITTER_MAX))
        try:
            log.info("  [%s] attempt %d/%d", description, attempt + 1, MAX_RETRIES)
            result = endpoint_cls(**kwargs, timeout=TIMEOUT)
            df = result.get_data_frames()[0]
            log.info("    -> OK  shape=%s", df.shape)
            return df
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                log.error("    All retries exhausted: %s", exc)
                raise RuntimeError(f"Failed: {description}") from exc
            wait = RETRY_WAITS[attempt]
            log.warning("    -> FAIL (%s). Sleeping %ds...", type(exc).__name__, wait)
            time.sleep(wait)
    raise RuntimeError("Unreachable")


def pull_season(endpoint_cls, tag: str, season: str, extra: dict) -> Optional[pd.DataFrame]:
    csv = DATA_DIR / f"{tag}_playoffs_{season}.csv"
    if csv.exists():
        log.info("  Cached: %s", csv.name)
        return pd.read_csv(csv)
    try:
        df = api_call(endpoint_cls, f"{tag} playoffs {season}", season=season, **extra)
        df["SEASON"] = season
        df.to_csv(csv, index=False)
        log.info("  Saved %s", csv.name)
        return df
    except RuntimeError:
        log.error("  SKIPPING %s %s — re-run to retry.", tag, season)
        log.info("  Cooldown %ds before next request...", COOLDOWN_AFTER_FAIL)
        time.sleep(COOLDOWN_AFTER_FAIL)
        return None


def merge_and_filter(clutch: pd.DataFrame, league: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    clutch_cols = [c for c in clutch.columns if c != "GROUP_SET"]
    league_cols = [c for c in league.columns if c != "GROUP_SET"]

    clutch_sub = clutch[clutch_cols].copy().add_prefix("CLUTCH_")
    clutch_sub.rename(columns={
        "CLUTCH_PLAYER_ID": "PLAYER_ID",
        "CLUTCH_PLAYER_NAME": "PLAYER_NAME",
        "CLUTCH_SEASON": "SEASON",
        "CLUTCH_TEAM_ID": "TEAM_ID",
        "CLUTCH_TEAM_ABBREVIATION": "TEAM_ABBREVIATION",
    }, inplace=True)

    league_sub = league[league_cols].copy().add_prefix("OVERALL_")
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
    log.info("After GP >= %d filter: kept %d, dropped %d", MIN_CLUTCH_GP, len(merged), len(dropped))
    return merged, dropped


def main():
    log.info("=" * 60)
    log.info("PLAYOFF DATA PULL — Clutch + Overall (8 seasons)")
    log.info("Rate limit: %ds + jitter | Retries: %d | Timeout: %ds", CALL_INTERVAL, MAX_RETRIES, TIMEOUT)
    log.info("=" * 60)

    clutch_frames = []
    league_frames = []

    # Step 1: Clutch base (playoffs)
    log.info("Step 1: LeagueDashPlayerClutch (Playoffs)...")
    for season in SEASONS:
        df = pull_season(
            LeagueDashPlayerClutch, "clutch_base", season,
            dict(
                clutch_time="Last 5 Minutes",
                ahead_behind="Ahead or Behind",
                point_diff=5,
                measure_type_detailed_defense="Base",
                per_mode_detailed="Totals",
                season_type_all_star="Playoffs",
            ),
        )
        if df is not None:
            clutch_frames.append(df)

    if not clutch_frames:
        log.error("No clutch data — aborting.")
        sys.exit(1)
    clutch_base = pd.concat(clutch_frames, ignore_index=True)
    log.info("Clutch base total: %d rows", len(clutch_base))

    # Step 2: League stats (playoffs)
    log.info("Step 2: LeagueDashPlayerStats (Playoffs)...")
    for season in SEASONS:
        df = pull_season(
            LeagueDashPlayerStats, "league_stats", season,
            dict(
                per_mode_detailed="Totals",
                season_type_all_star="Playoffs",
            ),
        )
        if df is not None:
            league_frames.append(df)

    if not league_frames:
        log.error("No league stats — aborting.")
        sys.exit(1)
    league_stats = pd.concat(league_frames, ignore_index=True)
    log.info("League stats total: %d rows", len(league_stats))

    # Step 3: Merge & filter
    log.info("Step 3: Merge & filter (GP >= %d)...", MIN_CLUTCH_GP)
    merged, dropped = merge_and_filter(clutch_base, league_stats)

    merged.to_csv(DATA_DIR / "merged_clutch_overall_playoffs.csv", index=False)
    log.info("Saved merged -> data/merged_clutch_overall_playoffs.csv")

    if len(dropped):
        dropped.to_csv(OUTPUT_DIR / "dropped_insufficient_sample_playoffs.csv", index=False)
        log.info("Saved %d dropped -> outputs/dropped_insufficient_sample_playoffs.csv", len(dropped))

    log.info("=" * 60)
    log.info("PLAYOFF PULL COMPLETE")
    log.info("  Merged: %d rows (%d player-seasons)", len(merged), merged["PLAYER_ID"].nunique())
    log.info("  Dropped: %d rows", len(dropped))
    for s in SEASONS:
        n = len(merged[merged["SEASON"] == s])
        log.info("    %s: %d rows", s, n)


if __name__ == "__main__":
    main()
