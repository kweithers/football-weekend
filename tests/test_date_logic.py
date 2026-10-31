from datetime import datetime, timezone
from unittest.mock import patch


def _freeze_tools(dt: datetime):
    """Context manager: freeze tools.datetime.now to return dt."""
    return patch("tools.datetime", **{"now.return_value": dt})


def _freeze_generate(dt: datetime):
    """Context manager: freeze generate_weekly.datetime.now to return dt."""
    return patch("generate_weekly.datetime", **{"now.return_value": dt})


class TestGetWeekendRange:
    def test_on_tuesday(self):
        # Tuesday 2026-10-27 → same day through Monday 2026-11-02
        frozen = datetime(2026, 10, 27, 0, 0, 0, tzinfo=timezone.utc)
        with _freeze_tools(frozen):
            from tools import _get_weekend_range
            date_from, date_to = _get_weekend_range()
        assert date_from == "2026-10-27"
        assert date_to == "2026-11-02"

    def test_on_friday(self):
        # Friday 2026-10-30 → previous Tuesday 2026-10-27
        frozen = datetime(2026, 10, 30, 0, 0, 0, tzinfo=timezone.utc)
        with _freeze_tools(frozen):
            from tools import _get_weekend_range
            date_from, date_to = _get_weekend_range()
        assert date_from == "2026-10-27"
        assert date_to == "2026-11-02"

    def test_on_monday(self):
        # Monday 2026-11-02 → Tuesday 6 days earlier, today is the last day
        frozen = datetime(2026, 11, 2, 0, 0, 0, tzinfo=timezone.utc)
        with _freeze_tools(frozen):
            from tools import _get_weekend_range
            date_from, date_to = _get_weekend_range()
        assert date_from == "2026-10-27"
        assert date_to == "2026-11-02"

    def test_on_wednesday(self):
        # Wednesday 2026-10-28 → Tuesday 2026-10-27
        frozen = datetime(2026, 10, 28, 0, 0, 0, tzinfo=timezone.utc)
        with _freeze_tools(frozen):
            from tools import _get_weekend_range
            date_from, date_to = _get_weekend_range()
        assert date_from == "2026-10-27"
        assert date_to == "2026-11-02"

    def test_range_is_always_7_days(self):
        from datetime import date, timedelta as td
        base = datetime(2026, 10, 27, 0, 0, 0, tzinfo=timezone.utc)
        for day_offset in range(7):
            frozen = base + td(days=day_offset)
            with _freeze_tools(frozen):
                from tools import _get_weekend_range
                date_from, date_to = _get_weekend_range()
            delta = date.fromisoformat(date_to) - date.fromisoformat(date_from)
            assert delta.days == 6, f"Expected 6-day span, got {delta.days} on offset {day_offset}"


class TestNextFriday:
    def test_on_friday_returns_same_day(self):
        frozen = datetime(2026, 10, 30, 10, 0, 0, tzinfo=timezone.utc)  # Friday
        with _freeze_generate(frozen):
            from generate_weekly import next_friday
            result = next_friday()
        assert result == "2026-10-30"

    def test_on_monday_returns_next_friday(self):
        frozen = datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        with _freeze_generate(frozen):
            from generate_weekly import next_friday
            result = next_friday()
        assert result == "2026-10-30"

    def test_on_saturday_returns_next_friday(self):
        frozen = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)  # Saturday
        with _freeze_generate(frozen):
            from generate_weekly import next_friday
            result = next_friday()
        assert result == "2026-11-06"

    def test_on_tuesday_returns_friday_same_week(self):
        frozen = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)  # Tuesday
        with _freeze_generate(frozen):
            from generate_weekly import next_friday
            result = next_friday()
        assert result == "2026-10-30"
