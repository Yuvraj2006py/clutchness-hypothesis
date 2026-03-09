"""
Phase 2 — Data Collection
=========================
Steps
  1. clutch_usage      : fetch 2 missing seasons (2020-21, 2024-25)
  2. league_stats      : already complete — skipped automatically
  3. team totals       : LeagueDashTeamStats + LeagueDashTeamClutch, all 8 seasons
  4. home/road splits  : LeagueDashPlayerClutch with location_nullable, all 8 seasons
  5. priority gamelogs : PlayerGameLog, 10 players × 8 seasons
  6. PBP events        : pbpstats / data.nba.com, clutch shot events only
  7. shot-creation     : aggregate by player-season and career

Speed strategy
  • Global RateLimiter holds nba_api to ≤ 1 call / NBA_CALL_INTERVAL seconds across
    all threads, while still allowing 2 threads to overlap I/O with processing.
  • data.nba.com (pbpstats) uses a separate, lighter limiter (3s) with 4 workers.
  • Every output file is cached on disk — re-run is fully safe.
"""

import sys
import time
import random
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
from nba_api.stats import endpoints as _nba_endpoints

# Inject real-browser headers — without these stats.nba.com throttles heavily
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
GAMELOGS   = DATA_DIR / "gamelogs"
PBP_RAW    = DATA_DIR / "pbp" / "raw"
PBP_OUT    = DATA_DIR / "pbp"

for d in [DATA_DIR, GAMELOGS, PBP_RAW, PBP_OUT]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25",
]

PRIORITY_PLAYERS = {
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
}

# Clutch definition (used at PBP parse time)
CLUTCH_PERIOD_MIN       = 4       # Q4 or OT
CLUTCH_SECONDS_MAX      = 300     # ≤ 5 minutes remaining in period
CLUTCH_MARGIN_MAX       = 5       # |margin| ≤ 5

# nba_api rate-limit: 1 call per NBA_CALL_INTERVAL seconds (global across threads)
NBA_CALL_INTERVAL = 10            # seconds — slightly tighter than Phase 1
NBA_WORKERS       = 1             # sequential — avoids rate-limit from parallel hits
NBA_MAX_RETRIES   = 5
NBA_RETRY_WAITS   = [20, 40, 80, 160, 300]
NBA_TIMEOUT       = 150

# PBP via nba_api PlayByPlayV2 — strict rate limit; sequential + jitter to avoid IP block
PBP_CALL_INTERVAL = 20   # base sleep between PBP calls (seconds)
PBP_WORKERS       = 1    # single-threaded to avoid triggering IP rate limiting

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / "phase2.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Shared, thread-safe rate limiter — enforces minimum gap between calls."""
    def __init__(self, interval: float):
        self._lock    = threading.Lock()
        self._last_ts = 0.0
        self.interval = interval

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self.interval - (now - self._last_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_ts = time.monotonic()

nba_limiter = RateLimiter(NBA_CALL_INTERVAL)
pbp_limiter = RateLimiter(PBP_CALL_INTERVAL)  # separate limiter — PBP hits same host but different endpoint

# ---------------------------------------------------------------------------
# nba_api helper
# ---------------------------------------------------------------------------
def nba_call(endpoint_cls, description: str, **kwargs) -> pd.DataFrame:
    """Call an nba_api endpoint, honouring the global rate limiter with retries."""
    for attempt in range(NBA_MAX_RETRIES):
        nba_limiter.acquire()
        try:
            log.info("  API [%s] attempt %d/%d", description, attempt + 1, NBA_MAX_RETRIES)
            result = endpoint_cls(**kwargs, timeout=NBA_TIMEOUT)
            df = result.get_data_frames()[0]
            log.info("    -> OK  shape=%s", df.shape)
            return df
        except Exception as exc:
            if attempt == NBA_MAX_RETRIES - 1:
                log.error("    All retries exhausted for [%s]: %s", description, exc)
                raise RuntimeError(f"Failed: {description}") from exc
            wait = NBA_RETRY_WAITS[attempt]
            log.warning("    -> FAIL (%s). Sleeping %ds before retry...", type(exc).__name__, wait)
            time.sleep(wait)


def pull_season(endpoint_cls, tag: str, season: str, extra: dict) -> Optional[pd.DataFrame]:
    """Pull one season, add SEASON column, save to cache. Returns df or None on failure."""
    csv = DATA_DIR / f"{tag}_{season}.csv"
    if csv.exists():
        log.info("  Cached: %s", csv.name)
        return pd.read_csv(csv)
    try:
        df = nba_call(endpoint_cls, f"{tag} {season}", season=season, **extra)
        df["SEASON"] = season
        df.to_csv(csv, index=False)
        log.info("  Saved %s", csv.name)
        return df
    except RuntimeError:
        log.error("  SKIPPING %s %s — re-run to retry.", tag, season)
        return None


def pull_all_seasons(endpoint_cls, tag: str, seasons: list, extra: dict,
                     workers: int = NBA_WORKERS) -> pd.DataFrame:
    """Pull multiple seasons in parallel (workers threads), return concatenated df."""
    frames = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(pull_season, endpoint_cls, tag, s, extra): s
            for s in seasons
        }
        for fut in as_completed(futures):
            df = fut.result()
            if df is not None:
                frames.append(df)
    if not frames:
        raise RuntimeError(f"No data for {tag}")
    return pd.concat(frames, ignore_index=True)

# ---------------------------------------------------------------------------
# Step 1 — clutch_usage missing seasons
# ---------------------------------------------------------------------------
def step1_clutch_usage():
    log.info("=" * 60)
    log.info("STEP 1 — clutch_usage (missing seasons)")
    from nba_api.stats.endpoints import LeagueDashPlayerClutch
    missing = [s for s in SEASONS
               if not (DATA_DIR / f"clutch_usage_{s}.csv").exists()]
    if not missing:
        log.info("  All clutch_usage seasons already cached — skipping.")
        return
    log.info("  Missing: %s", missing)
    pull_all_seasons(
        LeagueDashPlayerClutch, "clutch_usage", missing,
        dict(
            clutch_time="Last 5 Minutes",
            ahead_behind="Ahead or Behind",
            point_diff=5,
            measure_type_detailed_defense="Usage",
            per_mode_detailed="PerGame",
            season_type_all_star="Regular Season",
        ),
    )
    log.info("  Step 1 done.")

# ---------------------------------------------------------------------------
# Step 2 — league_stats (auto-skipped if complete)
# ---------------------------------------------------------------------------
def step2_league_stats():
    log.info("=" * 60)
    log.info("STEP 2 — league_stats")
    from nba_api.stats.endpoints import LeagueDashPlayerStats
    missing = [s for s in SEASONS
               if not (DATA_DIR / f"league_stats_{s}.csv").exists()]
    if not missing:
        log.info("  All league_stats seasons cached — skipping.")
        return
    log.info("  Missing: %s", missing)
    pull_all_seasons(
        LeagueDashPlayerStats, "league_stats", missing,
        dict(
            per_mode_detailed="Totals",
            season_type_all_star="Regular Season",
        ),
    )
    log.info("  Step 2 done.")

# ---------------------------------------------------------------------------
# Step 3 — team totals (overall + clutch)
# ---------------------------------------------------------------------------
def step3_team_totals():
    log.info("=" * 60)
    log.info("STEP 3 — team totals (overall + clutch)")
    from nba_api.stats.endpoints import LeagueDashTeamStats

    # overall
    missing_overall = [s for s in SEASONS
                       if not (DATA_DIR / f"team_overall_{s}.csv").exists()]
    if missing_overall:
        log.info("  Fetching team_overall for: %s", missing_overall)
        pull_all_seasons(
            LeagueDashTeamStats, "team_overall", missing_overall,
            dict(per_mode_detailed="Totals", season_type_all_star="Regular Season"),
        )
    else:
        log.info("  All team_overall cached — skipping.")

    # clutch — try LeagueDashTeamClutch first, fall back to LeagueDashTeamStats w/ clutch params
    missing_clutch = [s for s in SEASONS
                      if not (DATA_DIR / f"team_clutch_{s}.csv").exists()]
    if missing_clutch:
        log.info("  Fetching team_clutch for: %s", missing_clutch)
        try:
            from nba_api.stats.endpoints import LeagueDashTeamClutch
            pull_all_seasons(
                LeagueDashTeamClutch, "team_clutch", missing_clutch,
                dict(
                    clutch_time="Last 5 Minutes",
                    ahead_behind="Ahead or Behind",
                    point_diff=5,
                    per_mode_detailed="Totals",
                    season_type_all_star="Regular Season",
                ),
            )
        except ImportError:
            log.warning("  LeagueDashTeamClutch not in nba_api; using LeagueDashTeamStats "
                        "with clutch time params instead.")
            pull_all_seasons(
                LeagueDashTeamStats, "team_clutch", missing_clutch,
                dict(
                    per_mode_detailed="Totals",
                    season_type_all_star="Regular Season",
                    clutch_time="Last 5 Minutes",
                    ahead_behind="Ahead or Behind",
                    point_diff=5,
                ),
            )
    else:
        log.info("  All team_clutch cached — skipping.")
    log.info("  Step 3 done.")

# ---------------------------------------------------------------------------
# Step 4 — home / road clutch splits
# ---------------------------------------------------------------------------
def _pull_location_season(season: str, location: str) -> Optional[pd.DataFrame]:
    from nba_api.stats.endpoints import LeagueDashPlayerClutch
    tag  = f"clutch_{'home' if location == 'Home' else 'road'}"
    csv  = DATA_DIR / f"{tag}_{season}.csv"
    if csv.exists():
        log.info("  Cached: %s", csv.name)
        return pd.read_csv(csv)
    try:
        df = nba_call(
            LeagueDashPlayerClutch, f"{tag} {season}",
            season=season,
            clutch_time="Last 5 Minutes",
            ahead_behind="Ahead or Behind",
            point_diff=5,
            measure_type_detailed_defense="Base",
            per_mode_detailed="Totals",
            season_type_all_star="Regular Season",
            location_nullable=location,
        )
        df["SEASON"]   = season
        df["LOCATION"] = location
        df.to_csv(csv, index=False)
        log.info("  Saved %s", csv.name)
        return df
    except RuntimeError:
        log.error("  SKIPPING %s %s", tag, season)
        return None


def step4_home_road():
    log.info("=" * 60)
    log.info("STEP 4 — home/road clutch splits")
    tasks = [
        (s, loc)
        for s   in SEASONS
        for loc in ("Home", "Road")
        if not (DATA_DIR / f"clutch_{'home' if loc == 'Home' else 'road'}_{s}.csv").exists()
    ]
    if not tasks:
        log.info("  All home/road splits cached — skipping.")
        return
    log.info("  %d calls needed.", len(tasks))
    with ThreadPoolExecutor(max_workers=NBA_WORKERS) as pool:
        futures = [pool.submit(_pull_location_season, s, loc) for s, loc in tasks]
        for fut in as_completed(futures):
            fut.result()   # surface any exceptions
    log.info("  Step 4 done.")

# ---------------------------------------------------------------------------
# Step 5 — priority-player game logs
# ---------------------------------------------------------------------------
def _pull_gamelog(player_id: int, player_name: str, season: str) -> Optional[pd.DataFrame]:
    from nba_api.stats.endpoints import PlayerGameLog
    csv = GAMELOGS / f"gamelog_{player_id}_{season}.csv"
    if csv.exists():
        return pd.read_csv(csv)
    try:
        df = nba_call(
            PlayerGameLog, f"gamelog {player_name} {season}",
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season",
        )
        if df.empty:
            log.info("  No games: %s %s", player_name, season)
            df.to_csv(csv, index=False)   # cache empty file to avoid re-fetch
            return None
        df["PLAYER_ID"] = player_id
        df["SEASON"]    = season
        # Normalise home/road from MATCHUP string ("vs." = Home, "@" = Road)
        df["LOCATION"]  = df["MATCHUP"].apply(
            lambda m: "Home" if "vs." in str(m) else "Road"
        )
        df.to_csv(csv, index=False)
        log.info("  Saved %s (%d games)", csv.name, len(df))
        return df
    except RuntimeError:
        log.error("  SKIPPING gamelog %s %s", player_name, season)
        return None


