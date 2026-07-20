import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from utils.downloader import download_single_feed
from utils.feeds import load_feeds
from utils.calendar import create_calendar, event_id

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

    os.makedirs("calendars", exist_ok=True)

    for league, events in leagues.items():
        output = create_calendar()
        for event in events:
            output.add_component(event)

        filename = os.path.join(f"calendars/{league.lower()}.ics"
        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(f"{filename} créé: {len(events)} matchs")

if __name__ == "__main__":
    main()
