"""日期文本的解析与格式化。"""

import datetime
import re

from ..constants import LUNAR_MAX_YEAR, LUNAR_MIN_YEAR

# 支持 1992-09-28 / 1992/9/28 / 2023-闰02-04 / 兼容旧版损坏数据 2023--2-04
_LUNAR_RE = re.compile(
    r"^(\d{4})\s*[-/]\s*(?:(闰)|(-))?\s*(\d{1,2})\s*[-/]\s*(\d{1,2})$"
)
_SOLAR_RE = re.compile(r"^(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})$")


class DateInputError(ValueError):
    """用户输入的日期文本不合法。"""


def parse_lunar_text(text):
    """解析农历文本，返回 (年, 月, 日, 是否闰月)。月始终为正数。"""
    raw = (text or "").strip()
    if not raw:
        raise DateInputError("农历生日为空")
    match = _LUNAR_RE.match(raw)
    if not match:
        raise DateInputError("农历格式应为 YYYY-MM-DD 或 YYYY-闰MM-DD")
    year = int(match.group(1))
    leap = bool(match.group(2) or match.group(3))
    month = int(match.group(4))
    day = int(match.group(5))
    if not LUNAR_MIN_YEAR <= year <= LUNAR_MAX_YEAR:
        raise DateInputError(f"农历年份需在 {LUNAR_MIN_YEAR}-{LUNAR_MAX_YEAR} 之间")
    if not 1 <= month <= 12:
        raise DateInputError("农历月份需在 1-12 之间")
    if not 1 <= day <= 30:
        raise DateInputError("农历日期需在 1-30 之间")
    return year, month, day, leap


def format_lunar_text(year, month, day, leap=False):
    """把农历日期格式化为界面展示文本，闰月用「闰」标记。"""
    return f"{year:04d}-{'闰' if leap else ''}{month:02d}-{day:02d}"


def parse_solar_text(text):
    """解析公历文本，返回 datetime.date。"""
    raw = (text or "").strip()
    if not raw:
        raise DateInputError("公历生日为空")
    match = _SOLAR_RE.match(raw)
    if not match:
        raise DateInputError("公历格式应为 YYYY-MM-DD")
    year, month, day = (int(match.group(i)) for i in (1, 2, 3))
    if not LUNAR_MIN_YEAR <= year <= LUNAR_MAX_YEAR:
        raise DateInputError(f"公历年份需在 {LUNAR_MIN_YEAR}-{LUNAR_MAX_YEAR} 之间")
    try:
        return datetime.date(year, month, day)
    except ValueError as exc:
        raise DateInputError(f"公历日期不存在：{year}-{month:02d}-{day:02d}") from exc


def resolve_solar_date(year, month, day):
    """按公历月日取指定年份的日期，2 月 29 日在平年退到 2 月 28 日。

    返回 (datetime.date, 补偿说明)。补偿说明为空表示日期精确命中。
    """
    try:
        return datetime.date(year, month, day), ""
    except ValueError as exc:
        if month == 2 and day == 29:
            return datetime.date(year, 2, 28), "2月29日不存在，按2月28日处理"
        raise DateInputError(f"公历日期不存在：{year}-{month:02d}-{day:02d}") from exc
