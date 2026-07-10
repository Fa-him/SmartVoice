import json
import re
import uuid
from calendar import monthrange
from datetime import datetime, timedelta

from Backend.Config import ROOT_DIR
from Backend.ReminderManager import (
    ReminderParseError,
    _clean_message,
    _format_datetime,
    _load_reminders,
    _save_reminders,
    create_reminder,
    parse_reminder,
    pop_due_reminders as pop_one_time_due_reminders,
)


LAST_DUE_FILE = ROOT_DIR / "Data" / "last_due_reminders.json"

INTERVAL_RE = re.compile(
    r"\bevery\s+(?P<amount>\d+)\s+"
    r"(?P<unit>minute|minutes|min|mins|hour|hours|day|days|week|weeks|month|months)\b",
    re.IGNORECASE,
)
DAILY_RE = re.compile(r"\b(every\s+day|daily|each\s+day)\b", re.IGNORECASE)
WEEKLY_RE = re.compile(r"\b(every\s+week|weekly|each\s+week)\b", re.IGNORECASE)
MONTHLY_RE = re.compile(r"\b(every\s+month|monthly|each\s+month)\b", re.IGNORECASE)
DURATION_RE = re.compile(
    r"\b(?:for\s+|in\s+)?(?P<amount>\d+)\s*"
    r"(?P<unit>minute|minutes|min|mins|hour|hours|day|days)\b",
    re.IGNORECASE,
)
TIME_HINT_RE = re.compile(
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?\b|"
    r"\b\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?\b|"
    r"\b\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\b|"
    r"\btoday\b|\btomorrow\b|\bon\b|\bin\s+\d+",
    re.IGNORECASE,
)


def _normalize_unit(unit: str) -> str:
    unit = unit.lower()
    if unit.startswith("min"):
        return "minutes"
    if unit.startswith("hour"):
        return "hours"
    if unit.startswith("day"):
        return "days"
    if unit.startswith("week"):
        return "weeks"
    if unit.startswith("month"):
        return "months"
    return unit


def _duration_delta(amount: int, unit: str) -> timedelta:
    unit = _normalize_unit(unit)
    if unit == "minutes":
        return timedelta(minutes=amount)
    if unit == "hours":
        return timedelta(hours=amount)
    if unit == "days":
        return timedelta(days=amount)
    if unit == "weeks":
        return timedelta(weeks=amount)
    raise ReminderParseError("Please use minutes, hours, days, or weeks.")


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _advance_due_at(due_at: datetime, recurrence: dict, now: datetime) -> datetime:
    amount = int(recurrence.get("interval", 1))
    unit = recurrence.get("unit", "days")
    next_due = due_at

    for _ in range(1000):
        if unit == "months":
            next_due = _add_months(next_due, amount)
        else:
            next_due = next_due + _duration_delta(amount, unit)

        if next_due > now:
            return next_due

    raise ReminderParseError("Could not calculate the next recurring reminder time.")


def _extract_recurrence(text: str) -> tuple[dict | None, str]:
    match = INTERVAL_RE.search(text)
    if match:
        amount = int(match.group("amount"))
        unit = _normalize_unit(match.group("unit"))
        if amount <= 0:
            raise ReminderParseError("Recurring reminder interval must be positive.")
        label = f"every {amount} {unit[:-1] if amount == 1 else unit}"
        remaining = (text[:match.start()] + " " + text[match.end():]).strip()
        return {"interval": amount, "unit": unit, "label": label}, remaining

    for pattern, unit, label in (
        (DAILY_RE, "days", "every day"),
        (WEEKLY_RE, "weeks", "every week"),
        (MONTHLY_RE, "months", "every month"),
    ):
        match = pattern.search(text)
        if match:
            remaining = (text[:match.start()] + " " + text[match.end():]).strip()
            return {"interval": 1, "unit": unit, "label": label}, remaining

    return None, text


def _contains_time_hint(text: str) -> bool:
    return bool(TIME_HINT_RE.search(text))


def _sort_reminders(reminders: list[dict]) -> list[dict]:
    return sorted(reminders, key=lambda item: item.get("due_at", ""))


