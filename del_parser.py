from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime

def parse_del_html(html, team_name):
    soup = BeautifulSoup(html, "html.parser")
    cal = Calendar()

    rows = soup.select("table.team-schedule tbody tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        # Date (ex: Freitag, 18.09.2026)
        raw_date = cols[0].get_text(strip=True)
        # Remove weekday (Freitag,)
        raw_date = raw_date.split(",")[-1].strip()
        # Convert to datetime
        # Format: 18.09.2026
        try:
            date_obj = datetime.strptime(raw_date, "%d.%m.%Y")
        except:
            continue

        # Time (ex: 19:30)
        raw_time = cols[1].get_text(strip=True)
        try:
            time_obj = datetime.strptime(raw_time, "%H:%M").time()
        except:
            continue

        # Combine date + time
        dt = datetime.combine(date_obj, time_obj)

        # Home team
        home = cols[3].select_one("h6.team-meta__name")
        home = home.get_text(strip=True) if home else "Home"

        # Away team
        away = cols[4].select_one("h6.team-meta__name")
        away = away.get_text(strip=True) if away else "Away"

        event = Event()
        event.add("SUMMARY", f"{home} vs {away}")
        event.add("DTSTART", dt)
        event.add("DTEND", dt)
        event.add("UID", f"del-{home}-{away}-{dt.isoformat()}")

        cal.add_component(event)

    return cal
