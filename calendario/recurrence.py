import calendar
import datetime

MAX_OCCURRENCES = 104


class TooManyOccurrences(Exception):
    pass


def generate_occurrence_starts(
    start_at, frequency, end_date=None, occurrence_count=None
):
    """Returns the list of occurrence start datetimes for a recurring
    series, beginning with ``start_at`` (inclusive). Exactly one of
    ``end_date``/``occurrence_count`` should be given. Raises
    TooManyOccurrences if the series would exceed MAX_OCCURRENCES before
    the end condition is reached.

    Each occurrence is computed from the original ``start_at`` plus its
    index (not from the previous occurrence) so that day-of-month
    clamping in one occurrence (e.g. Jan 31 -> Feb 28) doesn't drift
    into the following ones (Mar should stay the 31st, not become the
    28th just because February was clamped)."""
    occurrences = []
    index = 0
    while True:
        if occurrence_count is not None and index >= occurrence_count:
            return occurrences
        if index >= MAX_OCCURRENCES:
            raise TooManyOccurrences

        candidate = _shift(start_at, frequency, index)
        if end_date is not None and candidate.date() > end_date:
            return occurrences

        occurrences.append(candidate)
        index += 1


def _shift(start_at, frequency, index):
    # `index` counts occurrences from start_at, not from the previous one
    # - always shifting the original date is what keeps a clamped month 
    # from dragging every later occurrence down with it. `else` stands in
    # for "monthly": RecurrenceForm's frequency field only offers 
    # "weekly"/"monthly". Update this function if that ever changes.
    if frequency == "weekly":
        return start_at + datetime.timedelta(weeks=index)
    return _add_months(start_at, index)


def _add_months(dt, months):
    # datetime.timedelta has no month unit (months vary in length), so the
    # month arithmetic is done by hand: shift the zero-based month index by
    # `months`, let it carry into the year via floor division, then clamp
    # the day to the target month's actual length (e.g. Jan 31 + 1 month ->
    # Feb 28/29, never Mar 3).
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)
