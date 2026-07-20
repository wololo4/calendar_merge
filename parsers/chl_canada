from icalendar import Event
from datetime import datetime, timedelta, timezone
from utils.calendar import create_calendar

def parse_chl_json_to_calendar(json_data):
    """Converts raw live Bell Media CHL JSON data into a standard icalendar Calendar object."""
    cal = create_calendar()

    # FIX: Loop through the date-string keys directly (e.g., "2026-05-22")
    for date_key, games_list in json_data.items():
        # Safety: skip if metadata strings are mixed into the root keys
        if not isinstance(games_list, list):
            continue

        for item in games_list:
            event_data = item.get("event", {})
            date_gmt = event_data.get("dateGMT")

            # Safety Check: Skip if the game has no timestamp yet
            if not date_gmt:
                continue

            event = Event()

            # Build Unique Identifier using the internal eventId matrix
            event_id = item.get("eventId", "unknown")
            event.add("uid", f"chl-game-{event_id}@chl.ca")

            try:
                # Parse the ISO-8601 string (e.g. 2026-05-23T01:00:00) and clamp it to UTC
                start_dt = datetime.fromisoformat(date_gmt).replace(
                    tzinfo=timezone.utc
                )

                # Estimate duration (Approx. 2.5 hours for a major junior hockey game)
                end_dt = start_dt + timedelta(hours=2, minutes=30)

                event.add("dtstart", start_dt)
                event.add("dtend", end_dt)

            except Exception as parse_err:
                print(
                    f"Erreur de formatage date pour le match CHL {event_id}: {parse_err}"
                )
                continue

            # Extract team details from 'top' (Away) and 'bottom' (Home) structures
            top_team = event_data.get("top", {})
            bottom_team = event_data.get("bottom", {})

            # Extract names gracefully (e.g., "Kitchener Rangers")
            away_name = (
                f"{top_team.get('location', '')} {top_team.get('name', '')}"
            ).strip()
            home_name = (
                f"{bottom_team.get('location', '')} {bottom_team.get('name', '')}"
            ).strip()
            venue = event_data.get("venue", "CHL Arena")

            event.add("summary", f"{away_name} @ {home_name}")
            event.add("location", venue)

            # Build the description context notes
            description = [
                "Official CHL Ice Hockey Match",
                f"Status: {event_data.get('formattedTime', 'Scheduled')}",
            ]

            # Attach TSN media video clip highlight urls if they are active in the feed
            videos = event_data.get("videosTsn", [])
            if videos and isinstance(videos, list):
                highlight = videos[0]
                if isinstance(highlight, dict) and highlight.get(
                    "description"
                ):
                    description.append(f"\nSummary: {highlight['description']}")

            event.add("description", "\n".join(description))
            cal.add_component(event)

    return cal
