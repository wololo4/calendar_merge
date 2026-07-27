from icalendar import Calendar, Event
from datetime import datetime

def parse_shl_json_to_calendar(league, team_name, json_data):
    cal = Calendar()
    cal.add("prodid", "-//SHL Parser//")
    cal.add("version", "2.0")

    games = json_data.get("gameInfo", [])

    for game in games:
        # Date
        dt = datetime.fromisoformat(game["rawStartDateTime"].replace("Z", "+00:00"))

        # Teams
        home = game["homeTeamInfo"]["names"]["long"]
        away = game["awayTeamInfo"]["names"]["long"]

        # Arena
        arena = game.get("venueInfo", {}).get("name")

        # Game Center
        game_center = (
            f"https://www.shl.se/game-center/{game['uuid']}/{game['ssgtUuid']}/"
            f"?state={game['state']}"
        )
        # UID
        uid = "shl" + game["uuid"]

        # ICS event
        event = Event()
        event.add("SUMMARY", f"🏒 | {home} vs {away}")
        event.add("DTSTART", dt)
        event.add("DTEND", dt)
        event.add("UID", uid)

        if arena:
            event.add("LOCATION", arena)

        event.add("DESCRIPTION", f"Game Center: {game_center}")

        cal.add_component(event)

    return cal
