import json
import time
from datetime import datetime, date

import cloudscraper
import requests
import yaml
from bs4 import BeautifulSoup

from parsers.ncaa import ncaa_date_range
from parsers.hockeytech import map_season_phases

REQUEST_TIMEOUT = 30

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ==========================
# Generic helpers
# ==========================
def fetch_html(url, attempts=3, timeout=(10, 60), headers=None):
    """GET a URL with retries. Returns the response text, or None on failure."""
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=headers or BROWSER_HEADERS)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            print(f"[WARN] fetch attempt {attempt}/{attempts} failed for {url}: {e}")
            if attempt < attempts:
                time.sleep(5 * attempt)
    return None


def scraper_get_text(url, attempts=3):
    """cloudscraper GET with timeout + retries. Returns text, or None on failure."""
    for attempt in range(1, attempts + 1):
        try:
            scraper = cloudscraper.create_scraper()
            r = scraper.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"[WARN] scraper attempt {attempt}/{attempts} failed for {url}: {e}")
            if attempt < attempts:
                time.sleep(5 * attempt)
    return None


def parse_any_date(s):
    formats = [
        "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%m-%d-%y", "%m/%d/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Unrecognized date format: {s}")


# ==========================
# HockeyTech helpers
# ==========================
def hockeytech_fetch_seasons(base_url):
    # Convert schedule URL -> seasons URL
    seasons_url = base_url.replace("view=schedule", "view=seasons") + "&fmt=json"
    raw = scraper_get_text(seasons_url)
    if raw is None:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[WARN] HockeyTech seasons response is not valid JSON: {e}")
        return []
    return data.get("SiteKit", {}).get("Seasons", [])


def hockeytech_pick_current_season(seasons):
    today = datetime.now()
    cutoff = datetime(today.year, 7, 1)
    if today >= cutoff:
        target_year = today.year
    else:
        target_year = today.year - 1

    for s in seasons:
        name = s.get("season_name", "").lower()
        if "memorial cup" in name:
            start = datetime.fromisoformat(s["start_date"])
            if start.year == target_year:
                return s

    for s in seasons:
        if s.get("playoff") == "0" and "Regular Season" in s.get("season_name", ""):
            start = datetime.fromisoformat(s["start_date"])
            if start.year == target_year:
                return s

    return None


def hockeytech_find_playoffs(seasons, regular_season):
    if not regular_season:
        return None

    reg_end = datetime.fromisoformat(regular_season["end_date"])
    for s in seasons:
        if s.get("playoff") == "1":
            start = datetime.fromisoformat(s["start_date"])
            if start > reg_end:
                return s
    return None


# ==========================
# VHL helpers
# ==========================
def vhl_fetch_calendar(base_url):
    html = fetch_html(base_url)
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    tournament_select = soup.find("select", {"name": "tournament"})
    club_select = soup.find("select", {"name": "club"})
    if not tournament_select or not club_select:
        print("[WARN] VHL page missing tournament/club selects (blocked or layout change?)")
        return None

    seasons = []
    for option in tournament_select.find_all("option"):
        value = option.get("value", "").strip()
        label = option.get_text(" ", strip=True)
        if not value or not label:
            continue

        parts = [part.strip() for part in label.split("|", 1)]
        if len(parts) != 2:
            continue

        season_name, stage = parts
        season_id = value.rstrip("/").split("/")[-1]
        if not season_id.isdigit():
            continue

        seasons.append({
            "season_id": season_id,
            "season": season_name,
            "stage": stage,
            "label": label,
        })

    teams = {}
    for option in club_select.find_all("option"):
        value = option.get("value", "").strip()
        site_name = option.get_text(" ", strip=True)
        if not value or not site_name:
            continue

        if site_name.lower() == "all":
            continue

        parts = value.rstrip("/").split("/")
        if len(parts) < 2:
            continue

        team_id = parts[-1]
        if not team_id.isdigit():
            continue

        teams[site_name] = team_id

    return {
        "seasons": seasons,
        "teams": teams,
    }


def vhl_current_season_name():
    today = datetime.now()
    if today >= datetime(today.year, 7, 1):
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year % 100:02d}/{(start_year + 1) % 100:02d}"


def vhl_find_current_seasons(seasons):
    target = vhl_current_season_name()
    regular = None
    playoffs = None
    for season in seasons:
        if season["season"] != target:
            continue
        stage = season["stage"].strip().lower()
        if stage == "regular season":
            regular = season
        elif stage == "playoffs":
            playoffs = season
    return regular, playoffs


def vhl_find_team_id(teams, configured_name):
    configured = configured_name.strip().lower()
    for site_name, team_id in teams.items():
        if site_name.strip().lower() == configured:
            return team_id

    for site_name, team_id in teams.items():
        site = site_name.strip().lower()
        if configured.startswith(site + " "):
            return team_id
    return None


# ==========================
# PublicationSports helpers
# ==========================
def extract_latest_season(html):
    soup = BeautifulSoup(html, "html.parser")
    season_select = soup.find("select", {"class": "season_select"})
    if not season_select:
        return None

    values = []
    for opt in season_select.find_all("option"):
        try:
            values.append(int(opt.get("value")))
        except (TypeError, ValueError):
            pass

    return str(max(values)) if values else None


def extract_regular_subseason(html):
    soup = BeautifulSoup(html, "html.parser")
    sub_select = soup.find("select", {"class": "sub_season_select"})
    if not sub_select:
        return []

    subseasons = []
    playoff_keywords = ["quart", "demi", "finale", "championnat", "coupe", "séries"]
    for opt in sub_select.find_all("option"):
        val = opt.get("value")
        name = opt.text.strip()
        if not val:
            continue
        if "saison régulière" in name.lower():
            subseasons.append((val, name))
            continue

        if any(k in name.lower() for k in playoff_keywords):
            subseasons.append((val, name))

    return subseasons


# ==========================
# Central parser registry
# ==========================
PARSER_HANDLERS = {}


def register_parser(name):
    def decorator(func):
        PARSER_HANDLERS[name] = func
        return func
    return decorator


# =========================
# Shared season-range helper
# =========================
def current_hockey_season_range():
    today = datetime.now()
    july_first = datetime(today.year, 7, 1)
    if today < july_first:
        start_year = today.year - 1
    else:
        start_year = today.year
    return (
        date(start_year, 7, 1),
        date(start_year + 1, 7, 1),
    )


# ============================================
# Unified team iteration
# ============================================
def iter_teams(data):
    for team in data.get("teams", []):
        yield team["name"], team.get("team_id"), team


def load_feeds():
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feeds = []

    for league, data in config.items():
        if league.startswith("#"):
            continue

        parser = data.get("parser")
        handler = PARSER_HANDLERS.get(parser)

        if not handler:
            print(f"Warning: Unknown parser for league '{league}'")
            continue

        # One failing league must not kill the whole run
        try:
            handler(feeds, league, data)
        except Exception as e:
            print(f"[ERROR] Handler for '{league}' failed: {type(e).__name__}: {e}")

    return feeds


# ============================
# CHL Europe (JSON + filters)
# ============================
@register_parser("chl_europe")
def handle_chl_europe(feeds, league, data):
    url = data["url"]
    for team_name, team_id, team in iter_teams(data):
        feeds.append((league, team_name, url, [team["code"]], "chl_europe"))


# ============================
# DEL parser (HTML)
# ============================
@register_parser("del")
def handle_del(feeds, league, data):
    base_url = data["base_url"]
    for team_name, team_id, team in iter_teams(data):
        url = f"{base_url}/{team_id}"
        feeds.append((league, team_name, url, None, "del"))


# ============================
# HockeyTech leagues (AHL, ECHL, LHJMQ, OHL, WHL, BCHL, PWHL)
# ============================
@register_parser("hockeytech")
def handle_hockeytech(feeds, league, data):
    if league == "Hockey_Canada":
        return handle_hockey_canada(feeds, league, data)

    base_url = data["base_url"]
    seasons = hockeytech_fetch_seasons(base_url)
    regular = hockeytech_pick_current_season(seasons)
    playoffs = hockeytech_find_playoffs(seasons, regular)

    if not data.get("teams"):
        if regular:
            season_id = regular["season_id"]
            season_name = regular["season_name"]
            url = f"{base_url}&season_id={season_id}"
            feeds.append((league, f"{league} ({season_name})", url, [], "hockeytech"))
        return

    for season_obj in [regular, playoffs]:
        if not season_obj:
            continue
        season_id = season_obj["season_id"]
        season_name = season_obj["season_name"]

        for team_name, team_id, team in iter_teams(data):
            url = (
                f"{base_url}"
                f"&team_id={team_id}"
                f"&season_id={season_id}"
            )

            feeds.append((league, f"{team_name} ({season_name})", url, [team_id], "hockeytech"))


# ============================
# HockeyTech leagues (hockey canada)
# ============================
def handle_hockey_canada(feeds, league, data):
    base_url = data["base_url"]
    season_start, season_end = current_hockey_season_range()

    for l in data["league_id"]:
        seasons_url = f"{base_url}&view=seasons&league_id={l}"
        try:
            r = requests.get(seasons_url, timeout=REQUEST_TIMEOUT, headers=BROWSER_HEADERS)
            r.raise_for_status()
            seasons = r.json()["SiteKit"]["Seasons"]
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            print(f"[WARN] Hockey Canada league_id={l} seasons fetch failed: {e}")
            continue

        filtered_seasons = []
        for s in seasons:
            start_date = datetime.strptime(s["start_date"], "%Y-%m-%d")
            if start_date.date() >= season_start:
                filtered_seasons.append(s)

        season_ids = [s["season_id"] for s in filtered_seasons]

        for season_id in season_ids:
            url = f"{base_url}&view=schedule&season_id={season_id}"
            feeds.append((league, f"(S{season_id})", url, [], "hockeytech"))


# ============================
# KHL
# ============================
@register_parser("khl")
def handle_khl(feeds, league, data):
    base_url = data["base_url"]

    season_start, season_end = current_hockey_season_range()
    season_start_ts = int(datetime.combine(season_start, datetime.min.time()).timestamp())
    season_end_ts = int(datetime.combine(season_end, datetime.min.time()).timestamp())

    for team_name, team_id, team in iter_teams(data):
        team_id = team["team_id"]
        url = (
            f"{base_url}"
            f"?q[team_a_or_team_b_in][]={team_id}"
            f"&q[start_at_gt_time_from_unixtime]={season_start_ts}"
            f"&q[start_at_lt_time_from_unixtime]={season_end_ts}"
            f"&order_direction=asc"
        )

        feeds.append((league, team_name, url, [team_id], "khl"))


# ============================
# LIIGA JSON parser
# ============================
@register_parser("liiga")
def handle_liiga(feeds, league, data):
    base_url = data["base_url"]
    season_url = (
        "https://cdn.builder.io/api/v3/query/"
        "f11503eeae084753968caac3899a5d78/season-teams-configuration"
    )
    raw = scraper_get_text(season_url)
    if raw is None:
        print("[ERROR] Skipping Liiga: could not fetch season configuration")
        return

    season_dict = json.loads(raw)
    seasonTeams = season_dict["season-teams-configuration"][0]["data"]["seasonTeams"]
    season = sorted(seasonTeams.keys())[-1]
    tournaments = data.get("tournament", [])
    if isinstance(tournaments, str):
        tournaments = [tournaments]

    for team_name, team_id, team in iter_teams(data):
        for t in tournaments:
            url = f"{base_url}?tournament={t}&season={season}"
            feeds.append((league, f"{team_name} (T{t})", url, [team_id], "liiga"))


# ============================
# NCAA_EAST (Hockey East conference)
# ============================
@register_parser("ncaa_east")
def handle_ncaa_east(feeds, league, data):
    from_date, to_date = ncaa_date_range()
    from_date = parse_any_date(from_date)
    to_date = parse_any_date(to_date)

    for team_name, team_id, team in iter_teams(data):
        base_url = team["base_url"]

        url = (
            f"{base_url}/api/v2/Calendar/from/{from_date}/to/{to_date}"
            f"?sportId={team['sport_id']}"
        )

        feeds.append((league, team_name, url, [], "ncaa_east"))


# ============================
# NCAA_conf (AHA, CCHC, ECAC, NCHC)
# ============================
@register_parser("ncaa_conf")
def handle_ncaa_conf(feeds, league, data):
    base_url = data["base_url"]
    season_start, season_end = current_hockey_season_range()

    url = (
        f"{base_url}"
        f"&start={season_start}"
        f"&end={season_end}"
    )

    for team_name, team_id, team in iter_teams(data):
        feeds.append((league, team_name, url, [], "ncaa_conf"))


# ============================
# NL JSON parser
# ============================
@register_parser("nl")
def handle_nl(feeds, league, data):
    url = data["base_url"]
    for team_name, team_id, team in iter_teams(data):
        feeds.append((league, team_name, url, [team_id], "nl"))


