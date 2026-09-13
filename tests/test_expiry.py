"""The rolling weekly expiry that replaced the fixed contest date.

The contest's `CONTEST_END = 4 Sep 2026` went negative once the week was over,
and the time gate then read every session as "inside the final three hours" —
so the desk ran on schedule and traded nothing for nine days. These pin the
replacement (STRATEGY.md "Post-contest operation", 13 Sep 2026).
"""
from datetime import date, datetime, timezone

from desk.run import minutes_to_expiry, next_weekly_friday


def test_midweek_points_at_this_week_s_friday():
    assert next_weekly_friday(date(2026, 9, 16)) == date(2026, 9, 18)   # Wed -> Fri
    assert next_weekly_friday(date(2026, 9, 14)) == date(2026, 9, 18)   # Mon -> Fri


def test_friday_still_trades_its_own_expiry():
    # a Friday-morning session writes that day's weekly, not next week's
    assert next_weekly_friday(date(2026, 9, 18)) == date(2026, 9, 18)


def test_the_weekend_rolls_forward():
    assert next_weekly_friday(date(2026, 9, 19)) == date(2026, 9, 25)   # Sat
    assert next_weekly_friday(date(2026, 9, 20)) == date(2026, 9, 25)   # Sun


def test_minutes_to_expiry_is_positive_all_week():
    """The defect in one line: this must never go negative again, or the time
    gate silently vetoes every position forever."""
    for day in range(14, 28):                       # a full fortnight, Mon-Sun
        for hour in (0, 9, 14, 19, 21, 23):
            now = datetime(2026, 9, day, hour, 0, tzinfo=timezone.utc)
            assert minutes_to_expiry(now) > 0, f"{now} produced a non-positive countdown"


def test_after_fridays_bell_it_points_at_next_week():
    after = datetime(2026, 9, 18, 20, 30, tzinfo=timezone.utc)   # Fri, past the 20:00 close
    mins = minutes_to_expiry(after)
    assert 6 * 24 * 60 < mins < 8 * 24 * 60, mins


def test_the_time_gate_only_bites_near_the_expiry():
    from desk import gates
    # Friday 17:30 UTC — two and a half hours to the close
    late = minutes_to_expiry(datetime(2026, 9, 18, 17, 30, tzinfo=timezone.utc))
    assert late < gates.FINAL_QUIET_MINUTES
    # Thursday — plenty of room
    early = minutes_to_expiry(datetime(2026, 9, 17, 14, 0, tzinfo=timezone.utc))
    assert early > gates.FINAL_QUIET_MINUTES
