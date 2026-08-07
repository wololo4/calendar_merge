from utils.calendar import create_calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder

def parse_chl_europe_json_to_calendar(json_data, team_filter):
    cal = create_calendar()

    for game in json_data.get("data", []):
        teams = game.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        home_short = home.get("shortName", "")
        away_short = away.get("shortName", "")

        # ⭐ FILTER: Only keep teams listed in feeds.txt
        if team_filter:
            if home_short not in team_filter and away_short not in team_filter:
                continue

        game_id = game.get("externalId", "unknown")
        start_dt, end_dt = parse_iso_datetime_duration(game.get("startDate"))
        home_name = home.get("name", "Home")
        away_name = away.get("name", "Away")
        venue = game.get("venue", {}).get("name", "Arena")

        stage = game.get("stage", {})
        group_name = stage.get("group", {}).get("name", "")
        round_name = stage.get("round", {}).get("name", "")

        link = game.get("link", {}).get("url")

        description = build_description([
            f"Stage: {group_name}",
            f"Round: {round_name}",
            f"Game Center: https://www.chl.hockey/en{link}" if link else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid("chleu", game_id))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away_name} @ {home_name}")
            .location(venue)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal
