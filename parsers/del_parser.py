from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

DEL_TEAMS = {
    "Augsburger Panther": "Curt Frenzel Stadium",
    "Eisbären Berlin": "Uber Arena",
    "Pinguins Bremerhaven": "Eisarena Bremerhaven",
    "Dresdner Eislöwen": "Joynext Arena",
    "Löwen Frankfurt": "Eissporthalle Frankfurt",
    "ERC Ingolstadt": "Saturn Arena",
    "Iserlohn Roosters": "Eissporthalle Iserlohn",
    "Kölner Haie": "Lanxess Arena",
    "Adler Mannheim": "SAP Arena",
    "EHC Red Bull München": "SAP Garden",
    "Nürnberg Ice Tigers": "PSD Bank Nürnberg Arena",
    "Schwenninger Wild Wings": "Helios Arena",
    "Straubing Tigers": "Eisstadion am Pulvertum",
    "Grizzlys Wolfsburg": "Eis Arena Wolfsburg",
    "Krefeld Pinguine": "Yayla Arena"
}

def normalize_del_team(name):
    key = name.lower().strip()

    # On normalise les clés du dict DEL_TEAMS
    # Exemple: "Kölner Haie" → "kölner haie"
    del_keys = {k.lower().strip(): v for k, v in DEL_TEAMS.items()}

    if key in del_keys:
        return del_keys[key]
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name

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
        dt_end = dt + timedelta(hours=2, minutes=30)

        spieltag_cell = cols[2].get_text(strip=True)
        try:
            spieltag = int(spieltag_cell)
        except:
            spieltag = 0

        # Home team
        home_name_tag = cols[3].select_one("h6.team-meta__name")
        home = home_name_tag.get_text(strip=True) if home_name_tag else "Home"

        home_logo = cols[3].select_one("img")
        home_logo_src = home_logo["src"] if home_logo and home_logo.has_attr("src") else ""
        home_id = home_logo_src.split("team_")[-1].split(".")[0] if "team_" in home_logo_src else "0"

        # Away team
        away_name_tag = cols[4].select_one("h6.team-meta__name")
        away = away_name_tag.get_text(strip=True) if away_name_tag else "Away"

        away_logo = cols[4].select_one("img")
        away_logo_src = away_logo["src"] if away_logo and away_logo.has_attr("src") else ""
        away_id = away_logo_src.split("team_")[-1].split(".")[0] if "team_" in away_logo_src else "0"

        arena = normalize_del_team(home)

        date_uid = date_obj.strftime("%Y")

        uid = f"del{date_uid}{home_id}{away_id}{spieltag}"

        event = Event()
        event.add("SUMMARY", f"🏒 | {away} @ {home}")
        event.add("DTSTART", dt)
        event.add("DTEND", dt_end)
        event.add("UID", uid)
        event.add("LOCATION", arena)

        cal.add_component(event)

    return cal
