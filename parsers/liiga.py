from icalendar import Calendar, Event
from datetime import datetime

def parse_liiga_json_to_calendar(games):
    cal = Calendar()

    for g in games:
        dt = datetime.fromisoformat(g["startTime"].replace("Z", "+00:00"))
        home = g.get("homeTeamName", "Home")
        away = g.get("awayTeamName", "Away")

        event = Event()
        event.add("SUMMARY", f"🏒 Liiga | {home} vs {away}")
        event.add("DTSTART", dt)
        event.add("DTEND", dt)
        event.add("LOCATION", venue)
        event.add("UID", f"liiga-{home}-{away}-{dt.isoformat()}")

        cal.add_component(event)

    return cal
