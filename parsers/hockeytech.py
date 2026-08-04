import requests
import json
from icalendar import Event
from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar

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

def map_season_phases(seasons_json):
    mapping = {}
    for season in seasons_json["SiteKit"]["Seasons"]:
        sid = season["season_id"]
        name = season["shortname"] or season["season_name"]
        mapping[sid] = name
    return mapping

def parse_hockeytech(json_data, team_filter):
    """
    Universal HockeyTech parser.
    Works for AHL, ECHL, LHJMQ, OHL, WHL, BCHL, PWHL.
    Uses ONLY the main schedule JSON (no gameSummary scraping needed).
    """
    cal = create_calendar()
    team_filter = [int(t) for t in team_filter]
    league = json_data["SiteKit"]["Parameters"]["client_code"].lower()
    league_id = json_data["SiteKit"]["Parameters"]["league_id"]
    season_id = json_data["SiteKit"]["Parameters"]["season_id"]

    schedule = json_data.get("SiteKit", {}).get("Schedule", [])

    for row in schedule:

        # Team filtering (HockeyTech uses numeric team_id)
        home_id = int(row.get("home_team"))
        away_id = int(row.get("visiting_team"))

        if team_filter:
            if home_id not in team_filter and away_id not in team_filter:
                continue

        # Extract fields directly from JSON
        game_id = row.get("game_id")
        home_team = row.get("home_team_name").replace(",", "")
        away_team = row.get("visiting_team_name").replace(",", "")
        home_code = row.get("home_team_code")
        away_code = row.get("visiting_team_code")
        venue_raw = row.get("venue_name", "")
        if " - " in venue_raw:
            venue = venue_raw.split(" - ")[0].strip()
        else:
            venue = venue_raw.strip()
        iso_time = row.get("GameDateISO8601")

        if not iso_time:
            print(f"Missing ISO time for game {game_id}")
            continue

        local_start = datetime.fromisoformat(iso_time)

        # Convert ISO8601 → datetime
        start_dt = local_start.astimezone(timezone.utc)
        end_dt = start_dt + timedelta(hours=2, minutes=30)

        # Game Center link
        # Build new ECHL Game Center URL
        date_str = row.get("date_played")  # "2026-10-16"
        yyyy, mm, dd = date_str.split("-")

        tournament = None

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

        home_slug = slugify(row.get("home_team_name"))
        away_slug = slugify(row.get("visiting_team_name"))

        if league == "ahl":
            game_center = f"https://theahl.com/stats/game-center/{game_id}"
            flo_id = row.get("flo_core_event_id")
            flo_link = f"https://www.flohockey.tv/events/{flo_id}" if flo_id and flo_id != "0" else None
        elif league == "bchl":
            game_center = f"https://bchl.ca/stats/game-center/{game_id}"
            flo_id = row.get("flo_core_event_id")
            flo_link = f"https://www.flohockey.tv/events/{flo_id}-{yyyy}-{away_slug}-vs-{home_slug}" if flo_id and flo_id != "0" else None
        elif league == "chl":
            game_center = f"https://chl.ca/games/chl/chl/{home_code}-{away_code}/{game_id}"
            flo_link = None
        elif league == "echl":
            game_center = f"https://echl.com/games/{yyyy}/{mm}/{dd}/{home_slug}-vs-{away_slug}"
            flo_id = row.get("flo_core_event_id")
            flo_link = f"https://www.flohockey.tv/events/{flo_id}-{yyyy}-{away_slug}-vs-{home_slug}" if flo_id and flo_id != "0" else None
        elif league == "hockeycanada":
            seasons_json = fetch_seasons_for_league(league_id)
            season_phase_map = map_season_phases(seasons_json)

            tournament_name = HCanada_Tournament.get(str(league_id))
            phase_name = season_phase_map.get(str(season_id))
            tournament = f"{tournament_name} - {phase_name}"
            current_year = datetime.now().year
            current_season = f"{current_year-1}-{str(current_year)[2:]}"
            if league_id == "7":
                game_center = f"https://www.hockeycanada.ca/en-ca/team-canada/men/junior/{current_season}/world-championship/stats/game-summary/{game_id}"
            if league_id == "24":
                game_center = f"https://www.hockeycanada.ca/en-ca/national-championships/men/u18-club/{current_year}/stats/game-summary/{game_id}"
            if league_id == "26":
                game_center = f"https://www.hockeycanada.ca/en-ca/team-canada/men/under-18/{current_season}/world-championship/stats/game-summary/{game_id}"
            if league_id == "27":
                game_center = f"https://www.hockeycanada.ca/en-ca/team-canada/men/national/{current_season}/world-championship/stats/game-summary/{game_id}"
            if league_id == "32":
                game_center = f"https://www.hockeycanada.ca/en-ca/national-championships/men/national-junior-a/{current_year}/stats/game-summary/{game_id}"
            if league_id == "34":
                game_center = f"https://www.hlinkagretzkycup.ca/en-ca/season/{current_year}/stats/game-summary?gameid={game_id}"
            if league_id == "38":
                game_center = f"https://www.hockeycanada.ca/en-ca/team-canada/men/olympics/{current_year}/stats/game-summary/{game_id}"
            flo_link = None
        elif league == "lhjmq":
            game_center = f"https://chl.ca/lhjmq/gamecentre/{game_id}"
            flo_id = row.get("flo_core_event_id")
            flo_link = f"https://www.flohockey.tv/events/{flo_id}-{yyyy}-{away_slug}-vs-{home_slug}" if flo_id and flo_id != "0" else None
        elif league == "ohl":
            game_center = f"https://chl.ca/ohl/gamecentre/{game_id}"
            flo_id = row.get("flo_core_event_id")
            flo_link = f"https://www.flohockey.tv/events/{flo_id}-{yyyy}-{away_slug}-vs-{home_slug}" if flo_id and flo_id != "0" else None
        elif league == "whl":
            game_center = f"https://chl.ca/whl/gamecentre/{game_id}"
            flo_link = None


        # Create ICS event
        event = Event()

        # UID
        event.add("uid", f"{league}{game_id}")

        # DTSTART / DTEND
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)

        # SUMMARY
        event.add("summary", f"🏒 | {away_team} @ {home_team}")

        # LOCATION
        event.add("location", venue)

        # DESCRIPTION
        description = []

        if tournament:
            description.append(f"Tournament: {tournament}")
        if game_center:
            description.append(f"Game Center: {game_center}")

        if flo_link:
            description.append(f"FloHockey: {flo_link}")

        event.add("description", "\n".join(description))

        cal.add_component(event)

    return cal
