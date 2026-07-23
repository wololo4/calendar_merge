import os
import requests
import json
import re
from icalendar import Calendar

from parsers.nhl import parse_nhl_json_to_calendar
from parsers.ahl import parse_ahl_json_to_calendar
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
        response = session.get(url, headers=headers, timeout=4)
        response.raise_for_status()

        # ============================
        # NHL (ICS or JSON)
        # ============================
        if parser == "nhl":

            try:
                raw_json = response.json()
            except Exception as e:
                print("Error parsing NHL JSON:", e)
                return league, team_name, None

            games_list = raw_json.get("games", [])

            calendar = parse_nhl_json_to_calendar({"games": games_list})
            return league, team_name, calendar


        # ============================
        # AHL JSON
        # ============================

        if parser == "ahl":
            try:
                text = response.text.strip()

                # Remove outer parentheses
                if text.startswith("(") and text.endswith(")"):
                    text = text[1:-1]

                # Remove trailing garbage brackets
                while text.endswith("]"):
                    text = text[:-1]
                text = text + "]"

                # Fix JavaScript escapes
                text = text.replace("\\/", "/")

                # Convert JS booleans to JSON booleans (same spelling)
                # No change needed: "false" and "true" are valid JSON

                # Convert single quotes to double quotes ONLY when safe
                # (Your feed already uses double quotes → no change needed)

                # Now parse JSON
                raw_json = json.loads(text)[0]

                calendar = parse_ahl_json_to_calendar(raw_json)
                return league, team_name, calendar

            except Exception as e:
                print("Error parsing AHL JSON:", e)
                return league, team_name, None


        # ============================
        # VHL HTML
        # ============================
        if league == "VHL":
            html = response.text
            calendar = parse_vhl_html(html, team_name)
            return league, team_name, calendar

        # ============================
        # LIIGA JSON
        # ============================
        if parser == "liiga":
            raw_json = response.json()
            team_id = team_filter[0]

            filtered = []
            for game in raw_json:
                home = game.get("homeTeamId")
                away = game.get("awayTeamId")
                if home == team_id or away == team_id:
                    filtered.append(game)

            calendar = parse_liiga_json_to_calendar(filtered)
            return league, team_name, calendar

        # ============================
        # DEL HTML
        # ============================
        if parser == "del":
            html = response.text
            calendar = parse_del_html(html, team_name)
            return league, team_name, calendar

        # ============================
        # UFA JSON  (FIX)
        # ============================
        if parser == "ufa":
            try:
                raw_json = response.json()
                calendar = parse_ufa_json_to_calendar(raw_json)
                return league, team_name, calendar
            except Exception:
                return league, team_name, None

        # ============================
        # OTHER JSON (CHL)
        # ============================
        try:
            raw_json = response.json()

            # CHL Europe JSON
            if raw_json.get("_type") == "Corebine.Core.Protocol.Response.Array":
                calendar = parse_chl_europe_json_to_calendar(raw_json, team_filter)
                return league, team_name, calendar

            # CHL Canada JSON
            calendar = parse_chl_json_to_calendar(raw_json)
            return league, team_name, calendar

        except (ValueError, TypeError, json.JSONDecodeError):
            # ICS fallback
            ics_data = response.content.strip()
            if not ics_data:
                print(f"Skipping empty ICS for {league} - {team_name} (season not available yet)")
                return league, team_name, None
            calendar = Calendar.from_ical(ics_data)
            return league, team_name, calendar

    except Exception as e:
        print(f"Error downloading {league} - {team_name}: {e}")
        return league, team_name, None
