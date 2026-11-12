"""设置窗口：默认值、提醒规则与全局开关。"""

import customtkinter as ctk
from tkinter import messagebox

from .. import __version__
from ..constants import MAX_REMIND_DAYS, MAX_YEARS, NO_REMIND
from ..core.lunar_calc import AGE_NONE, AGE_VIRTUAL, AGE_ZODIAC
from ..core.models import DateInputError
from .helpers import center_on_parent

AGE_LABELS = {AGE_NONE: "不显示", AGE_ZODIAC: "周岁", AGE_VIRTUAL: "虚岁"}
LABEL_AGE_MODES = {label: mode for mode, label in AGE_LABELS.items()}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app = app_instance
        self.title("设置")
        self.geometry("420x540")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.after(10, self.show_centered)

        # 1. 默认年数
        frame_years = ctk.CTkFrame(self, fg_color="transparent")
        frame_years.pack(pady=(20, 10), padx=20, fill="x")
        ctk.CTkLabel(frame_years, text="默认推算年数:").pack(side="left")
        self.years_input = ctk.CTkEntry(frame_years, width=80)
        self.years_input.pack(side="right")
        self.years_input.insert(0, str(self.app.default_years))

        # 2. 默认提醒天数
        frame_remind = ctk.CTkFrame(self, fg_color="transparent")
        frame_remind.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_remind, text="默认提醒天数:").pack(side="left")
        self.remind_input = ctk.CTkEntry(frame_remind, width=80)
        self.remind_input.pack(side="right")
        self.remind_input.insert(0, str(self.app.default_remind_days))

        # 3. 起始年份模式
        frame_start_mode = ctk.CTkFrame(self, fg_color="transparent")
        frame_start_mode.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_start_mode, text="计算起始年份:").pack(side="left")
        self.start_mode_var = ctk.StringVar(value=self.app.start_year_mode)
        self.start_mode_seg = ctk.CTkSegmentedButton(
            frame_start_mode,
            values=["今年", "出生年"],
            variable=self.start_mode_var,
            width=150,
        )
        self.start_mode_seg.pack(side="right")

        # 4. 年龄口径
        frame_age = ctk.CTkFrame(self, fg_color="transparent")
        frame_age.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_age, text="标题显示年龄:").pack(side="left")
        self.age_mode_var = ctk.StringVar(value=AGE_LABELS.get(self.app.age_mode, "不显示"))
        self.age_mode_seg = ctk.CTkSegmentedButton(
            frame_age,
            values=["不显示", "周岁", "虚岁"],
            variable=self.age_mode_var,
            width=180,
        )
        self.age_mode_seg.pack(side="right")

        # 5. 提醒时刻
        frame_hour = ctk.CTkFrame(self, fg_color="transparent")
        frame_hour.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_hour, text="提醒时刻 (小时):").pack(side="left")
        self.hour_input = ctk.CTkEntry(frame_hour, width=80)
        self.hour_input.pack(side="right")
        self.hour_input.insert(0, str(self.app.remind_hour))

        # 6. 当天再提醒
        frame_on_day = ctk.CTkFrame(self, fg_color="transparent")
        frame_on_day.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_on_day, text="生日当天再提醒一次:").pack(side="left")
        self.on_day_switch = ctk.CTkSwitch(frame_on_day, text="", command=None)
        self.on_day_switch.pack(side="right")
        if self.app.remind_on_day:
            self.on_day_switch.select()

        # 7. 跳过历史事件
        frame_skip_past = ctk.CTkFrame(self, fg_color="transparent")
        frame_skip_past.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_skip_past, text="跳过今天之前的事件:").pack(side="left")
        self.skip_past_switch = ctk.CTkSwitch(frame_skip_past, text="", command=None)
        self.skip_past_switch.pack(side="right")
        if self.app.skip_past:
            self.skip_past_switch.select()

        hint = ctk.CTkLabel(
            self,
            text="提示：条目里的提前天数填 0 表示当天提醒，填 -1 表示只建事件不提醒。",
            text_color="gray",
            font=("Arial", 11),
            wraplength=370,
            justify="left",
        )
        hint.pack(pady=(12, 0), padx=20)

        # 按钮区
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="保存默认值", width=120, command=self.save_defaults).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            btn_frame,
            text="同步现有条目",
            width=120,
            fg_color="#D35400",
            command=self.apply_to_all,
        ).pack(side="left", padx=5)

        version_label = ctk.CTkLabel(
            self, text=f"version {__version__}", text_color="gray", font=("Arial", 10)
        )
        version_label.pack(side="bottom", pady=10)

    def show_centered(self):
        """真正居中并抢占焦点。"""
        center_on_parent(self, self.app)
        self.grab_set()

    def _read_numbers(self):
        try:
            years = int(self.years_input.get().strip())
            remind = int(self.remind_input.get().strip())
            hour = int(self.hour_input.get().strip())
        except ValueError as exc:
            raise DateInputError("默认年数、提醒天数与提醒时刻需为整数") from exc
        if not 1 <= years <= MAX_YEARS:
            raise DateInputError(f"默认推算年数需在 1-{MAX_YEARS} 之间")
        if remind != NO_REMIND and not 0 <= remind <= MAX_REMIND_DAYS:
            raise DateInputError(f"默认提醒天数需为 0-{MAX_REMIND_DAYS}，或 {NO_REMIND} 表示不提醒")
        if not 0 <= hour <= 23:
            raise DateInputError("提醒时刻需在 0-23 之间")
        return years, remind, hour

    def _apply(self, years, remind, hour):
        self.app.default_years = years
        self.app.default_remind_days = remind
        self.app.remind_hour = hour
        self.app.start_year_mode = self.start_mode_var.get()
        self.app.age_mode = LABEL_AGE_MODES.get(self.age_mode_var.get(), AGE_NONE)
        self.app.show_age_mode = self.app.age_mode != AGE_NONE
        self.app.remind_on_day = self.on_day_switch.get() == 1
        self.app.skip_past = self.skip_past_switch.get() == 1

    def save_defaults(self):
        try:
            years, remind, hour = self._read_numbers()
        except DateInputError as exc:
            messagebox.showerror("错误", str(exc))
            return
        self._apply(years, remind, hour)
        self.app.schedule_autosave()
        messagebox.showinfo("成功", "设置已保存。")
        self.destroy()

    def apply_to_all(self):
        try:
            years, remind, hour = self._read_numbers()
        except DateInputError as exc:
            messagebox.showerror("错误", str(exc))
            return
        self._apply(years, remind, hour)
        for entry in self.app.entries:
            entry.set_config(years, remind)
            entry.refresh_validation()
        self.app.schedule_autosave()
        messagebox.showinfo("成功", "已同步设置并应用到全部条目。")
        self.destroy()
