import datetime

import pytest

from lunar_birthday.core.lunar_calc import lunar_display, resolve_lunar
from lunar_birthday.core.models import (
    DateInputError,
    format_lunar_text,
    parse_lunar_text,
    parse_solar_text,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1992-09-28", (1992, 9, 28, False)),
        (" 1992/9/8 ", (1992, 9, 8, False)),
        ("2023-闰02-04", (2023, 2, 4, True)),
        ("2023--2-04", (2023, 2, 4, True)),
    ],
)
def test_parse_lunar_valid(text, expected):
    assert parse_lunar_text(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "abc", "2020-13-01", "2020-02-31", "1899-01-01", "2101-01-01"],
)
def test_parse_lunar_invalid(text):
    with pytest.raises(DateInputError):
        parse_lunar_text(text)


def test_format_lunar_text():
    assert format_lunar_text(2023, 2, 4, True) == "2023-闰02-04"
    assert format_lunar_text(1992, 9, 28) == "1992-09-28"


def test_parse_solar_text():
    assert parse_solar_text("1992/10/23") == datetime.date(1992, 10, 23)
    with pytest.raises(DateInputError):
        parse_solar_text("1992-02-30")
    with pytest.raises(DateInputError):
        parse_solar_text("2101-01-01")


def test_small_month_falls_back_to_last_day():
    lunar, note = resolve_lunar(2024, 1, 30)
    assert lunar.getDay() == 29
    assert "三十不存在" in note


def test_small_month_exact_hit_has_no_note():
    assert resolve_lunar(2023, 2, 30)[1] == ""


def test_leap_month_resolution():
    lunar, note = resolve_lunar(2023, 2, 15, True)
    assert lunar.toString().startswith("二〇二三年闰二月")
    assert note == ""


def test_leap_month_mismatch_rejected():
    with pytest.raises(DateInputError):
        resolve_lunar(2024, 2, 15, True)
    with pytest.raises(DateInputError):
        resolve_lunar(2023, 3, 15, True)


def test_lunar_new_year_eve_crosses_solar_year():
    lunar, _note = resolve_lunar(1963, 11, 17)
    assert lunar.getSolar().toYmd() == "1964-01-01"


def test_lunar_display():
    lunar, _note = resolve_lunar(1992, 9, 28)
    assert lunar_display(lunar) == "1992壬申年九月廿八"


def test_lunar_thirty_never_missing_in_100_years():
    missing = []
    compensated = 0
    for year in range(2026, 2126):
        try:
            _lunar, note = resolve_lunar(year, 12, 30)
        except DateInputError:
            missing.append(year)
            continue
        if note:
            compensated += 1
    assert missing == []
    assert 30 <= compensated <= 60
