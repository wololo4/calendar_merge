import os
import json  # <-- Fixed: Added to prevent the NameError on KHL/UFA fallback
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests
from icalendar import Calendar, Event
from concurrent.futures import ThreadPoolExecutor  # <-- New: For parallel downloads
from utils.downloader import download_single_feed

FEEDS_FILE = "feeds.txt"

def load_feeds():
    feeds = []
    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            league = parts[0].strip()
            url = parts[1].strip()
            team_filter = parts[2].strip() if len(parts) > 2 else ""

            team_filter_list = [t.strip() for t in team_filter.split(",") if t.strip()]
            feeds.append((league, url, team_filter_list))
    return feeds

def download_single_feed(feed_info):
    """Worker function to process one feed concurrently."""
    league, url, team_filter = feed_info
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
        response = session.get(url, headers=headers, timeout=4) # Reduced timeout
        response.raise_for_status()

        try:
            raw_json = response.json()
            if "games" in raw_json:
                games_list = raw_json.get("games", [])
                if games_list and isinstance(games_list, list) and "startTimeUTC" in games_list[0]:
                    return league, parse_nhl_json_to_calendar(raw_json)
                else:
                    return league, parse_ufa_json_to_calendar(raw_json)
            if raw_json.get("_type") == "Corebine.Core.Protocol.Response.Array":
                return league, parse_chl_europe_json_to_calendar(raw_json, team_filter)
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
    with ThreadPoolExecutor(max_workers=35) as executor:
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
