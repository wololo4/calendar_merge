from icalendar import Event
from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar

def parse_ufa_json_to_calendar(json_data):
    """Converts raw UFA JSON data into a standard icalendar Calendar object using exact API structural keys."""
    cal = create_calendar()

    for game in json_data.get("games", []):
        # Read the unified timestamp provided by the API
        start_timestamp = game.get("startTimestamp")

        # Safety Check: Skip if the game has no scheduled timestamp yet
        if not start_timestamp:
            away = game.get("awayTeamName")
            home = game.get("homeTeamName")
            print(f"Matchup sauté (Timestamp manquant): {away} @ {home}")
            continue

        event = Event()

        # Build Unique Identifier using the provided gameID string
        game_id = game.get("gameID")
        event.add("uid", f"ufa{game_id}")

        try:
            # Parse the ISO-8601 date string directly (handles offsets perfectly)
            start_dt = datetime.fromisoformat(start_timestamp).astimezone(timezone.utc)

            # Estimate duration (Approx. 2 hours for Ultimate Frisbee match duration)
            end_dt = start_dt + timedelta(hours=2)

            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)

        except Exception as parse_err:
            print(
                f"Erreur de formatage ISO pour le match {game_id}: {parse_err}"
            )
            continue

        # Extract root-level team names and stadium locations
        away_name = game.get("awayTeamName", "Away Team")
        away_city = game.get("awayTeamCity", "Away City")
        home_name = game.get("homeTeamName", "Home Team")
        home_city = game.get("homeTeamCity", "Home City")
        location = game.get("locationName", "UFA field")

        event.add("summary", f"🥏 | {away_city} {away_name} @ {home_city} {home_name}")
        event.add("location", location)

        # Include official streaming and ticket URLs inside the description field
        description = [
            f"Game Center: https://www.watchufa.com/league/game/{game_id}"
        ]

        if game.get("streamingURL"):
            description.append(f"Watch Live: {game['streamingURL']}")
        if game.get("ticketURL"):
            description.append(f"Tickets: {game['ticketURL']}")

        event.add("description", "\n".join(description))

        cal.add_component(event)

    return cal
