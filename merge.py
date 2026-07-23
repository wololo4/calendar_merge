import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from utils.database import export_calendar_from_db, initialize_database, store_event
from utils.downloader import download_single_feed
from utils.feeds import load_feeds
from utils.calendar import create_calendar, event_id

def event_id(event):
    dtstart = str(event.get("DTSTART"))
    summary = str(event.get("SUMMARY", "")).strip()

    if " vs " in summary:
        parts = summary.split(" vs ")
        home = parts[0].strip()
        away = parts[1].strip()
        teams_sorted = "-".join(sorted([home, away]))
        return f"{dtstart}-{teams_sorted}"

    return f"{dtstart}-{summary}"

def main():
    leagues = defaultdict(list)
    seen = defaultdict(set)
    feeds = load_feeds()
    initialize_database()

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

            uid = str(event.get("UID", "")).strip()

            if uid in seen[league]:
                continue

            seen[league].add(uid)
            leagues[league].append(event)

            summary = str(event.get("SUMMARY", ""))
            location = str(event.get("LOCATION", ""))
            description = str(event.get("DESCRIPTION", ""))
            uid = str(event.get("UID", ""))
            dtstart = event.get("DTSTART")
            dtend = event.get("DTEND")
            dtstart_value = dtstart.dt.isoformat() if hasattr(dtstart, "dt") else str(dtstart)
            dtend_value = dtend.dt.isoformat() if hasattr(dtend, "dt") else str(dtend)

            store_event(
                league=league,
                team_name=team_name,
                source_url="",
                parser="",
                uid=uid,
                summary=summary,
                location=location or None,
                description=description or None,
                dtstart=dtstart_value,
                dtend=dtend_value or None,
            )

    os.makedirs("calendars", exist_ok=True)

    for league, events in leagues.items():
        output = export_calendar_from_db(league=league)

        filename = f"calendars/{league.lower()}.ics"
        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(f"{filename} créé: {len(events)} matchs")

if __name__ == "__main__":
    main()