def create_smart_reminder(text: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    recurrence, schedule_text = _extract_recurrence(text)

    if not recurrence:
        return create_reminder(text)

    schedule_text = schedule_text.strip()
    if _contains_time_hint(schedule_text):
        due_at, message = parse_reminder(schedule_text, now)
    else:
        due_at = _advance_due_at(now, recurrence, now)
        message = _clean_message(schedule_text)

    reminders = _load_reminders()
    reminders.append({
        "id": str(uuid.uuid4()),
        "message": message,
        "due_at": due_at.isoformat(timespec="seconds"),
        "created_at": now.isoformat(timespec="seconds"),
        "recurrence": recurrence,
    })
    _save_reminders(_sort_reminders(reminders))

    return (
        f"Recurring reminder set for {_format_datetime(due_at)} "
        f"({recurrence['label']}): {message}."
    )


def _load_last_due(now: datetime) -> dict | None:
    try:
        data = json.loads(LAST_DUE_FILE.read_text(encoding="utf-8"))
        triggered_at = datetime.fromisoformat(data.get("triggered_at", ""))
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if now - triggered_at > timedelta(hours=12):
        return None

    reminders = data.get("reminders", [])
    return reminders[-1] if reminders else None


def _save_last_due(reminders: list[dict], now: datetime) -> None:
    LAST_DUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_DUE_FILE.write_text(
        json.dumps(
            {
                "triggered_at": now.isoformat(timespec="seconds"),
                "reminders": reminders,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def pop_due_reminders(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    due_reminders = pop_one_time_due_reminders(now)

    if not due_reminders:
        return []

    _save_last_due(due_reminders, now)
    reminders = _load_reminders()

    for reminder in due_reminders:
        recurrence = reminder.get("recurrence")
        if not recurrence:
            continue

        try:
            due_at = datetime.fromisoformat(reminder["due_at"])
            next_due = _advance_due_at(due_at, recurrence, now)
        except (KeyError, TypeError, ValueError, ReminderParseError):
            continue

        next_reminder = dict(reminder)
        next_reminder["due_at"] = next_due.isoformat(timespec="seconds")
        next_reminder["last_triggered_at"] = now.isoformat(timespec="seconds")
        reminders.append(next_reminder)

    _save_reminders(_sort_reminders(reminders))
    return due_reminders


def list_reminders() -> str:
    reminders = _sort_reminders(_load_reminders())
    if not reminders:
        return "You have no reminders set."

    lines = [f"You have {len(reminders)} reminder{'s' if len(reminders) != 1 else ''}:"]
    for index, reminder in enumerate(reminders, start=1):
        try:
            due_at = datetime.fromisoformat(reminder["due_at"])
            when = _format_datetime(due_at)
        except (KeyError, TypeError, ValueError):
            when = "unknown time"

        recurrence = reminder.get("recurrence") or {}
        recurrence_text = f" ({recurrence.get('label')})" if recurrence else ""
        message = reminder.get("message", "your reminder")
        lines.append(f"{index}. {when} - {message}{recurrence_text}")

    return "\n".join(lines)


def _cancel_all_reminders() -> str:
    count = len(_load_reminders())
    _save_reminders([])
    if count == 0:
        return "You have no reminders to cancel."
    return f"Cancelled {count} reminder{'s' if count != 1 else ''}."


def _reminder_search_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(cancel|delete|remove|clear|my|the|a|an|reminders?|please)\b", " ", text)
    return " ".join(text.split())


def cancel_reminder(text: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    reminders = _sort_reminders(_load_reminders())
    if not reminders:
        return "You have no reminders to cancel."

    lower_text = text.lower()
    if re.search(r"\b(all|everything)\b", lower_text):
        return _cancel_all_reminders()

    index_match = re.search(r"(?:reminder\s+|number\s+|#)(?P<number>\d+)\b", lower_text)
    if not index_match and lower_text.strip().isdigit():
        index_match = re.search(r"(?P<number>\d+)", lower_text)

    if index_match:
        index = int(index_match.group("number")) - 1
        if 0 <= index < len(reminders):
            removed = reminders.pop(index)
            _save_reminders(reminders)
            return f"Cancelled reminder: {removed.get('message', 'your reminder')}."
        return "I could not find a reminder with that number."

    query = _reminder_search_text(text)
    if query in {"this", "that"}:
        last_due = _load_last_due(now)
        if last_due:
            query = last_due.get("id", "")

    matches = []
    for reminder in reminders:
        message = reminder.get("message", "").lower()
        reminder_id = reminder.get("id", "")
        if query and (query in message or query == reminder_id):
            matches.append(reminder)

    if not matches:
        return "I could not find a matching reminder to cancel."
    if len(matches) > 1:
        return "I found more than one matching reminder. Say 'show my reminders' and cancel by number."

    removed = matches[0]
    reminders = [item for item in reminders if item.get("id") != removed.get("id")]
    _save_reminders(reminders)
    return f"Cancelled reminder: {removed.get('message', 'your reminder')}."


def snooze_reminder(text: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    match = DURATION_RE.search(text)
    if not match:
        return "Please tell me how long to snooze, like 'snooze for 10 minutes'."

    amount = int(match.group("amount"))
    if amount <= 0:
        return "Snooze time must be in the future."

    last_due = _load_last_due(now)
    if not last_due:
        return "I do not have a recent reminder to snooze."

    due_at = now + _duration_delta(amount, match.group("unit"))
    message = last_due.get("message", "your reminder")
    reminders = _load_reminders()
    reminders.append({
        "id": str(uuid.uuid4()),
        "message": message,
        "due_at": due_at.isoformat(timespec="seconds"),
        "created_at": now.isoformat(timespec="seconds"),
        "snoozed_from": last_due.get("id"),
    })
    _save_reminders(_sort_reminders(reminders))
    return f"Snoozed reminder until {_format_datetime(due_at)}: {message}."


def handle_reminder_command(command: str) -> str:
    text = command.strip()
    if text.lower().startswith("reminder "):
        text = text[9:].strip()

    lower_text = text.lower()

    if re.search(r"\b(show|list|view|what are|what's|check)\b", lower_text):
        return list_reminders()

    if re.search(r"\b(snooze|delay|postpone)\b", lower_text):
        return snooze_reminder(text)

    if re.search(r"\b(cancel|delete|remove|clear)\b", lower_text):
        return cancel_reminder(text)

    try:
        return create_smart_reminder(text)
    except ReminderParseError as e:
        return f"Could not set reminder: {e}"
