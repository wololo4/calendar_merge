from icalendar import Event
from datetime import datetime, timedelta
from utils.calendar import create_calendar

def parse_ufa_json_to_calendar(json_data):
    """Converts raw UFA JSON data into a standard icalendar Calendar object using exact API structural keys."""
    cal = create_calendar()

    for game in json_data.get("games", []):
        # Read the unified timestamp provided by the API
        start_timestamp = game.get("startTimestamp")

        # Safety Check: Skip if the game has no scheduled timestamp yet
        if not start_timestamp:
            away = game.get("awayTeamName", "Away Team")
            home = game.get("homeTeamName", "Home Team")
            print(f"Matchup sauté (Timestamp manquant): {away} @ {home}")
            continue

        event = Event()

        # Build Unique Identifier using the provided gameID string
        game_id = game.get("gameID", "unknown")
        event.add("uid", f"ufa-game-{game_id}@ufastats.com")

        try:
            # Parse the ISO-8601 date string directly (handles offsets perfectly)
            start_dt = datetime.fromisoformat(start_timestamp)

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
        home_name = game.get("homeTeamName", "Home Team")
        location = game.get("locationName", "UFA Field")

        event.add("summary", f"{away_name} @ {home_name}")
        event.add("location", location)

        # Include official streaming and ticket URLs inside the description field
        description = [
            "Official UFA Ultimate Frisbee Match",
            f"Status: {game.get('status', 'Upcoming')}",
        ]
        if game.get("streamingURL"):
            description.append(f"Watch Live: {game['streamingURL']}")
        if game.get("ticketURL"):
            description.append(f"Tickets: {game['ticketURL']}")

        event.add("description", "\n".join(description))

        cal.add_component(event)

    return cal
