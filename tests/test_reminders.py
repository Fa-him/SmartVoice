import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from Backend import ReminderManager as reminders


class ReminderParsingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 2, 15, 0, 0)

    def test_relative_reminder(self):
        due_at, message = reminders.parse_reminder("in 10 minutes stretch", self.now)

        self.assertEqual(due_at, datetime(2026, 7, 2, 15, 10, 0))
        self.assertEqual(message, "stretch")

    def test_tomorrow_reminder(self):
        due_at, message = reminders.parse_reminder("tomorrow 7 am tea", self.now)

        self.assertEqual(due_at, datetime(2026, 7, 3, 7, 0, 0))
        self.assertEqual(message, "tea")

    def test_past_today_is_rejected(self):
        with self.assertRaises(reminders.ReminderParseError):
            reminders.parse_reminder("today 9:00 am late", self.now)

    def test_past_month_day_rolls_to_next_year(self):
        due_at, message = reminders.parse_reminder(
            "9:00pm 25th june business meeting",
            self.now,
        )

        self.assertEqual(due_at, datetime(2027, 6, 25, 21, 0, 0))
        self.assertEqual(message, "business meeting")

    def test_pop_due_reminders_keeps_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            reminder_file = Path(tmp) / "reminders.json"
            reminder_file.write_text(
                json.dumps(
                    [
                        {
                            "id": "due",
                            "message": "stand up",
                            "due_at": "2026-07-02T14:59:00",
                        },
                        {
                            "id": "pending",
                            "message": "tea",
                            "due_at": "2026-07-02T15:30:00",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(reminders, "REMINDERS_FILE", reminder_file):
                due = reminders.pop_due_reminders(self.now)
                stored = json.loads(reminder_file.read_text(encoding="utf-8"))

        self.assertEqual([item["id"] for item in due], ["due"])
        self.assertEqual([item["id"] for item in stored], ["pending"])


if __name__ == "__main__":
    unittest.main()
