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
                feeds.append((league, team["name"], url, []))
            continue

        # ============================
        # LeagueStat leagues (AHL, OHL, LHJMQ, WHL)
        # unified structure
        # ============================
        if parser == "leaguestat":
            base_url = data["base_url"]
            client_code = data["client_code"]

            # season_id can be int or list
            season_ids = data["season_id"]
            if isinstance(season_ids, int):
                season_ids = [season_ids]

            for team in data["teams"]:
                team_name = team["name"]
                team_id = team["team_id"]

                for season_id in season_ids:
                    url = (
                        f"{base_url}"
                        f"?client_code={client_code}"
                        f"&season_id={season_id}"
                        f"&team_id={team_id}"
                    )
                    feeds.append((league, f"{team_name} (S{season_id})", url, []))

            continue

        # ============================
        # CHL Europe (JSON + filters)
        # ============================
        if parser == "chl_europe":
            url = data["url"]

            for team in data.get("teams", []):
                team_name = team["name"]
                team_code = team["code"]
                
                feeds.append((league, team_name, url, [team_code]))
            continue

        # ============================
        # CHL Memorial Cup (JSON)
        # ============================
        if parser == "chl_memorial":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, team["name"], url, []))
            continue

        # ============================
        # UFA JSON feed
        # ============================
        if parser == "ufa":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, team["name"], url, []))
            continue

        # ============================
        # ICS-only leagues (ECHL, NCAA, SHL, KHL)
        # ============================
        if parser == "ics":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, team["name"], url, []))
            continue

        print(f"Warning: Unknown parser for league '{league}'")

    return feeds
