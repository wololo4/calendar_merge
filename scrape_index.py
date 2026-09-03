import requests
import html
from bs4 import BeautifulSoup
from utils.team_id import update_team_ids

HABSPROSPECTS_URL = "https://habsprospects.com/index.html"
BASE_URL = "https://habsprospects.com/"

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

    return russia

def scrape_chl_page(filename):
    soup = fetch_soup(BASE_URL + filename)
    teams = set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        team_name = tds[2].get_text(strip=True)
        if team_name.lower() in ("team", "player"):
            continue
        team_name = html.unescape(team_name)
        if team_name:
            teams.add(team_name)
    return sorted(teams)

def scrape_league_page(filename):
    soup = fetch_soup(BASE_URL + filename)
    teams = set()

    for td in soup.find_all("td", class_="Style2"):
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
