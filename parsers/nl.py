from icalendar import Calendar, Event
from datetime import datetime, timedelta

def parse_nl_json(json_data, team_id):
    cal = Calendar()

    for g in json_data:
        # Liiga uses "start", not "startTime"
        raw_start = g.get("date")
        if not raw_start:
            continue

        # Convert start time
        dt = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))

        # Teams
        home = g.get("homeTeamName", "")
        away = g.get("awayTeamName", "")

        home_id = g.get("homeTeamId", "")
        away_id = g.get("awayTeamId", "")

        exhibition = g.get("isExhibition", "")

        if exhibition == True:
            continue

        if away_id != str(team_id) and home_id != str(team_id):
            continue

        # Venue
        venue = g.get("arena", "")

        uid = g.get("gameId")
        game_center = f"https://www.nationalleague.ch/game/{uid}"

        event = Event()
        event.add("SUMMARY", f"🏒 | {away} @ {home}")
        event.add("DTSTART", dt)
        dt_end = dt + timedelta(hours=2, minutes=30)
        event.add("DTEND", dt_end)
        event.add("LOCATION", venue)
        event.add("UID", f"nl{uid}")    
        event.add("DESCRIPTION", f"Game Center: {game_center}")

        cal.add_component(event)

    return cal
