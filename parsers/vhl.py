from bs4 import BeautifulSoup
from icalendar import Calendar
from datetime import datetime, timedelta
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder
from dict.vhl_dict import VHL_TEAMS

def normalize_vhl(name):
    key = name.lower().strip()
    # Debug print intégré
    if key in VHL_TEAMS:
        return VHL_TEAMS[key]["name"]
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name

def parse_vhl_html(html, team_name, season_id):
    soup = BeautifulSoup(html, "html.parser")
    cal = Calendar()

    for day in soup.select(".calendar-page__day"):
        date_text = day.select_one(".calendar-page__day-date").text.strip()
        matches = day.select(".calendar-page__match")

        # Extract month name
        try:
            day_num, month_name = date_text.split()
        except:
            continue

        # Determine correct year
        month_num = datetime.strptime(month_name, "%B").month

        if month_num >= 8:   # Aug-Dec
            year = 2025
        else:                # Jan-Apr
            year = 2026

        # Convert date (ex: "14 March")
        try:
            dt_date = datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y")
            dtstart = dt_date.replace(hour=0, minute=0)
            end_dt = dtstart + timedelta(hours=2, minutes=30)
        except:
            continue
                
        for match in matches:
            home_raw = match.select(".calendar-page__match-team--home .calendar-page__match-team-name")[0].text.strip()
            away_raw = match.select(".calendar-page__match-team--guest .calendar-page__match-team-name")[0].text.strip()

            home = normalize_vhl(home_raw)
            away = normalize_vhl(away_raw)

            # Normalisation pour matcher "Khimik Voskresensk" avec "Khimik"
            if not (
                home_raw.lower() in team_name.lower()
                or away_raw.lower() in team_name.lower()
                or team_name.lower() in home_raw.lower()
                or team_name.lower() in away_raw.lower()
            ):
                continue

            link = match.select_one(".calendar-page__match-detail-link")
            game_id = None

            if link and link.has_attr("href"):
                href = link["href"]
                if "idgame=" in href:
                    game_id = href.split("idgame=")[-1].split("&")[0]

            game_center = f"https://www.vhlru.ru/en/report/{season_id}/?idgame={game_id}"
            home_key = home_raw.lower().strip()
            arena = VHL_TEAMS.get(home_key, {}).get("arena")

            description = build_description([
                f"Game Center: {game_center}"
            ])
    
            event = (
                ICSEventBuilder()
                .uid(uid("vhl", game_id))
                .start(dtstart)
                .end(end_dt)
                .summary(f"🏒 | {home} vs {away}")
                .location(arena)
                .description(description)
                .build()
            )

            cal.add_component(event)

    return cal
