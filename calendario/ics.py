import datetime

from django.utils import timezone

_DEFAULT_DURATION = datetime.timedelta(hours=1)


def _escape_text(value):
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _format_datetime(value):
    return value.astimezone(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def build_event_ics(event):
    """Renders a single event as a minimal RFC 5545 VCALENDAR/VEVENT.
    Recurring events are stored as one row per occurrence, so this 
    always describes one concrete occurrence, never a recurrence rule
    i.e. each occurrence is exported independently."""

    end_at = event.end_at or (event.start_at + _DEFAULT_DURATION)

    location = event.location
    if event.meeting_link:
        location = (
            f"{location} ({event.meeting_link})"
            if location
            else event.meeting_link
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Residencial La Antigua//Calendario//ES",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:event-{event.pk}@arbolesdelaantigua.org",
        f"DTSTAMP:{_format_datetime(timezone.now())}",
        f"DTSTART:{_format_datetime(event.start_at)}",
        f"DTEND:{_format_datetime(end_at)}",
        f"SUMMARY:{_escape_text(event.title)}",
    ]
    if event.description:
        lines.append(f"DESCRIPTION:{_escape_text(event.description)}")
    if location:
        lines.append(f"LOCATION:{_escape_text(location)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]

    return "\r\n".join(lines) + "\r\n"
