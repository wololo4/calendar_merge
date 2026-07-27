from icalendar import Calendar, Event
from datetime import datetime, timedelta

def parse_liiga_json_to_calendar(games):
    cal = Calendar()

    for g in games:
        # Liiga uses "start", not "startTime"
        raw_start = g.get("start")
        if not raw_start:
            continue

        # Convert start time
        dt = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))

        # Teams
        home = g.get("homeTeamName", "Home")
        away = g.get("awayTeamName", "Away")

        # Venue
        venue = ""
        if "iceRink" in g and g["iceRink"]:
            venue = g["iceRink"].get("name", "")

        uid = g.get("id")
        season = g.get("season")
        game_center = f"https://liiga.fi/en/game/{season}/{uid}"

        event = Event()
        event.add("SUMMARY", f"🏒 | {home} vs {away}")
        event.add("DTSTART", dt)
        dt_end = dt + timedelta(hours=2, minutes=30)
        event.add("DTEND", dt_end)
        event.add("LOCATION", venue)
        event.add("UID", f"liiga-{uid}")    
        event.add("DESCRIPTION", f"Game Center: {game_center}")

        cal.add_component(event)

    return cal
