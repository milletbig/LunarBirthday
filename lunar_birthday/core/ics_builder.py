"""ICS（RFC 5545）渲染与写入。"""

import datetime

from .. import __version__
from ..constants import DEFAULT_REMIND_HOUR, NO_REMIND
from .lunar_calc import expand_events


def ics_escape(text):
    """RFC 5545 TEXT 转义。"""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def ics_fold(line, limit=75):
    """按 75 字节折行，多字节字符不截断。"""
    if len(line.encode("utf-8")) <= limit:
        return line
    parts = []
    current = []
    size = 0
    current_limit = limit
    for char in line:
        char_size = len(char.encode("utf-8"))
        if size + char_size > current_limit:
            parts.append("".join(current))
            current = []
            size = 0
            current_limit = limit - 1  # 续行以一个空格开头
        current.append(char)
        size += char_size
    parts.append("".join(current))
    return "\r\n ".join(parts)


def write_ics(path, lines):
    """以纯 CRLF 写入 ICS，避免 Windows 文本模式重复转换。"""
    payload = "".join(ics_fold(line) + "\r\n" for line in lines)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(payload)


def format_trigger(days_before, hour):
    """把「提前 N 天、当天 H 点提醒」换算为 RFC 5545 时长。

    全天事件以当天 00:00 为基准，提前 N 天的 H 点即 -(N*24-H) 小时。
    """
    seconds = int(days_before) * 86400 - int(hour) * 3600
    sign = "-" if seconds > 0 else ""
    seconds = abs(seconds)
    if seconds == 0:
        return "PT0S"
    days, rest = divmod(seconds, 86400)
    hours = rest // 3600
    text = "P" + (f"{days}D" if days else "")
    if hours:
        text += ("" if days else "T") + f"{hours}H"
    return sign + text


def render_ics(events, remind_hour=DEFAULT_REMIND_HOUR, remind_on_day=False, now=None):
    """把事件列表渲染为 ICS 行。"""
    now = now or datetime.datetime.now()
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//Lunar Birthday v{__version__}//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:农历生日",
    ]

    for event in events:
        dt_start = event["date"].strftime("%Y%m%d")
        dt_end = (event["date"] + datetime.timedelta(days=1)).strftime("%Y%m%d")
        category = str(event.get("category", "")).strip()
        categories = ",".join(ics_escape(part) for part in ("生日", category) if part)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{event['person_id']}-{event['target_year']}@lunar-birthday",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{dt_start}",
                f"DTEND;VALUE=DATE:{dt_end}",
                f"SUMMARY:{ics_escape(event['summary'])}",
                f"DESCRIPTION:{ics_escape(event['description'])}",
                f"CATEGORIES:{categories}",
                "TRANSP:TRANSPARENT",
            ]
        )

        remind_days = event["remind_days"]
        if remind_days != NO_REMIND:
            lines.extend(
                [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"TRIGGER:{format_trigger(remind_days, remind_hour)}",
                    f"DESCRIPTION:{ics_escape('提醒：' + event['summary'] + '快到了')}",
                    "END:VALARM",
                ]
            )
            if remind_on_day and remind_days > 0:
                lines.extend(
                    [
                        "BEGIN:VALARM",
                        "ACTION:DISPLAY",
                        f"TRIGGER:{format_trigger(0, remind_hour)}",
                        f"DESCRIPTION:{ics_escape('今天就是' + event['summary'])}",
                        "END:VALARM",
                    ]
                )
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return lines


def build_events(
    entries,
    start_year_mode,
    age_mode,
    now=None,
    remind_hour=DEFAULT_REMIND_HOUR,
    remind_on_day=False,
    skip_past=False,
):
    """展开并渲染，返回 (ICS 行, 统计信息)。age_mode 兼容旧版布尔值。"""
    events, stats = expand_events(
        entries,
        start_year_mode,
        age_mode,
        options={"skip_past": skip_past},
        now=now,
    )
    return render_ics(events, remind_hour, remind_on_day, now), stats
