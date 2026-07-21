import yaml

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
        # NHL (ICS + JSON)
        # ============================
        if parser == "nhl":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # LeagueStat leagues (AHL, OHL, LHJMQ, WHL)
        # ============================
        if parser == "leaguestat":
            base_url = data["base_url"]
            client_code = data["client_code"]

            # AHL uses "params" inside each team
            if "teams" in data:
                team_id = data["team_id"]
                for team in data["teams"]:
                    season_id = team["season_id"]
                    url = (
                        f"{base_url}"
                        f"?client_code={client_code}"
                        f"&season_id={season_id}"
                        f"&team_id={team_id}"
                    )
                    feeds.append((league, url, []))
                continue

            # OHL / LHJMQ / WHL use league-level client_code + season_id
            client_code = data["client_code"]
            season_id = data["season_id"]

            for team in data["teams"]:
                team_id = team["team_id"]
                url = (
                    f"{base_url}"
                    f"?client_code={client_code}"
                    f"&season_id={season_id}"
                    f"&team_id={team_id}"
                )
                feeds.append((league, url, []))
            continue

        # ============================
        # CHL Europe (JSON + filters)
        # ============================
        if parser == "chl_europe":
            url = data["url"]
            team_filter = data.get("filter", {}).get("teams", [])
            feeds.append((league, url, team_filter))
            continue

        # ============================
        # CHL Memorial Cup (JSON)
        # ============================
        if parser == "chl_memorial":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # UFA JSON feed
        # ============================
        if parser == "ufa":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # ICS-only leagues (ECHL, NCAA, SHL, KHL)
        # ============================
        if parser == "ics":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        print(f"Warning: Unknown parser for league '{league}'")

    return feeds
