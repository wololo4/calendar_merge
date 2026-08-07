import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from icalendar import Calendar
from parsers.common import parse_iso_datetime_duration, build_description, uid
from utils.ics import ICSEventBuilder
from dict.dict_publicationsports import TEAM_NAMES

def extract_eventsinfo_json(script_text):

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

    if not target_script:
        print(f"eventsInfo introuvable dans le HTML: {league}")
        return cal

    data = extract_eventsinfo_json(target_script)
    if not data:
        print(f"Impossible de parser les informations d'événements: {league}")
        return cal

    events_info = data["eventsInfo"]

    locations_data = extract_json_object(target_script, "locationsInfo")
    if locations_data:
        locations_info = locations_data["locationsInfo"]
    else:
        locations_info = {}

    for timestamp_str, items in events_info.items():
        try:
            ts = int(timestamp_str)
            dtstart = datetime.utcfromtimestamp(ts)
        except:
            continue

        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
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

            if league == 'LHMAAAQ':
                boxscore_url = f"https://www.m18aaa.com/fr/stats/boxscore.html?season=4939&subSeason=4951&category=5366&game={game_id}"
            if league == 'LHJAAAQ':
                boxscore_url = f"https://www.lhjaaaq.com/fr/stats/sommaire.html?season=4908&subSeason=4910&category=1093&game={game_id}"
    
            event = (
                ICSEventBuilder()
                .uid(uid(league, game_id))
                .start(dtstart)
                .end(dtend)
                .summary(f"🏒 | {away_name} @ {home_name}")
                .location(location_name)
                .description(boxscore_url)
                .build()
            )

            cal.add_component(event)

    return cal
