import requests
import html
from bs4 import BeautifulSoup
from utils.team_id import update_team_ids

HABSPROSPECTS_URL = "https://habsprospects.com/index.html"
BASE_URL = "https://habsprospects.com/"

# CHANGE 1: single source of truth for injury detection
INJURY_TERMS = ("injury", "injured", "return expected")

LEAGUE_MAP = {
    "qmjhl.html": "QMJHL",
    "ohl.html": "OHL",
    "whl.html": "WHL",
    "ncaa.html": "NCAA",
    "bchl.html": "BCHL",
    "russia.html": "Russia",
    "sweden.html": "Sweden",
    "finland.html": "Finland",
    "switzerland.html": "Switzerland",
    "germany.html": "Germany",
    "statschamps.html": "CHL",
}

def fetch_soup(url):
    return BeautifulSoup(requests.get(url).text, "html.parser")

def clean_href(a):
    return (a.get("href") or "").lower().strip()

# CHANGE 1 (continued): shared helper
def is_injured(text):
    text = text.lower()
    return any(term in text for term in INJURY_TERMS)

def scrape_index():
    soup = fetch_soup(HABSPROSPECTS_URL)
    leagues = {}

    def extract_leagues(ul):
        for li in ul.find_all("li"):
            a = li.find("a")
            if not a:
                continue

            href = clean_href(a)

            if href.startswith("stats") and not href.startswith("statschamp"):
                continue
            if href in ("montreal.html", "laval.html", "troisrivieres.html"):
                continue
            if "-" in href:
                continue
            if href.endswith(".html"):
                league_key = LEAGUE_MAP.get(href)
                if league_key:
                    leagues[league_key] = href

    na_menu = soup.find("a", string=lambda x: x and "N-A Prospects" in x)
    extract_leagues(na_menu.find_next("ul"))
    euro_menu = soup.find("a", string=lambda x: x and "Euro Prospects" in x)
    extract_leagues(euro_menu.find_next("ul"))

    return leagues

def scrape_ncaa_page(filename):
    soup = fetch_soup(BASE_URL + filename)

    ncaa = {
        "NCAA_AHA": [],
        "NCAA_BIG10": [],
        "NCAA_CCHA": [],
        "NCAA_EAST": [],
        "NCAA_ECAC": [],
        "NCAA_NCHC": [],
    }

    for td in soup.find_all("td", class_="Style2"):
        text = td.get_text(" ", strip=True)

        # CHANGE 2: skip injured players so injured-only teams drop out
        if is_injured(text):
            continue

        if "(" not in text:
            continue

        conf = text.split("(")[-1].split(")")[0].strip()
        links = td.find_all("a")
        if len(links) < 2:
            continue

        team = links[-1].text.strip()
        if not team:
            continue

        if conf == "Atlantic Hockey":
            ncaa["NCAA_AHA"].append(team)
        elif conf == "Big Ten":
            ncaa["NCAA_BIG10"].append(team)
        elif conf == "CCHA":
            ncaa["NCAA_CCHA"].append(team)
        elif conf == "Hockey East":
            school_url = links[-1].get("href", "").strip()
            if school_url.startswith("http"):
                domain = school_url.split("/")[2]
                base_url = f"https://{domain}"
                ncaa["NCAA_EAST"].append({"name": team, "base_url": base_url})
        elif conf == "ECAC Hockey":
            ncaa["NCAA_ECAC"].append(team)
        elif conf == "NCHC":
            ncaa["NCAA_NCHC"].append(team)

    return ncaa

def scrape_russia(filename):
    soup = fetch_soup(BASE_URL + filename)
    russia = {"KHL": [], "VHL": [], "MHL": []}

    for td in soup.find_all(["td", "span"], class_="Style2"):
        # skip injured players
        if is_injured(td.get_text(" ", strip=True)):
            continue

        links = td.find_all("a")
        if len(links) < 3:
            continue

        team_name = links[1].text.strip()
        league_tag = links[2].text.strip()

        if "KHL" in league_tag:
            russia["KHL"].append(team_name)
        if "VHL" in league_tag:
            russia["VHL"].append(team_name)
        if "MHL" in league_tag:
            russia["MHL"].append(team_name)

    return {league: sorted(teams) for league, teams in russia.items()}

def scrape_chl_page(filename):
    soup = fetch_soup(BASE_URL + filename)
    team_players = {}

    # CHANGE 4: this page is a stats table (Player | Team | GP | ...).
    # The old code looped over every <tr>, including the outer one that wraps
    # the whole table, so it read two player links and used the second player
    # as the team. Now we read only the rows of the sortable table, taking the
    # player from column 2 and the team (plain text, not a link) from column 3.
    for tr in soup.select("table.sortable tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3:
            continue

        if not tds[1].find("a"):  # header row
            continue

        player_name = tds[1].get_text(strip=True)
        team_name = html.unescape(tds[2].get_text(strip=True))
        row_text = tr.get_text(" ", strip=True)

        if not team_name:
            continue

        injured = is_injured(row_text)

        team_players.setdefault(team_name, []).append(injured)

    return sorted(
        team for team, injuries in team_players.items()
        if not all(injuries)
    )

def scrape_league_page(filename):
    soup = fetch_soup(BASE_URL + filename)
    teams = set()

    for td in soup.find_all("td", class_="Style2"):
        # CHANGE 5: skip injured players (QMJHL, OHL, WHL, BCHL, Sweden,
        # Finland, Switzerland, Germany)
        if is_injured(td.get_text(" ", strip=True)):
            continue

        links = td.find_all("a")
        if len(links) >= 2:
            teams.add(links[1].text.strip())

    return sorted(teams)

def main():
    leagues = scrape_index()
    habs_teams = {}
    for league_name, filename in leagues.items():
        if league_name.startswith("NCAA"):
            habs_teams.update(scrape_ncaa_page(filename))
        elif league_name == "Russia":
            habs_teams.update(scrape_russia(filename))
        elif league_name == "CHL":
            habs_teams["STATSCHAMPS"] = scrape_chl_page(filename)
        else:
            habs_teams[league_name] = scrape_league_page(filename)

    update_team_ids(habs_teams)

if __name__ == "__main__":
    main()
