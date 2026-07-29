import json
from icalendar import Calendar, Event
from datetime import datetime, timedelta, date
from utils.calendar import create_calendar

TEAM_STADIUM = {
    "arizona state sun devils": "Mullett Arena",
    "augustana vikings": "Midco Arena",
    "bemidji state beavers": "Sanford Center",
    "bowling green falcons": "Slater Family Ice Arena",
    "colorado college tigers": "Ed Robson Arena",
    "ferris state bulldogs": "Robert L. Ewigleben Ice Arena",
    "lake superior state lakers": "Taffy Abel Arena",
    "merrimack warriors": "Lawler Rink",
    "miami redhawks": "Goggin Ice Center",
    "michigan tech huskies": "John MacInnes Student Ice Arena",
    "michigan wolverines": "Yost Ice Arena",
    "minnesota duluth bulldogs": "AMSOIL Arena",
    "minnesota golden gophers": "3M Arena at Mariucci",
    "minnesota state mavericks": "Mayo Clinic HSEC",
    "nebraska mavericks": "Baxter Arena",
    "north dakota fighting hawks": "Ralph Engelstad Arena",
    "northern michigan wildcats": "Berry Events Center",
    "notre dame fighting irish": "Compton Family Ice Arena",
    "st. cloud state huskies": "Herb Brooks National Hockey Center",
    "st. thomas tommies": "Lee & Penny Anderson Arena",
    "western michigan broncos": "Lawson Arena"
}

CITY_TO_ARENA = {
    "": "To be determined",
    "Amherst, MA": "Mullins Center",
    "Anchorage, Alaska": "Seawolf Sports Complex",
    "Ann Arbor, MI": "Yost Ice Arena",
    "Ann Arbor, Mich.": "Yost Ice Arena",
    "Bemidji, Minn.": "Sanford Center",
    "Bemidji, MN": "Sanford Center",
    "Big Rapids, Mich.": "Ewigleben Ice Arena",
    "Big Rapids, MI": "Ewigleben Ice Arena",
    "Boston, Mass.": "Matthews Arena",
    "Boston, MA (TD Garden)": "TD Garden",
    "Bowling Green, Ohio": "Slater Family Ice Arena",
    "Bowling Green, OH": "Slater Family Ice Arena",
    "Brainerd, Minn.": "Essentia health Sports Center",
    "Burlington, VT.": "Gutterson Fieldhouse",
    "Burlington, VT": "Gutterson Fieldhouse",
    "Cambridge, MA": "Bright-Landry Hockey Center",
    "Canton, NY": "Appleton Arena",
    "Chestnut Hill, MA": "Conte Forum",
    "Chestnut Hill, Mass.": "Conte Forum",
    "Colorado springs, Colo.": "Ed Robson Arena",
    "Columbus, OH": "Value City Arena",
    "Columbus, Ohio": "Value City Arena",
    "Denver, Colo.": "Magness Arena",
    "Denver, CO": "Magness Arena",
    "Duluth Minn.": "AMSOIL Arena",
    "Duluth, MN": "AMSOIL Arena",
    "Durham, NH": "Whittemore Center",
    "East Lansing, Mich.": "Munn Ice Arena",
    "East Lansing, MI": "Munn Ice Arena",
    "Fairbanks, AK": "Carlson Center",
    "Grand Forks, N.D.": "Ralph Engelstad Arena",
    "Grand Forks, ND": "Ralph Engelstad Arena",
    "Grand Rapids, Mich.": "Van Andel Arena",
    "Hamden, CT": "M&T Bank Arena",
    "Hamilton, NY": "Class of 1965 Arena",
    "Hanover, NH": "Thompson Arena",
    "Houghton, MI": "John MacInnes Student Ice Arena",
    "Ithaca, NY": "Lynah Rink",
    "Kalamazoo, MI": "Lawson Ice Arena",
    "Kalamazoo, Mich.": "Lawson Ice Arena",
    "Lawler Rink": "Lawler Arena",
    "Lawson Arena": "Lawson Ice Arena",
    "Lowell, MA": "Tsongas Center",
    "Madison, WI": "Kohl Center",
    "Madison, Wis.": "Kohl Center",
    "Mankato, MN": "Mayo Clinic HSEC",
    "Marquette, Mich.": "Berry Events Center",
    "Marquette, MI": "Berry Events Center",
    "Minneapolis": "3M Arena at Mariucci",
    "Minneapolis, MN": "3M Arena at Mariucci",
    "Minneapolis, Minn.": "3M Arena at Mariucci",
    "Moon Township, Pa.": "RMU Island Sports Center",
    "M & T Bank Arena": "M&T Bank Arena",
    "New Haven, CT": "Ingalls Rink",
    "North Andover, MA": "Lawler Rink",
    "Omaha, Neb.": "Baxter Arena",
    "Omaha, NE": "Baxter Arena",
    "Orono, ME": "Alfond Arena",
    "Orono, Maine": "Alfond Arena",
    "Oxford, Ohio": "Goggin Ice Center",
    "Oxford, OH": "Goggin Ice Center",
    "Plymouth, Mich.": "USA Hockey Arena",
    "Potsdam, NY": "Cheel Arena",
    "Princeton, NJ": "Hobey Baker Rink",
    "Providence, RI": "Schneider Arena",
    "Robert L. Ewigleben Ice Arena": "Ewigleben Ice Arena",
    "Sault Ste. Marie, MI": "Taffy Abel Arena",
    "Schenectady, NY": "M&T Bank Center",
    "Sioux Falls, SD": "Midco Arena",
    "South Bend, Ind.": "Compton Family Ice Arena",
    "South Bend, IN": "Compton Family Ice Arena",
    "Storrs, CT": "Toscano Ice Forum",
    "St. Cloud, Minn.": "Herb Brooks National Hockey Center",
    "St. Cloud, MN": "Herb Brooks National Hockey Center",
    "St. Paul, Minn.": "Lee & Penny Anderson Arena",
    "St. Paul, MN": "Lee & Penny Anderson Arena",
    "Steve Cady Arena": "Goggin Ice Center",
    "TBD": "To be determined",
    "Tempe, Ariz.": "Mullett Arena",
    "Tempe, AZ": "Mullett Arena",
    "Troy, NY": "Houston Field House",
    "University Park, Pa": "Pegula Ice Arena",
    "University Park, Pa.": "Pegula Ice Arena",
}

