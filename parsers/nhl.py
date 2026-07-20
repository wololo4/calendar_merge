from icalendar import Event
from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar

def parse_nhl_json_to_calendar(json_data):
    """Converts modern NHL REST API club season JSON data into an icalendar Calendar object."""
    cal = create_calendar()

    for game in json_data.get("games", []):
        utc_time_str = game.get("startTimeUTC")

        # Safety Check: Skip if the game has no timestamp yet
        if not utc_time_str:
            continue

        event = Event()

        # Build Unique Identifier using the official NHL Game ID
        game_id = game.get("id", "unknown")
        event.add("uid", f"nhl-game-{game_id}@nhle.com")

        try:
            # Clean up the timezone suffix 'Z' for fromisoformat compatibility
            clean_utc = utc_time_str.replace("Z", "")
            start_dt = datetime.fromisoformat(clean_utc).replace(
                tzinfo=timezone.utc
            )

            # Estimate duration (Approx. 2.5 hours for an NHL game with intermissions)
            end_dt = start_dt + timedelta(hours=2, minutes=30)

            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)

        except Exception as parse_err:
            print(
                f"Erreur de formatage date pour le match NHL {game_id}: {parse_err}"
            )
            continue

        # Extract team details using nested dictionary definitions
        away_team = game.get("awayTeam", {})
        home_team = game.get("homeTeam", {})

        away_abbrev = away_team.get("abbrev", "AWAY")
        home_abbrev = home_team.get("abbrev", "HOME")

        # Create matchup text representation
        event.add("summary", f"{away_abbrev} @ {home_abbrev}")

        # Extract explicit venue names gracefully from the dictionary node
        venue_info = game.get("venue", {})
        venue_name = venue_info.get("default", f"{home_abbrev} Home Arena")
        event.add("location", venue_name)

        # Map game type values to readable descriptors
        # 1 = Preseason, 2 = Regular Season, 3 = Playoffs
        game_type_id = game.get("gameType", 2)
        game_type_str = "Regular Season" if game_type_id == 2 else "Pre-Season" if game_type_id == 1 else "Playoffs"

        description = [
            "Official NHL Ice Hockey Match",
            f"League Stage: {game_type_str}",
        ]

        # Extract networks dynamically from TV broadcast array
        broadcasts = game.get("tvBroadcasts", [])
        if broadcasts and isinstance(broadcasts, list):
            channels = [b.get("network", "") for b in broadcasts if b.get("network")]
            if channels:
                description.append(f"TV Network: {', '.join(channels)}")

        # Append interactive URLs if available in the dataset
        if game.get("gameCenterLink"):
            description.append(f"Game Center: https://www.nhl.com{game['gameCenterLink']}")
        if game.get("ticketsLink"):
            description.append(f"Tickets: {game['ticketsLink']}")

        event.add("description", "\n".join(description))
        cal.add_component(event)

    return cal
