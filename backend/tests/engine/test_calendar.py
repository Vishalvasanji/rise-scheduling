from datetime import date

from app.engine import calendar

MON = date(2026, 6, 22)  # a Monday
FRI = date(2026, 6, 26)
SAT = date(2026, 6, 27)
NEXT_MON = date(2026, 6, 29)


def test_is_working_day():
    assert calendar.is_working_day(MON)
    assert calendar.is_working_day(FRI)
    assert not calendar.is_working_day(SAT)
    assert not calendar.is_working_day(date(2026, 6, 28))  # Sunday


def test_friday_plus_one_is_monday():
    assert calendar.add_working_days(FRI, 1) == NEXT_MON


def test_monday_minus_one_is_previous_friday():
    assert calendar.add_working_days(MON, -1) == date(2026, 6, 19)  # prior Friday


def test_add_zero_snaps_to_working_day():
    assert calendar.add_working_days(SAT, 0) == NEXT_MON  # forward snap
    assert calendar.add_working_days(MON, 0) == MON


def test_add_five_working_days_skips_weekend():
    # Mon + 5 working days -> next Monday (skips Sat/Sun)
    assert calendar.add_working_days(MON, 5) == NEXT_MON


def test_working_days_between_signed():
    assert calendar.working_days_between(MON, FRI) == 4
    assert calendar.working_days_between(FRI, MON) == -4
    assert calendar.working_days_between(MON, MON) == 0
    assert calendar.working_days_between(FRI, NEXT_MON) == 1  # weekend skipped


def test_index_roundtrip():
    for n in (-10, -1, 0, 1, 7, 40, 180):
        assert calendar.date_to_index(calendar.index_to_date(n, MON), MON) == n
