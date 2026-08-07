from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

def get_fr_or_default(obj):
    return obj.get("fr") or obj.get("default")

def get_full_team_name_fr(team):
    city = get_fr_or_default(team.get("placeName", {}))
    name = get_fr_or_default(team.get("commonName", {}))
    return f"{city} {name}"

def parse_nhl_json_to_calendar(json_data):
    """Converts modern NHL REST API club season JSON data into an icalendar Calendar object."""
    cal = create_calendar()

    for game in json_data.get("games", []):
        start_dt, end_dt = parse_iso_datetime_duration(game.get("startTimeUTC"))
        if not start_dt:
            continue

        game_id = game.get("id", "unknown")

        away_team = game.get("awayTeam", {})
        home_team = game.get("homeTeam", {})

        away_abbrev = get_full_team_name_fr(away_team)
        home_abbrev = get_full_team_name_fr(home_team)
 
        venue_name = get_fr_or_default(game.get("venue", {}))

        game_type_id = game.get("gameType", 2)
        game_type_str = "Regular Season" if game_type_id == 2 else "Pre-Season" if game_type_id == 1 else "Playoffs"

        broadcasts = game.get("tvBroadcasts", [])
        gameCenterLink = game.get("gameCenterLink")
        ticketsLink = game.get("ticketsLink")
        channels = []
        if broadcasts and isinstance(broadcasts, list):
            channels = [b.get("network", "") for b in broadcasts if b.get("network")]

        description = build_description([
            f"{game_type_str} Game",
            f"TV Network: {', '.join(channels)}" if channels else None,
            f"Game Center: https://www.nhl.com{gameCenterLink}" if gameCenterLink else None,
            f"Tickets: {game['ticketsLink']}" if ticketsLink else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid("nhl", game_id))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away_abbrev} @ {home_abbrev}")
            .location(venue_name)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal
