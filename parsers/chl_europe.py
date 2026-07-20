from icalendar import Event
from datetime import datetime, timedelta
from utils.calendar import create_calendar

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

        event = Event()

        game_id = game.get("externalId", "unknown")
        event.add("uid", f"chleu-game-{game_id}@championshockeyleague.com")

        start_str = game.get("startDate")
        if not start_str:
            continue

        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(hours=2, minutes=30)

        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)

        home_name = home.get("name", "Home")
        away_name = away.get("name", "Away")
        event.add("summary", f"{away_name} @ {home_name}")

        venue = game.get("venue", {}).get("name", "Arena")
        event.add("location", venue)

        stage = game.get("stage", {})
        group_name = stage.get("group", {}).get("name", "")
        round_name = stage.get("round", {}).get("name", "")

        description = [
            "Champions Hockey League Match",
            f"Stage: {group_name}",
            f"Round: {round_name}",
            f"Status: {game.get('status', 'Scheduled')}",
        ]

        link = game.get("link", {}).get("url")
        if link:
            description.append(f"Match Page: https://www.chl.hockey{link}")

        event.add("description", "\n".join(description))
        cal.add_component(event)

    return cal