def step5_gamelogs() -> list:
    """Returns list of unique GAME_ID values for priority players."""
    log.info("=" * 60)
    log.info("STEP 5 — priority-player game logs")
    tasks = [
        (pid, name, season)
        for pid, name in PRIORITY_PLAYERS.items()
        for season in SEASONS
    ]
    all_game_ids = set()
    with ThreadPoolExecutor(max_workers=NBA_WORKERS) as pool:
        futures = {
            pool.submit(_pull_gamelog, pid, name, season): (pid, name, season)
            for pid, name, season in tasks
        }
        for fut in as_completed(futures):
            df = fut.result()
            if df is not None and not df.empty and "Game_ID" in df.columns:
                all_game_ids.update(df["Game_ID"].astype(str).tolist())

    unique_csv = GAMELOGS / "priority_unique_game_ids.csv"
    uid_df = pd.DataFrame(sorted(all_game_ids), columns=["GAME_ID"])
    uid_df.to_csv(unique_csv, index=False)
    log.info("  Unique priority games: %d  -> %s", len(uid_df), unique_csv.name)
    log.info("  Step 5 done.")
    return sorted(all_game_ids)

# ---------------------------------------------------------------------------
# Step 6 — event-level PBP (nba_api PlayByPlayV2 / stats.nba.com)
# ---------------------------------------------------------------------------

def _pctimestring_to_seconds(clock: str) -> Optional[int]:
    """Convert 'M:SS' clock string to total seconds remaining in period."""
    try:
        parts = str(clock).strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None


def _parse_margin(raw: str) -> Optional[int]:
    """
    Parse SCOREMARGIN from PlayByPlayV2.
    Values: '+5', '-3', 'TIE', '', or None.
    Returns int margin (positive = home team leads) or None.
    """
    if not raw or str(raw).strip() in ("", "TIE"):
        return 0 if str(raw).strip() == "TIE" else None
    try:
        return int(str(raw).strip().replace("+", ""))
    except ValueError:
        return None


def _parse_pbp_game(game_id: str, season: str) -> list[dict]:
    """
    Fetch PlayByPlayV2 for one game via nba_api (stats.nba.com).
    Uses per-game CSV cache in PBP_RAW. Filters to clutch FG events.
    Returns list of row-dicts.
    """
    from nba_api.stats.endpoints import PlayByPlayV2

    cache_csv = PBP_RAW / f"pbp_{game_id}.csv"

    # Load or fetch raw PBP
    if cache_csv.exists():
        raw = pd.read_csv(cache_csv)
    else:
        pbp_limiter.acquire()
        time.sleep(random.uniform(0, 5))  # extra jitter so pattern isn't robotic
        try:
            result = PlayByPlayV2(game_id=game_id, timeout=NBA_TIMEOUT)
            raw = result.get_data_frames()[0]
            raw.to_csv(cache_csv, index=False)
        except Exception as exc:
            log.warning("  PBP fetch failed game=%s: %s", game_id, exc)
            return []

    if raw.empty:
        return []

    # EVENTMSGTYPE 1 = made FG,  2 = missed FG
    fg_events = raw[raw["EVENTMSGTYPE"].isin([1, 2])].copy()

    rows = []
    for _, ev in fg_events.iterrows():
        period = ev.get("PERIOD")
        if period is None or int(period) < CLUTCH_PERIOD_MIN:
            continue

        clock = ev.get("PCTIMESTRING", "")
        secs  = _pctimestring_to_seconds(clock)
        if secs is None or secs > CLUTCH_SECONDS_MAX:
            continue

        margin = _parse_margin(str(ev.get("SCOREMARGIN", "")))
        if margin is None or abs(margin) > CLUTCH_MARGIN_MAX:
            continue

        is_made     = int(ev.get("EVENTMSGTYPE", 2)) == 1
        player_id   = ev.get("PLAYER1_ID")
        player2_id  = ev.get("PLAYER2_ID") if is_made else None
        is_assisted = bool(is_made and player2_id and int(player2_id) != 0)

        # Shot value: look for "3PT" in the play description columns
        desc = " ".join([
            str(ev.get("HOMEDESCRIPTION", "") or ""),
            str(ev.get("VISITORDESCRIPTION", "") or ""),
            str(ev.get("NEUTRALDESCRIPTION", "") or ""),
        ])
        shot_value = 3 if "3PT" in desc.upper() else 2

        rows.append(dict(
            game_id      = game_id,
            season       = season,
            period       = int(period),
            seconds_rem  = secs,
            score_margin = margin,
            player_id    = player_id,
            player2_id   = int(player2_id) if is_assisted else None,
            is_made      = is_made,
            is_assisted  = is_assisted,
            shot_value   = shot_value,
        ))
    return rows


def _game_season_from_id(game_id: str) -> str:
    """
    NBA game ID format: 002SYYOOONNNN (10 chars zero-padded)
      positions [3:5] = 2-digit season start year  (e.g. "17" → 2017-18)
    Example: 0021700007 → "17" → 2017-18
    """
    try:
        year_2d = int(str(game_id).zfill(10)[3:5])
        year    = 2000 + year_2d
        return f"{year}-{str(year + 1)[-2:]}"
    except (ValueError, IndexError):
        return "unknown"


def step6_pbp(game_ids: list) -> pd.DataFrame:
    log.info("=" * 60)
    log.info("STEP 6 — PBP event parsing (%d games)", len(game_ids))

    out_csv = PBP_OUT / "priority_clutch_events.csv"
    # Load any already-parsed events so we can skip completed games
    parsed_games: set = set()
    existing_rows: list[dict] = []
    if out_csv.exists():
        try:
            existing = pd.read_csv(out_csv)
            if not existing.empty and "game_id" in existing.columns:
                parsed_games = set(existing["game_id"].astype(str))
                existing_rows = existing.to_dict("records")
                log.info("  Resuming — %d games already parsed.", len(parsed_games))
            else:
                log.info("  Events file empty — starting fresh.")
        except (pd.errors.EmptyDataError, KeyError):
            log.info("  Events file unreadable — starting fresh.")

    todo = [g for g in game_ids if str(g) not in parsed_games]
    log.info("  %d games left to parse.", len(todo))

    all_rows = list(existing_rows)
    lock = threading.Lock()

    def _process(gid: str):
        season = _game_season_from_id(gid)
        rows   = _parse_pbp_game(gid, season)
        with lock:
            all_rows.extend(rows)
        return len(rows)

    checkpoint_every = 50   # save CSV every N games to protect against crashes
    with ThreadPoolExecutor(max_workers=PBP_WORKERS) as pool:
        futures = {pool.submit(_process, g): g for g in todo}
        completed = 0
        for fut in as_completed(futures):
            try:
                n = fut.result()
            except Exception as exc:
                log.warning("  Game error: %s", exc)
                n = 0
            completed += 1
            if completed % checkpoint_every == 0:
                with lock:
                    snap = list(all_rows)
                pd.DataFrame(snap).to_csv(out_csv, index=False)
                log.info("  Checkpoint: %d games done, %d clutch events so far.",
                         completed, len(snap))

    events_df = pd.DataFrame(all_rows)
    events_df.to_csv(out_csv, index=False)
    log.info("  Total clutch events: %d  -> %s", len(events_df), out_csv.name)
    log.info("  Step 6 done.")
    return events_df

