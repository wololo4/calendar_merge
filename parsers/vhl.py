from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

VHL_TEAMS = {
    "akm": {
        "name": "AKM Tula",
        "arena": "Ice Palace"
    },
    "bars": {
        "name": "Bars Kazan",
        "arena": "Sports Palace Kazan"
    },
    "buran": {
        "name": "Buran Voronezh",
        "arena": "LDS Jubileiny"
    },
    "chelmet": {
        "name": "Chelmet Chelyabinsk",
        "arena": "Yunost Sport Palace"
    },
    "ska-vmf": {
        "name": "SKA-VMF Saint Petersburg",
        "arena": "Ice Palace"
    },

    "csk vvs": {
        "name": "CSK VVS Samara",
        "arean": "Vladimir Vysotsky Sport Palace"
    },
    "chelny": {
        "name": "Chelny Naberezhnye",
        "arena": "Ice Sports Palace"
    },
    "dizel": {
        "name": "Dizel Penza",
        "arena": "Dizel Arena"
    },
    "dynamo spb": {
        "name": "Dynamo Saint-Petersburg",
        "arena": "Yubileyny Sports Palace"
    },
    "dynamo-altai": {
        "name": "Dynamo Altai Barnaul",
        "arena": "Titov Arena"
    },
    "gornyak-ugmk": {
        "name": "Gornyak-UGMK Verkhnyaya Pyshma",
        "arena": "Alexei Kozitsyn Ice Arena"
    },
    "hc norilsk": {
        "name": "HC Norilsk",
        "arena": "Artika Sport Palace"
    },
    "hc tambov": {
        "name": "HC Tambov",
        "arena": "Crystall Ice Palace"
    },
    "izhstal": {
        "name": "Izhstal Izhevsk",
        "arena": "Sports Palace Izhstal"
    },
    "khimik": {
        "name": "Khimik Voskresensk",
        "arena": "Podmoskovie Ice Palace"
    },
    "kristall s": {
        "name": "Kristall Saratov",
        "arena": "Sports Palace Kristall"
    },
    "magnitka": {
        "name": "Magnitka Magnitogorsk",
        "arena": "Ice Sport Palace"
    },
    "metallurg nk": {
        "name": "Metallurg Novokuznetsk",
        "arena": "Kuznetsk Metallurgists Sports Palace"
    },
    "molot": {
        "name": "Molot Perm",
        "arena": "Universal Sports Palace Molot"
    },
    "neftyanik": {
        "name": "Neftyanik Almetyevsk",
        "arena": "Yubileyny Sports Palace"
    },
    "olimpiya": {
        "name": "Olympiya Kirovo-Chepetsk",
        "arena": "Olimp-Arena"
    },
    "omskie krylya": {
        "name": "Omskie Krylya Omsk",
        "arena": "Avangard Hockey Academy"
    },
    "rostov": {
        "name": "HC Rostov",
        "arena": "Ice Arena"
    },
    "rubin": {
        "name": "Rubin Tyumen",
        "arena": "Sports Palace Tyumen"
    },
    "ryazan-vdv": {
        "name": "Ryazan-VDV",
        "arena": "Ryazan Olympic Sports Palace"
    },
    "ska-vmf": {
        "name": "SKA-VMF Saint Petersburg",
        "arena": "Hockey City Sport Complex"
    },
    "sokol": {
        "name": "Sokol Krasnoyarsk",
        "arena": "Arena Sever"
    },
    "toros": {
        "name": "Toros Neftekamsk",
        "arena": "Ice Palace Neftekamsk"
    },
    "torpedo-gorky": {
        "name": "Topedo-Gorky Nizhny-Novgorod",
        "arena": "Konovalenko Sports Palace"
    },
    "ugra": {
        "name": "Ugra Khanty-Mansiysk",
        "arena": "Arena Ugra"
    },
    "yuzhny ural": {
        "name": "Yuzhny Ural Orsk",
        "arena": "Ice Palace Yubileyny"
    },
    "zauralye": {
        "name": "Zauralye Kurgan",
        "arena": "Ice Sports Palace Mostovik"
    },
    "zvezda": {
        "name": "Zvezda Moscow",
        "arena": "CSKA Ice Palace"
    }
}

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

            # No time in VHL pages → default 00:00
            dtstart = dt_date.replace(hour=0, minute=0)
            end_dt = dtstart + timedelta(hours=2, minutes=30)

            link = match.select_one(".calendar-page__match-detail-link")
            game_id = None

            if link and link.has_attr("href"):
                href = link["href"]
                if "idgame=" in href:
                    game_id = href.split("idgame=")[-1].split("&")[0]

            game_center = f"https://www.vhlru.ru/en/report/{season_id}/?idgame={game_id}"

            event = Event()
            event.add("SUMMARY", f"🏒 | {home} vs {away}")
            event.add("DTSTART", dtstart)
            event.add("DTEND", end_dt)
            event.add("UID", f"vhl{game_id}")
            event.add("DESCRIPTION", f"Game Center: {game_center}")

            home_key = home_raw.lower().strip()
            arena = VHL_TEAMS.get(home_key, {}).get("arena")
            if arena:
                event.add("LOCATION", arena)

            cal.add_component(event)

    return cal
