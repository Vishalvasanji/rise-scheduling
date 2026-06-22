"""Working-day calendar utility (Mon-Fri, no holidays for the pilot).

Two layers:

* ``is_working_day`` — the single predicate that decides whether a date counts.
  Adding a holiday calendar in production is a change to *only* this function.
* Arithmetic built on top: add/subtract working days, signed working-day spans,
  and the index<->date mapping used by the CPM index space.

Durations and lags throughout the engine are expressed in working days.
"""

from __future__ import annotations

from datetime import date, timedelta

_WEEKEND = {5, 6}  # date.weekday(): Mon=0 ... Sat=5, Sun=6


def is_working_day(d: date) -> bool:
    """Return True if ``d`` is a working day (production: also check holidays)."""
    return d.weekday() not in _WEEKEND


def next_working_day(d: date) -> date:
    """Return ``d`` if it is a working day, else the next working day."""
    while not is_working_day(d):
        d += timedelta(days=1)
    return d


def prev_working_day(d: date) -> date:
    """Return ``d`` if it is a working day, else the previous working day."""
    while not is_working_day(d):
        d -= timedelta(days=1)
    return d


def add_working_days(start: date, n: int) -> date:
    """Advance ``n`` working days from ``start`` (``start`` itself is day 0).

    ``n`` may be negative. ``start`` is first normalised to a working day in the
    direction of travel so the result is always a working day. With ``n == 0``
    this simply snaps ``start`` onto the nearest working day.
    """
    if n >= 0:
        current = next_working_day(start)
        step = timedelta(days=1)
    else:
        current = prev_working_day(start)
        step = timedelta(days=-1)
        n = -n

    remaining = n
    while remaining > 0:
        current += step
        if is_working_day(current):
            remaining -= 1
    return current


def working_days_between(a: date, b: date) -> int:
    """Signed count of working days in the half-open interval ``[a, b)``.

    Positive when ``b > a``, negative when ``b < a``, zero when they fall on the
    same working day. This is the inverse of :func:`add_working_days`, so
    ``working_days_between(anchor, add_working_days(anchor, n)) == n`` for a
    working-day anchor.
    """
    if a == b:
        return 0
    sign = 1 if b > a else -1
    lo, hi = (a, b) if sign == 1 else (b, a)
    count = 0
    current = lo
    while current < hi:
        if is_working_day(current):
            count += 1
        current += timedelta(days=1)
    return sign * count


def date_to_index(d: date, anchor: date) -> int:
    """Map a calendar date to a working-day index relative to ``anchor``."""
    return working_days_between(anchor, d)


def index_to_date(i: int, anchor: date) -> date:
    """Map a working-day index back to a calendar date relative to ``anchor``."""
    return add_working_days(anchor, i)
