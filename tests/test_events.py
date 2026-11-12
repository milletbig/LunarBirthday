import datetime

import pytest

from lunar_birthday.core.lunar_calc import expand_events

NOW = datetime.datetime(2026, 11, 12, 12, 0, 0)
ENTRY = {
    "id": "p1",
    "name": "王潇",
    "lunar": "1992-09-28",
    "lunar_is_leap": False,
    "years": 30,
    "remind_days": 7,
}


def test_expands_requested_number_of_years():
    events, stats = expand_events([ENTRY], "今年", False, now=NOW)
    assert len(events) == 30
    assert stats["events"] == 30
    assert stats["people"] == 1
    assert events[0]["target_year"] == 2026


def test_skip_past_removes_earlier_dates():
    entry = dict(ENTRY, lunar="1992-01-01", years=4)
    all_events, all_stats = expand_events(
        [entry], "今年", False, options={"skip_past": False}, now=NOW
    )
    new_events, new_stats = expand_events(
        [entry], "今年", False, options={"skip_past": True}, now=NOW
    )
    assert new_stats["past"] >= 1
    assert len(new_events) < len(all_events)
    assert all(event["date"] >= NOW.date() for event in new_events)
    assert all_stats["past"] == 0


def test_show_age_in_summary():
    events, _stats = expand_events([dict(ENTRY, years=1)], "今年", True, now=NOW)
    assert events[0]["target_year"] == 2026
    assert events[0]["summary"] == "王潇的 34 岁农历生日"


def test_leap_month_entries_skip_non_leap_years():
    entry = dict(ENTRY, lunar="2023-02-04", lunar_is_leap=True, years=4)
    events, stats = expand_events([entry], "出生年", False, now=NOW)
    assert stats["skipped"] >= 1
    assert events
    assert all("闰" in event["description"] for event in events)


def test_invalid_entry_is_reported_without_crash():
    events, stats = expand_events([dict(ENTRY, lunar="bad")], "今年", False, now=NOW)
    assert events == []
    assert stats["events"] == 0
    assert "王潇" in stats["notes"][0]


def test_stops_at_lunar_max_year():
    entry = dict(ENTRY, lunar="2000-01-01", years=200)
    events, stats = expand_events([entry], "出生年", False, now=NOW)
    assert events[-1]["target_year"] == 2100
    assert any("超出农历可靠区间" in note for note in stats["notes"])


def test_progress_reported_per_entry():
    calls = []
    entries = [ENTRY, dict(ENTRY, id="b"), dict(ENTRY, id="c")]
    expand_events(entries, "今年", False, progress=lambda done, total: calls.append((done, total)), now=NOW)
    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_month_short_fallback_is_counted():
    entry = dict(ENTRY, lunar="2024-01-30", years=1)
    events, stats = expand_events([entry], "出生年", False, now=NOW)
    assert stats["fallback"] == 1
    assert len(events) == 1
    assert "不存在" in events[0]["description"]


@pytest.mark.parametrize("mode,expected_year", [("今年", NOW.year), ("出生年", 1992)])
def test_start_year_modes(mode, expected_year):
    events, _stats = expand_events([dict(ENTRY, years=1)], mode, False, now=NOW)
    assert events[0]["target_year"] == expected_year
