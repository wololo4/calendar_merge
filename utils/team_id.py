from ruamel.yaml import YAML
import json
import requests
import time
from dict.khl_dict import TEAM_SYNONYMS

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=4, offset=2)

ALWAYS_KEEP = {
    "LHJMQ": {"Chicoutimi Saguenéens"},
}

NCAA_MAP = {
    "NCAA_AHA": "NCAA",
    "NCAA_CCHA": "NCAA",
    "NCAA_ECAC": "NCAA",
    "NCAA_NCHC": "NCAA",
}

LIIGA_SYNONYMS = {
    "TPS": "TPS Turku",
}

SHL_SYNONYMS = {
    "Luleå Hockey": "Luleå HF",
}

SCRAPER_TO_YAML = {
    "Finland": "Liiga",
    "Germany": "DEL",
    "KHL": "Russia",
    "MHL": "Russia",
    "LHJMQ": "QMJHL",
    "STATSCHAMPS": "CHL",
    "Switzerland": "NL",
    "VHL": "Russia",
}

def normalize_team_name(name, league=None):
    name = name.strip()

    if league == "LHJMQ":
        # API: "City, Nickname"
        if "," in name:
            city, nickname = name.split(",", 1)
            return f"{city.strip()} {nickname.strip()}"
        parts = name.split()
        if len(parts) >= 2:
            city = parts[0]
            nickname = " ".join(parts[1:])
            return f"{nickname.strip()} {city.strip()}"
    if league.startswith("NCAA"):
        name = name.replace("University of ", "")
        name = name.replace("University ", "")
        out = name.strip()
        return out

    return name

def fetch_json(url, timeout=10):
    return json.loads(requests.get(url, timeout=timeout).text)

def chl_fetch(base_url, league=None):
    data = fetch_json(base_url.replace("schedule", "teams"))
    return {
        t["name"].strip(): t["shortName"].strip()
        for t in data.get("data", [])
        if t.get("name") and t.get("shortName")
    }

def del_fetch(base_url, league=None):
    raw = requests.get(base_url).text
    teams = {}
    for line in raw.splitlines():
        line = line.strip()
        if "<option value=\"/spiele/team/" in line:
            try:
                tid = line.split("team/")[1].split("\"")[0].strip()
                name = line.split(">")[1].split("<")[0].strip()
                teams[name] = tid
            except:
                pass
    return teams

def discover_sidearm_sport_id(base_url):
    sports = fetch_json(f"{base_url}/api/v2/Sports")
    for s in sports:
        if s.get("abbrev") == "MHOCKEY":
            return s["id"]
    return None

def hockeytech_fetch(base_url, league=None):
    url = base_url.replace("view=schedule", "view=teamsbyseason")
    data = fetch_json(url)
    return {
        normalize_team_name(t["name"], league): int(t["id"])
        for t in data["SiteKit"]["Teamsbyseason"]
    }

def khl_fetch(base_url, league=None):
    url = base_url.replace("events_v2.json", "teams_v2.json")
    data = fetch_json(url)
    teams = {}
    for t in data:
        cyr_name = t.get("team").get("name").strip().lower()
        tid = t.get("team").get("id")
        name = TEAM_SYNONYMS.get(cyr_name)
        if name:
            teams[name] = int(tid)
        else:
            print(f"KHL WARNING: Non synonym for {cyr_name}")
    return teams

def liiga_fetch():
    url = "https://cdn.builder.io/api/v3/query/f11503eeae084753968caac3899a5d78/team?options.team.limit=30"
    data = fetch_json(url)
    teams = {}
    for item in data.get("team", []):
        raw_name = item.get("name")
        name = LIIGA_SYNONYMS.get(raw_name, raw_name)
        tid = f"{item.get("data").get("id")}:{raw_name.lower()}"
        teams[name.strip()] = tid
    return teams

def ncaa_b10_fetch(base_url, league=None):
    url = base_url.replace("api/game", "api/team")
    docs = fetch_json(url)["docs"]
    return {
        normalize_team_name(t["name"], league): int(t["id"])
        for t in docs if t.get("name")
    }

def nl_fetch(base_url, league=None):
    data = fetch_json(base_url.replace("games?", "teams?"))
    return {
        t["name"].strip(): t["teamId"].strip()
        for t in data if isinstance(t,dict) and t.get("name")
    }

def shl_fetch():
    url = "https://www.shl.se/api/site/settings"
    for attempt in range(5):
        try:
            settings = fetch_json(url)
            break
        except Exception as e:
            print(f"SHL ERROR attempt {attempt+1}/5: {e}")
            if attempt == 4:
                return {}
            time.sleep(1)

    teams = {}
    for t in settings.get("teamsInSite", []):
        if not any(s.get("code") == "SHL" for s in t.get("series", [])):
            continue
        raw_name = t.get("teamNames", {}).get("longSite")
        name = SHL_SYNONYMS.get(raw_name, raw_name)
        uuid = t.get("uuid")
        if uuid and name:
            teams[name.strip()] = uuid.strip()
    return teams

