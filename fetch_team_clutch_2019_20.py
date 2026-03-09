"""
One-off fetch for the single missing file: team_clutch_2019-20.csv
Uses same headers, timeout, and retry logic as phase2_data_pull.py.
"""
import time
import sys
from pathlib import Path

import pandas as pd
from nba_api.stats import endpoints as _nba_endpoints

# Same browser headers as phase2 (stats.nba.com expects these)
_nba_endpoints.headers = {
    "Host":              "stats.nba.com",
    "User-Agent":        (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":            "application/json, text/plain, */*",
    "Accept-Language":   "en-US,en;q=0.9",
    "Accept-Encoding":   "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection":        "keep-alive",
    "Referer":           "https://www.nba.com/",
    "Pragma":            "no-cache",
    "Cache-Control":     "no-cache",
}

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_PATH = DATA_DIR / "team_clutch_2019-20.csv"
TIMEOUT = 150
RETRIES = 5
RETRY_WAITS = [20, 40, 80, 160, 300]


def main():
    if OUT_PATH.exists():
        print(f"Already exists: {OUT_PATH}")
        return 0

    from nba_api.stats.endpoints import LeagueDashTeamClutch

    for attempt in range(RETRIES):
        try:
            print(f"Attempt {attempt + 1}/{RETRIES} ...", flush=True)
            result = LeagueDashTeamClutch(
                season="2019-20",
                clutch_time="Last 5 Minutes",
                ahead_behind="Ahead or Behind",
                point_diff=5,
                per_mode_detailed="Totals",
                season_type_all_star="Regular Season",
                timeout=TIMEOUT,
            )
            df = result.get_data_frames()[0]
            df["SEASON"] = "2019-20"
            df.to_csv(OUT_PATH, index=False)
            print(f"Saved {len(df)} rows -> {OUT_PATH.name}")
            return 0
        except Exception as e:
            print(f"  Failed: {e}", flush=True)
            if attempt == RETRIES - 1:
                print("All retries exhausted.")
                return 1
            wait = RETRY_WAITS[attempt]
            print(f"  Waiting {wait}s before retry ...", flush=True)
            time.sleep(wait)

    return 1


if __name__ == "__main__":
    sys.exit(main())
