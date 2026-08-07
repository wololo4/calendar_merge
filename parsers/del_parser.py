from bs4 import BeautifulSoup
from icalendar import Calendar
from datetime import datetime, timedelta
from parsers.common import parse_iso_datetime_duration, build_description, uid, normalize_team
from utils.ics import ICSEventBuilder
from dict.del_dict import DEL_TEAMS

DEL_TEAMS_NORMALIZED = {k.lower().strip(): v for k, v in DEL_TEAMS.items()}

def parse_del_html(html, team_name):
    soup = BeautifulSoup(html, "html.parser")
    cal = Calendar()

    rows = soup.select("table.team-schedule tbody tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        raw_date = cols[0].get_text(strip=True).split(",")[-1].strip()
        raw_time = cols[1].get_text(strip=True)

        try:
            date_obj = datetime.strptime(raw_date, "%d.%m.%Y")
        except:
            continue
        
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

        arena = DEL_TEAMS_NORMALIZED.get(home.lower().strip(), home)

        date_uid = date_obj.strftime("%Y")

        game_id = f"{date_uid}{home_id}{away_id}{spieltag}"

        event = (
            ICSEventBuilder()
            .uid(uid("del", game_id))
            .start(dt)
            .end(dt_end)
            .summary(f"🏒 | {away} @ {home}")
            .location(arena)
            #.description()
            .build()
        )

        cal.add_component(event)

    return cal
