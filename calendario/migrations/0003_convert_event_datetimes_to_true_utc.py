import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

# Kept self-contained (not imported from calendario.timezones) so this
# migration keeps working from a clean database even if that module is
# later refactored or removed. Every Event row saved before this migration
# has its start_at/end_at stored as Costa Rica wall-clock numbers labeled
# UTC, not genuine UTC.
RESIDENT_TZ = ZoneInfo("America/Costa_Rica")


def _to_true_utc(value):
    return value.replace(tzinfo=RESIDENT_TZ).astimezone(datetime.UTC)


def _to_local_wall_clock(value):
    return value.astimezone(RESIDENT_TZ).replace(tzinfo=datetime.UTC)


def convert_to_true_utc(apps, schema_editor):
    Event = apps.get_model("calendario", "Event")
    for event in Event.objects.all():
        event.start_at = _to_true_utc(event.start_at)
        if event.end_at:
            event.end_at = _to_true_utc(event.end_at)
        event.save(update_fields=["start_at", "end_at"])


def revert_to_local_labeled_utc(apps, schema_editor):
    Event = apps.get_model("calendario", "Event")
    for event in Event.objects.all():
        event.start_at = _to_local_wall_clock(event.start_at)
        if event.end_at:
            event.end_at = _to_local_wall_clock(event.end_at)
        event.save(update_fields=["start_at", "end_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("calendario", "0002_event_meeting_link"),
    ]

    operations = [
        migrations.RunPython(convert_to_true_utc, revert_to_local_labeled_utc),
    ]
