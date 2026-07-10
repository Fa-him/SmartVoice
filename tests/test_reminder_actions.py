import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from Backend import ReminderActions as actions
from Backend import ReminderManager as reminders


class ReminderActionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 2, 15, 0, 0)

    def reminder_files(self):
        tmp = tempfile.TemporaryDirectory()
        reminder_file = Path(tmp.name) / "reminders.json"
        last_due_file = Path(tmp.name) / "last_due_reminders.json"
        reminder_file.write_text("[]", encoding="utf-8")
        return tmp, reminder_file, last_due_file

    def test_create_recurring_daily_reminder(self):
        tmp, reminder_file, last_due_file = self.reminder_files()
        with tmp:
            with patch.object(reminders, "REMINDERS_FILE", reminder_file), patch.object(actions, "LAST_DUE_FILE", last_due_file):
                response = actions.create_smart_reminder(
                    "every day at 8 pm to study",
                    self.now,
                )
                stored = json.loads(reminder_file.read_text(encoding="utf-8"))

        self.assertIn("Recurring reminder set", response)
        self.assertEqual(stored[0]["message"], "study")
        self.assertEqual(stored[0]["due_at"], "2026-07-02T20:00:00")
        self.assertEqual(stored[0]["recurrence"]["label"], "every day")

    def test_due_recurring_reminder_is_rescheduled(self):
        tmp, reminder_file, last_due_file = self.reminder_files()
        reminder_file.write_text(
            json.dumps([
                {
                    "id": "daily",
                    "message": "study",
                    "due_at": "2026-07-02T14:59:00",
                    "recurrence": {
                        "interval": 1,
                        "unit": "days",
                        "label": "every day",
                    },
                }
            ]),
            encoding="utf-8",
        )

        with tmp:
            with patch.object(reminders, "REMINDERS_FILE", reminder_file), patch.object(actions, "LAST_DUE_FILE", last_due_file):
                due = actions.pop_due_reminders(self.now)
                stored = json.loads(reminder_file.read_text(encoding="utf-8"))

        self.assertEqual([item["id"] for item in due], ["daily"])
        self.assertEqual(stored[0]["id"], "daily")
        self.assertEqual(stored[0]["due_at"], "2026-07-03T14:59:00")

    def test_list_and_cancel_reminders(self):
        tmp, reminder_file, last_due_file = self.reminder_files()
        reminder_file.write_text(
            json.dumps([
                {
                    "id": "medicine",
                    "message": "take medicine",
                    "due_at": "2026-07-02T20:00:00",
                }
            ]),
            encoding="utf-8",
        )

        with tmp:
            with patch.object(reminders, "REMINDERS_FILE", reminder_file), patch.object(actions, "LAST_DUE_FILE", last_due_file):
                listed = actions.handle_reminder_command("list")
                cancelled = actions.handle_reminder_command("cancel medicine")
                stored = json.loads(reminder_file.read_text(encoding="utf-8"))

        self.assertIn("take medicine", listed)
        self.assertEqual(cancelled, "Cancelled reminder: take medicine.")
        self.assertEqual(stored, [])

    def test_snooze_recent_due_reminder(self):
        tmp, reminder_file, last_due_file = self.reminder_files()
        reminder_file.write_text(
            json.dumps([
                {
                    "id": "break",
                    "message": "take a break",
                    "due_at": "2026-07-02T14:59:00",
                }
            ]),
            encoding="utf-8",
        )

        with tmp:
            with patch.object(reminders, "REMINDERS_FILE", reminder_file), patch.object(actions, "LAST_DUE_FILE", last_due_file):
                actions.pop_due_reminders(self.now)
                response = actions.snooze_reminder("snooze for 10 minutes", self.now)
                stored = json.loads(reminder_file.read_text(encoding="utf-8"))

        self.assertIn("Snoozed reminder", response)
        self.assertEqual(stored[0]["message"], "take a break")
        self.assertEqual(stored[0]["due_at"], "2026-07-02T15:10:00")


if __name__ == "__main__":
    unittest.main()
