from icalendar import Calendar

def create_calendar():
    cal = Calendar()
    cal.add("prodid", "-//Hockey Calendar//")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    return cal


def event_id(event):
    # Normalize DTSTART
    dt = event.get("DTSTART")
    dt_str = dt.dt.isoformat() if hasattr(dt, "dt") else str(dt)

    # Normalize SUMMARY
    summary = str(event.get("SUMMARY", "")).strip().lower()

    # Normalize LOCATION
    location = str(event.get("LOCATION", "")).strip().lower()

    # Build stable key
    return f"{dt_str}|{summary}|{location}"
