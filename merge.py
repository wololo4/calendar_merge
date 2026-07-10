import requests
from icalendar import Calendar
from collections import defaultdict


FEEDS_FILE = "feeds.txt"


def load_feeds():

    feeds = []

    with open(FEEDS_FILE, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            league, url = line.split("|", 1)

            feeds.append(
                (league.strip(), url.strip())
            )

    return feeds



def download_calendar(url):
    
    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Accept": "text/calendar,text/plain,*/*",
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

    return Calendar.from_ical(response.content)



def create_calendar():

    cal = Calendar()

    cal.add(
        "prodid",
        "-//Hockey Calendar//"
    )

    cal.add(
        "version",
        "2.0"
    )

    return cal



def event_id(event):

    return (
        str(event.get("UID"))
        +
        str(event.get("DTSTART"))
    )



def main():

    leagues = defaultdict(list)

    seen = defaultdict(set)


    feeds = load_feeds()


    for league, url in feeds:

        print(
            "Téléchargement:",
            league
        )

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

            print(
                "Erreur:",
                league,
                e
            )



    for league, events in leagues.items():

        output = create_calendar()


        for event in events:

            output.add_component(event)


        filename = (
            league.lower()
            +
            ".ics"
        )


        with open(
            filename,
            "wb"
        ) as file:

            file.write(
                output.to_ical()
            )


        print(
            filename,
            "créé:",
            len(events),
            "matchs"
        )



if __name__ == "__main__":

    main()
