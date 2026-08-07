from icalendar import Calendar
from datetime import datetime, timedelta, timezone
from dict.khl_dict import KNOWN_ARENAS, CITY_TO_ARENA, TEAM_SYNONYMS
from parsers.common import parse_iso_datetime_duration, build_description, uid, city_to_arena, normalize_team
from utils.ics import ICSEventBuilder
import re


def validate_arena(arena_name): 
    if arena_name not in KNOWN_ARENAS: 
        print(f"[ERROR] Arena not in KNOWN_ARENAS: '{arena_name}'")

    return arena_name

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


def parse_khl_json(events, team_filter):
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
            home = normalize_team(team_a.get("name", ""), TEAM_SYNONYMS)
            away = normalize_team(team_b.get("name", ""), TEAM_SYNONYMS)

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

            # ============================
            # Location
            # ============================
            raw_loc = ev_event.get("location", "")
            arena_final = validate_arena(city_to_arena(raw_loc, CITY_TO_ARENA))

            game_center = f"https://en.khl.ru/game/{season_id}/{match_id}/preview"


            event = (
                ICSEventBuilder()
                .uid(uid("khl", (match_id)))
                .start(dtstart)
                .end(dtend)
                .summary(f"🏒 | {away} @ {home}")
                .location(arena_final)
                .description(f"Game Center: {game_center}")
                .build()
            )

            cal_out.add_component(event)

        except Exception as e:
            print(f"[ERROR] KHL JSON parse error: {e}")
            continue

    return cal_out
