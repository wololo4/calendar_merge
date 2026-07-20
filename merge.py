import os
import json  # <-- Fixed: Added to prevent the NameError on KHL/UFA fallback
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests
from icalendar import Calendar, Event
from concurrent.futures import ThreadPoolExecutor  # <-- New: For parallel downloads
from utils.downloader import download_single_feed

FEEDS_FILE = "feeds.txt"

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
