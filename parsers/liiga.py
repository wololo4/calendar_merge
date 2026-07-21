from icalendar import Calendar, Event
from datetime import datetime

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

        event = Event()
        event.add("SUMMARY", f"{home} vs {away}")
        event.add("DTSTART", dt)
        event.add("DTEND", dt)
        event.add("LOCATION", venue)
        event.add("UID", f"liiga-{home}-{away}-{dt.isoformat()}")

        cal.add_component(event)

    return cal
