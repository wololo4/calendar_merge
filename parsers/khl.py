from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
import re

TEAM_SYNONYMS = {
    "авангард": "Avangard Omsk",
    "автомобилист": "Avtomobilist Ekaterinburg",
    "адмирал": "Admiral Vladivostok",
    "ак барс": "Ak Bars Kazan",
    "амур": "Amur Khabarovsk",
    "барыс": "Barys Astana",
    "динамо мн": "Dinamo Minsk",
    "динамо м": "Dynamo Moscow",
    "лада": "Lada Togliatti",
    "локомотив": "Lokomotiv Yaroslavl",
    "металлург мг": "Metallurg Magnitogorsk",
    "нефтехимик": "Neftekhimik Nizhnekamsk",
    "салават юлаев": "Salavat Yulaev Ufa",
    "северсталь": "Severstal Cherepovets",
    "сибирь": "Sibir Novosibrisk Region",
    "ска": "SKA Saint Petersburg",
    "спартак": "Spartak Moscow",
    "торпедо": "Torpedo Nizhny Novgorod",
    "трактор": "Traktor Chelyabinsk",
    "хк сочи": "HC Sochi",
    "цска": "CSKA Moscow",
    "драконы": "Shanghai Dragons",
}

CITY_TO_ARENA = {
    "Ярославль": "Arena-2000 Lokomotiv",
    "Магнитогорск": "Arena Metallurg",
    "Астана": "Barys Arena",
    "ФТ Сириус": "Bolshoy Ice Dome",
    "Москва": "CSKA Arena",
    "Владивосток": "Fetisov Arena",
    "Омск": "G-Drive Arena",
    "Череповец": "Ice Palace",
    "Тольятти": "Lada Arena",
    # "Megasport": "Megasport Arena",
    "Минск": "Minsk Arena",
    "Нижний Новгород": "CEC Nagorny",
    "Нижнекамск": "Neftekhim Ice Palace",
    "Хабаровск": "Platinum Arena",
    "Санкт-Петербург": "SKA Arena",
    "Новосибирск": "Sibir Arena",
    "Казань": "Tatneft Arena",
    "Челябинск": "Traktor Ice Arena",
    "Уфа": "Ufa Arena",
    "Екатеринбург": "UMMC Arena",
}

KNOWN_ARENAS = {
    "Arena-2000 Lokomotiv",
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

        # Convertir Europe/Moscow → UTC
        dtstart = dtstart_raw.astimezone(timezone.utc)
        dtend = dtend_raw.astimezone(timezone.utc)

        match_id = str(component.get("UID", ""))

        # UID propre
        uid = f"khl{match_id}"

        game_center = f"https://en.khl.ru/game/{season_id}/{match_id}/preview"

        # Créer événement propre
        event = Event()
        event.add("SUMMARY", f"🏒 | {away_norm} @ {home_norm}")
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


def parse_khl_json(events, team_filter):
    """
    Convertit les événements JSON du KHL Mobile API → ICS Calendar()
    """
    cal_out = Calendar()

    target_team_id = team_filter[0] if (team_filter and isinstance(team_filter, list)) else None
    
    for ev in events:
        try:
            if not isinstance(ev, dict) or "event" not in ev:
                print(f"[Warn] Unexpected KHL JSON structure: {ev}")

            ev_event = ev["event"]
            # ============================
            # Filtrage par équipe
            # ============================
            team_a = ev_event.get("team_a", {})
            team_b = ev_event.get("team_b", {})

            team_a_id = team_a.get("id")
            team_b_id = team_b.get("id")

            if target_team_id is not None:
                if team_a_id != target_team_id and team_b_id != target_team_id:
                    continue

            # ============================
            # Noms normalisés
            # ============================
            home = normalize(team_a.get("name", ""))
            away = normalize(team_b.get("name", ""))

            # ============================
            # Horaires
            # ============================
            ts = ev_event.get("start_at")
            if not ts:
                continue

            if ts > 10**12:
                ts = ts//1000

            dtstart = datetime.fromtimestamp(ts, tz=timezone.utc)
            dtend = dtstart + timedelta(hours=2, minutes=30)

            # ============================
            # UID
            # ============================
            match_id = ev_event.get("khl_id")
            season_id = ev_event.get("outer_stage_id")
            uid = f"khl{match_id}"

            # ============================
            # Location
            # ============================
            raw_loc = ev_event.get("location", "")
            arena_final = validate_arena(city_to_arena(raw_loc))

            game_center = f"https://en.khl.ru/game/{season_id}/{match_id}/preview"

            # ============================
            # ICS Event
            # ============================
            event = Event()
            event.add("SUMMARY", f"🏒 | {away} @ {home}")
            event.add("DTSTART", dtstart)
            event.add("DTEND", dtend)
            event.add("UID", uid)

            # Game Center (optionnel)
            event.add("DESCRIPTION", f"Game Center: {game_center}")

            if arena_final:
                event.add("LOCATION", arena_final)

            cal_out.add_component(event)

        except Exception as e:
            print(f"[ERROR] KHL JSON parse error: {e}")
            continue

    return cal_out
