"""CSV 导入导出：用表格批量维护条目。"""

import csv
import io

from .models import DateInputError, format_lunar_text, parse_lunar_text, parse_solar_text

CSV_HEADERS = ["姓名", "历法", "生日", "推算年数", "提前天数", "分类"]


def _read_text(path):
    """读取 CSV 文本，兼容 Excel 常见的 UTF-8 BOM 与 GBK 编码。"""
    with open(path, "rb") as file:
        raw = file.read()
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别 CSV 编码，请另存为 UTF-8 或 GBK")


def export_entries_csv(path, entries):
    """导出条目，返回实际写入的行数。空姓名或空生日会被跳过。"""
    rows = []
    for item in entries:
        name = str(item.get("name", "")).strip()
        calendar = "公历" if item.get("calendar") == "solar" else "农历"
        if calendar == "公历":
            birthday = str(item.get("solar", "")).strip()
        else:
            try:
                year, month, day, leap = parse_lunar_text(item.get("lunar", ""))
                birthday = format_lunar_text(
                    year, month, day, leap or item.get("lunar_is_leap", False)
                )
            except DateInputError:
                birthday = str(item.get("lunar", "")).strip()
        if not name or not birthday:
            continue
        rows.append(
            [
                name,
                calendar,
                birthday,
                item.get("years", ""),
                item.get("remind_days", ""),
                str(item.get("category", "")).strip(),
            ]
        )

    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
        writer.writerows(rows)
    return len(rows)


def import_entries_csv(path):
    """解析 CSV，返回 (条目列表, 跳过原因列表)。无效行不会中断导入。"""
    text = _read_text(path)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [name.strip() for name in (reader.fieldnames or []) if name]
    if "姓名" not in fieldnames or "生日" not in fieldnames:
        raise ValueError("CSV 需要至少包含「姓名」「生日」两列")

    entries = []
    skipped = []
    for line_no, raw in enumerate(reader, start=2):
        values = {(key or "").strip(): (value or "").strip() for key, value in raw.items()}
        if not any(values.values()):
            continue

        name = values.get("姓名", "")
        birthday = values.get("生日", "")
        if not name:
            skipped.append(f"第 {line_no} 行：姓名为空")
            continue
        if not birthday:
            skipped.append(f"第 {line_no} 行：生日为空")
            continue

        calendar_text = values.get("历法", "农历")
        calendar = "solar" if calendar_text.startswith("公") else "lunar"
        entry = {
            "name": name,
            "calendar": calendar,
            "solar": "",
            "lunar": "",
            "lunar_is_leap": False,
            "years": None,
            "remind_days": None,
            "category": values.get("分类", ""),
        }
        try:
            if calendar == "solar":
                entry["solar"] = parse_solar_text(birthday).isoformat()
            else:
                year, month, day, leap = parse_lunar_text(birthday)
                entry["lunar"] = f"{year:04d}-{month:02d}-{day:02d}"
                entry["lunar_is_leap"] = leap
        except DateInputError as exc:
            skipped.append(f"第 {line_no} 行：{exc}")
            continue

        for key in ("years", "remind_days"):
            raw_value = values.get("推算年数" if key == "years" else "提前天数", "")
            try:
                entry[key] = int(raw_value)
            except ValueError:
                entry[key] = None

        entries.append(entry)
    return entries, skipped
