import datetime

import pytest

from lunar_birthday import __version__
from lunar_birthday.constants import NO_REMIND
from lunar_birthday.core.ics_builder import (
    build_events,
    format_trigger,
    ics_escape,
    ics_fold,
    render_ics,
    write_ics,
)
from lunar_birthday.core.lunar_calc import expand_events

NOW = datetime.datetime(2026, 11, 12, 12, 0, 0)
ENTRY = {
    "id": "p1",
    "name": "王潇",
    "lunar": "1992-09-28",
    "lunar_is_leap": False,
    "years": 5,
    "remind_days": 7,
}


def test_ics_escape_reserved_characters():
    assert ics_escape("a,b;c\\d") == "a\\,b\\;c\\\\d"
    assert ics_escape("a\nb") == "a\\nb"
    assert ics_escape("a\r\nb") == "a\\nb"


def test_ics_fold_short_line_untouched():
    assert ics_fold("VERSION:2.0") == "VERSION:2.0"


def test_ics_fold_respects_byte_limit_and_utf8_boundaries():
    original = "DESCRIPTION:" + "农历生日" * 30
    folded = ics_fold(original)
    for physical in folded.split("\r\n"):
        assert len(physical.encode("utf-8")) <= 75
    assert folded.split("\r\n")[0].startswith("DESCRIPTION:")
    assert all(line.startswith(" ") for line in folded.split("\r\n")[1:])
    assert folded.replace("\r\n ", "") == original


def test_write_ics_uses_pure_crlf(tmp_path):
    path = tmp_path / "out.ics"
    write_ics(str(path), ["BEGIN:VCALENDAR", "SUMMARY:" + "生日" * 40, "END:VCALENDAR"])
    data = path.read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")
    assert data.endswith(b"\r\n")
    text = data.decode("utf-8")
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")


@pytest.mark.parametrize(
    "days,hour,expected",
    [
        (7, 9, "-P6D15H"),
        (1, 9, "-PT15H"),
        (0, 9, "PT9H"),
        (0, 0, "PT0S"),
        (6, 0, "-P6D"),
    ],
)
def test_format_trigger(days, hour, expected):
    assert format_trigger(days, hour) == expected


def test_uids_are_deterministic():
    first, _ = build_events([ENTRY], "今年", False, now=NOW)
    second, _ = build_events([ENTRY], "今年", False, now=NOW)
    uids_first = [line for line in first if line.startswith("UID:")]
    uids_second = [line for line in second if line.startswith("UID:")]
    assert uids_first == uids_second
    assert uids_first[0] == "UID:p1-2026@lunar-birthday"
    assert len(set(uids_first)) == len(uids_first)


def test_render_ics_escapes_summary():
    lines, _stats = build_events([dict(ENTRY, name="张,三", years=1)], "今年", False, now=NOW)
    assert any(line == "SUMMARY:张\\,三的农历生日" for line in lines)


def test_remind_on_day_adds_second_alarm():
    events, _stats = expand_events([ENTRY], "今年", False, now=NOW)
    with_day = render_ics(events, remind_hour=9, remind_on_day=True, now=NOW)
    without_day = render_ics(events, remind_hour=9, remind_on_day=False, now=NOW)
    assert with_day.count("BEGIN:VALARM") == len(events) * 2
    assert without_day.count("BEGIN:VALARM") == len(events)
    assert any("今天就是" in line for line in with_day)


def test_zero_day_does_not_duplicate_alarm():
    events, _stats = expand_events([dict(ENTRY, remind_days=0)], "今年", False, now=NOW)
    lines = render_ics(events, remind_hour=9, remind_on_day=True, now=NOW)
    assert lines.count("BEGIN:VALARM") == len(events)
    assert "TRIGGER:PT9H" in lines


def test_no_remind_keeps_events_without_alarm():
    events, _stats = expand_events([dict(ENTRY, remind_days=NO_REMIND)], "今年", False, now=NOW)
    lines = render_ics(events, now=NOW)
    assert lines.count("BEGIN:VEVENT") == len(events)
    assert "BEGIN:VALARM" not in lines


def test_prodid_uses_single_version_source():
    lines, _stats = build_events([ENTRY], "今年", False, now=NOW)
    assert f"PRODID:-//Lunar Birthday v{__version__}//CN" in lines
