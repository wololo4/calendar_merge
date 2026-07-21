import requests
import json
from icalendar import Calendar

from parsers.nhl import parse_nhl_json_to_calendar
from parsers.chl_canada import parse_chl_json_to_calendar
from parsers.chl_europe import parse_chl_europe_json_to_calendar
from parsers.ufa import parse_ufa_json_to_calendar
from parsers.vhl import parse_vhl_html
from parsers.liiga import parse_liiga_json_to_calendar
from parsers.del_parser import parse_del_html

def download_single_feed(feed_info):
    """Worker function to process one feed concurrently."""
    league, team_name, url, team_filter, parser = feed_info
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    if "khl.ru" in url:
        headers.update({
            "Referer": "https://www.khl.ru/",
            "Origin": "https://www.khl.ru",
            "Accept": "text/calendar,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
    
    try:
        print(f"Downloading: {league} - {team_name} -> {url[:50]}...")
        response = session.get(url, headers=headers, timeout=4) # Reduced timeout
        response.raise_for_status()

        if league == "VHL": 
            html = response.text
            return league, team_name, parse_vhl_html(html, team_name)

        # LIIGA JSON
        if parser == "liiga":
            raw_json = response.json()
            team_id = team_filter[0]

            # Filtrer les matchs où TPS apparaît
            filtered = []
            for game in raw_json:
                home = game.get("homeTeamId")
                away = game.get("awayTeamId")

                if home == team_id or away == team_id:
                    filtered.append(game)

            return league, team_name, parse_liiga_json_to_calendar(filtered)

        # DEL HTML
        if parser == "del":
            html = response.text
            return league, team_name, parse_del_html(html, team_name)

        try:
            raw_json = response.json()

            #NHL JSON
                if parser == "nhl" and team_filter == []:
                    raw_json = response.json()
                    games_list = raw_json.get("games", [])
                
                    # Pré-saison uniquement
                    preseason_games = [
                        g for g in games_list
                        if g.get("gameType") == 1
                    ]
                
                    return league, team_name, parse_nhl_json_to_calendar(preseason_games)
                else:
                    return league, team_name, parse_ufa_json_to_calendar(raw_json)
            #CHL Europe JSON
            if raw_json.get("_type") == "Corebine.Core.Protocol.Response.Array":
                return league, team_name, parse_chl_europe_json_to_calendar(raw_json, team_filter)
            else:
                return league, team_name, parse_chl_json_to_calendar(raw_json)
        except (ValueError, TypeError, json.JSONDecodeError):
            ics_data = response.content.strip()
            if not ics_data:
                print(f"Skipping empty ICS for {league} - {team_name} (season not available yet)")
                return league, team_name, None
            return league, team_name, Calendar.from_ical(ics_data)
            
    except Exception as e:
        print(f"Error downloading {league} - {team_name}: {e}")
        return league, team_name, None
