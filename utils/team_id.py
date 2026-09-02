from ruamel.yaml import YAML
import json
import requests
import time
from dict.khl_dict import TEAM_SYNONYMS

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=4, offset=2)

LEAGUE_ALIAS = {
    "LHJMQ": "QMJHL",
}

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

def hockeytech_fetch_teams(base_url, league=None):
    teams_url = base_url.replace("view=schedule", "view=teamsbyseason")

    raw = requests.get(teams_url).text
    data = json.loads(raw)

    teams = {}
    for t in data["SiteKit"]["Teamsbyseason"]:
        name = normalize_team_name(t["name"], league)
        team_id = int(t["id"])
        teams[name] = team_id

    return teams

def ncaa_b10_fetch_teams(base_url, league=None):
    teams_url = (base_url).replace("api/game", "api/team")
    raw = requests.get(teams_url).text
    data = json.loads(raw)
    docs = data["docs"]

    teams = {}
    for t in docs:
        name = t.get("name", "").strip()
        if not name:
            continue
        name = normalize_team_name(name, league)
        team_id = int(t["id"])
        teams[name] = team_id

    return teams

def discover_sidearm_sport_id(base_url):
    sports_url = f"{base_url}/api/v2/Sports"
    raw = requests.get(sports_url).text
    sports = json.loads(raw)

    for s in sports:
        if s.get("abbrev") == "MHOCKEY":
            return s["id"]

    raise ValueError(f"mhky sport_id not found at {sports_url}")

def khl_fetch_teams(base_url, league=None):
    teams_url = base_url.replace("events_v2.json", "teams_v2.json")
    raw = requests.get(teams_url).text
    data = json.loads(raw)
    teams = {}
    for t in data:
        cyr_name = t.get("team").get("name").strip().lower()
        tid = t.get("team").get("id")
        if not cyr_name or not tid:
            continue

        name = TEAM_SYNONYMS.get(cyr_name)
        if not name:
            print(f"KHL WARNING: Non synonym for {cyr_name}")
            continue
        teams[name] = int(tid)
    return teams

def shl_fetch_teams():
    url = "https://www.shl.se/api/site/settings"
    for attempt in range(5):
        try:
            raw = requests.get(url, timeout=5).text
            break
        except Exception as e:
            print(f"SHL ERROR attempt {attempt+1}/5: {e}")
            if attempt == 4:
                return {}
            time.sleep(1)
    settings = json.loads(raw)
    teams = {}
    for t in settings.get("teamsInSite", []):
        series_list = t.get("series", [])
        if not any(s.get("code") == "SHL" for s in series_list):
            continue
        uuid = t.get("uuid")
        raw_name = t.get("teamNames", {}).get("longSite")
        name = SHL_SYNONYMS.get(raw_name, raw_name)
        if uuid and name:
            teams[name.strip()] = uuid.strip()
    return teams

def liiga_fetch_teams():
    url = "https://cdn.builder.io/api/v3/query/f11503eeae084753968caac3899a5d78/team?options.team.limit=30"
    raw = requests.get(url).text
    data = json.loads(raw)
    teams = {}
    for item in data.get("team", []):
        raw_name = item.get("name")
        name = LIIGA_SYNONYMS.get(raw_name, raw_name)
        tid = f"{item.get("data").get("id")}:{raw_name.lower()}"
        if not name or not tid:
            continue
        teams[name.strip()] = tid
    return teams

def nl_fetch_teams(base_url, league=None):
    teams_url = base_url.replace("games?", "teams?")
    raw = requests.get(teams_url).text
    data = json.loads(raw)
    teams = {}
    for t in data:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        tid = t.get("teamId")
        if not name or not tid:
            continue
        teams[name.strip()] = tid.strip()
    return teams

def del_fetch_teams(base_url, league=None):
    raw = requests.get(base_url).text
    teams = {}
    for line in raw.splitlines():
        line = line.strip()
        if "<option value=\"/spiele/team/" in line:
            try:
                part = line.split("value=\"/spiele/team/")[1]
                tid = part.split("\"")[0].strip()
                name = line.split(">")[1].split("<")[0].strip()
                teams[name] = tid
            except Exception:
                continue
    return teams

def chl_fetch_teams(base_url, league=None):
    teams_url = base_url.replace("schedule", "teams")
    raw = requests.get(teams_url).text
    data = json.loads(raw)
    teams = {}
    for t in data.get("data", []):
        name = t.get("name")
        code = t.get("shortName")
        if not name or not code:
            continue
        teams[name.strip()] = code.strip()

    return teams

PARSERS = {
    "chl": chl_fetch_teams,
    "del": del_fetch_teams,
    "khl": khl_fetch_teams,
    "hockeytech": hockeytech_fetch_teams,
    "liiga": liiga_fetch_teams,
    "ncaa_b10": ncaa_b10_fetch_teams,
    "ncaa_east": None,
    "nl": nl_fetch_teams,
    "shl": shl_fetch_teams,
}

def normalize_team_name(name, league=None):
    name = name.strip()

    if league == "LHJMQ":
        # API: "City, Nickname"
        if "," in name:
            city, nickname = name.split(",", 1)
            return f"{city.strip()} {nickname.strip()}"

        # HabsProspects: "City Nickname"
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

