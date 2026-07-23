import re
import requests
import json
from icalendar import Event
from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar

def get_ahl_game_info(game_id):
    url = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed"
        "&view=gameSummary"
        f"&game_id={game_id}"
        "&key=ccb91f29d6744675"
        "&site_id=3"
        "&client_code=ahl"
    )

    try:
        r = requests.get(url, timeout=10)
        text = r.text.strip()

        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1]

        text = text.replace("\\/", "/")
        data = json.loads(text)

        details = data.get("details", {})
        home = data.get("homeTeam", {}).get("info", {})
        away = data.get("visitingTeam", {}).get("info", {})

        venue = details.get("venue")
        iso_time = details.get("GameDateISO8601")

        # Convert ISO8601 → datetime
        start_dt = None
        if iso_time:
            start_dt = datetime.fromisoformat(iso_time)

        return {
            "venue": venue,
            "home_name": home.get("name"),
            "away_name": away.get("name"),
            "home_city": home.get("city"),
            "away_city": away.get("city"),
            "home_abbrev": home.get("abbreviation"),
            "away_abbrev": away.get("abbreviation"),
            "start_dt": start_dt,
            "iso": iso_time,
            "date_text": details.get("date"),
            "status_text": details.get("status"),
        }

    except Exception as e:
        print("AHL venue error:", e)
        return None

def parse_ahl_json_to_calendar(json_data):

    """Converts AHL schedule JSON into an icalendar Calendar object."""
    cal = create_calendar()

    sections = json_data.get("sections", [])

    section = sections[0]
    items = section.get("data", [])

    for item in items:
        row = item.get("row", {})
        prop = item.get("prop", {})

        game_id = row.get("game_id")
        info = get_ahl_game_info(game_id)
        
        if not info:
            continue

        home_team = info["home_name"]
        away_team = info["away_name"]
        venue = info["venue"]

        start_dt = info["start_dt"]
        if not start_dt:
            print(f"Missing ISO time for game {game_id}")
            continue

         # DTEND = +2h30
        end_dt = start_dt + timedelta(hours=2, minutes=30)

        # Create event
        event = Event()

        # UID
        event.add("uid", f"ahl{game_id}")

        # DTSTART / DTEND
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)

        # SUMMARY
        event.add("summary", f"🏒 | {away_team} @ {home_team}")

        # LOCATION (arena)
        event.add("location", venue)

        # DESCRIPTION
        description = []

        description.append(f"Game Center: https://theahl.com/stats/game-center/{game_id}")

        flo_link = prop.get("flohockey_url", {}).get("link")
        if flo_link:
            description.append(f"FloHockey: {flo_link}")

        event.add("description", "\n".join(description))

        cal.add_component(event)

    return cal
