import datetime

from lunar_birthday.constants import NO_REMIND
from lunar_birthday.core.config_store import normalize_entry
from lunar_birthday.core.ics_builder import build_events, render_ics
from lunar_birthday.core.lunar_calc import (
    AGE_NONE,
    AGE_VIRTUAL,
    AGE_ZODIAC,
    expand_events,
    normalise_age_mode,
)
from lunar_birthday.core.models import resolve_solar_date

NOW = datetime.datetime(2026, 11, 12, 12, 0, 0)

LUNAR_ENTRY = {
    "id": "l1",
    "name": "王潇",
    "lunar": "1992-09-28",
    "calendar": "lunar",
    "years": 1,
    "remind_days": 7,
}
SOLAR_ENTRY = {
    "id": "s1",
    "name": "李四",
    "solar": "2000-02-29",
    "calendar": "solar",
    "years": 5,
    "remind_days": 7,
}


def test_solar_events_follow_solar_month_day():
    events, stats = expand_events([SOLAR_ENTRY], "出生年", AGE_NONE, now=NOW)
    assert [event["date"] for event in events][:2] == [
        datetime.date(2000, 2, 29),
        datetime.date(2001, 2, 28),
    ]
    assert stats["fallback"] == 3
    assert "公历 2 月 29 日" in events[1]["description"]
    assert events[1]["calendar"] == "solar"


def test_solar_entry_summary_uses_solar_label():
    events, _stats = expand_events([SOLAR_ENTRY], "今年", AGE_ZODIAC, now=NOW)
    assert events[0]["summary"] == "李四的 26 岁公历生日"


def test_solar_events_respect_skip_past():
    entry = dict(SOLAR_ENTRY, solar="2000-01-01", years=4)
    events, stats = expand_events(
        [entry], "今年", AGE_NONE, options={"skip_past": True}, now=NOW
    )
    assert stats["past"] >= 1
    assert all(event["date"] >= NOW.date() for event in events)


def test_resolve_solar_date_leap_day():
    assert resolve_solar_date(2000, 2, 29) == (datetime.date(2000, 2, 29), "")
    assert resolve_solar_date(2026, 2, 29) == (
        datetime.date(2026, 2, 28),
        "2月29日不存在，按2月28日处理",
    )


def test_virtual_age_is_one_year_more_than_zodiac():
    zodiac, _ = expand_events([LUNAR_ENTRY], "今年", AGE_ZODIAC, now=NOW)
    virtual, _ = expand_events([LUNAR_ENTRY], "今年", AGE_VIRTUAL, now=NOW)
    assert zodiac[0]["summary"] == "王潇的 34 岁农历生日"
    assert virtual[0]["summary"] == "王潇的 35 虚岁农历生日"


def test_age_mode_accepts_legacy_bool():
    assert normalise_age_mode(True) == AGE_ZODIAC
    assert normalise_age_mode(False) == AGE_NONE
    legacy, _ = expand_events([LUNAR_ENTRY], "今年", True, now=NOW)
    assert legacy[0]["summary"] == "王潇的 34 岁农历生日"
    plain, _ = expand_events([LUNAR_ENTRY], "今年", False, now=NOW)
    assert plain[0]["summary"] == "王潇的农历生日"


def test_virtual_age_for_solar_entry():
    entry = dict(SOLAR_ENTRY, solar="2000-02-29", years=1)
    events, _stats = expand_events([entry], "出生年", AGE_VIRTUAL, now=NOW)
    assert events[0]["summary"] == "李四的 1 虚岁公历生日"


def test_normalize_entry_reads_calendar_and_category():
    entry = normalize_entry(
        {"name": "李四", "calendar": "solar", "solar": "2000-02-29", "category": "家人"},
        30,
        7,
    )
    assert entry["calendar"] == "solar"
    assert entry["solar"] == "2000-02-29"
    assert entry["category"] == "家人"
    assert entry["lunar"] == ""
    legacy = normalize_entry({"lunar": "1992-09-28"}, 30, 7)
    assert legacy["calendar"] == "lunar"
    assert legacy["category"] == ""


def test_ics_categories_include_label():
    entry = dict(LUNAR_ENTRY, category="家人")
    lines, _stats = build_events([entry], "今年", AGE_NONE, now=NOW)
    assert "CATEGORIES:生日,家人" in lines


def test_ics_categories_escape_comma():
    entry = dict(LUNAR_ENTRY, category="同事,好友")
    lines, _stats = build_events([entry], "今年", AGE_NONE, now=NOW)
    assert "CATEGORIES:生日,同事\\,好友" in lines


def test_ics_without_category_is_unchanged():
    lines, _stats = build_events([LUNAR_ENTRY], "今年", AGE_NONE, now=NOW)
    assert "CATEGORIES:生日" in lines


def test_no_remind_still_works_for_solar_entry():
    entry = dict(SOLAR_ENTRY, remind_days=NO_REMIND, years=1)
    events, _stats = expand_events([entry], "出生年", AGE_NONE, now=NOW)
    lines = render_ics(events, now=NOW)
    assert "BEGIN:VALARM" not in lines
    assert lines.count("BEGIN:VEVENT") == 1
