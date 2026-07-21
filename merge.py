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
    
    for league, team_name, calendar in results:
        if calendar is None:
            print(f"Téléchargement: {league} – {team_name} (0 events, skipped)")
            continue
    
        event_count = sum(1 for e in calendar.walk() if e.name == "VEVENT")
        print(f"Téléchargement: {league} – {team_name} ({event_count} events)")
        if calendar is None:
            continue

        for event in calendar.walk():
            if event.name != "VEVENT":
                continue

            # Remove ECAL marketing events
            summary = str(event.get("SUMMARY", ""))
            location = str(event.get("LOCATION", ""))
            description = str(event.get("DESCRIPTION", ""))
                
            if "Welcome to" in summary:
                continue

            if "Proudly powered by ECAL" in location:
                continue

            if "powered by ECAL" in description:
                continue

            # Remove DESCRIPTION only if it starts with "You have booked some"
            DESCRIPTION_PREFIXES = [
                "You have booked some",
                "Grab your Tickets",
                "Reminder",
                "Manage my ECAL",
                "SHL | Upplev matchen"
            ]
            
            if any(description.startswith(prefix) for prefix in DESCRIPTION_PREFIXES):
                if "DESCRIPTION" in event:
                    del event["DESCRIPTION"]

           # Remove VALARM blocks inside VEVENT
            for sub in list(event.subcomponents):
                if sub.name == "VALARM":
                    event.subcomponents.remove(sub)

            #remove Microsoft/APPLE/ECAL metadata
            for key in list(event.keys()):
                if key.startswith("X-ECAL"):
                    del event[key]
                if key.startswith("X-MICROSOFT"):
                    del event[key]
                if key.startswith("X-APPLE"):
                    del event[key]

            UNUSED_FIELDS = [
                "TZID",
                "STATUS",
                "PRIORITY",
                "SEQUENCE",
                "CLASS",
                "LAST-MODIFIED",
                "TRANSP",
                "DTSTAMP"
            ]

            for field in UNUSED_FIELDS:
                if field in event:
                    del event[field]

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

        filename = f"calendars/{league.lower()}.ics"
        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(f"{filename} créé: {len(events)} matchs")

if __name__ == "__main__":
    main()
