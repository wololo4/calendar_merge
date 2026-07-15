from datetime import datetime, timedelta
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


def parse_ufa_json_to_calendar(json_data):
    """Converts raw UFA JSON data into a standard icalendar Calendar object."""
    cal = create_calendar()
    
    for game in json_data.get("games", []):
        event = Event()
        
        # Build Unique Identifier
        event.add("uid", f"ufa-game-{game['gameID']}@ufastats.com")
        
        # Parse start times (Format: YYYY-MM-DD and HH:MM)
        date_str = game["date"].replace("-", "")
        time_str = game["time"].replace(":", "") + "00"
        start_dt = datetime.strptime(f"{date_str}T{time_str}", "%Y%m%dT%H%M%S")
        
        # Estimate duration (Approx. 2 hours for Ultimate Frisbee)
        end_dt = start_dt + timedelta(hours=2)
        
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("summary", f"{game['awayTeamName']} @ {game['homeTeamName']}")
        event.add("location", game.get("field", "UFA Field"))
        event.add("description", "Official UFA Ultimate Frisbee Match")
        
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

    # Intercept the pipeline if the request comes from the UFA JSON API
    if "://ufastats.com" in url or response.headers.get("Content-Type", "").startswith("application/json"):
        return parse_ufa_json_to_calendar(response.json())

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

    for league, events in leagues.items():
        output = create_calendar()

        for event in events:
            output.add_component(event)

        filename = league.lower() + ".ics"

        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(filename, "créé:", len(events), "matchs")


if __name__ == "__main__":
    main()
