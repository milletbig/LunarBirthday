"""项目级常量，界面与核心逻辑共用。"""

from . import __version__

APP_NAME = "农历生日"
# 兼容旧引用；新代码应直接使用 __version__
APP_VERSION = __version__

# 农历库可靠区间，超出后为算法外推，不再生成
LUNAR_MIN_YEAR = 1900
LUNAR_MAX_YEAR = 2100

DEFAULT_YEARS = 30
DEFAULT_REMIND_DAYS = 7
DEFAULT_REMIND_HOUR = 9
MAX_YEARS = 200
MAX_REMIND_DAYS = 365
# remind_days 取该值时只生成事件、不生成提醒
NO_REMIND = -1
BACKUP_KEEP = 5

SCHEMA_VERSION = 2

COLOR_ERROR = "#E74C3C"
COLOR_WARN = "#E67E22"
