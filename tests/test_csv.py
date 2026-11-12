import csv
import json

import pytest

from lunar_birthday.core.csv_io import (
    CSV_HEADERS,
    export_entries_csv,
    import_entries_csv,
)


def test_csv_roundtrip(tmp_path):
    source = [
        {
            "name": "王潇",
            "calendar": "lunar",
            "lunar": "1992-09-28",
            "lunar_is_leap": False,
            "years": 30,
            "remind_days": 7,
            "category": "家人",
        },
        {
            "name": "李四",
            "calendar": "solar",
            "solar": "2000-02-29",
            "lunar": "",
            "lunar_is_leap": False,
            "years": 10,
            "remind_days": 0,
            "category": "",
        },
    ]
    path = tmp_path / "birthdays.csv"
    assert export_entries_csv(str(path), source) == 2

    entries, skipped = import_entries_csv(str(path))
    assert skipped == []
    assert [entry["name"] for entry in entries] == ["王潇", "李四"]
    assert entries[0]["calendar"] == "lunar"
    assert entries[0]["lunar"] == "1992-09-28"
    assert entries[0]["category"] == "家人"
    assert entries[0]["years"] == 30
    assert entries[1]["calendar"] == "solar"
    assert entries[1]["solar"] == "2000-02-29"
    assert entries[1]["remind_days"] == 0


def test_csv_export_formats_leap_month(tmp_path):
    path = tmp_path / "leap.csv"
    export_entries_csv(
        str(path),
        [
            {
                "name": "闰月",
                "calendar": "lunar",
                "lunar": "2023-02-04",
                "lunar_is_leap": True,
                "years": 5,
                "remind_days": 7,
            }
        ],
    )
    text = path.read_text(encoding="utf-8-sig")
    assert "2023-闰02-04" in text


def test_csv_export_skips_blank_rows(tmp_path):
    path = tmp_path / "blank.csv"
    count = export_entries_csv(
        str(path),
        [
            {"name": "", "lunar": "1992-09-28", "years": 5, "remind_days": 7},
            {"name": "无生日", "lunar": "", "years": 5, "remind_days": 7},
        ],
    )
    assert count == 0
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))
    assert rows == [CSV_HEADERS]


def test_csv_import_skips_invalid_rows_without_abort(tmp_path):
    path = tmp_path / "mixed.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
        writer.writerow(["好行", "农历", "1992-09-28", "30", "7", "家人"])
        writer.writerow(["坏日期", "农历", "1992-13-40", "30", "7", ""])
        writer.writerow(["", "农历", "1992-09-28", "30", "7", ""])
        writer.writerow(["缺生日", "公历", "", "30", "7", ""])
        writer.writerow(["坏数字", "公历", "2000-02-29", "abc", "-1", ""])

    entries, skipped = import_entries_csv(str(path))
    assert [entry["name"] for entry in entries] == ["好行", "坏数字"]
    assert len(skipped) == 3
    assert entries[0]["years"] == 30
    assert entries[1]["years"] is None
    assert entries[1]["remind_days"] == -1


def test_csv_import_accepts_gbk(tmp_path):
    path = tmp_path / "gbk.csv"
    content = "姓名,历法,生日,推算年数,提前天数,分类\n张三,农历,1992-09-28,5,7,同学\n"
    path.write_bytes(content.encode("gbk"))
    entries, skipped = import_entries_csv(str(path))
    assert skipped == []
    assert entries[0]["name"] == "张三"
    assert entries[0]["category"] == "同学"


def test_csv_missing_headers_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("名字,日期\n张三,1992-09-28\n", encoding="utf-8")
    with pytest.raises(ValueError):
        import_entries_csv(str(path))


def test_csv_import_ignores_unknown_columns(tmp_path):
    path = tmp_path / "extra.csv"
    path.write_text(
        "姓名,生日,备注\n张三,1992-09-28,随便写\n", encoding="utf-8-sig"
    )
    entries, _skipped = import_entries_csv(str(path))
    assert entries[0]["calendar"] == "lunar"
    assert json.dumps(entries, ensure_ascii=False)
