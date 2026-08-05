import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from icalendar import Calendar, Event

TEAM_NAMES = {
    "10570": "Braves de Valleyfield",
    "10571": "Rangers de Montréal",
    "10573": "Prédateurs de Joliette",
    "10574": "Cobras de Terrebonne",
    "10575": "Titan de Princeville",
    "10578": "L'Indigo de Granby",
    "10579": "Collège Français de Longueuil",
    "10581": "Panthères de Saint-Jérôme",
    "10591": "Nomad de Gatineau",
    "49443": "L'Everest de la Côte-du-Sud",
    "110271": "Vikings de Saint-Eustache",
    "110272": "Estacades de Trois-Rivières",
    "110273": "Blizzard du Séminaire Saint-François",
    "110275": "Chevaliers de Lévis",
    "110276": "Rousseau-Royal Laval-Montréal",
    "110277": "Lions du Lac St-Louis",
    "110278": "Élites de Jonquière",
    "110279": "L'Intrépide de Gatineau",
    "110280": "Albatros du Collège Notre-Dame",
    "110281": "Phénix du Collège Esther-Blondin",
    "110282": "Riverains du Collège Charles-Lemoyne",
    "110283": "Gaulois de Saint-Hyacinthe",
    "110284": "Grenadiers de Châteauguay",
    "110285": "Forestiers d'Amos",
    "110535": "Condors du Cégep Beauce-Appalaches",
    "117597": "Cantonniers de Magog",
    "139435": "L'Énergie de Laval",
    "139922": "Phoenix de Montréal",
}

def extract_eventsinfo_json(script_text):
    """
    Extract the JSON object containing "eventsInfo" using brace counting.
    No regex, no heuristics.
    """

    key = '"eventsInfo"'
    pos = script_text.find(key)
    if pos == -1:
        return None

    # Find first '{' after "eventsInfo"
    start = script_text.find("{", pos)
    if start == -1:
        return None

    # Count braces to find the end of the JSON object
    brace_count = 0
    end = start

    while end < len(script_text):
        if script_text[end] == "{":
            brace_count += 1
        elif script_text[end] == "}":
            brace_count -= 1

        end += 1

        if brace_count == 0:
            break

    json_str = script_text[start:end]

    wrapped = '{"eventsInfo": ' + json_str + '}'

    try:
        return json.loads(wrapped)
    except Exception as e:
        print("JSON parsing error:", e)
        print("RAW JSON:", wrapped[:500])
        return None
    
def extract_json_object(script_text, key):
    """
    Extract a JSON object by finding the key and counting braces.
    No regex.
    """
    pos = script_text.find(key)
    if pos == -1:
        return None

    start = script_text.find("{", pos)
    if start == -1:
        return None

    brace_count = 0
    end = start

    while end < len(script_text):
        if script_text[end] == "{":
            brace_count += 1
        elif script_text[end] == "}":
            brace_count -= 1
        end += 1
        if brace_count == 0:
            break

    json_str = script_text[start:end]
    wrapped = "{" + f'"{key}": ' + json_str + "}"

    try:
        return json.loads(wrapped)
    except Exception as e:
        print("JSON parsing error:", e)
        print("RAW JSON:", wrapped[:500])
        return None

def parse_publicationsports(html, team_filter=None, league=None):
    soup = BeautifulSoup(html, 'html.parser')
    cal = Calendar()

    target_script = None
    for script in soup.find_all("script"):
        if script.string and "PS.component.statistic_schedule_sd" in script.string:
            target_script = script.string
            break
    print("DEBUG: Found script block, first 1000 chars:")
    print(target_script[:1000])

    if not target_script:
        print("eventsInfo introuvable dans le HTML")
        return cal

    data = extract_eventsinfo_json(target_script)
    if not data:
        print("Impossible de parser les informations d'événements")
        return cal

    events_info = data["eventsInfo"]
    print("DEBUG: eventsInfo keys:", list(events_info.keys())[:20])

    locations_data = extract_json_object(target_script, "locationsInfo")
    if locations_data:
        locations_info = locations_data["locationsInfo"]
    else:
        locations_info = {}
    print("DEBUG: locationsInfo keys:", list(locations_info.keys())[:20])

    for timestamp_str, items in events_info.items():
        print("DEBUG: timestamp:", timestamp_str, "items:", len(items))
        try:
            ts = int(timestamp_str)
            dtstart = datetime.utcfromtimestamp(ts)
        except:
            continue

        for item in items:
            print("DEBUG: item:", item)
            event_name = item.get("eventName", "Match")
            begin_time = item.get("beginTime")
            game_id = item.get("gameId")
            home_id = item.get("eventLocalTeamId")
            away_id = item.get("eventVisitorTeamId")
            location_id = item.get("locationId")

            home_name = TEAM_NAMES.get(home_id)
            away_name = TEAM_NAMES.get(away_id)

            if "VS" in event_name:
                away, home = event_name.split("VS")
                if not home_name:
                    print(f"Error no full name for {home}")
                elif not away_name:
                    print(f"Error no full name for {away}")
            else:
                print(f"Error with event name: {event_name}")

            if team_filter:
                if home_id not in team_filter and away_id not in team_filter:
                    continue

            if begin_time:
                try:
                    hh, mm = begin_time.split(":")
                    dtstart = dtstart.replace(hour=int(hh), minute=int(mm))
                except Exception:
                    pass

            dtend = dtstart + timedelta(hours=2, minutes=30)
            
            location_name = None
            if location_id and str(location_id) in locations_info:
                location_name = locations_info[str(location_id)].get("locationName")

            event = Event()
            event.add("SUMMARY", f"🏒 | {away_name} @ {home_name}")
            event.add("DTSTART", dtstart)
            event.add("DTEND", dtend)
            event.add("UID", f"lhmaaaq{game_id}")

            if location_name:
                event.add("LOCATION", location_name)

            if league == 'LHMAAAQ':
                boxscore_url = f"https://www.m18aaa.com/fr/stats/boxscore.html?season=4939&subSeason=4951&category=5366&game={game_id}"
            if league == 'LHJAAAQ':
                boxscore_url = f"https://www.lhjaaaq.com/fr/stats/sommaire.html?season=4908&subSeason=4910&category=1093&game={game_id}"
            event.add("DESCRIPTION", f"Game Center: {boxscore_url}")

            cal.add_component(event)

    return cal
