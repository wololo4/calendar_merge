from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import 

def parse_vhl_html(html, team_name):
    soup = BeautifulSoup(html, "html.parser")
    cal = Calendar()

    for day in soup.select(".calendar-page__day"):
        date_text = day.select_one(".calendar-page__day-date").text.strip()
        matches = day.select(".calendar-page__match")

        # Convert date (ex: "14 March")
        try:
            dt_date = datetime.strptime(date_text + " 2026", "%d %B %Y")
        except:
            continue
                
        for match in matches:
            home = match.select(".calendar-page__match-team--home .calendar-page__match-team-name")[0].text.strip()
            away = match.select(".calendar-page__match-team--guest .calendar-page__match-team-name")[0].text.strip()

            if team_name not in (home, away):
                continue

            # No time in VHL pages → default 00:00
            dtstart = dt_date.replace(hour=0, minute=0)

            event = Event()
            event.add("SUMMARY", f"🏒 VHL | {home} vs {away}")
            event.add("DTSTART", dtstart)
            event.add("DTEND", dtstart)
            event.add("UID", f"vhl-{home}-{away}-{dtstart}")

            cal.add_component(event)

    return cal
