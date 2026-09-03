from bs4 import BeautifulSoup
from icalendar import Calendar
from datetime import datetime, timedelta, timezone
from parsers.common import build_description, uid
from utils.ics import ICSEventBuilder
from dict.vhl_dict import VHL_TEAMS, VHL_ARENAS

MSK_TZ = timezone(timedelta(hours=3))

def normalize_vhl(name):
    key = name.lower().strip()
    mapping = VHL_TEAMS.get(key)
    if mapping:
        return mapping["name"]
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
            year = 2026
        else:                # Jan-Apr
            year = 2027

        # Convert date (ex: "14 March")
        try:
            dt_date = datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y")
        except:
            continue
                
        for match in matches:
            home_raw = match.select(".calendar-page__match-team--home .calendar-page__match-team-name")[0].text.strip()
            away_raw = match.select(".calendar-page__match-team--guest .calendar-page__match-team-name")[0].text.strip()
            
            home = normalize_vhl(home_raw)
            away = normalize_vhl(away_raw)

            if not (
                home_raw.lower() in team_name.lower()
                or away_raw.lower() in team_name.lower()
                or team_name.lower() in home_raw.lower()
                or team_name.lower() in away_raw.lower()
            ):
                continue

            time_tag = match.select_one(".calendar-page__match-date-time")
            if not time_tag:
                continue
            time_text = time_tag.text.strip()
            if not time_text or ":" not in time_text:
                continue
            try:
                hour_str, minute_str = time_text.split(":")
                hour = int(hour_str)
                minute = int(minute_str)
            except ValueError:
                print(f"WARNING Cannot parse time {time_text}")
            msk = timezone(timedelta(hours=3))
            dtstart_msk = dt_date.replace(hour=hour, minute=minute, tzinfo=msk)
            end_dt_msk = dtstart_msk + timedelta(hours=2, minutes=30)
            dtstart = dtstart_msk.astimezone(timezone.utc)
            end_dt = end_dt_msk.astimezone(timezone.utc)

            link = match.select_one(".calendar-page__match-detail-link")
            game_id = None

            if link and link.has_attr("href"):
                href = link["href"]
                game_id = href.split("/")[-1].split(".html")[0]

            game_center = f"https://online.vhlru.ru/online/{game_id}"
            city = match.select_one(".calendar-page__match-city").text.strip()
            team_key = home_raw.lower().strip()
            if city in ("Moscow", "Saint Petersburg"):
                arena = VHL_TEAMS.get(team_key, {}).get("arena")
                if not arena:
                    print(f"WARNING No arena for team {home_raw} in {city}")
            else:
                arena = VHL_ARENAS.get(city)
                if arena is None:
                    print(f"WARNING no known arena for {city}")

            description = build_description([
                f"Game Center: {game_center}"
            ])
    
            event = (
                ICSEventBuilder()
                .uid(uid("vhl", game_id))
                .start(dtstart)
                .end(end_dt)
                .summary(f"🏒 | {away} @ {home}")
                .location(arena)
                .description(description)
                .build()
            )

            cal.add_component(event)

    return cal
