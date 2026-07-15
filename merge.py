import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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

    games_list = json_data.get("sportsEvents", [])

    for item in games_list:
        event_data = item.get("event", {})
        date_gmt = event_data.get("dateGMT")

        if not date_gmt:
            continue

        event = Event()
        event_id = item.get("eventId", "unknown")
        event.add("uid", f"chl-game-{event_id}@chl.ca")

        try:
            start_dt = datetime.fromisoformat(date_gmt).replace(
                tzinfo=timezone.utc
            )
            end_dt = start_dt + timedelta(hours=2, minutes=30)
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
        except Exception as parse_err:
            print(
                f"Erreur de formatage date pour le match CHL {event_id}: {parse_err}"
            )
            continue

        top_team = event_data.get("top", {})
        bottom_team = event_data.get("bottom", {})

        away_name = (
            f"{top_team.get('location', '')} {top_team.get('name', '')}"
        ).strip()
        home_name = (
            f"{bottom_team.get('location', '')} {bottom_team.get('name', '')}"
        ).strip()
        venue = event_data.get("venue", "CHL Arena")

        event.add("summary", f"{away_name} @ {home_name}")
        event.add("location", venue)

        description = [
            "Official CHL Ice Hockey Match",
            f"Status: {event_data.get('formattedTime', 'Scheduled')}",
        ]

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
        start_timestamp = game.get("startTimestamp")

        if not start_timestamp:
            away = game.get("awayTeamName", "Away Team")
            home = game.get("homeTeamName", "Home Team")
            print(f"Matchup sauté (Timestamp manquant): {away} @ {home}")
            continue

        event = Event()
        game_id = game.get("gameID", "unknown")
        event.add("uid", f"ufa-game-{game_id}@ufastats.com")

        try:
            start_dt = datetime.fromisoformat(start_timestamp)
            end_dt = start_dt + timedelta(hours=2)
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
        except Exception as parse_err:
            print(
                f"Erreur de formatage ISO pour le match {game_id}: {parse_err}"
            )
            continue

        away_name = game.get("awayTeamName", "Away Team")
        home_name = game.get("homeTeamName", "Home Team")
        location = game.get("locationName", "UFA Field")

        event.add("summary", f"{away_name} @ {home_name}")
        event.add("location", location)

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
        "Referer": "https://khl.ru",
    }

    response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.raise_for_status()

    is_json_url = ("://ufastats.com" in url or "bellmedia.ca" in url) or response.headers.get("Content-Type", "").startswith("application/json")

    if is_json_url:
        raw_json = response.json()
        if "games" in raw_json:
            return parse_ufa_json_to_calendar(raw_json)
        else:
            return parse_chl_json_to_calendar(raw_json)

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

    # --- FOLDER CONFIGURED AS CALENDARS ---
    OUTPUT_DIR = "calendars"
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
