from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

def parse_ufa_json_to_calendar(json_data):
    cal = create_calendar()

    for game in json_data.get("games", []):
        start_dt, end_dt = parse_iso_datetime_duration(game.get("startTimestamp"))
        game_id = game.get("gameID")


        # Extract root-level team names and stadium locations
        away_name = game.get("awayTeamName", "Away Team")
        away_city = game.get("awayTeamCity", "Away City")
        home_name = game.get("homeTeamName", "Home Team")
        home_city = game.get("homeTeamCity", "Home City")
        location = game.get("locationName", "UFA field")

        description = build_description([
            f"Game Center: https://www.watchufa.com/league/game/{game_id}",
            f"Watch Live: {game['streamingURL']}" if game.get("streamingURL") else None,
            f"Tickets: {game['ticketURL']}" if game.get("ticketURL") else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid("ufa", game_id))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🥏 | {away_city} {away_name} @ {home_city} {home_name}")
            .location(location)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal
