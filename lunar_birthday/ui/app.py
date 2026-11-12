"""主窗口与程序入口。"""

import datetime
import json
import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from .. import __version__
from ..constants import (
    COLOR_ERROR,
    COLOR_WARN,
    DEFAULT_REMIND_DAYS,
    DEFAULT_REMIND_HOUR,
    DEFAULT_YEARS,
    SCHEMA_VERSION,
)
from ..core.config_store import (
    app_data_dir,
    atomic_write_json,
    backup_config,
    normalize_entry,
)
from ..core.csv_io import export_entries_csv, import_entries_csv
from ..core.ics_builder import render_ics, write_ics
from ..core.lunar_calc import AGE_MODES, AGE_NONE, AGE_ZODIAC, expand_events
from ..core.models import DateInputError, format_lunar_text, parse_lunar_text
from .entry_row import COLUMN_SPECS, BirthdayEntry, configure_columns
from .preview import PreviewWindow
from .settings import SettingsWindow

SHORTCUT_HINT = "Ctrl+S 另存 · Ctrl+O 读取 · Ctrl+Enter 生成"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"农历生日生成工具 v{__version__}")
        self.geometry("1020x760")

        # 配置存储
        self.default_years = DEFAULT_YEARS
        self.default_remind_days = DEFAULT_REMIND_DAYS
        self.remind_hour = DEFAULT_REMIND_HOUR
        self.remind_on_day = True
        self.skip_past = True
        self.start_year_mode = "今年"
        self.age_mode = AGE_NONE
        self.show_age_mode = False

        self.entries = []
        self.settings_window = None
        self.current_drag_item = None
        self.config_dir = app_data_dir()
        self.config_path = os.path.join(self.config_dir, "config.json")
        self._autosave_job = None
        self._busy = False
        self._generation_result = None
        self._progress_value = 0.0

        # 表头：列定义与条目行共用
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 0))
        configure_columns(header_frame)
        for index, (_key, label, width) in enumerate(COLUMN_SPECS):
            ctk.CTkLabel(header_frame, text=label, width=width).grid(
                row=0, column=index, padx=5
            )

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.empty_label = ctk.CTkLabel(
            self.scroll_frame,
            text="还没有条目\n点击下方「+ 添加新条目」开始录入，或用 Ctrl+O 读取已有配置。",
            text_color="gray",
            justify="center",
        )

        self.add_btn = ctk.CTkButton(self, text="+ 添加新条目", command=self.add_entry)
        self.add_btn.pack(pady=5)

        # 状态栏：进度 + 自动保存状态
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=f"自动保存：{self.config_path} · {SHORTCUT_HINT}",
            text_color="gray",
            anchor="w",
            font=("Arial", 11),
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.progress = ctk.CTkProgressBar(self.status_frame, width=200)
        self.progress.set(0)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", padx=20, pady=20)

        self.settings_btn = ctk.CTkButton(
            bottom_frame, text="⚙️ 设置", width=70, fg_color="gray", command=self.open_settings
        )
        self.settings_btn.pack(side="left", padx=(0, 10))

        self.save_btn = ctk.CTkButton(
            bottom_frame, text="💾 另存为", width=90, fg_color="#27AE60", command=self.save_config
        )
        self.save_btn.pack(side="left", padx=(0, 10))

        self.load_btn = ctk.CTkButton(
            bottom_frame, text="📂 读取配置", width=90, fg_color="#F39C12", command=self.load_config
        )
        self.load_btn.pack(side="left", padx=(0, 10))

        self.import_csv_btn = ctk.CTkButton(
            bottom_frame, text="⬆ 导入CSV", width=90, fg_color="#8E44AD", command=self.import_csv
        )
        self.import_csv_btn.pack(side="left", padx=(0, 10))

        self.export_csv_btn = ctk.CTkButton(
            bottom_frame, text="⬇ 导出CSV", width=90, fg_color="#16A085", command=self.export_csv
        )
        self.export_csv_btn.pack(side="left")

        self.generate_btn = ctk.CTkButton(
            bottom_frame,
            text="🚀 生成 ICS 文件",
            width=180,
            height=40,
            font=("Arial", 14, "bold"),
            command=self.generate_ics,
        )
        self.generate_btn.pack(side="right")

        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._load_initial_config()

    def _bind_shortcuts(self):
        self.bind("<Control-s>", self._shortcut_save)
        self.bind("<Control-o>", self._shortcut_load)
        self.bind("<Control-Return>", self._shortcut_generate)

    def _shortcut_save(self, event=None):
        self.save_config()
        return "break"

    def _shortcut_load(self, event=None):
        self.load_config()
        return "break"

    def _shortcut_generate(self, event=None):
        self.generate_ics()
        return "break"

    def refresh_empty_state(self):
        """没有任何条目时给出空状态提示。"""
        if self.entries:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(fill="x", pady=60)

    def add_entry(self, data=None):
        data = data or {}
        entry = BirthdayEntry(
            self,
            self.scroll_frame,
            delete_callback=self.remove_entry,
            default_years=self.default_years,
            default_remind=self.default_remind_days,
            entry_id=data.get("id"),
        )
        entry.name_entry.insert(0, data.get("name", ""))
        entry.solar_entry.insert(0, data.get("solar", ""))
        entry.set_profile(data.get("calendar", "lunar"), data.get("category", ""))
        if data.get("lunar"):
            try:
                year, month, day, leap = parse_lunar_text(data["lunar"])
                entry.lunar_entry.insert(
                    0, format_lunar_text(year, month, day, leap or data.get("lunar_is_leap", False))
                )
            except DateInputError:
                entry.lunar_entry.insert(0, data["lunar"])
        entry.set_config(
            data.get("years", self.default_years), data.get("remind_days", self.default_remind_days)
        )
        entry.refresh_validation()
        entry.pack(fill="x", pady=2)
        self.entries.append(entry)
        self.refresh_empty_state()
        self.schedule_autosave()

    def repack_entries(self):
        for entry in self.entries:
            entry.pack_forget()
        for entry in self.entries:
            entry.pack(fill="x", pady=2)
        self.schedule_autosave()

    def remove_entry(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)
            self.refresh_empty_state()
            self.schedule_autosave()

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self)
        else:
            self.settings_window.focus()
            self.settings_window.lift()

    def _collect_rows(self):
        rows = [entry.get_data() for entry in self.entries]
        problems = [(row["name"] or "（未命名）", row["errors"]) for row in rows if row["errors"]]
        return rows, problems

    @staticmethod
    def _format_problems(problems, limit=5):
        lines = []
        for name, errors in problems[:limit]:
            lines.append(f"· {name}：{'；'.join(errors)}")
        if len(problems) > limit:
            lines.append(f"… 另有 {len(problems) - limit} 行存在问题")
        return "\n".join(lines)

    def _config_payload(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "default_years": self.default_years,
            "default_remind_days": self.default_remind_days,
            "remind_hour": self.remind_hour,
            "remind_on_day": self.remind_on_day,
            "skip_past": self.skip_past,
            "start_year_mode": self.start_year_mode,
            "age_mode": self.age_mode,
            "show_age_mode": self.show_age_mode,
            "entries": [entry.get_storage() for entry in self.entries],
        }

    def _set_status(self, text, color="gray"):
        self.status_label.configure(text=text, text_color=color)

    def _autosave(self, notify=False):
        try:
            backup_config(self.config_path)
            atomic_write_json(self.config_path, self._config_payload())
        except OSError as exc:
            self._set_status(f"自动保存失败：{exc}", COLOR_ERROR)
            if notify:
                messagebox.showerror("保存失败", f"无法写入默认配置：{exc}")
            return False
        self._set_status(f"已自动保存 {datetime.datetime.now():%H:%M:%S} · {self.config_path}")
        if notify:
            messagebox.showinfo("已保存", "配置已保存到默认位置。")
        return True

    def schedule_autosave(self, delay=1200):
        if getattr(self, "_initialising", False):
            return
        if self._autosave_job is not None:
            try:
                self.after_cancel(self._autosave_job)
            except Exception:
                pass
        self._autosave_job = self.after(delay, self._autosave)

    def on_close(self):
        if self._autosave_job is not None:
            try:
                self.after_cancel(self._autosave_job)
            except Exception:
                pass
            self._autosave_job = None
        self._autosave()
        self.destroy()

    def save_config(self):
        _rows, problems = self._collect_rows()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="LunarBirthday_Config.json",
            filetypes=[("JSON Config Files", "*.json")],
        )
        if not file_path:
            return
        try:
            atomic_write_json(file_path, self._config_payload())
        except OSError as exc:
            messagebox.showerror("保存失败", f"无法写入文件：{exc}")
            return
        if problems:
            messagebox.showwarning(
                "已保存（部分行未通过校验）",
                f"配置已保存，但有 {len(problems)} 行需要修正：\n\n" + self._format_problems(problems),
            )
            return
        messagebox.showinfo("成功", "配置已保存。")

    def _apply_config_data(self, data):
        """把已解析的配置应用到界面；结构不合法时抛 ValueError。"""
        if not isinstance(data, dict):
            raise ValueError("配置文件格式不正确")
        raw_entries = data.get("entries", [])
        if not isinstance(raw_entries, list):
            raise ValueError("entries 字段格式不正确")

        default_years = data.get("default_years", DEFAULT_YEARS)
        default_remind = data.get("default_remind_days", DEFAULT_REMIND_DAYS)
        try:
            default_years = int(default_years)
        except (TypeError, ValueError):
            default_years = DEFAULT_YEARS
        try:
            default_remind = int(default_remind)
        except (TypeError, ValueError):
            default_remind = DEFAULT_REMIND_DAYS

        entries = [
            normalize_entry(item, default_years, default_remind)
            for item in raw_entries
            if isinstance(item, dict)
        ]

        self.default_years = default_years
        self.default_remind_days = default_remind
        self.start_year_mode = data.get("start_year_mode", "今年")
        if "age_mode" in data:
            raw_age_mode = data.get("age_mode")
            self.age_mode = raw_age_mode if raw_age_mode in AGE_MODES else AGE_NONE
        else:
            self.age_mode = AGE_ZODIAC if bool(data.get("show_age_mode", False)) else AGE_NONE
        self.show_age_mode = self.age_mode != AGE_NONE
        self.remind_hour = int(data.get("remind_hour", DEFAULT_REMIND_HOUR))
        if not 0 <= self.remind_hour <= 23:
            self.remind_hour = DEFAULT_REMIND_HOUR
        self.remind_on_day = bool(data.get("remind_on_day", True))
        self.skip_past = bool(data.get("skip_past", True))

        for entry in list(self.entries):
            entry.delete_self()
        for entry_data in entries:
            self.add_entry(data=entry_data)
        if not self.entries:
            self.add_entry()
        self.refresh_empty_state()

    def _load_initial_config(self):
        self._initialising = True
        try:
            if not os.path.exists(self.config_path):
                self.add_entry()
                return
            try:
                with open(self.config_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                self._apply_config_data(data)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self._set_status(f"默认配置读取失败，已忽略：{exc}", COLOR_WARN)
                self.add_entry()
        finally:
            self._initialising = False

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Config Files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            self._apply_config_data(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("读取失败", f"配置文件无法解析：{exc}")
            return
        self.schedule_autosave(0)
        messagebox.showinfo("成功", "配置已读取。")

    def import_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        try:
            rows, skipped = import_entries_csv(file_path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("导入失败", f"无法读取 CSV：{exc}")
            return
        if not rows:
            messagebox.showwarning(
                "导入失败", "\n".join(skipped[:5]) or "CSV 中没有有效数据。"
            )
            return
        for row in rows:
            if row.get("years") is None:
                row["years"] = self.default_years
            if row.get("remind_days") is None:
                row["remind_days"] = self.default_remind_days
            self.add_entry(data=row)
        self.schedule_autosave(0)
        message = f"已导入 {len(rows)} 条。"
        if skipped:
            message += f"\n跳过 {len(skipped)} 行：\n" + "\n".join(skipped[:5])
        self._set_status(f"已从 CSV 导入 {len(rows)} 条")
        messagebox.showinfo("导入完成", message)

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"农历生日_{datetime.date.today():%Y%m%d}.csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return
        try:
            count = export_entries_csv(
                file_path, [entry.get_storage() for entry in self.entries]
            )
        except OSError as exc:
            messagebox.showerror("导出失败", f"无法写入文件：{exc}")
            return
        self._set_status(f"已导出 {count} 条到 CSV · {file_path}")
        messagebox.showinfo("导出完成", f"已导出 {count} 条到：\n{file_path}")

    def generate_ics(self):
        if self._busy:
            return
        rows, problems = self._collect_rows()
        if problems:
            messagebox.showerror("无法生成", "请先修正以下条目：\n\n" + self._format_problems(problems))
            return

        usable = [row for row in rows if row["name"]]
        if not usable:
            messagebox.showwarning("提示", "没有可用的条目。")
            return
        self._start_generation(usable)

    def _start_generation(self, usable):
        self._busy = True
        self.generate_btn.configure(state="disabled")
        self._generation_result = None
        self._progress_value = 0.0
        self.progress.set(0)
        self.progress.pack(side="right", padx=(10, 0))
        self._set_status("正在推算农历日期…")

        def worker():
            try:
                events, stats = expand_events(
                    usable,
                    self.start_year_mode,
                    self.age_mode,
                    options={"skip_past": self.skip_past},
                    progress=self._report_progress,
                )
                lines = render_ics(events, self.remind_hour, self.remind_on_day)
                self._generation_result = (events, stats, lines, None)
            except Exception as exc:  # 工作线程必须兜底，否则界面会永久卡在忙碌态
                self._generation_result = (None, None, None, exc)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll_generation)

    def _report_progress(self, done, total):
        self._progress_value = done / total if total else 1.0

    def _poll_generation(self):
        if self._generation_result is None:
            self.progress.set(self._progress_value)
            self.after(100, self._poll_generation)
            return

        events, stats, lines, error = self._generation_result
        self._generation_result = None
        self._busy = False
        self.generate_btn.configure(state="normal")
        self.progress.pack_forget()
        self.progress.set(0)

        if error is not None:
            self._set_status("生成失败", COLOR_ERROR)
            messagebox.showerror("生成失败", f"推算过程中出错：{error}")
            return
        if not events:
            self._set_status("没有可生成的事件", COLOR_WARN)
            messagebox.showwarning(
                "没有可生成的事件", "\n".join(stats["notes"][:5]) or "请检查推算范围与起始年份设置。"
            )
            return

        self._set_status(f"推算完成：{stats['events']} 条事件，等待确认")
        PreviewWindow(self, events, stats, lambda: self._save_generated(lines, stats))

    def _save_generated(self, lines, stats):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".ics",
            initialfile=f"农历生日_{datetime.date.today():%Y%m%d}.ics",
            filetypes=[("iCalendar Files", "*.ics")],
        )
        if not file_path:
            return
        try:
            write_ics(file_path, lines)
        except OSError as exc:
            messagebox.showerror("生成失败", f"无法写入文件：{exc}")
            return

        report = f"共生成 {stats['events']} 条事件，覆盖 {stats['people']} 人。"
        if stats["past"]:
            report += f"\n已跳过 {stats['past']} 条历史事件。"
        if stats["skipped"]:
            report += f"\n跳过 {stats['skipped']} 个无法推算的年份。"
        if stats.get("fallback"):
            report += f"\n{stats['fallback']} 条日期补偿（当月无对应日）。"
        if stats["notes"]:
            report += "\n\n" + "\n".join(stats["notes"][:5])
            if len(stats["notes"]) > 5:
                report += f"\n… 另有 {len(stats['notes']) - 5} 条提示"
        self._set_status(f"已导出 {stats['events']} 条事件 · {file_path}")
        messagebox.showinfo("完成", report)


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()


if __name__ == "__main__":
    main()
