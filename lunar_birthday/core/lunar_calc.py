"""农历/公历推算：月小兜底、闰月校验、事件展开。"""

import datetime

from lunar_python import Lunar, LunarYear, Solar
from lunar_python.util import LunarUtil

from ..constants import LUNAR_MAX_YEAR, LUNAR_MIN_YEAR
from .models import DateInputError, parse_lunar_text, parse_solar_text, resolve_solar_date

AGE_NONE = "none"
AGE_ZODIAC = "zodiac"
AGE_VIRTUAL = "virtual"
AGE_MODES = (AGE_NONE, AGE_ZODIAC, AGE_VIRTUAL)


def resolve_lunar(year, month, day, leap=False):
    """把农历日期解析为 Lunar 对象，月小（无三十）时自动退到月末。

    返回 (Lunar 对象, 补偿说明)。补偿说明为空表示日期精确命中。
    """
    if leap:
        try:
            actual_leap = LunarYear.fromYear(year).getLeapMonth()
        except Exception as exc:  # 库内部数据缺失时才可能触发
            raise DateInputError(f"农历 {year} 年数据不可用") from exc
        if actual_leap != month:
            raise DateInputError(f"{year} 年没有闰{month}月")

    lunar_month = -month if leap else month
    # 仅对「当月天数不足」这一种可预期情况逐日回退，其余异常继续向外抛出
    for candidate in range(day, 0, -1):
        try:
            lunar = Lunar.fromYmd(year, lunar_month, candidate)
        except Exception:
            continue
        if candidate == day:
            return lunar, ""
        return lunar, f"{LunarUtil.DAY[day]}不存在，按{LunarUtil.DAY[candidate]}处理"
    raise DateInputError(f"无法解析农历 {year}-{month}-{day}")


def lunar_display(lunar):
    """传统农历展示文本，如 1992壬申年九月廿八。"""
    return (
        f"{lunar.getYear()}{lunar.getYearInGanZhi()}年"
        f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    )


def normalise_age_mode(value):
    """兼容旧版布尔开关，统一为 none/zodiac/virtual。"""
    if isinstance(value, bool):
        return AGE_ZODIAC if value else AGE_NONE
    return value if value in AGE_MODES else AGE_NONE


def _lunar_year_of(date):
    return Solar.fromYmd(date.year, date.month, date.day).getLunar().getYear()


def expand_events(entries, start_year_mode, age_mode, options=None, progress=None, now=None):
    """把条目展开为事件列表，返回 (事件列表, 统计信息)。

    age_mode 支持 none（不显示年龄）、zodiac（周岁）、virtual（虚岁），
    同时兼容旧版布尔值。options 支持 skip_past（跳过今天之前的事件）。
    progress(done, total) 用于汇报进度，可在工作线程中调用。
    """
    options = options or {}
    skip_past = options.get("skip_past", False)
    age_mode = normalise_age_mode(age_mode)
    now = now or datetime.datetime.now()
    today = now.date()
    current_year = now.year

    events = []
    stats = {"events": 0, "people": 0, "skipped": 0, "past": 0, "fallback": 0, "notes": []}
    total = len(entries)

    for index, item in enumerate(entries):
        name = item["name"]
        calendar = "solar" if item.get("calendar") == "solar" else "lunar"
        calendar_label = "公历" if calendar == "solar" else "农历"

        if calendar == "solar":
            try:
                birth_date = parse_solar_text(item.get("solar", ""))
            except DateInputError as exc:
                stats["notes"].append(f"{name}：{exc}")
                if progress:
                    progress(index + 1, total)
                continue
            birth_year = birth_date.year
            birth_lunar_year = _lunar_year_of(birth_date)
        else:
            try:
                birth_year, month, day, leap = parse_lunar_text(item["lunar"])
                if item.get("lunar_is_leap"):
                    leap = True
            except DateInputError as exc:
                stats["notes"].append(f"{name}：{exc}")
                if progress:
                    progress(index + 1, total)
                continue
            birth_lunar_year = birth_year

        calc_start_year = current_year if start_year_mode == "今年" else birth_year
        produced = 0

        for offset in range(item["years"]):
            target_year = calc_start_year + offset
            if target_year > LUNAR_MAX_YEAR:
                stats["notes"].append(
                    f"{name}：{target_year} 年超出农历可靠区间，已停止推算"
                )
                break
            if target_year < LUNAR_MIN_YEAR:
                stats["skipped"] += 1
                continue

            if calendar == "solar":
                try:
                    solar_date, fallback_note = resolve_solar_date(
                        target_year, birth_date.month, birth_date.day
                    )
                except DateInputError as exc:
                    stats["skipped"] += 1
                    stats["notes"].append(f"{name} {target_year} 年：{exc}")
                    continue
                description = (
                    f"公历 {birth_date.month} 月 {birth_date.day} 日（{target_year} 年）"
                )
            else:
                try:
                    lunar, fallback_note = resolve_lunar(target_year, month, day, leap)
                except DateInputError as exc:
                    stats["skipped"] += 1
                    stats["notes"].append(f"{name} {target_year} 年：{exc}")
                    continue
                solar = lunar.getSolar()
                solar_date = datetime.date(solar.getYear(), solar.getMonth(), solar.getDay())
                description = (
                    f"农历{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
                    f"（{solar.getYear()} 年 {solar.getMonth()} 月 {solar.getDay()} 日）"
                )

            if skip_past and solar_date < today:
                stats["past"] += 1
                continue

            if fallback_note:
                description += f"｜{fallback_note}"
                stats["fallback"] += 1

            if age_mode == AGE_VIRTUAL:
                virtual_age = max(1, _lunar_year_of(solar_date) - birth_lunar_year + 1)
                summary = f"{name}的 {virtual_age} 虚岁{calendar_label}生日"
            elif age_mode == AGE_ZODIAC:
                age = target_year - birth_year
                if age > 0:
                    summary = f"{name}的 {age} 岁{calendar_label}生日"
                else:
                    summary = f"{name}的出生{calendar_label}日"
            else:
                summary = f"{name}的{calendar_label}生日"

            events.append(
                {
                    "person_id": item["id"],
                    "person": name,
                    "target_year": target_year,
                    "date": solar_date,
                    "summary": summary,
                    "description": description,
                    "remind_days": item["remind_days"],
                    "fallback": fallback_note,
                    "calendar": calendar,
                    "category": str(item.get("category", "")).strip(),
                }
            )
            produced += 1

        stats["events"] += produced
        if produced:
            stats["people"] += 1
        if progress:
            progress(index + 1, total)

    return events, stats
