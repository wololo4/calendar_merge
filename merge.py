import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests
from icalendar import Calendar, Event

FEEDS_FILE = "feeds.txt"

def load_feeds():
    feeds = []
    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            league, url = line.split("|", 1)
            feeds.append((league.strip(), url.strip()))
    return feeds

def parse_chl_json_to_calendar(json_data):
    """Converts raw live Bell Media CHL JSON data into a standard icalendar Calendar object."""
    cal = create_calendar()

    # The production Bell Media endpoint wraps events in a root 'sportsEvents' array
    games_list = json_data.get("sportsEvents", [])

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
            if highlight.get("description"):
                description.append(f"\nSummary: {highlight['description']}")

        event.add("description", "\n".join(description))
        cal.add_component(event)

    return cal

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
    
def download_calendar(url):
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Accept": "text/calendar,text/plain,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        "Referer": "https://www.khl.ru/",
    }
    
    response = session.get(
        url,
        headers=headers,
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    # --- ADJUSTMENT 1: ROUTING ROUTINE ---
    # Intercept the pipeline if the request contains JSON data or sports API signatures
    is_json = (
        "www.backend.ufastats.com" in url
        or "sports.bellmedia.ca" in url
        or response.headers.get("Content-Type", "").startswith(
            "application/json"
        )
    )

    if is_json:
        raw_json = response.json()
        # Direct parsing requests using signature parent dictionary indicators
        if "games" in raw_json:
            return parse_ufa_json_to_calendar(raw_json)
        else:
            return parse_chl_json_to_calendar(raw_json)

    # Fallback to normal .ics parsing for standard hockey feeds
    return Calendar.from_ical(response.content)

def create_calendar():
    cal = Calendar()
    cal.add("prodid", "-//Hockey Calendar//")
    cal.add("version", "2.0")
    return cal


def event_id(event):
    return str(event.get("UID")) + str(event.get("DTSTART"))


def main():
    leagues = defaultdict(list)
    seen = defaultdict(set)
    feeds = load_feeds()

    for league, url in feeds:
        print("Téléchargement:", league)
        try:
            calendar = download_calendar(url)

            for event in calendar.walk():
                if event.name != "VEVENT":
                    continue

                key = event_id(event)
                if key in seen[league]:
                    continue

                seen[league].add(key)
                leagues[league].append(event)

        except Exception as e:
            print("Erreur:", league, e)

    OUTPUT_DIR = "calendars"                    # Define subfolder name
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for league, events in leagues.items():
        output = create_calendar()

        for event in events:
            output.add_component(event)

        filename = os.path.join(OUTPUT_DIR, league.lower() + ".ics")

        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(filename, "créé:", len(events), "matchs")


if __name__ == "__main__":
    main()
