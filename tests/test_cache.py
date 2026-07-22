import os
import tempfile
import unittest

from icalendar import Calendar, Event

from utils.cache import load_cached_calendar, save_cached_calendar


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cache_dir = os.path.join(self.tempdir.name, "cache")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_save_and_load_cached_calendar(self):
        calendar = Calendar()
        event = Event()
        event.add("summary", "Test game")
        event.add("dtstart", "2026-01-01 20:00:00")
        calendar.add_component(event)

        key = "nhl-test-team"
        save_cached_calendar(self.cache_dir, key, calendar)

        loaded = load_cached_calendar(self.cache_dir, key)

        self.assertIsNotNone(loaded)
        self.assertEqual(len([component for component in loaded.walk() if component.name == "VEVENT"]), 1)
