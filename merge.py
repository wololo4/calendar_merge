import os
import json  # <-- Fixed: Added to prevent the NameError on KHL/UFA fallback
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests
from icalendar import Calendar, Event
from concurrent.futures import ThreadPoolExecutor  # <-- New: For parallel downloads

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

def download_single_feed(feed_info):
    """Worker function to process one feed concurrently."""
    league, url = feed_info
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    if "khl.ru" in url:
        headers.update({
            "Referer": "https://www.khl.ru/",
            "Origin": "https://www.khl.ru",
            "Accept": "text/calendar,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
    
    try:
        print(f"Downloading: {league} -> {url[:50]}...")
        response = session.get(url, headers=headers, timeout=15) # Reduced timeout
        response.raise_for_status()

        try:
            raw_json = response.json()
            if "games" in raw_json:
                games_list = raw_json.get("games", [])
                if games_list and isinstance(games_list, list) and "startTimeUTC" in games_list[0]:
                    return league, parse_nhl_json_to_calendar(raw_json)
                else:
                    return league, parse_ufa_json_to_calendar(raw_json)
            else:
                return league, parse_chl_json_to_calendar(raw_json)
        except (ValueError, TypeError, json.JSONDecodeError):
            return league, Calendar.from_ical(response.content)
            
    except Exception as e:
        print(f"Error downloading {league}: {e}")
        return league, None

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

    # OPTIMIZATION: Download all URLs at the same time using a Thread Pool
    # max_workers=10 runs up to 10 network requests simultaneously
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(download_single_feed, feeds)
    
    for league, calendar in results:
        print("Téléchargement:", league)
        if calendar is None:
            continue

        for event in calendar.walk():
            if event.name != "VEVENT":
                continue

            key = event_id(event)
            if key in seen[league]:
                continue

            seen[league].add(key)
            leagues[league].append(event)

    OUTPUT_DIR = "calendars"                    # Target folder name
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for league, events in leagues.items():
        output = create_calendar()

        for event in events:
            output.add_component(event)

        filename = os.path.join(OUTPUT_DIR, league.lower() + ".ics")

        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(f"{filename} créé: {len(events)} matchs")

if __name__ == "__main__":
    main()
