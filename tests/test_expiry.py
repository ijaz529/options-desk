"""The rolling weekly expiry that replaced the fixed contest date.

The contest's `CONTEST_END = 4 Sep 2026` went negative once the week was over,
and the time gate then read every session as "inside the final three hours" —
so the desk ran on schedule and traded nothing for nine days. These pin the
replacement (STRATEGY.md "Post-contest operation", 13 Sep 2026).

The expiry's day and close come from the broker's calendar since 14 Nov 2026 (STRATEGY.md
rule 6): the Thursday when the Friday is a holiday, the early close on a half-day, and the
close an hour later in UTC in winter. The calendar here is a stand-in with the real dates.
"""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from alpaca.trading.models import Calendar

from desk import broker, gates, log, run
from desk.broker import PutQuote
from desk.run import minutes_to_expiry, next_weekly_friday, weekly_expiry

NY = ZoneInfo("America/New_York")
HOLIDAYS = {date(2026, 11, 26), date(2026, 12, 25), date(2027, 1, 1)}
HALF_DAYS = {date(2026, 11, 27), date(2026, 12, 24)}      # the market closes at 13:00 New York


def _calendar(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in HOLIDAYS:
            hh = 13 if d in HALF_DAYS else 16
            out.append((d, datetime(d.year, d.month, d.day, hh, tzinfo=NY).astimezone(timezone.utc)))
        d += timedelta(days=1)
    return out


@pytest.fixture(autouse=True)
def _broker_calendar(monkeypatch):
    monkeypatch.setattr(broker, "trading_days", _calendar)


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


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


# the broker's calendar (14 Nov 2026)

def test_a_holiday_friday_moves_the_expiry_to_thursday():
    # Christmas Day and New Year's Day fall on Fridays: those weeks' contracts expire on Thursday
    assert weekly_expiry(date(2026, 12, 25)) == (date(2026, 12, 24), _utc(2026, 12, 24, 18, 0))
    assert weekly_expiry(date(2027, 1, 1)) == (date(2026, 12, 31), _utc(2026, 12, 31, 21, 0))


def test_an_ordinary_friday_keeps_its_own_expiry_and_close():
    assert weekly_expiry(date(2026, 9, 18)) == (date(2026, 9, 18), _utc(2026, 9, 18, 20, 0))   # summer
    assert weekly_expiry(date(2026, 11, 20)) == (date(2026, 11, 20), _utc(2026, 11, 20, 21, 0))  # winter


def test_the_time_gate_reads_the_winter_close():
    # Fri 20 Nov 17:30 UTC is three and a half hours before a 21:00 close: still open. The fixed
    # 20:00 close shut the gate here, an hour early.
    assert minutes_to_expiry(_utc(2026, 11, 20, 17, 30)) == 210
    assert minutes_to_expiry(_utc(2026, 11, 20, 18, 30)) < gates.FINAL_QUIET_MINUTES


def test_the_time_gate_reads_a_half_day_close():
    # Fri 27 Nov closes at 18:00 UTC, so the final three hours start at 15:00, not 17:00
    assert minutes_to_expiry(_utc(2026, 11, 27, 15, 30)) == 150
    assert minutes_to_expiry(_utc(2026, 11, 27, 14, 50)) == 190


def test_after_a_holiday_thursday_s_bell_it_points_at_next_week():
    # Thu 24 Dec after its 18:00 close: next week's expiry is Thu 31 Dec, 21:00 UTC
    assert minutes_to_expiry(_utc(2026, 12, 24, 18, 30)) == (7 * 24 + 2.5) * 60
    # and on the holiday itself
    assert minutes_to_expiry(_utc(2026, 12, 25, 15, 0)) == (6 * 24 + 6) * 60


def test_the_broker_s_close_is_read_in_new_york_time(monkeypatch):
    """The broker's calendar gives "13:00" with no zone; it is New York's."""
    raw = [{"date": "2026-11-27", "open": "09:30", "close": "13:00"},
           {"date": "2026-09-18", "open": "09:30", "close": "16:00"}]
    fake = SimpleNamespace(get_calendar=lambda req: [Calendar(**r) for r in raw])
    monkeypatch.undo()                              # the real trading_days, a stand-in client
    monkeypatch.setattr(broker, "trading", lambda: fake)
    assert broker.trading_days(date(2026, 9, 18), date(2026, 11, 27)) == [
        (date(2026, 11, 27), _utc(2026, 11, 27, 18, 0)), (date(2026, 9, 18), _utc(2026, 9, 18, 20, 0))]


def test_the_steward_sells_the_thursday_expiry_in_christmas_week(monkeypatch):
    """Mon 21 Dec 2026: the coming Friday is Christmas Day, so his puts are the 24 Dec ones. Before
    14 Nov he asked for 25 Dec contracts, found none, and wrote 'no put earns its keep' twelve times."""
    rows, sold, asked = [], [], []
    monkeypatch.setattr(run, "UNIVERSE", ["KO"])
    monkeypatch.setattr(run, "_entries_blocked", lambda agent: False)
    monkeypatch.setattr(run, "next_weekly_friday", lambda today=None: date(2026, 12, 25))
    state = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0,
                               sleeve_used={"steward": 0.0, "hunter": 0.0},
                               underlying_notional={}, minutes_to_expiry=4_000.0)
    monkeypatch.setattr(run, "desk_state", lambda expiry=None: (state, {}))
    monkeypatch.setattr(run, "read_positions", lambda: [])
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(log, "rows", lambda *a: [])
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action)))
    monkeypatch.setattr(broker, "earnings_dates", lambda u: [date(2027, 2, 10)])
    put = PutQuote(symbol="KO261224P00066000", underlying="KO", strike=66.0, expiry=date(2026, 12, 24),
                   bid=0.12, ask=0.14, delta=-0.18, spot=70.0)
    monkeypatch.setattr(broker, "weekly_puts", lambda u, e: asked.append(e) or [put])
    monkeypatch.setattr(broker, "sell_put", lambda sym, px: sold.append(sym) or "o-1")
    run.steward_session()
    assert asked == [date(2026, 12, 24)] and sold == ["KO261224P00066000"] and rows[-1] == ("steward", "sell_put")