KNOWN_ARENAS = {
    "3M Arena at Mariucci",
    "Agganis Arena",
    "Alfond Arena",
    "AMSOIL Arena",
    "Appleton Arena",
    "Baxter Arena",
    "Berry Events Center",
    "Bright-Landry Hockey Center",
    "Carlson Center",
    "Cheel Arena",
    "Class of 1965 Arena",
    "Compton Family Ice Arena",
    "Conte Forum",
    "Ed Robson Arena",
    "Essentia health Sports Center",
    "Ewigleben Ice Arena",
    "Goggin Ice Center",
    "Gutterson Fieldhouse",
    "Herb Brooks National Hockey Center",
    "Hobey Baker Rink",
    "Houston Field House",
    "Ingalls Rink",
    "John MacInnes Student Ice Arena",
    "Kohl Center",
    "Kreitzberg Arena",
    "Lawler Arena",
    "Lawler Rink",
    "Lawson Ice Arena",
    "Lee & Penny Anderson Arena",
    "Lynah Rink",
    "Magness Arena",
    "Matthews Arena",
    "Mayo Clinic HSEC",
    "Meehan Auditorium",
    "Midco Arena",
    "Mullett Arena",
    "Mullins Center",
    "Munn Ice Arena",
    "M&T Bank Arena",
    "M&T Bank Center",
    "Pegula Ice Arena",
    "Ralph Engelstad Arena",
    "RMU Island Sports Center",
    "Sanford Center",
    "Schneider Arena",
    "Seawolf Sports Complex",
    "Slater Family Ice Arena",
    "Stafford-Smith Field at Waldo Stadium",
    "Taffy Abel Arena",
    "TD Garden",
    "The O2 Belfast",
    "Thompson Arena",
    "To be determined",
    "Toscano Ice Forum",
    "Tsongas Center",
    "USA Hockey Arena",
    "Value City Arena",
    "Van Andel Arena",
    "Whittemore Center",
    "Yost Ice Arena",
}

NCAA_MASCOT_FIX = {
    "Fighting Sioux": "Fighting Hawks"
}

NCAA_TEAM_FIX = {
    "Alaska Fairbanks": "Alaska",
    "Merrimack College": "Merrimack",
    "Rensselaer Polytechnic Institute": "RPI",
    "Union College": "Union",
    "USA Hockey Under-18 Team": "US National Team Development Program",
}

TEAM_NORMALIZATION = {
    "Dartmouth College Big Green": "Dartmouth College",
    "Denver Pioneers": "Denver",
    "Miami Redhawks": "Miami",
    "St. Cloud State Huskies": "St. Cloud State",
    "Western Michigan Broncos": "Western Michigan",
}

TEAM_MASCOTS_FALLBACK = {
    "Alaska": "Nanooks",
    "Alaska Anchorage": "Seawolves",
    "Bowling Green": "Falcons",
    "Boston": "Terriers",
    "Boston College": "Eagles",
    "Denver": "Pioneers",
    "Ferris State": "Bulldogs",
    "Great Lakes Invitational": " ",
    "Holy Cross": "Crusaders",
    "Lindenwood" :"Lions",
    "Long Island": "Sharks",
    "Merrimack": "Warriors",
    "Michigan": "Wolverines",
    "Minnesota": "Golden Gophers",
    "Minnesota Duluth": "Bulldogs",
    "New Hampshire": "Wildcats",
    "North Dakota": "Fighting Hawks",
    "Northeastern": "Huskies",
    "Norwich": "Cadets",
    "Notre Dame": "Fighting Irish",
    "Stonehill": "Skyhawks",
    "St. Cloud State": "Huskies",
    "St. Thomas": "Tommies",
    "US National Team Development Program": " ",
    "Vermont": "Catamounts",
    "Western Ontario": "Mustangs",
    "Wisconsin": "Badgers",
}

