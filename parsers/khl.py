from icalendar import Calendar, Event
from datetime import datetime, timedelta
import re

TEAM_SYNONYMS = {
    "avangard": "Avangard Omsk",
    "avtomobilist": "Avtomobilist Ekaterinburg",
    "admiral": "Admiral Vladivostok",
    "ak bars": "Ak Bars Kazan",
    "amur": "Amur Khabarovsk",
    "amur khabarovsk": "Amur Khabarovsk",
    "barys": "Barys Astana",
    "dinamo mn": "Dinamo Minsk",
    "dinamo msk": "Dynamo Moscow",
    "dynamo msk": "Dynamo Moscow",
    "lada": "Lada Togliatti",
    "lokomotiv": "Lokomotiv Yaroslavl",
    "metallurg mg": "Metallurg Magnitogorsk",
    "neftekhimik": "Neftekhimik Nizhnekamsk",
    "salavat yulaev ufa": "Salavat Yulaev Ufa",
    "salavat yulaev": "Salavat Yulaev Ufa",
    "severstal": "Severstal Cherepovets",
    "sibir": "Sibir Novosibrisk Region",
    "ska": "SKA Saint Petersburg",
    "spartak": "Spartak Moscow",
    "spartak moscow": "Spartak Moscow",
    "torpedo": "Torpedo Nizhny Novgorod",
    "torpedo nizhny novgorod": "Torpedo Nizhny Novgorod",
    "traktor": "Traktor Chelyabinsk",
    "hc sochi": "HC Sochi",
    "cska": "CSKA Moscow",
    "dragons": "Shanghai Dragons"
}

CITY_TO_ARENA = {
    "Arena-2000-Lokomotiv": "Arena 2000",
    "Bolshoy": "Bolshoy Ice Dome",
    "Lada-Arena": "Lada Arena",
    "Ledovyy Dvorets": "Ice Palace",
    "Megasport": "Megasport Arena",
    "Minsk-Arena": "Minsk Arena",
    "Nagornyy": "CEC Nagorny",
    "Neftekhim Arena": "Neftekhim Ice Palace",
    "Sibir-Arena": "Sibir Arena",
    "Traktor": "Traktor Ice Arena",
    "TsSKA Arena": "CSKA Arena",
    "Ufa-Arena": "Ufa Arena",
    "UGMK Arena": "UMMC Arena",
}

KNOWN_ARENAS = {
    "Arena 2000",
    "Arena Metallurg",
    "Barys Arena",
    "Bolshoy Ice Dome",
    "CEC Nagorny",
    "CSKA Arena",
    "Fetisov Arena",
    "G-Drive Arena",
    "Ice Palace",
    "Lada Arena",
    "Megasport Arena",
    "Minsk Arena",
    "Neftekhim Ice Palace",
    "Platinum Arena",
    "Sibir Arena",
    "SKA Arena",
    "Tatneft Arena",
    "Traktor Ice Arena",
    "Ufa Arena",
    "UMMC Arena",
    "VTB Arena",
}

def validate_arena(arena_name): 
    if arena_name not in KNOWN_ARENAS: 
        print(f"[ERROR] Arena not in KNOWN_ARENAS: '{arena_name}'")

    return arena_name

def city_to_arena(raw_location): 
    if not raw_location: 
        return raw_location 
        
    if raw_location in CITY_TO_ARENA: 
        return CITY_TO_ARENA[raw_location] 
        
    raw_no_comma = raw_location.replace(",", "")
    for key in CITY_TO_ARENA: 
        if raw_no_comma.lower() == key.replace(",", "").lower(): 
            return CITY_TO_ARENA[key] 
            
    return raw_location

def normalize(name):
    key = name.lower().strip()
        # Debug print intégré
    if key in TEAM_SYNONYMS:
        return TEAM_SYNONYMS[key]
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name

def translit_ru_to_lat(text):
    table = {
        "А":"A","Б":"B","В":"V","Г":"G","Д":"D","Е":"E","Ё":"Yo","Ж":"Zh","З":"Z",
        "И":"I","Й":"Y","К":"K","Л":"L","М":"M","Н":"N","О":"O","П":"P","Р":"R",
        "С":"S","Т":"T","У":"U","Ф":"F","Х":"Kh","Ц":"Ts","Ч":"Ch","Ш":"Sh",
        "Щ":"Shch","Ы":"Y","Э":"E","Ю":"Yu","Я":"Ya",
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z",
        "и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r",
        "с":"s","т":"t","у":"u","ф":"f","х":"kh","ц":"ts","ч":"ch","ш":"sh",
        "щ":"shch","ы":"y","э":"e","ю":"yu","я":"ya",
        "Ь":"", "ь":"", "Ъ":"", "ъ":""
    }
    return "".join(table.get(c, c) for c in text)

def clean_location(description):
    """
    Convert 'Novosibirsk «Сибирь-Арена»' → 'Сибирь-Арена'
    """
    if not description:
        return None

    # 1. Extraire ce qui est entre guillemets « »
    arena = re.findall(r"«([^»]+)»", description)
    if arena:
        return arena[0].strip()

    # 2. Sinon, essayer après le dernier espace
    parts = description.split()
    if len(parts) > 1:
        return parts[-1].strip()

    # 3. Sinon retourner brut
    return description.strip()

def parse_khl_ics(raw_ics, team_name, season_id):
    cal_in = Calendar.from_ical(raw_ics)
    cal_out = Calendar()

    MOSCOW_OFFSET = timedelta(hours=3)

    for component in cal_in.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", ""))

        # Format KHL: "Dinamo Mn - Torpedo"
        if "-" not in summary:
            continue

        home, away = [x.strip() for x in summary.split("-")]

        home_norm = normalize(home)
        away_norm = normalize(away)
        team_norm = normalize(team_name)

        # Filtrer par équipe
        if not (
            team_norm in home_norm
            or team_norm in away_norm
        ):
            print(f"SKIPPED: team '{team_name}")
            continue

        # DTSTART / DTEND → datetime naïf (Moscow)
        dtstart_raw = component.get("DTSTART").dt
        dtend_raw = component.get("DTEND").dt

        # Convertir Europe/Moscow → UTC (soustraire 3h)
        dtstart = dtstart_raw - MOSCOW_OFFSET
        dtend = dtend_raw - MOSCOW_OFFSET

        match_id = str(component.get("UID", ""))

        # UID propre
        uid = f"khl{match_id}"

        game_center = f"https://en.khl.ru/game/{season_id}/{match_id}/preview"

        # Créer événement propre
        event = Event()
        event.add("SUMMARY", f"🏒 | {home_norm} vs {away_norm}")
        event.add("DTSTART", dtstart)
        event.add("DTEND", dtend)
        event.add("UID", uid)
        event.add("DESCRIPTION", f"Game Center: {game_center}")

        raw_loc = description.replace("Location of the event:", "").strip()
        arena_ru = clean_location(raw_loc)
        arena_en = translit_ru_to_lat(arena_ru)

        if arena_en:
            event.add("LOCATION", validate_arena(city_to_arena(arena_en)))

        cal_out.add_component(event)

    return cal_out
