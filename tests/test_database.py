import os
import tempfile
import unittest

from utils.database import export_calendar_from_db, get_events, initialize_database, store_event


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "calendar.db")
        initialize_database(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_store_and_read_events(self):
        store_event(
            self.db_path,
            league="NHL",
            team_name="Montréal Canadiens",
            source_url="https://example.com/feed",
            parser="nhl",
            uid="test-uid-1",
            summary="Team A @ Team B",
            location="Arena",
            description="Official game",
            dtstart="2026-01-01T01:00:00+00:00",
            dtend="2026-01-01T03:30:00+00:00",
        )

        rows = get_events(self.db_path, league="NHL")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["summary"], "Team A @ Team B")

    def test_export_calendar_from_db(self):
        store_event(
            self.db_path,
            league="NHL",
            team_name="Montréal Canadiens",
            source_url="https://example.com/feed",
            parser="nhl",
            uid="test-uid-2",
            summary="Team C @ Team D",
            location="Arena",
            description="Official game",
            dtstart="2026-01-02T01:00:00+00:00",
            dtend="2026-01-02T03:30:00+00:00",
        )

        calendar = export_calendar_from_db(self.db_path, league="NHL")
        vevents = [component for component in calendar.walk() if component.name == "VEVENT"]
        self.assertEqual(len(vevents), 1)
