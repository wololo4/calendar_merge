import yaml
from parsers.ncaa import ncaa_date_range
from datetime import datetime
from dateutil.relativedelta import relativedelta

def parse_any_date(s):
    # Formats possibles
    formats = [
        "%Y-%m-%d",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%m-%d-%y",
        "%m/%d/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Unrecognized date format: {s}")

def load_feeds():
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feeds = []

    for league, data in config.items():

        # Skip comments or separators
        if league.startswith("#"):
            continue

        parser = data.get("parser")

        # ============================
        # NHL (JSON)
        # ============================
        if parser == "nhl":
            for team in data.get("teams", []):
                team_name = team["name"]
                url = team["url"]
                feeds.append((league, team_name, url, [], "nhl"))
            continue

        # ============================
        # HockeyTech leagues (AHL, ECHL, LHJMQ, OHL, WHL, BCHL, PWHL)
        # ============================
        if parser == "hockeytech":
            base_url = data["base_url"]

            # season_id can be int or list (ECHL uses int)
            season_ids = data.get("season_id", [])
            if isinstance(season_ids, int):
                season_ids = [season_ids]

            if not data.get("teams", []):
                for season_id in season_ids:
                    url = f"{base_url}&season_id={season_id}"
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

            for team in data.get("teams", []):
                team_name = team["name"]
                team_id = team["team_id"]

                for season_id in season_ids:
                    # HockeyTech schedule URL already contains season_id inside the JSON response
                    # so we do NOT append season_id to the URL.
                    url = (
                        f"{base_url}"
                        f"&team_id={team_id}"
                        f"&season_id={season_id}"
                    )

                    feeds.append(
                        (
                            league,            # "ECHL"
                            f"{team_name} (S{season_id})",
                            url,               # base_url from YAML
                            [team_id],         # team filter list
                            "hockeytech"       # parser name
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
                team_name = team["name"]
                team_code = team["code"]
                
                feeds.append((league, team_name, url, [team_code], parser))
            continue

        # ============================
        # LIIGA JSON parser
        # ============================
        if parser == "liiga":
            base_url = data["base_url"]
            season = data["season"]
            tournaments = data.get("tournament", [])

            # Normalize tournaments to a list
            if isinstance(tournaments, str):
                tournaments = [tournaments]

            for team in data.get("teams", []):
                team_name = team["name"]
                team_id = team["team_id"]

                for tournament in tournaments:
                    url = f"{base_url}?tournament={tournament}&season={season}"
                    feeds.append((league, f"{team_name} (T{tournament})", url, [team_id], parser))

            continue

        # ============================
        # DEL parser (HTML)
        # ============================
        if parser == "del":
            base_url = data["base_url"]
            for team in data.get("teams", []):
                team_name = team["name"]
                team_id = team["team_id"]
                url = (f"{base_url}/{team_id}")
                feeds.append((league, team_name, url, None, parser))
            continue

        # ============================
        # UFA JSON feed
        # ============================
        if parser == "ufa":
            base_url = data["base_url"]
            for team in data["teams"]:
                team_id = team["team_id"]
                url = (f"{base_url}&teamID={team_id}")
                feeds.append((league, team["name"], url, [], parser))
            continue

        # ============================
        # VHL parser
        # ============================
        if parser == "vhl":
            base_url = data["base_url"]
            season_id = data["season_id"]
            
            for team in data.get("teams", []):
                team_name = team["name"]
                team_id = team["team_id"]
                url = f"{base_url}/{season_id}/0/{team_id}/"
                
                feeds.append((league, team_name, url, season_id, parser))
            continue

        # ============================
        # KHL ICS parser (auto URL)
        # ============================
        if parser == "khl":
            base_url = data["base_url"]
            
            for team in data.get("teams", []):
                team_name = team["name"]
                team_id = team["team_id"]
                
                url = f"{base_url}/{team_id};/"
                feeds.append((league, team_name, url, data.get("season_id"), parser))
            continue

        print(f"Warning: Unknown parser for league '{league}'")

    return feeds
