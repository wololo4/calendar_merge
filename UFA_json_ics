from datetime import datetime, timedelta
import requests


def fetch_montreal_royal_events():
    url = "https://ufastats.com"
    try:
        response = requests.get(url).json()
    except Exception:
        return []  # Handle api downtime safely

    events = []

    # Map the ufastats API schema directly to icalendar text lines
    for game in response.get("games", []):
        # Format dates (UFA uses YYYY-MM-DD and HH:MM)
        date_str = game["date"].replace("-", "")
        time_str = game["time"].replace(":", "") + "00"

        # Calculate an estimated end time (approx. 2 hours for Ultimate matches)
        start_dt = datetime.strptime(f"{date_str}T{time_str}", "%Y%m%dT%H%M%S")
        end_dt = start_dt + timedelta(hours=2)
        end_str = end_dt.strftime("%Y%m%dT%H%M%S")

        # Create standard VEVENT strings to append directly to your merge compiler
        event = [
            "BEGIN:VEVENT",
            f"UID:ufa-game-{game['gameID']}@ufastats.com",
            f"DTSTART;TZID=America/Montreal:{date_str}T{time_str}",
            f"DTEND;TZID=America/Montreal:{end_str}",
            f"SUMMARY:{game['awayTeamName']} @ {game['homeTeamName']}",
            f"LOCATION:{game.get('field', 'UFA Field')}",
            "DESCRIPTION:Official UFA Ultimate Frisbee Match",
            "END:VEVENT",
        ]
        events.append("\n".join(event))

    return events
