import yaml

def load_feeds():
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feeds = []

    # Iterate through each league block in YAML
    for league, data in config.items():

        # Skip comments or non-league keys
        if league.startswith("#"):
            continue

        # ============================
        # 1. LeagueStat leagues (OHL, LHJMQ, WHL, AHL)
        # ============================
        if data.get("parser") == "leaguestat":
            base_url = data["base_url"]
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
        # 2. CHL Europe (special JSON parser + filters)
        # ============================
        if data.get("parser") == "chl_europe":
            url = data["url"]
            team_filter = data.get("filter", {}).get("teams", [])
            feeds.append((league, url, team_filter))
            continue

        # ============================
        # 3. UFA JSON feed
        # ============================
        if data.get("parser") == "ufa":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # 4. CHL Memorial Cup (JSON)
        # ============================
        if data.get("parser") == "chl_memorial":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # 5. NHL (ICS + JSON)
        # ============================
        if data.get("parser") == "nhl":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # 6. ICS-only leagues (ECHL, NCAA, SHL, KHL)
        # ============================
        if data.get("parser") == "ics":
            for team in data["teams"]:
                url = team["url"]
                feeds.append((league, url, []))
            continue

        # ============================
        # 7. Unknown parser → skip
        # ============================
        print(f"Warning: League '{league}' has unknown parser '{data.get('parser')}'")

    return feeds
