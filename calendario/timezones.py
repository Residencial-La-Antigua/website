import datetime
from zoneinfo import ZoneInfo

# The whole community is physically in Costa Rica; there's no per-user
# timezone preference. Fixed UTC-6, no DST, so this is safe to reuse in
# both directions without ever hitting a DST transition.
RESIDENT_TZ = ZoneInfo("America/Costa_Rica")


def to_true_utc(value, tz: datetime.tzinfo = RESIDENT_TZ):
    """Returns the genuine UTC instant. Used at the point a resident-facing 
    value (a submitted event time, or a calendar date-range query param) 
    becomes a database value."""
    return value.replace(tzinfo=tz).astimezone(datetime.UTC)


def to_local_wall_clock(value, tz: datetime.tzinfo = RESIDENT_TZ):
    """Inverse of `to_true_utc`: takes a genuine UTC instant (as stored
    in the database) and returns a value whose wall-clock numbers are
    `tz` local time (FullCalendar has `timeZone: 'UTC'` so it displays 
    whatever wall-clock numbers it's given)."""
    return value.astimezone(tz).replace(tzinfo=datetime.UTC)
