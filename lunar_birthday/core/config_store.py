"""配置读写：目录定位、原子写、滚动备份、旧数据迁移。"""

import datetime
import json
import os
import shutil
import tempfile
import uuid

from ..constants import (
    BACKUP_KEEP,
    DEFAULT_REMIND_DAYS,
    DEFAULT_YEARS,
    MAX_REMIND_DAYS,
    MAX_YEARS,
    NO_REMIND,
)
from .models import DateInputError, parse_lunar_text


def normalize_entry(raw, default_years, default_remind_days):
    """把配置中的单条记录规整为当前 schema，兼容旧版本数据。"""
    calendar = "solar" if str(raw.get("calendar", "")).lower() == "solar" else "lunar"
    entry = {
        "id": str(raw.get("id") or uuid.uuid4().hex),
        "name": str(raw.get("name", "")),
        "calendar": calendar,
        "solar": str(raw.get("solar", "")),
        "lunar": str(raw.get("lunar", "")),
        "lunar_is_leap": bool(raw.get("lunar_is_leap", False)),
        "category": str(raw.get("category", "")).strip(),
        "years": default_years,
        "remind_days": default_remind_days,
    }
    try:
        entry["years"] = int(raw.get("years", default_years))
    except (TypeError, ValueError):
        pass
    if not 1 <= entry["years"] <= MAX_YEARS:
        entry["years"] = default_years
    try:
        entry["remind_days"] = int(raw.get("remind_days", default_remind_days))
    except (TypeError, ValueError):
        pass
    if entry["remind_days"] != NO_REMIND and not 0 <= entry["remind_days"] <= MAX_REMIND_DAYS:
        entry["remind_days"] = default_remind_days

    if calendar == "lunar":
        try:
            year, month, day, leap = parse_lunar_text(entry["lunar"])
            entry["lunar"] = f"{year:04d}-{month:02d}-{day:02d}"
            entry["lunar_is_leap"] = leap or entry["lunar_is_leap"]
        except DateInputError:
            # 保留原文，交给界面标红，由用户修正
            pass
    return entry


def app_data_dir():
    """默认配置目录：Windows 用 %APPDATA%，其余平台用 ~/.config。"""
    base = os.environ.get("APPDATA")
    if base:
        return os.path.join(base, "LunarBirthday")
    return os.path.join(os.path.expanduser("~"), ".config", "LunarBirthday")


def atomic_write_json(path, payload):
    """先写临时文件再替换，避免中途崩溃留下半个配置。"""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def backup_config(path, keep=BACKUP_KEEP):
    """覆盖前备份，只保留最近若干份。"""
    if not os.path.exists(path):
        return
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(path)), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = os.path.join(backup_dir, f"config-{stamp}.json")
    try:
        shutil.copy2(path, target)
    except OSError:
        return
    backups = sorted(
        name for name in os.listdir(backup_dir) if name.startswith("config-") and name.endswith(".json")
    )
    for name in backups[:-keep]:
        try:
            os.remove(os.path.join(backup_dir, name))
        except OSError:
            pass
