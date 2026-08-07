from utils.calendar import create_calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

def parse_shl_json_to_calendar(league, team_name, json_data):
    cal = create_calendar()

    games = json_data.get("gameInfo", [])

    for game in games:
        dt, end_dt = parse_iso_datetime_duration(game["rawStartDateTime"])

        home = game["homeTeamInfo"]["names"]["long"]
        away = game["awayTeamInfo"]["names"]["long"]

        arena = game.get("venueInfo", {}).get("name")
        game_id = game["uuid"]

        game_center = (
            f"https://www.shl.se/game-center/{game_id}/{game['ssgtUuid']}/"
            f"?state={game['state']}"
        )

        event = (
            ICSEventBuilder()
            .uid(uid("shl", game_id))
            .start(dt)
            .end(end_dt)
            .summary(f"🏒 | {away} @ {home}")
            .location(arena)
            .description(f"Game Center: {game_center}")
            .build()
        )

        cal.add_component(event)

    return cal
