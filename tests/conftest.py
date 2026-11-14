"""No test reads the broker's calendar. The time gate asks it for the week's expiry and its close
(STRATEGY.md rule 6, 14 Nov 2026); here every weekday trades and closes at 16:00 New York.
tests/test_expiry.py sets the real holidays and half-days of this winter."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from desk import broker

NY = ZoneInfo("America/New_York")


def plain_weeks(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append((d, datetime(d.year, d.month, d.day, 16, tzinfo=NY).astimezone(timezone.utc)))
        d += timedelta(days=1)
    return out


@pytest.fixture(autouse=True)
def _no_broker_calendar(monkeypatch):
    monkeypatch.setattr(broker, "trading_days", plain_weeks)
