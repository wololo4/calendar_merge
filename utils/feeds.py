import yaml
import requests
import cloudscraper
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from parsers.ncaa import ncaa_date_range
from parsers.hockeytech import map_season_phases

def parse_any_date(s):
    # Formats possibles
    formats = [
        "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%m-%d-%y", "%m/%d/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Unrecognized date format: {s}")

def hockeytech_fetch_seasons(base_url):
    # Convert schedule URL → seasons URL
    seasons_url = base_url.replace("view=schedule", "view=seasons") + "&fmt=json"
    scraper = cloudscraper.create_scraper()
    raw = scraper.get(seasons_url).text
    data = json.loads(raw)
    return data.get("SiteKit", {}).get("Seasons", [])


def hockeytech_pick_current_season(seasons):
    today = datetime.now()
    cutoff = datetime(today.year, 7, 1)
    if today >= cutoff:
        target_year = today.year
    else:
        target_year = today.year - 1
    for s in seasons:
        if s.get("playoff") == "0" and "Regular Season" in s.get("season_name", ""):
            start = datetime.fromisoformat(s["start_date"])
            if start.year == target_year:
                return s

    return None

def hockeytech_find_playoffs(seasons, regular_season):
    if not regular_season:
        return None

    reg_end = datetime.fromisoformat(regular_season["end_date"])
    for s in seasons:
        if s.get("playoff") == "1":
            start = datetime.fromisoformat(s["start_date"])
            if start > reg_end:
                return s
    return None

def extract_latest_season(html):
    soup = BeautifulSoup(html, "html.parser")
    season_select = soup.find("select", {"class": "season_select"})
    if not season_select:
        return None

    values = []
    for opt in season_select.find_all("option"):
        try:
            values.append(int(opt.get("value")))
        except:
            pass

    return str(max(values)) if values else None

def extract_regular_subseason(html):
    soup = BeautifulSoup(html, "html.parser")
    sub_select = soup.find("select", {"class": "sub_season_select"})
    if not sub_select:
        return None

    subseasons = []
    playoff_keywords = ["quart", "demi", "finale", "championnat", "coupe", "séries"]
    for opt in sub_select.find_all("option"):
        val = opt.get("value")
        name = opt.text.strip()
        if not val:
            continue
        if "saison régulière" in name.lower():
            subseasons.append((val, opt.text.strip()))
            continue

        if any(k in name.lower() for k in playoff_keywords):
            subseasons.append((val, opt.text.strip()))
    
    return subseasons