PARSERS = {
    "chl": chl_fetch,
    "del": del_fetch,
    "hockeytech": hockeytech_fetch,
    "khl": khl_fetch,
    "liiga": liiga_fetch,
    "ncaa_b10": ncaa_b10_fetch,
    "ncaa_east": None,
    "nl": nl_fetch,
    "shl": shl_fetch,
}

def update_team_ids(habs_teams):
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        feeds = yaml.load(f)

    for league, data in feeds.items():
        parser = data.get("parser")

        if league == "CHL":
            hp_list = habs_teams.get("STATSCHAMPS", [])
            chl_map = chl_fetch(data["url"])
            fresh = []
            for name in hp_list:
                match = chl_map.get(name)
                if not match:
                    print(f"WARNING: CHL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "code": match})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "DEL":
            hp_list = habs_teams.get("Germany", [])
            del_map = del_fetch(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = del_map.get(name)
                if not tid:
                    print(f"WARNING: DEL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "team_id": int(tid)})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "KHL":
            hp_list = habs_teams.get("KHL", [])
            khl_map = khl_fetch(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = khl_map.get(name)
                if not tid:
                    print(f"WARNING: KHL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "team_id": tid})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "Liiga":
            hp_list = habs_teams.get("Finland", [])
            liiga_map = liiga_fetch()
            fresh = []
            for name in hp_list:
                tid = liiga_map.get(name)
                if not tid:
                    print(f"WARNING: LIIGA -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "team_id": str(tid)})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "MHL":
            hp_list = habs_teams.get("MHL", [])
            khl_map = khl_fetch(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = khl_map.get(name)
                if not tid:
                    print(f"WARNING: MHL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "team_id": tid})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if parser == "ncaa_conf":
            name = {
                normalize_team_name(n, league)
                for n in habs_teams.get(league, [])
                if n.strip()
            }
            data["teams"] = [{"name": n} for n in name]
            continue

        if league == "NCAA_EAST":
            fresh = []
            for entry in habs_teams.get("NCAA_EAST", []):
                sport_id = None
                try:
                    sport_id = discover_sidearm_sport_id(entry["base_url"])
                except Exception as e:
                    print(f"ERROR discovering sport_id for NCAA_EAST {entry['name']}: {e}")
                    sport_id = None
                
                fresh.append({
                    "name": entry["name"],
                    "base_url": entry["base_url"],
                    "sport_id": sport_id,
                })
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "NL":
            hp_list = habs_teams.get("Switzerland", [])
            nl_map = nl_fetch(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = nl_map.get(name)
                if not tid:
                    print(f"WARNING: NL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "team_id": int(tid)})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "SHL":
            hp_list = habs_teams.get("Sweden", [])
            shl_map = shl_fetch()
            fresh = []
            for name in hp_list:
                uuid = shl_map.get(name)
                if not uuid:
                    print(f"WARNING: SHL -> Team not found in API: {name}")
                    continue
                fresh.append({"name": name, "uuid": uuid})
            data["teams"].clear()
            data["teams"].extend(fresh)
            continue

        if league == "VHL":
            unique = []
            seen = set()
            for name in habs_teams.get("VHL", []):
                if name not in seen:
                    seen.add(name)
                    unique.append({"name": name})
            data["teams"] = unique
            continue

        if parser not in PARSERS:
            continue
        habs_key = SCRAPER_TO_YAML.get(league, league)
        sub_league = league if league in ("KHL", "MHL", "VHL") else None
        if habs_key not in habs_teams:
            continue

        handler = PARSERS[parser]
        base_url = data["base_url"]

        try:
            api_teams = handler(base_url, league)
        except Exception as e:
            print(f"ERROR fetching {league}: {e}")
            api_raw = {}


        target_names = {
            normalize_team_name(n, league) 
            for n in habs_teams[habs_key]
        } | {
            normalize_team_name(n, league)
            for n in ALWAYS_KEEP.get(league, set())
        }

        fresh = []
        for name in target_names:
            match = None
            for api_name, tid in api_teams.items():
                if normalize_team_name(api_name, league) == name:
                    match = tid
                    break
            if match is None:
                print(f"Warning: {league} -> Team not found in API: {name}")
                continue
            fresh.append({"name": name, "team_id": match})
        data["teams"].clear()
        data["teams"].extend(fresh)

    with open("feeds.yaml", "w", encoding="utf-8") as f:
        yaml.dump(feeds, f)

    print("Team IDs updated.")

