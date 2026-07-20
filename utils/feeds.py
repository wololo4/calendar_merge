import yaml

def load_feeds():
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feeds = []

    # LeagueStat block
    if "leaguestat" in config:
        for league, data in config["leaguestat"].items():
            base = data["base_url"]
            season = data["season_id"]
            for team in data["teams"]:
                url = f"{base}?client_code={league.lower()}&season_id={season}&team_id={team['team_id']}"
                feeds.append((league, url, []))

    # CHL Europe block
    if "chl_europe" in config:
        url = config["chl_europe"]["url"]
        team_filter = [t["abbr"] for t in config["chl_europe"]["teams"]]
        feeds.append(("CHL_EU", url, team_filter))

    # Generic feeds
    for entry in config.get("feeds", []):
        league = entry["league"]
        url = entry["url"]
        team_filter = entry.get("teams", [])
        feeds.append((league, url, team_filter))

    return feeds
