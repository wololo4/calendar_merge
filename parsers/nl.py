from icalendar import Calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

NL_TEAM_FIX = {
    "SCRJ Lakers": "SC Rapperswil-Jona Lakers",
    "SC Rapperswil-Jona Lakers": "SC Rapperswil-Jona Lakers",
}

def parse_nl_json(json_data, team_id):
    cal = Calendar()

    for g in json_data:
        start_dt, end_dt = parse_iso_datetime_duration(g.get("date"))
        if not start_dt:
            continue

        home = NL_TEAM_FIX.get(g.get("homeTeamName", ""), g.get("homeTeamName", ""))
        away = NL_TEAM_FIX.get(g.get("awayTeamName", ""), g.get("awayTeamName", ""))

        home_id = g.get("homeTeamId", "")
        away_id = g.get("awayTeamId", "")

        exhibition = g.get("isExhibition", "")

        if exhibition == True:
            continue

        team_id_value = str(team_id[0])

        if away_id != team_id_value and home_id != team_id_value:
            continue

        # Venue
        venue = g.get("arena", "")

        game_id = g.get("gameId")
        game_center = f"https://www.nationalleague.ch/game/{game_id}"

        event = (
            ICSEventBuilder()
            .uid(uid("nl", game_id))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away} @ {home}")
            .location(venue)
            .description(f"Game Center: {game_center}")
            .build()
        )

        cal.add_component(event)

    return cal
