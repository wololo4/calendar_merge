import requests
import json
from datetime import datetime, timedelta, timezone, date
from utils.calendar import create_calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

HCanada_Tournament = {
    "7": "World Junior Championship",
    "24": "Telus Cup",
    "26": "World U18 Championship",
    "27": "World Championship",
    "32": "Centennial Cup",
    "34": "Hlinka Gretzky Cup",
    "38": "Olympic Games",
}

def fetch_seasons_for_league(league_id):
    url = ("https://lscluster.hockeytech.com/feed/index.php?"
        "feed=modulekit&view=seasons&client_code=hockeycanada&key=a575453e4321c122"
        f"&league_id={league_id}")
    return requests.get(url).json()

def slugify(name):
    return (
        name.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ô", "o")
        .replace("î", "i")
        .replace(" ", "-")
        .replace("'", "")
        .replace(",", "")
        .replace("--", "")
        .replace("-(ohl)", "")
    )

def flo_event_link(flo_id, yyyy, away_slug, home_slug):
    if not flo_id or flo_id == "0":
        return None
    return f"https://www.flohockey.tv/events/{flo_id}-{yyyy}-{away_slug}-vs-{home_slug}"

def hockeytech_game_center(league, game_id, yyyy, mm, dd, home_slug, away_slug, home_code, away_code):
    routes = {
        "ahl": f"https://theahl.com/stats/game-center/{game_id}",
        "bchl": f"https://bchl.ca/stats/game-center/{game_id}",
        "chl": f"https://chl.ca/games/chl/chl/{home_code}-{away_code}/{game_id}",
        "echl": f"https://echl.com/games/{yyyy}/{mm}/{dd}/{home_slug}-vs-{away_slug}",
        "lhjmq": f"https://chl.ca/lhjmq/gamecentre/{game_id}",
        "ohl": f"https://chl.ca/ohl/gamecentre/{game_id}",
        "whl": f"https://chl.ca/whl/gamecentre/{game_id}",
    }
    return routes.get(league)

def hockeycanada_game_center(league_id, game_id, current_year, current_season):
    routes = {
        "7": f"https://www.hockeycanada.ca/en-ca/team-canada/men/junior/{current_season}/world-championship/stats/game-summary/{game_id}",
        "24": f"https://www.hockeycanada.ca/en-ca/national-championships/men/u18-club/{current_year}/stats/game-summary/{game_id}",
        "26": f"https://www.hockeycanada.ca/en-ca/team-canada/men/under-18/{current_season}/world-championship/stats/game-summary/{game_id}",
        "27": f"https://www.hockeycanada.ca/en-ca/team-canada/men/national/{current_season}/world-championship/stats/game-summary/{game_id}",
        "32": f"https://www.hockeycanada.ca/en-ca/national-championships/men/national-junior-a/{current_year}/stats/game-summary/{game_id}",
        "34": f"https://www.hlinkagretzkycup.ca/en-ca/season/{current_year}/stats/game-summary?gameid={game_id}",
        "38": f"https://www.hockeycanada.ca/en-ca/team-canada/men/olympics/{current_year}/stats/game-summary/{game_id}",
    }
    return routes.get(league_id)


def map_season_phases(seasons_json):
    mapping = {}
    for season in seasons_json["SiteKit"]["Seasons"]:
        sid = season["season_id"]
        name = season["shortname"] or season["season_name"]
        mapping[sid] = name
    return mapping

def parse_hockeytech(json_data, team_filter):
    cal = create_calendar()
    team_filter = [int(t) for t in team_filter]
    league = json_data["SiteKit"]["Parameters"]["client_code"].lower()
    league_id = json_data["SiteKit"]["Parameters"]["league_id"]
    season_id = json_data["SiteKit"]["Parameters"]["season_id"]

    schedule = json_data.get("SiteKit", {}).get("Schedule", [])

    today = date.today()

    if today >= date(today.year, 7, 1):
        season_start = date(today.year, 7, 1)
    else:
        season_start = date(today.year - 1, 7, 1)
    
    for row in schedule:
        date_str = row.get("date_played")

        if not date_str:
            continue

        try:
            game_date = datetime.strptime(date_str,"%Y-%m-%d").date()

        except ValueError:
            continue

        if game_date < season_start:
            continue
        
        home_id = int(row.get("home_team"))
        away_id = int(row.get("visiting_team"))

        if team_filter:
            if home_id not in team_filter and away_id not in team_filter:
                continue

        game_id = row.get("game_id")
        home_team = row.get("home_team_name").replace(",", "")
        away_team = row.get("visiting_team_name").replace(",", "")
        home_code = row.get("home_team_code")
        away_code = row.get("visiting_team_code")
        venue_raw = row.get("venue_name", "")
        if " - " in venue_raw:
            venue = venue_raw.split(" - ")[0].strip() if " - " in venue_raw else venue_raw
        else:
            venue = venue_raw.strip()
        iso_time = row.get("GameDateISO8601")

        if not iso_time:
            print(f"Missing ISO time for game {game_id}")
            continue

        start_dt, end_dt = parse_iso_datetime_duration(iso_time)

        date_str = row.get("date_played")  # "2026-10-16"
        yyyy, mm, dd = date_str.split("-")

        home_slug = slugify(home_team)
        away_slug = slugify(away_team)

        flo_id = row.get("flo_core_event_id")
        flo_link = flo_event_link(flo_id, yyyy, away_slug, home_slug)

        tournament = None
        
        if league == "hockeycanada":
            seasons_json = fetch_seasons_for_league(league_id)
            season_phase_map = map_season_phases(seasons_json)

            tournament_name = HCanada_Tournament.get(str(league_id))
            phase_name = season_phase_map.get(str(season_id))
            tournament = f"{tournament_name} - {phase_name}"
            current_year = datetime.now().year
            current_season = f"{current_year-1}-{str(current_year)[2:]}"
            game_center = hockeycanada_game_center(league_id, game_id, current_year, current_season)
        else:
            game_center = hockeytech_game_center(league, game_id, yyyy, mm, dd, home_slug, away_slug, home_code, away_code)

        description = build_description([
            f"Tournament: {tournament}" if tournament else None,
            f"Game Center: {game_center}" if game_center else None,
            f"FloHockey: {flo_link}" if flo_link else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid(league, game_id))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away_team} @ {home_team}")
            .location(venue)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal
