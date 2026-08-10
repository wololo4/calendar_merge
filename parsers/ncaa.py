import json
from icalendar import Calendar, Event
from datetime import datetime, timedelta, date
from utils.calendar import create_calendar
from utils.ics import ICSEventBuilder
from dict.ncaa_dict import TEAM_STADIUM, CITY_TO_ARENA, KNOWN_ARENAS, NCAA_MASCOT_FIX, NCAA_TEAM_FIX, TEAM_NORMALIZATION, TEAM_MASCOTS_FALLBACK
from parsers.common import parse_iso_datetime_duration, build_description, uid, city_to_arena, normalize_team

TEAM_MASCOTS_FALLBACK_NORMALIZED = {
    key.lower(): f"{key} {value}".strip()
    for key, value in TEAM_MASCOTS_FALLBACK.items()
}

def normalize_team_ncaa(title):
    cleaned = clean_ncaa_team_name(title)
    cleaned_title, _ = clean_ncaa_title_and_flags(cleaned)
    name_low = cleaned_title.lower().strip()

    for short_name in TEAM_MASCOTS_FALLBACK:
        short_lower = short_name.lower()

        # FIX: exact match OR prefix match ONLY
        if name_low == short_lower or name_low.startswith(short_lower + " "):
            return normalize_team(fix_ncaa_team_name(short_name), TEAM_MASCOTS_FALLBACK_NORMALIZED)

    return normalize_team(fix_ncaa_team_name(cleaned_title), TEAM_MASCOTS_FALLBACK_NORMALIZED)

def full_team_name_conf(team_obj):
    raw_title = team_obj.get("title", "").strip()
    title = fix_ncaa_team_name(
        clean_ncaa_title_and_flags(
            clean_ncaa_team_name(raw_title)
        )[0]
    )
    mascot = (team_obj.get("mascot") or "").strip()

    if mascot and mascot.lower() in title.lower():
        return title

    if mascot:
        return f"{title} {mascot}".strip()

    fallback = TEAM_MASCOTS_FALLBACK.get(title)
    if fallback:
        return f"{title} {fallback}".strip()

    print(f"ERROR no mascot with {title}")
    return title

def is_ncaa_tournament(name):
    if not name:
        return False
    
    tournament_keywords = [
        "ccha mason cup championship",
        "ccha mason cup championship - first round series",
        "ccha mason cup championship - semifinals",
        "ccha mason cup playoffs - first round series",
        "ccha mason cup playoffs - semifinals",
        "ccha championship",
        "ccha quarterfinals",
        "ccha semifinal",
        "ncaa frozen four",
        "ncaa regional",
        "ncaa regionals",
        "nchc championship",
        "nchc first round",
        "nchc quarterfinal",
        "nchc quarterfinal (if necessary)",
        "nchc semifinal",
        "nchc semifinals",
    ]

    name_lower = name.lower()

    return any(keyword in name_lower for keyword in tournament_keywords)

def clean_ncaa_title_and_flags(title):
    #Remove '(Exhibtition)' from opponent title
    is_exhibition = False
    clean = title.strip()

    exhibition_markers = [
        "(Exhibition)",
        "(ex)",
        "(exh.)",
        "Exhibition",
    ]

    for marker in exhibition_markers:
        if marker.lower() in clean.lower():
            is_exhibition = True
            clean = clean.replace(marker, "").strip()

    return clean, is_exhibition

def fix_ncaa_team_name(name):
    return NCAA_TEAM_FIX.get(name, name)

def clean_mascot(mascot):
    if not mascot:
        return mascot
    return NCAA_MASCOT_FIX.get(mascot, mascot)

def stadium(name):
    key = name.lower().strip()
    if key in TEAM_STADIUM:
        return TEAM_STADIUM[key]
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name

def validate_arena(arena_name):
    if arena_name not in KNOWN_ARENAS:
        print(f"[ERROR] Arena not in KNOWN_ARENAS: '{arena_name}'")

    return arena_name

def clean_ncaa_team_name(name):
    name = name.strip()

    patterns = [
        "University of Nebraska at ",
        "University of ",
        "University",
        "University (OH)",
        "(SD)",
        "(Exhibition)",
        "(ex)",
        "(exh.)",
        "Exhibition",
        "(Ont.)"
    ]

    name_low = name.lower()

    for p in patterns:
        p_low = p.lower()
        if name_low.startswith(p_low):
            name = name[len(p):].strip()
            name_low = name.lower()
        if name_low.endswith(p_low):
            name = name[:-len(p)].strip()
            name_low = name.lower()
    
    return name

def resolve_venue(raw_location, home_team):
    if not raw_location:
        return "To be determined"
    venue_raw = str(raw_location).strip()
    if "/" in venue_raw or "|" in venue_raw:
        venue = venue_raw.split("/")[-1].split("|")[0].strip()
    elif venue_raw.lower() == "home":
        venue = stadium(home_team)
    else:
        venue = venue_raw.strip()
    return venue

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

def resolve_home_away(ev, home_name, away_name):
    loc = ev.get("locationIndicator") or ev.get("location_indicator")
    if loc == "H":
        return home_name, away_name
    return away_name, home_name    

