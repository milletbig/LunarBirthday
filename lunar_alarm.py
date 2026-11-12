"""农历生日提醒生成工具 —— 启动入口与公共 API 导出。

实际实现位于 lunar_birthday 包。本文件保留 `python lunar_alarm.py` 的启动方式，
并继续导出公共函数，便于脚本与既有调用方复用。
"""

import json

from lunar_birthday import __version__
from lunar_birthday.constants import (
    APP_NAME,
    APP_VERSION,
    BACKUP_KEEP,
    COLOR_ERROR,
    COLOR_WARN,
    DEFAULT_REMIND_DAYS,
    DEFAULT_REMIND_HOUR,
    DEFAULT_YEARS,
    LUNAR_MAX_YEAR,
    LUNAR_MIN_YEAR,
    MAX_REMIND_DAYS,
    MAX_YEARS,
    NO_REMIND,
    SCHEMA_VERSION,
)
from lunar_birthday.core.config_store import (
    app_data_dir,
    atomic_write_json,
    backup_config,
    normalize_entry,
)
from lunar_birthday.core.csv_io import (
    CSV_HEADERS,
    export_entries_csv,
    import_entries_csv,
)
from lunar_birthday.core.ics_builder import (
    build_events,
    format_trigger,
    ics_escape,
    ics_fold,
    render_ics,
    write_ics,
)
from lunar_birthday.core.lunar_calc import (
    AGE_NONE,
    AGE_VIRTUAL,
    AGE_ZODIAC,
    expand_events,
    lunar_display,
    resolve_lunar,
)
from lunar_birthday.core.models import (
    DateInputError,
    format_lunar_text,
    parse_lunar_text,
    parse_solar_text,
    resolve_solar_date,
)
from lunar_birthday.ui.app import App, main
from lunar_birthday.ui.entry_row import BirthdayEntry
from lunar_birthday.ui.preview import PreviewWindow
from lunar_birthday.ui.settings import SettingsWindow

__all__ = [
    "__version__",
    "AGE_NONE",
    "AGE_VIRTUAL",
    "AGE_ZODIAC",
    "APP_NAME",
    "APP_VERSION",
    "BACKUP_KEEP",
    "COLOR_ERROR",
    "COLOR_WARN",
    "CSV_HEADERS",
    "DEFAULT_REMIND_DAYS",
    "DEFAULT_REMIND_HOUR",
    "DEFAULT_YEARS",
    "LUNAR_MAX_YEAR",
    "LUNAR_MIN_YEAR",
    "MAX_REMIND_DAYS",
    "MAX_YEARS",
    "NO_REMIND",
    "SCHEMA_VERSION",
    "App",
    "BirthdayEntry",
    "DateInputError",
    "PreviewWindow",
    "SettingsWindow",
    "app_data_dir",
    "atomic_write_json",
    "backup_config",
    "build_events",
    "expand_events",
    "export_entries_csv",
    "format_lunar_text",
    "format_trigger",
    "ics_escape",
    "ics_fold",
    "import_entries_csv",
    "json",
    "lunar_display",
    "main",
    "normalize_entry",
    "parse_lunar_text",
    "parse_solar_text",
    "render_ics",
    "resolve_lunar",
    "resolve_solar_date",
    "write_ics",
]


if __name__ == "__main__":
    main()
