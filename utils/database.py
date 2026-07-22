import os
import sqlite3
from datetime import datetime

from icalendar import Event

from utils.calendar import create_calendar


DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calendar.db")


def initialize_database(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league TEXT NOT NULL,
            team_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            parser TEXT NOT NULL,
            uid TEXT UNIQUE NOT NULL,
            summary TEXT NOT NULL,
            location TEXT,
            description TEXT,
            dtstart TEXT NOT NULL,
            dtend TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def store_event(
    db_path=DEFAULT_DB_PATH,
    *,
    league,
    team_name,
    source_url,
    parser,
    uid,
    summary,
    location,
    description,
    dtstart,
    dtend,
):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO events (
            league, team_name, source_url, parser, uid, summary, location,
            description, dtstart, dtend
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            league,
            team_name,
            source_url,
            parser,
            uid,
            summary,
            location,
            description,
            dtstart,
            dtend,
        ),
    )
    conn.commit()
    conn.close()


def get_events(db_path=DEFAULT_DB_PATH, *, league=None, team_name=None, start_date=None, end_date=None):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM events WHERE 1=1"
    params = []

    if league:
        query += " AND league = ?"
        params.append(league)

    if team_name:
        query += " AND team_name = ?"
        params.append(team_name)

    if start_date:
        query += " AND dtstart >= ?"
        params.append(start_date)

    if end_date:
        query += " AND dtstart <= ?"
        params.append(end_date)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def export_calendar_from_db(db_path=DEFAULT_DB_PATH, *, league=None, team_name=None, start_date=None, end_date=None):
    cal = create_calendar()

    for item in get_events(
        db_path,
        league=league,
        team_name=team_name,
        start_date=start_date,
        end_date=end_date,
    ):
        event = Event()
        event.add("uid", item["uid"])
        event.add("summary", item["summary"])
        if item.get("location"):
            event.add("location", item["location"])
        if item.get("description"):
            event.add("description", item["description"])

        try:
            start_dt = datetime.fromisoformat(item["dtstart"])
            event.add("dtstart", start_dt)
        except ValueError:
            continue

        if item.get("dtend"):
            try:
                end_dt = datetime.fromisoformat(item["dtend"])
                event.add("dtend", end_dt)
            except ValueError:
                pass

        cal.add_component(event)

    return cal
