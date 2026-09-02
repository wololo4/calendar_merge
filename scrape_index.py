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

def scrape_index():
    resp = requests.get(HABSPROSPECTS_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    leagues = {}

    # 1. Find the N-A Prospects menu
    na_menu = soup.find("a", string=lambda x: x and "N-A Prospects" in x)
    na_ul = na_menu.find_next("ul")

    # 2. Find the Euro Prospects menu
    euro_menu = soup.find("a", string=lambda x: x and "Euro Prospects" in x)
    euro_ul = euro_menu.find_next("ul")

    # Helper to extract league pages
    def extract_leagues(ul):
        for li in ul.find_all("li"):
            a = li.find("a")
            if not a:
                continue

            href = a.get("href", "").lower()

            # IGNORE stats pages
            if href.startswith("stats") and not href.startswith("statschamp"):
                continue

            # IGNORE pro team pages
            if href in ("montreal.html", "laval.html", "troisrivieres.html"):
                continue

            # IGNORE player pages
            if href.endswith(".html") and "-" in href:
                continue

            # Only league pages remain
            if href.endswith(".html"):
                league_name = href.replace(".html", "").upper()
                leagues[league_name] = href

    extract_leagues(na_ul)
    extract_leagues(euro_ul)

    return leagues

def scrape_ncaa_page(filename):
    url = BASE_URL + filename
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    ncaa = {
        "NCAA_AHA": [],
        "NCAA_BIG10": [],
        "NCAA_CCHA": [],
        "NCAA_EAST": [],
        "NCAA_ECAC": [],
        "NCAA_NCHC": [],
    }

    for td in soup.find_all("td"):
        classes = td.get("class", [])
        if "Style2" not in classes:
            continue

        text = td.get_text(" ", strip=True)
        if "(" not in text or ")" not in text:
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
                ncaa["NCAA_EAST"].append({
                    "name": team,
                    "base_url": base_url
                })
            else:
                print(f"No base url for NCAA_EAST {team}")
        elif conf == "ECAC Hockey":
            ncaa["NCAA_ECAC"].append(team)
        elif conf == "NCHC":
            ncaa["NCAA_NCHC"].append(team)
        
    return ncaa

def scrape_russia(filename):
    url = BASE_URL + filename
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    russia = {
        "KHL": [],
        "VHL": [],
        "MHL": [],
    }

    for td in soup.find_all(["td", "span"], class_="Style2"):
        links = td.find_all("a")
        if len(links) < 3:
            continue

        team_name = links[1].text.strip()
        profile_league = links[2].text.strip()

        if "KHL" in profile_league:
            league = "KHL"
        if "VHL" in profile_league:
            league = "VHL"
        if "MHL" in profile_league:
            league = "MHL"

        # Store result
        if league:
            russia[league].append(team_name)

    return russia

def extract_hockey_east_school_urls(filename):
    url = BASE_URL + filename
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    schools = {}

    for td in soup.find_all("td", class_="Style2"):
        text = td.get_text(" ", strip=True)

        if "(Hockey East)" not in text:
            continue

        links = td.find_all("a")
        if len(links) < 2:
            continue

        team_name = links[-1].text.strip()
        school_url = links[-1].get("href", "").strip()

        if not school_url.startswith("http"):
            continue

        domain = school_url.split("/")[2]
        base_url = f"https://{domain}/api/v2/Calendar"

        schools[team_name] = base_url

    return schools

def scrape_chl_page(filename):
    url = BASE_URL + filename
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    teams = set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        team_cell = tds[2]
        team_name = team_cell.get_text(strip=True)
        if team_name.lower() == "team" or team_name.lower() == "player":
            continue
        team_name = html.unescape(team_name)
        if team_name:
            teams.add(team_name)
    return sorted(teams)

def scrape_league_page(league_filename):
    url = BASE_URL + league_filename
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    teams = set()

    # Every player row looks like: PLAYER - TEAM
    for td in soup.find_all("td", class_="Style2"):
        links = td.find_all("a")
        if len(links) < 2:
            continue

        # SECOND <a> IS ALWAYS THE TEAM
        team = links[1].text.strip()
        teams.add(team)

    return sorted(teams)

def main():
    leagues = scrape_index()
    habs_teams = {}
    for league_name, filename in leagues.items():
        if league_name.startswith("NCAA"):
            habs_teams.update(scrape_ncaa_page(filename))
        elif league_name == "RUSSIA":
            habs_teams.update(scrape_russia(filename))
        elif league_name == "STATSCHAMPS":
            habs_teams["STATSCHAMPS"] = scrape_chl_page(filename)
        else:
            habs_teams[league_name] = scrape_league_page(filename)

    update_team_ids(habs_teams)

if __name__ == "__main__":
    main()
