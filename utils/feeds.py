FEEDS_FILE = "feeds.txt"

def load_feeds():
    feeds = []
    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            league = parts[0].strip()
            url = parts[1].strip()
            team_filter = parts[2].strip() if len(parts) > 2 else ""

            team_filter_list = [t.strip() for t in team_filter.split(",") if t.strip()]
            feeds.append((league, url, team_filter_list))
    return feeds
