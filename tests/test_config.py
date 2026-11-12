import json
import os

from lunar_birthday.constants import NO_REMIND
from lunar_birthday.core.config_store import (
    app_data_dir,
    atomic_write_json,
    backup_config,
    normalize_entry,
)


def test_normalize_migrates_legacy_leap_text():
    entry = normalize_entry({"name": "旧", "lunar": "2023--2-04"}, 30, 7)
    assert entry["lunar"] == "2023-02-04"
    assert entry["lunar_is_leap"] is True


def test_normalize_keeps_invalid_text_for_ui_fixing():
    entry = normalize_entry({"name": "坏数据", "lunar": "bad"}, 30, 7)
    assert entry["lunar"] == "bad"


def test_normalize_repairs_out_of_range_numbers():
    entry = normalize_entry({"lunar": "1992-09-28", "years": 0, "remind_days": -5}, 30, 7)
    assert entry["years"] == 30
    assert entry["remind_days"] == 7


def test_normalize_allows_no_remind():
    entry = normalize_entry({"lunar": "1992-09-28", "remind_days": NO_REMIND}, 30, 7)
    assert entry["remind_days"] == NO_REMIND


def test_normalize_generates_stable_id_for_existing_entry():
    entry = normalize_entry({"id": "abc", "lunar": "1992-09-28"}, 30, 7)
    assert entry["id"] == "abc"


def test_atomic_write_leaves_no_temp_files(tmp_path):
    path = tmp_path / "nested" / "config.json"
    atomic_write_json(str(path), {"a": 1, "中文": "值"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1, "中文": "值"}
    leftovers = [name for name in os.listdir(path.parent) if name.startswith(".tmp-")]
    assert leftovers == []


def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / "config.json"
    atomic_write_json(str(path), {"v": 1})
    atomic_write_json(str(path), {"v": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"v": 2}


def test_backup_keeps_latest_five(tmp_path):
    path = tmp_path / "config.json"
    atomic_write_json(str(path), {"v": 0})
    for index in range(7):
        atomic_write_json(str(path), {"v": index})
        backup_config(str(path))
    backups = sorted(os.listdir(tmp_path / "backups"))
    assert len(backups) == 5
    assert backups == sorted(backups)


def test_app_data_dir_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert app_data_dir() == os.path.join(str(tmp_path), "LunarBirthday")


def test_app_data_dir_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    expected = os.path.join(os.path.expanduser("~"), ".config", "LunarBirthday")
    assert app_data_dir() == expected