# ---------------------------------------------------------------------------
# Step 7 — shot-creation summaries
# ---------------------------------------------------------------------------
def step7_shot_creation(events_df: pd.DataFrame):
    log.info("=" * 60)
    log.info("STEP 7 — shot-creation summary tables")

    if events_df.empty:
        log.warning("  No PBP events — skipping Step 7.")
        return

    priority_ids = set(PRIORITY_PLAYERS.keys())
    df = events_df[events_df["player_id"].isin(priority_ids)].copy()
    df["player_name"] = df["player_id"].map(PRIORITY_PLAYERS)

    # Per player-season
    grp = df.groupby(["player_id", "player_name", "season"])
    by_season = grp.agg(
        clutch_made_fg            = ("is_made", "sum"),
        clutch_att_fg             = ("is_made", "count"),
        clutch_made_fg_assisted   = ("is_assisted",
                                     lambda s: (s & df.loc[s.index, "is_made"]).sum()),
    ).reset_index()
    by_season["clutch_made_fg_unassisted"] = (
        by_season["clutch_made_fg"] - by_season["clutch_made_fg_assisted"]
    )
    by_season["clutch_assisted_rate"]   = (
        by_season["clutch_made_fg_assisted"]   / by_season["clutch_made_fg"].replace(0, pd.NA)
    )
    by_season["clutch_unassisted_rate"] = (
        by_season["clutch_made_fg_unassisted"] / by_season["clutch_made_fg"].replace(0, pd.NA)
    )
    by_season_csv = DATA_DIR / "priority_shot_creation_by_season.csv"
    by_season.to_csv(by_season_csv, index=False)
    log.info("  Saved %s  (%d rows)", by_season_csv.name, len(by_season))

    # Career summary
    career = by_season.groupby(["player_id", "player_name"]).agg(
        seasons               = ("season", "count"),
        clutch_made_fg        = ("clutch_made_fg", "sum"),
        clutch_att_fg         = ("clutch_att_fg", "sum"),
        clutch_made_fg_assisted   = ("clutch_made_fg_assisted", "sum"),
        clutch_made_fg_unassisted = ("clutch_made_fg_unassisted", "sum"),
    ).reset_index()
    career["clutch_assisted_rate"]   = (
        career["clutch_made_fg_assisted"]   / career["clutch_made_fg"].replace(0, pd.NA)
    )
    career["clutch_unassisted_rate"] = (
        career["clutch_made_fg_unassisted"] / career["clutch_made_fg"].replace(0, pd.NA)
    )
    # Season-by-season trend (assisted_rate per season, comma-separated)
    trend = (
        by_season.sort_values("season")
        .groupby(["player_id", "player_name"])["clutch_assisted_rate"]
        .apply(lambda s: ",".join(f"{v:.3f}" for v in s.dropna()))
        .reset_index(name="assisted_rate_trend")
    )
    career = career.merge(trend, on=["player_id", "player_name"], how="left")

    career_csv = DATA_DIR / "priority_shot_creation_summary.csv"
    career.to_csv(career_csv, index=False)
    log.info("  Saved %s  (%d rows)", career_csv.name, len(career))
    log.info("  Step 7 done.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("PHASE 2 — Data Collection")
    log.info("Seasons: %s", SEASONS)
    log.info("NBA call interval: %ds  |  PBP interval: %ds", NBA_CALL_INTERVAL, PBP_CALL_INTERVAL)
    log.info("=" * 60)

    step1_clutch_usage()
    step2_league_stats()
    step3_team_totals()
    step4_home_road()
    game_ids = step5_gamelogs()

    if game_ids:
        events_df = step6_pbp(game_ids)
    else:
        log.warning("No game IDs found — Steps 6 & 7 skipped.")
        events_df = pd.DataFrame()

    step7_shot_creation(events_df)

    # ---- Final completeness report ----------------------------------------
    log.info("=" * 60)
    log.info("PHASE 2 SUMMARY")
    checks = {
        "clutch_usage":   [DATA_DIR / f"clutch_usage_{s}.csv"   for s in SEASONS],
        "league_stats":   [DATA_DIR / f"league_stats_{s}.csv"   for s in SEASONS],
        "team_overall":   [DATA_DIR / f"team_overall_{s}.csv"   for s in SEASONS],
        "team_clutch":    [DATA_DIR / f"team_clutch_{s}.csv"    for s in SEASONS],
        "clutch_home":    [DATA_DIR / f"clutch_home_{s}.csv"    for s in SEASONS],
        "clutch_road":    [DATA_DIR / f"clutch_road_{s}.csv"    for s in SEASONS],
    }
    for tag, paths in checks.items():
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            log.warning("  INCOMPLETE  %s — missing: %s", tag, missing)
        else:
            log.info("  COMPLETE    %s — all 8 seasons", tag)

    log.info("  Unique priority game IDs: %d", len(game_ids))
    pbp_events = PBP_OUT / "priority_clutch_events.csv"
    if pbp_events.exists():
        n = sum(1 for _ in open(pbp_events)) - 1
        log.info("  Clutch PBP events: %d", n)
    log.info("Phase 2 done.")


if __name__ == "__main__":
    main()
