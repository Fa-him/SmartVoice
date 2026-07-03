import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from Backend.Config import ROOT_DIR


REMINDERS_FILE = ROOT_DIR / "Data" / "reminders.json"

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

RELATIVE_RE = re.compile(
    r"\bin\s+(?P<amount>\d+)\s+"
    r"(?P<unit>minute|minutes|min|mins|hour|hours|day|days)\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(
    r"\b(?:at\s+)?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*"
    r"(?P<ampm>a\.?m\.?|p\.?m\.?)?\b",
    re.IGNORECASE,
)
DAY_MONTH_RE = re.compile(
    r"\b(?:on\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(?P<month>[a-zA-Z]+)(?:\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
MONTH_DAY_RE = re.compile(
    r"\b(?:on\s+)?(?P<month>[a-zA-Z]+)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)


class ReminderParseError(ValueError):
    """Raised when a reminder command cannot be converted into a date/time."""


def _ensure_file() -> None:
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not REMINDERS_FILE.exists():
        REMINDERS_FILE.write_text("[]", encoding="utf-8")


def _load_reminders() -> list[dict]:
    _ensure_file()
    try:
        data = json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_reminders(reminders: list[dict]) -> None:
    _ensure_file()
    REMINDERS_FILE.write_text(
        json.dumps(reminders, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _clean_message(text: str) -> str:
    message = " ".join(text.split())
    message = re.sub(
        r"^(for|to|that|about|me to|me that|remind me to|remind me that)\s+",
        "",
        message,
        flags=re.IGNORECASE,
    )
    return message.strip(" ,.-") or "your reminder"


def _format_datetime(dt: datetime) -> str:
    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{dt.strftime('%M')} {dt.strftime('%p')} on {dt.strftime('%B')} {dt.day}, {dt.year}"


def _parse_time(text: str, now: datetime) -> tuple[int, int, re.Match | None]:
    match = TIME_RE.search(text)
    if not match:
        raise ReminderParseError(
            "Please include a time, like 'at 9:00 PM' or 'in 10 minutes'."
        )

    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    ampm = (match.group("ampm") or "").replace(".", "").lower()

    if minute > 59:
        raise ReminderParseError("Reminder minute must be between 0 and 59.")

    if ampm:
        if hour < 1 or hour > 12:
            raise ReminderParseError("12-hour reminder time must be between 1 and 12.")
        if ampm.startswith("p") and hour != 12:
            hour += 12
        elif ampm.startswith("a") and hour == 12:
            hour = 0
    elif hour > 23:
        raise ReminderParseError("24-hour reminder time must be between 0 and 23.")

    return hour, minute, match


def _parse_date(text: str, now: datetime) -> tuple[int | None, int | None, int | None, re.Match | None]:
    lower = text.lower()
    if re.search(r"\btomorrow\b", lower):
        tomorrow = now + timedelta(days=1)
        return tomorrow.year, tomorrow.month, tomorrow.day, re.search(r"\btomorrow\b", text, re.IGNORECASE)

    if re.search(r"\btoday\b", lower):
        return now.year, now.month, now.day, re.search(r"\btoday\b", text, re.IGNORECASE)

    for pattern in (DAY_MONTH_RE, MONTH_DAY_RE):
        match = pattern.search(text)
        if not match:
            continue

        month_name = match.group("month").lower()
        month = MONTHS.get(month_name)
        if not month:
            continue

        day = int(match.group("day"))
        year = int(match.group("year") or now.year)
        return year, month, day, match

    return None, None, None, None


def parse_reminder(text: str, now: datetime | None = None) -> tuple[datetime, str]:
    now = now or datetime.now()
    payload = text.removeprefix("reminder ").strip()
    if not payload:
        raise ReminderParseError("Please tell me when and what to remind you about.")

    relative = RELATIVE_RE.search(payload)
    if relative:
        amount = int(relative.group("amount"))
        unit = relative.group("unit").lower()
        if amount <= 0:
            raise ReminderParseError("Reminder time must be in the future.")

        if unit.startswith("min"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("hour"):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)

        message_text = payload[:relative.start()] + " " + payload[relative.end():]
        return now + delta, _clean_message(message_text)

    hour, minute, time_match = _parse_time(payload, now)
    year, month, day, date_match = _parse_date(payload, now)

    if year is None:
        due_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due_at <= now:
            due_at += timedelta(days=1)
    else:
        try:
            due_at = datetime(year, month, day, hour, minute)
        except ValueError as e:
            raise ReminderParseError(f"Invalid reminder date: {e}") from e

        matched_date_text = date_match.group(0).lower() if date_match else ""
        if "today" in matched_date_text and due_at <= now:
            raise ReminderParseError("That reminder time has already passed today.")

        if date_match and not date_match.groupdict().get("year") and due_at <= now:
            try:
                due_at = due_at.replace(year=due_at.year + 1)
            except ValueError:
                due_at = due_at + timedelta(days=365)

    message_text = payload
    for match in sorted(
        [m for m in (time_match, date_match) if m],
        key=lambda m: m.start(),
        reverse=True,
    ):
        message_text = message_text[:match.start()] + " " + message_text[match.end():]

    return due_at, _clean_message(message_text)


def create_reminder(text: str) -> str:
    due_at, message = parse_reminder(text)
    reminders = _load_reminders()
    reminders.append({
        "id": str(uuid.uuid4()),
        "message": message,
        "due_at": due_at.isoformat(timespec="seconds"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    reminders.sort(key=lambda item: item.get("due_at", ""))
    _save_reminders(reminders)
    return f"Reminder set for {_format_datetime(due_at)}: {message}."


def pop_due_reminders(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    reminders = _load_reminders()
    due = []
    pending = []

    for reminder in reminders:
        try:
            due_at = datetime.fromisoformat(reminder["due_at"])
        except (KeyError, ValueError, TypeError):
            continue

        if due_at <= now:
            due.append(reminder)
        else:
            pending.append(reminder)

    if due:
        _save_reminders(pending)

    return due