def parse_ncaa_east(json_data, team_name):
    cal = create_calendar()

    # json_data is ALWAYS a list of day objects
    for day in json_data:
        events = day.get("events", [])
        if not events:
            continue

        for ev in events:
            start_dt, end_dt = parse_iso_datetime_duration(ev.get("dateUtc"))

            # -----------------------------
            # Teams
            # -----------------------------
            opponent_obj = ev.get("opponent", {})
            raw_title = opponent_obj.get("title", "").replace(",", "")
            clean_title, is_exhibition = clean_ncaa_title_and_flags(raw_title)
            opponent_title = clean_ncaa_team_name(clean_title)
            opponent_title = fix_ncaa_team_name(opponent_title)
            if is_ncaa_tournament(opponent_title):
                continue
            opponent_mascot = opponent_obj.get("mascot", "")
            opponent_full = f"{opponent_title} {opponent_mascot}".strip()

            full_team_name = team_name  # from YAML

            home_team, away_team = resolve_home_away(ev, full_team_name, opponent_full)

            # -----------------------------
            # Venue (prefer facility.title)
            # -----------------------------
            facility = ev.get("facility")
            if facility and facility.get("title"):
                venue = facility["title"]
            else:
                venue = resolve_venue(ev.get("location", ""), home_team)

            venue_city_or_arena = venue.strip()
            venue_from_city = city_to_arena(venue_city_or_arena, CITY_TO_ARENA)
            venue = validate_arena(venue_from_city)

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

            start_date = ev.get("date")[:10] if ev.get("date") else None
            end_date = ev.get("enddate")[:10] if ev.get("enddate") else None

            promo = ev.get("gamePromotionText", "")

            description = build_description([
                f"Game date to be determined" if ev.get("tbd") else None,
                f"From {start_date} to {end_date}" if start_date and end_date and start_date != end_date else None,
                links[0] if links else None,
                f"Exhibition Game" if is_exhibition else None,
                f"Scrimmage Game" if promo and "scrimmage" in promo.lower() else None
            ])

            event = (
                ICSEventBuilder()
                .uid(uid("ncaa", game_id))
                .start(start_dt)
                .end(end_dt)
                .summary(f"🏒 | {away_team} @ {home_team}")
                .location(venue)
                .description(description)
                .build()
            )

            cal.add_component(event)

    return cal

def parse_ncaa_conf(json_data, team_name):
    cal = create_calendar()

    for ev in json_data:

        # Filter by team
        school = ev.get("school", {})
        opp = ev.get("opponent", {})

        school_title = normalize_team_ncaa(school.get("title", ""))
        opp_title = normalize_team_ncaa(opp.get("title", ""))
        team_title = normalize_team_ncaa(TEAM_NORMALIZATION.get(team_name, team_name))

        if team_title != school_title and team_title != opp_title:
            continue

        home_title = full_team_name_conf(school)
        away_title = full_team_name_conf(opp)

        home_team, away_team = resolve_home_away(ev, home_title, away_title)

        if ev.get("tba") == True:
            start_dt, end_dt = parse_iso_datetime_duration(ev.get("date", ""))
        elif ev.get("tba") == False:
            start_dt, end_dt = parse_iso_datetime_duration(ev.get("date_utc", ""))
        if not start_dt:
            continue

        venue = resolve_venue(ev.get("location"), home_team)

        venue_city_or_arena = venue.strip()
        venue_from_city = city_to_arena(venue_city_or_arena, CITY_TO_ARENA)
        venue = validate_arena(venue_from_city)

        # Scrimmage detection
        scrimmage = ev.get("type", "")
        is_scrimmage = scrimmage == 'S'

        description = build_description([
            f"Game time to be determined" if ev.get("tba") == True else None,
            f"Scrimmage Game" if is_scrimmage else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid("ncaa", ev.get("id", "")))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away_team} @ {home_team}")
            .location(venue)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal

def parse_ncaa_b10(json_data, team_filter):
    cal = create_calendar()
    target_team_id = team_filter[0] if team_filter else None

    for ev in json_data.get("docs",[]):

        # Filter by team
        teams = ev.get("teams",{})
        home_team = teams.get("home_team", {}).get("name", "")
        away_team = teams.get("away_team", {}).get("name", "")

        home_id = teams.get("home_team", {}).get("id", "")
        away_id = teams.get("away_team", {}).get("id", "")

        if target_team_id is not None:
            if away_id != target_team_id and home_id != target_team_id:
                continue

        # Date/time
        start_dt, end_dt = parse_iso_datetime_duration(ev.get("datetime", {}).get("date_scheduled"))

        # Venue
        venue = resolve_venue(ev.get("info", {}).get("venue", ""), home_team)

        venue_city_or_arena = venue.strip()
        venue_from_city = city_to_arena(venue_city_or_arena, CITY_TO_ARENA)
        venue = validate_arena(venue_from_city)

        description = build_description([
            f"Game time to be determined" if ev.get("datetime_is_tba") == True else None
        ])

        event = (
            ICSEventBuilder()
            .uid(uid("ncaa", ev.get("db", {}).get("boost_id", "")))
            .start(start_dt)
            .end(end_dt)
            .summary(f"🏒 | {away_team} @ {home_team}")
            .location(venue)
            .description(description)
            .build()
        )

        cal.add_component(event)

    return cal
