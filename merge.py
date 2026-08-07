import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from utils.database import export_calendar_from_db, initialize_database, store_event
from utils.downloader import download_single_feed
from utils.feeds import load_feeds

def main():
    leagues = defaultdict(list)
    feeds = load_feeds()
    initialize_database()

    with ThreadPoolExecutor(max_workers=35) as executor:
        results = executor.map(download_single_feed, feeds)
    
    for league, team_name, calendar in results:
        if calendar is None:
            print(f"Téléchargement: {league} – {team_name} (0 events, skipped)")
            continue
    
        event_count = sum(1 for e in calendar.walk() if e.name == "VEVENT")
        print(f"Téléchargement: {league} – {team_name} ({event_count} events)")

        for event in calendar.walk():
            if event.name != "VEVENT":
                continue

            summary = str(event.get("SUMMARY", ""))
            location = str(event.get("LOCATION", ""))
            description = str(event.get("DESCRIPTION", ""))
            uid = str(event.get("UID", ""))

            dtstart = event.get("DTSTART")
            dtend = event.get("DTEND")
            dtstart_value = dtstart.dt.isoformat() if hasattr(dtstart, "dt") else str(dtstart)
            dtend_value = dtend.dt.isoformat() if hasattr(dtend, "dt") else str(dtend)

            db_league = "NCAA" if league.startswith("NCAA") else league

            store_event(
                league=db_league,
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

            leagues[league].append(event)

    os.makedirs("calendars", exist_ok=True)

    ncaas = []
    for league, events in leagues.items():
        if league.startswith("NCAA"):
            ncaas.extend(events)

    if ncaas:
        leagues["NCAA"] = ncaas
        for league in list(leagues.keys()):
            if league.startswith("NCAA_"):
                del leagues[league]

    for league, events in leagues.items():
        output = export_calendar_from_db(league=league)

        filename = f"calendars/{league.lower()}.ics"
        with open(filename, "wb") as file:
            file.write(output.to_ical())

        print(f"{filename} créé: {len(events)} matchs")

if __name__ == "__main__":
    main()
