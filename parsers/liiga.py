from icalendar import Calendar, Event
from datetime import datetime, timedelta
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

def parse_liiga_json_to_calendar(games):
    cal = Calendar()

    for g in games:
        # Convert start time
        dt, dt_end = parse_iso_datetime_duration(g.get("start"))

        # Teams
        home = g.get("homeTeamName", "Home")
        away = g.get("awayTeamName", "Away")

        # Venue
        venue = ""
        if "iceRink" in g and g["iceRink"]:
            venue = g["iceRink"].get("name", "")

        game_id = g.get("id")
        season = g.get("season")
        game_center = f"https://liiga.fi/en/game/{season}/{game_id}"

        event = (
            ICSEventBuilder()
            .uid(uid("liiga", game_id))
            .start(dt)
            .end(dt_end)
            .summary(f"🏒 | {away} @ {home}")
            .location(venue)
            .description(f"Game Center: {game_center}")
            .build()
        )

        cal.add_component(event)

    return cal
