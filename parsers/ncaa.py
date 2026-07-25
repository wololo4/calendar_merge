import json
from icalendar import Calendar, Event
from datetime import datetime, timedelta, date
from utils.calendar import create_calendar

def events_to_ics(events):
    cal = Calendar()
    cal.add("prodid", "-//calendar_merge//")
    cal.add("version", "2.0")

    for ev in events:
        event = Event()

        # UID unique
        event.add("uid", f"{ev['id']}@calendar_merge")

        # Résumé
        opponent = ev.get("opponent")
        if isinstance(opponent, dict):
            summary = opponent.get("title", "Match")
        else:
            summary = opponent or "Match"
        event.add("summary", summary)

        # Date (format ISO)
        try:
            dt = datetime.fromisoformat(ev["date"])
            event.add("dtstart", dt)
        except:
            continue

        cal.add_component(event)

    return cal


def ncaa_date_range():
    today = date.today()
    year = today.year

    # Off-season: June, July, August → next season
    if today.month in (6, 7, 8):
        season_start_year = year
        season_end_year = year + 1
    else:
        # In-season: September → May → current season
        season_start_year = year
        season_end_year = year + 1

    # You can adjust these exact days if needed
    date_from = f"9-01-{season_start_year}"
    date_to   = f"5-01-{season_end_year}"

    return date_from, date_to

def parse_ncaa(json_data, team_name):
    """
    SIDEARM NCAA parser.
    Input format:
      [
        { "date": "...", "events": [ {...}, {...} ] },
        { "date": "...", "events": [] },
        ...
      ]
    """

    cal = create_calendar()

    # json_data is ALWAYS a list of day objects
    for day in json_data:
        events = day.get("events", [])
        if not events:
            continue

        for ev in events:

            # -----------------------------
            # Extract date/time
            # -----------------------------
            iso_time = (
                ev.get("dateUtc")
                or ev.get("date")
                or ev.get("startDate")
            )

            if not iso_time:
                print(f"Missing date for NCAA event id={ev.get('id')}")
                continue

            start_dt = datetime.fromisoformat(
                iso_time.replace("Z", "+00:00")
            )
            end_dt = start_dt + timedelta(hours=2, minutes=30)

            # -----------------------------
            # Teams
            # -----------------------------
            opponent_obj = ev.get("opponent", {})
            opponent_title = opponent_obj.get("title", "").replace(",", "")
            opponent_mascot = opponent_obj.get("mascot", "")
            opponent_full = f"{opponent_title} {opponent_mascot}".strip()

            full_team_name = team_name  # from YAML

            loc_ind = ev.get("locationIndicator")

            if loc_ind == "H":
                # Your team is home
                home_team = full_team_name
                away_team = opponent_full
            else:
                # Your team is away
                home_team = opponent_full
                away_team = full_team_name

            # -----------------------------
            # Venue (prefer facility.title)
            # -----------------------------
            facility = ev.get("facility")
            if facility and facility.get("title"):
                venue = facility["title"]
            else:
                venue_raw = ev.get("location", "")
                if "/" in venue_raw:
                    venue = venue_raw.split("/")[-1].strip()
                else:
                    venue = venue_raw.strip()

            # -----------------------------
            # Links
            # -----------------------------
            media = ev.get("media", {})
            links = []

            stats = media.get("stats") or {}
            if stats.get("url"):
                links.append(f"Live Stats: {stats['url']}")

            # -----------------------------
            # UID
            # -----------------------------
            game_id = ev.get("id")
            uid = f"ncaa{game_id}"

            # -----------------------------
            # Create ICS event
            # -----------------------------
            event = Event()
            event.add("uid", uid)
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
            event.add("summary", f"🏒 | {away_team} @ {home_team}")
            event.add("location", venue)

            description = []
            description.append(f"Status: {ev.get('gameStateDisplay', 'SCHEDULED')}")
            # -----------------------------
            # Ajouter info TBD + dates multi-day
            # -----------------------------
            if ev.get("tbd"):
                description.append("Game date to be determined")

            start_date = ev.get("date")[:10] if ev.get("date") else None
            end_date = ev.get("enddate")[:10] if ev.get("enddate") else None

            if start_date and end_date and start_date != end_date:
                description.append(f"From {start_date} to {end_date}")
            if links:
                description.extend(links)

            event.add("description", "\n".join(description))

            cal.add_component(event)

    return cal