def normalize_team(name):
    name = name.strip()
    return TEAM_NORMALIZATION.get(name, name)

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

    if ("Exhibition") in title:
        is_exhibition = True
        title = title.replace("(Exhibition)", "").strip()
    if ("(ex)") in title:
        is_exhibition = True
        title = title.replace("(ex)", "").strip()

    return title, is_exhibition

def fix_ncaa_team_name(name):
    return NCAA_TEAM_FIX.get(name, name)

def clean_mascot(mascot):
    if not mascot:
        return mascot
    return NCAA_MASCOT_FIX.get(mascot, mascot)

def stadium(name):
    key = name.lower().strip()
        # Debug print intégré
    if key in TEAM_STADIUM:
        return TEAM_STADIUM[key]
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name

def city_to_arena(raw_location):
    if not raw_location:
        return raw_location

    raw_location = raw_location.replace("\\", "").strip()

    if raw_location in CITY_TO_ARENA:
        return CITY_TO_ARENA[raw_location]

    raw_no_comma = raw_location.replace(",", "")
    for key in CITY_TO_ARENA:
        if raw_no_comma.lower() == key.replace(",", "").lower():
            return CITY_TO_ARENA[key]

    return raw_location

def validate_arena(arena_name):
    if arena_name not in KNOWN_ARENAS:
        print(f"[ERROR] Arena not in KNOWN_ARENAS: '{arena_name}'")

    return arena_name

def clean_ncaa_team_name(name):
    name = name.strip()

    patterns = [
        "University of ",
        "University",
        "at Omaha",
        "University (OH)",
        "(SD)"
    ]

    for p in patterns:
        if name.startswith(p):
            name = name[len(p):].strip()
        if name.endswith(p):
            name = name[:-len(p)].strip()
    
    return name

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
            raw_title = opponent_obj.get("title", "").replace(",", "")
            clean_title, is_exhibition = clean_ncaa_title_and_flags(raw_title)
            opponent_title = clean_ncaa_team_name(clean_title)
            opponent_title = fix_ncaa_team_name(opponent_title)
            if is_ncaa_tournament(opponent_title):
                continue
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
                if "/" or "|" in venue_raw:
                    venue = venue_raw.split("/")[-1].split("|")[-1].strip()
                else:
                    venue = venue_raw.strip()

            venue_city_or_arena = venue.strip()
            venue_from_city = city_to_arena(venue_city_or_arena)
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

            if is_exhibition:
                description.append("Exhibition Game")

            promo = ev.get("gamePromotionText", "")
            if promo and "scrimmage" in promo.lower():
                description.append("Scrimmage Game")

            event.add("description", "\n".join(description))

            cal.add_component(event)

    return cal

def parse_ncaa_conf(json_data, team_name):
    cal = create_calendar()

    for ev in json_data:

        # Filter by team
        school = ev.get("school", {})
        opp = ev.get("opponent", {})

        home_title = clean_ncaa_team_name(school.get("title", ""))
        away_title = clean_ncaa_team_name(opp.get("title", ""))

        team_norm = normalize_team(team_name)
        home_norm = normalize_team(home_title)
        away_norm = normalize_team(away_title)

        if team_norm != home_norm and team_norm != away_norm:
            continue

        # Determine home/away
        loc_ind = ev.get("location_indicator")
        if loc_ind == "H":
            home_team = full_team_name_conf(school)
            away_team = full_team_name_conf(opp)
        else:
            home_team = full_team_name_conf(opp)
            away_team = full_team_name_conf(school)

        # Date/time
        iso_time = ev.get("date_utc") or ev.get("date")
        start_dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(hours=2, minutes=30)

        # Venue
        venue_raw = ev.get("location") or ""
        venue_raw = str(venue_raw)
        venue = venue_raw.strip()

        if "/" in venue_raw:
            venue = venue_raw.split("/")[-1].strip()
        elif venue_raw.lower() == "home":
            venue = stadium(home_team)
        elif venue_raw == "":
            venue = f"To be determined"
        else:
            venue = venue_raw.strip()

        venue_city_or_arena = venue.strip()
        venue_from_city = city_to_arena(venue_city_or_arena)
        venue = validate_arena(venue_from_city)

        # Scrimmage detection
        scrimmage = ev.get("type", "")
        is_scrimmage = scrimmage == 'S'

        # Create event
        event = Event()
        event.add("uid", f"ncaa{ev['id']}")
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("summary", f"🏒 | {away_team} @ {home_team}")
        event.add("location", venue)

        description = []

        if ev.get("tba") == True:
            description.append("Game time to be determined")

        if is_scrimmage:
            description.append("Scrimmage Game")

        event.add("description", "\n".join(description))

        cal.add_component(event)

    return cal