def update_team_ids(habs_teams):
    with open("feeds.yaml", "r", encoding="utf-8") as f:
        feeds = yaml.load(f)

    for league, data in feeds.items():
        parser = data.get("parser")
        if league == "NCAA_EAST":
            data["teams"] = []
            for entry in habs_teams.get("NCAA_EAST", []):
                team_name = entry["name"]
                team_base = entry["base_url"]

                try:
                    sport_id = discover_sidearm_sport_id(team_base)
                except Exception as e:
                    print(f"ERROR discovering sport_id for NCAA_EAST {team_name}: {e}")
                    sport_id = None
                
                data["teams"].append({
                    "name": team_name,
                    "base_url": team_base,
                    "sport_id": sport_id,
                })

            continue
        if league == "VHL":
            data["teams"] = []
            unique = set()
            for entry in habs_teams.get("VHL", []):
                if isinstance(entry, dict):
                    name = entry.get("name")
                else:
                    name = entry
                if name not in unique:
                    unique.add(name)
                    data["teams"].append({"name": name})
            continue
        if league == "SHL":
            hp_list = habs_teams.get("SWEDEN", [])
            shl_map = shl_fetch_teams()
            fresh = []
            for name in hp_list:
                uuid = shl_map.get(name)
                if not uuid:
                    print(f"WARNING: SHL -> Team not found in API: {name}")
                    continue
                fresh.append({
                    "name": name,
                    "uuid": uuid,
                })
            data["teams"] = fresh
            continue
        if league == "Liiga":
            hp_list = habs_teams.get("FINLAND", [])
            liiga_map = liiga_fetch_teams()
            fresh = []
            for name in hp_list:
                tid = liiga_map.get(name)
                if not tid:
                    print(f"WARNING: LIIGA -> Team not found in API: {name}")
                    continue
                fresh.append({
                    "name": name,
                    "team_id": str(tid),
                })

            data["teams"] = fresh
            continue
        if league == "NL":
            hp_list = habs_teams.get("SWITZERLAND", [])
            nl_map = nl_fetch_teams(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = nl_map.get(name)
                if not tid:
                    print(f"WARNING: NL -> Team not found in API: {name}")
                    continue
                fresh.append({
                    "name": name,
                    "team_id": int(tid),
                })
            data["teams"] = fresh
            continue
        if league == "DEL":
            hp_list = habs_teams.get("GERMANY", [])
            del_map = del_fetch_teams(data["base_url"])
            fresh = []
            for name in hp_list:
                tid = del_map.get(name)
                if not tid:
                    print(f"WARNING: DEL -> Team not found in API: {name}")
                    continue
                fresh.append({
                    "name": name,
                    "team_id": int(tid),
                })
            data["teams"] = fresh
            continue

        if league == "CHL":
            hp_list = habs_teams.get("STATSCHAMPS", [])
            chl_map = chl_fetch_teams(data["url"])
            fresh = []
            for name in hp_list:
                match = chl_map.get(name)
                if not match:
                    print(f"WARNING: CHL -> Team not found in API: {name}")
                    continue
                fresh.append({
                    "name": name,
                    "code": match,
                })
            data["teams"] = fresh
            continue

        if parser == "ncaa_conf":
            target_names = {
                normalize_team_name(n, league)
                for n in habs_teams.get(league, [])
                if n.strip()
            }
            existing = {
                t["name"].strip(): t
                for t in data["teams"]
            }
            data["teams"] = [
                {"name": name}
                for name in target_names
            ]
            continue

        if parser not in PARSERS:
            continue
        habs_key = LEAGUE_ALIAS.get(league, league)
        if habs_key not in habs_teams:
            continue

        handler = PARSERS[parser]

        base_url = data["base_url"]
        try:
            api_raw = handler(base_url, league)
        except Exception as e:
            print(f"ERROR fetching {league}: {e}")
            api_raw = {}

        api_teams = api_raw

        keep_extra = ALWAYS_KEEP.get(league, set())
        keep_extra_norm = {
            normalize_team_name(n, league)
            for n in keep_extra
        }
        target_names = {
            normalize_team_name(n, league) 
            for n in habs_teams[habs_key]
        } | keep_extra_norm

        existing = {normalize_team_name(t["name"], league): t for t in data["teams"]}

        for name in target_names:
            if league == "LHJMQ":
                target_names = {
                    normalize_team_name(n, league)
                    for n in habs_teams.get("QMJHL", [])
                    if n.strip()
                } | {
                    normalize_team_name(n, league)
                    for n in ALWAYS_KEEP.get("LHJMQ", set())
                }
                fresh = []
                for name in target_names:
                    match = None
                    for api_name, tid in api_teams.items():
                        if normalize_team_name(api_name, league) == name:
                            match = tid
                            break
                    if match is None:
                        print(f"Warning: LHJMQ -> Team not found in API: {name}")
                        continue
                    fresh.append({
                        "name": name,
                        "team_id": match,
                    })
                data["teams"] = fresh
                continue

    with open("feeds.yaml", "w", encoding="utf-8") as f:
        yaml.dump(feeds, f)

    print("Team IDs updated.")

