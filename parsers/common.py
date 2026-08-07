from datetime import datetime, timedelta, timezone

def parse_iso_datetime_duration(iso_str, hours=2, minutes=30):
    if not iso_str:
        return None, None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return None, None
    dt_utc = dt.astimezone(timezone.utc)
    dt_naive = dt_utc.replace(tzinfo=None)
    dt_end = dt_naive + timedelta(hours=hours, minutes=minutes)
    return dt_naive, dt_end

def build_description(lines):
    return "\n".join([line for line in lines if line])

def uid(prefix, game_id):
    return f"{prefix}{game_id}"

def city_to_arena(raw_location, mapping):
    if not raw_location:
        return raw_location
    loc = str(raw_location).replace("\\", "").strip()
    if loc in mapping:
        return mapping[loc]
    loc_no_comma = loc.replace(",", "")
    for key in mapping:
        key_no_comma = key.replace(",", "")
        if loc_no_comma.lower() == key_no_comma.lower():
            return mapping[key]
    return loc

def normalize_team(name, mapping):
    key = name.lower().strip()
    if key in mapping:
        return mapping.get(key, name)
    else:
        print(f"[WARN] No mapping for '{name}' (key='{key}')")
        return name