import requests
from icalendar import Calendar
from datetime import datetime
import os

OUTPUT_FILE = "calendar.ics"
FEEDS_FILE = "feeds.txt"


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip() and not line.startswith("#")
        ]


def download_calendar(url):
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )
        response.raise_for_status()
        return Calendar.from_ical(response.content)

    except Exception as e:
        print(f"Erreur avec {url}")
        print(e)
        return None


def event_key(event):
    uid = str(event.get("UID", ""))
    start = str(event.get("DTSTART", ""))
    return uid + start


def merge_calendars():

    merged = Calendar()

    merged.add(
        "prodid",
        "-//Calendrier fusionné//ChatGPT//"
    )

    merged.add(
        "version",
        "2.0"
    )

    seen = set()

    feeds = load_feeds()

    print(f"{len(feeds)} calendriers trouvés")

    for url in feeds:

        print(f"Chargement : {url}")

        calendar = download_calendar(url)

        if calendar is None:
            continue

        for component in calendar.walk():

            if component.name != "VEVENT":
                continue

            key = event_key(component)

            if key in seen:
                continue

            seen.add(key)
            merged.add_component(component)


    with open(
        OUTPUT_FILE,
        "wb"
    ) as file:

        file.write(
            merged.to_ical()
        )

    print(
        f"{len(seen)} événements créés dans {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    merge_calendars()