# ============================
# NHL (JSON)
# ============================
@register_parser("nhl")
def handle_nhl(feeds, league, data):
    for team_name, team_id, team in iter_teams(data):
        feeds.append((league, team_name, team["url"], [], "nhl"))


# ============================
# Publication Sports league (LHMAAAQ et LHJAAAQ)
# ============================
@register_parser("publicationsports")
def handle_publicationsports(feeds, league, data):
    base_url = data["base_url"]
    team_filter = [str(team_id) for _, team_id, _ in iter_teams(data)]

    html = scraper_get_text(base_url)
    if html is None:
        print(f"[ERROR] Skipping {league}: could not fetch {base_url}")
        return

    current_season = extract_latest_season(html)
    current_sub = extract_regular_subseason(html)

    if not current_season or not current_sub:
        print(f"[WARN] Skipping {league}: no season/subseason found on page")
        return

    for team_name, team_id, team in iter_teams(data):
        for sub_id, sub_name in current_sub:
            if league == "LHMAAAQ":
                category = "5366"
                full_url = (
                    f"https://www.m18aaa.com/fr/stats/horaire.html?"
                    f"season={current_season}&subSeason={sub_id}&category={category}"
                )
            elif league == "LHJAAAQ":
                category = "1093"
                full_url = (
                    f"https://www.lhjaaaq.com/fr/stats/horaire.html?"
                    f"season={current_season}&subSeason={sub_id}&category={category}"
                )
            else:
                print(f"[WARN] publicationsports: unknown league '{league}'")
                return

            feeds.append((league, team_name, full_url, team_filter, "publicationsports"))


# ============================
# SHL
# ============================
@register_parser("shl")
def handle_shl(feeds, league, data):
    base_url = data["base_url"]
    seasons_url = base_url.replace("game-schedule", "season-series-game-types-filter")
    raw = scraper_get_text(seasons_url)
    if raw is None:
        print("[ERROR] Skipping SHL: could not fetch season filters")
        return

    shl_dict = json.loads(raw)
    season = shl_dict.get("season", [{}])[0].get("uuid", "")
    series = shl_dict.get("series", [{}, {}])[1].get("uuid", "")
    game_type = shl_dict.get("gameType", [{}])[0].get("uuid", "")

    for team_name, team_id, team in iter_teams(data):
        team_uuid = team["uuid"]

        url = (
            f"{base_url}"
            f"?seasonUuid={season}"
            f"&seriesUuid={series}"
            f"&gameTypeUuid={game_type}"
            f"&teams[]={team_uuid}"
        )

        feeds.append((league, team_name, url, None, "shl"))


# ============================
# UFA JSON feed
# ============================
@register_parser("ufa")
def handle_ufa(feeds, league, data):
    base_url = data["base_url"]
    for team_name, team_id, team in iter_teams(data):
        url = f"{base_url}&teamID={team_id}"
        feeds.append((league, team_name, url, [], "ufa"))


# ============================
# VHL parser
# ============================
@register_parser("vhl")
def handle_vhl(feeds, league, data):
    base_url = data["base_url"]
    calendar = vhl_fetch_calendar(base_url)
    if not calendar:
        print("[ERROR] Skipping VHL: could not load calendar")
        return

    seasons = calendar["seasons"]
    teams = calendar["teams"]
    regular, playoffs = vhl_find_current_seasons(seasons)
    if not regular:
        print(f"[ERROR] Skipping VHL: no regular season found for {vhl_current_season_name()}")
        return

    regular_season_id = regular["season_id"]

    for team_name, _, team in iter_teams(data):
        if team_name.lower() == "akademia mikhailov":
            team_name = "AKM"

        team_id = vhl_find_team_id(teams, team_name)
        if not team_id:
            print(f"VHL Warning: could not find {team_name} on VHL Page")
            continue

        # Same URL shape for both (no trailing slash), matching the regular-season URL
        regular_url = f"{base_url}{regular_season_id}/0/{team_id}"
        feeds.append((league, f"{team_name} (Regular Season)", regular_url, regular_season_id, "vhl"))

        if playoffs:
            playoff_season_id = playoffs["season_id"]
            playoff_url = f"{base_url}{playoff_season_id}/0/{team_id}"
            feeds.append((league, f"{team_name} (Playoffs)", playoff_url, playoff_season_id, "vhl"))