def load_feeds():
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feeds = []

    for league, data in config.items():
        if league.startswith("#"):
            continue

        parser = data.get("parser")

        # ============================
        # NHL (JSON)
        # ============================
        if parser == "nhl":
            for team in data.get("teams", []):
                feeds.append((league, team["name"], team["url"], [], "nhl"))
            continue

        # ============================
        # HockeyTech leagues (AHL, ECHL, LHJMQ, OHL, WHL, BCHL, PWHL)
        # ============================
        if parser == "hockeytech" and league != "Hockey_Canada":
            base_url = data["base_url"]
            teams = data.get("teams", [])

            seasons = hockeytech_fetch_seasons(base_url)
            regular = hockeytech_pick_current_season(seasons)
            playoffs = hockeytech_find_playoffs(seasons, regular)
            
            for season_obj in [regular, playoffs]:
                if not season_obj:
                    continue
                season_id = season_obj["season_id"]
                season_name = season_obj["season_name"]

                for team in teams:
                    team_name = team["name"]
                    team_id = team["team_id"]
                    url = (
                        f"{base_url}"
                        f"&team_id={team_id}"
                        f"&season_id={season_id}"
                    )

                    feeds.append(
                        (
                            league,
                            f"{team_name} ({season_name})",
                            url,
                            [team_id],
                            "hockeytech"
                        )
                    )
            continue

        # ============================
        # HockeyTech leagues (hockey canada)
        # ============================
        if parser == "hockeytech" and league == "Hockey_Canada":
            base_url = data["base_url"]

            for l in data["league_id"]:
                seasons_url = (f"{base_url}&view=seasons&league_id={l}")
                seasons_json = requests.get(seasons_url).json()
                seasons = seasons_json["SiteKit"]["Seasons"]

                today = datetime.now()
                july_first_this_year = datetime(today.year, 7, 1)

                if today < july_first_this_year:
                    cutoff = datetime(today.year - 1, 7, 1)
                else:
                    cutoff = july_first_this_year

                filtered_seasons = []
                for s in seasons:
                    start_date = datetime.strptime(s["start_date"], "%Y-%m-%d")
                    if start_date >= cutoff:
                        filtered_seasons.append(s)

                # season_id can be int or list (ECHL uses int)
                season_ids = [s["season_id"] for s in filtered_seasons]
                if isinstance(season_ids, int):
                    season_ids = [season_ids]

                for season_id in season_ids:
                    url = f"{base_url}&view=schedule&season_id={season_id}"
                    feeds.append(
                        (
                            league,
                            f"{league} (S{season_id})",
                            url,
                            [],
                            "hockeytech"
                        )
                    )
                continue

        # ============================
        # Publication Sports league (LHMAAAQ et LHJAAAQ)
        # ============================
        if parser == "publicationsports":
            base_url = data["base_url"]
            team_filter = [str(t["team_id"]) for t in data.get("teams", [])]

            scraper = cloudscraper.create_scraper()
            html = scraper.get(base_url).text

            response = scraper.get(base_url)

            current_season = extract_latest_season(html)
            current_sub = extract_regular_subseason(html)

            for sub_id, sub_name in current_sub:
                if league == "LHMAAAQ":
                    category = "5366"
                    full_url = (
                        f"https://www.m18aaa.com/fr/stats/horaire.html?"
                        f"season={current_season}&subSeason={sub_id}&category={category}"
                    )
                if league == "LHJAAAQ":
                    category = "1093"
                    full_url = (
                        f"https://www.lhjaaaq.com/fr/stats/horaire.html?"
                        f"season={current_season}&subSeason={sub_id}&category={category}"
                    )

                feeds.append(
                    (
                        league,
                        f"{league}",
                        full_url,
                        team_filter,
                        "publicationsports"
                    )
                )

            continue

        # ============================
        # NCAA (SIDEARM JSON)
        # ============================
        if parser == "ncaa":
            from_date, to_date = ncaa_date_range()
            from_date = parse_any_date(from_date)
            to_date   = parse_any_date(to_date)

            for team in data.get("teams", []):
                team_name = team["name"]
                base_url = team["base_url"]

                # NEW: detect responsive-calendar feeds
                if "responsive-calendar.ashx" in base_url:
                    # Generate one URL per month
                    current = from_date.replace(day=1)

                    while current <= to_date:
                        # MM/DD/YYYY
                        date_param = f"{current.month:02d}/01/{current.year}"

                        url = (
                            f"{base_url}"
                            f"?type=month"
                            f"&sport={team['sport_id']}"
                            f"&date={date_param}"
                        )

                        feeds.append(
                            (
                                league,
                                team_name,
                                url,
                                [],          # no team filter
                                "ncaa"
                            )
                        )

                        current = current + relativedelta(months=1)

                else:
                    # Standard SIDEARM NCAA JSON feed
                    url = (
                        f"{base_url}/from/{from_date}/to/{to_date}"
                        f"?sportId={team['sport_id']}"
                    )

                    # NCAA does NOT use team filters
                    feeds.append(
                        (
                            league,
                            team_name,
                            url,
                            [],          # no team filter
                            "ncaa"
                        )
                    )

            continue

        # ============================
        # NCAA_ashx (NCHC)
        # ============================
        if parser == "ncaa_conf":
            url = data["base_url"]
            
            for team in data.get("teams", []):
                feeds.append(
                    (
                        league,
                        team["name"],
                        url,
                        [],          # no team filter
                        "ncaa_conf"
                    )
                )
            continue

        # ============================
        # SHL
        # ============================
        if parser == "shl":
            season = data["seasonUuid"]
            series = data["seriesUuid"]
            game_type = data["gameTypeUuid"]
            base_url = data["base_url"]

            for team in data.get("teams", []):
                team_name = team["name"]
                team_uuid = team["uuid"]

                url = (
                    f"{base_url}"
                    f"?seasonUuid={season}"
                    f"&seriesUuid={series}"
                    f"&gameTypeUuid={game_type}"
                    f"&teams[]={team_uuid}"
                )

                feeds.append((league, team_name, url, None, parser))
            continue

        # ============================
        # CHL Europe (JSON + filters)
        # ============================
        if parser == "chl_europe":
            url = data["url"]
            for team in data.get("teams", []):
                feeds.append((league, team["name"], url, [team["code"]], parser))
            continue

        # ============================
        # LIIGA JSON parser
        # ============================
        if parser == "liiga":
            base_url = data["base_url"]
            season = data["season"]
            tournaments = data.get("tournament", [])
            if isinstance(tournaments, str):
                tournaments = [tournaments]

            for team in data.get("teams", []):
                for t in tournaments:
                    url = f"{base_url}?tournament={t}&season={season}"
                    feeds.append((league, f"{team['name']} (T{t})", url, [team["team_id"]], parser))

            continue

        # ============================
        # DEL parser (HTML)
        # ============================
        if parser == "del":
            base_url = data["base_url"]
            for team in data.get("teams", []):
                url = (f"{base_url}/{team['team_id']}")
                feeds.append((league, team["name"], url, None, parser))
            continue

        # ============================
        # UFA JSON feed
        # ============================
        if parser == "ufa":
            base_url = data["base_url"]
            for team in data["teams"]:
                url = (f"{base_url}&teamID={team['team_id']}")
                feeds.append((league, team["name"], url, [], parser))
            continue

        # ============================
        # VHL parser
        # ============================
        if parser == "vhl":
            base_url = data["base_url"]
            season_id = data["season_id"]
            for team in data.get("teams", []):
                url = f"{base_url}/{season_id}/0/{team['team_id']}/"
                feeds.append((league, team["name"], url, season_id, parser))
            continue

        # ============================
        # KHL 
        # ============================
        if parser == "khl":
            base_url = data["base_url"]
            today = datetime.now()
            july_first_this_year = datetime(today.year,7,1)

            if today < july_first_this_year:
                season_start_year = today.year - 1
            else:
                season_start_year = today.year

            season_start = int(datetime(season_start_year,7,1).timestamp())
            season_end = int(datetime(season_start_year + 1,7,1).timestamp())

            for team in data.get("teams", []):
                team_id = team["team_id"]
                url = (
                    f"{base_url}"
                    f"?q[team_a_or_team_b_in][]={team_id}"
                    f"&q[start_at_gt_time_from_unixtime]={season_start}"
                    f"&q[start_at_lt_time_from_unixtime]={season_end}"
                    f"&order_direction=asc"
                )

                feeds.append(
                    (
                        league,
                        team["name"],
                        url,
                        [team_id],
                        "khl"
                    )
                )
            continue

        if parser not in ["hockeytech", "nhl", "publicationsports", "ncaa", "ncaa_conf", "shl", "chl_europe", "liiga", "del", "ufa", "vhl", "khl"]:
            print(f"Warning: Unknown parser for league '{league}'")

    return feeds
