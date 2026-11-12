"""条目行控件：录入、历法选择、行内校验、公历农历互转、拖拽排序。"""

import uuid

import customtkinter as ctk
from lunar_python import Solar
from tkinter import messagebox

from ..constants import COLOR_ERROR, COLOR_WARN, DEFAULT_REMIND_DAYS, DEFAULT_YEARS, MAX_REMIND_DAYS, MAX_YEARS, NO_REMIND
from ..core.lunar_calc import lunar_display, resolve_lunar
from ..core.models import (
    DateInputError,
    format_lunar_text,
    parse_lunar_text,
    parse_solar_text,
)

# 表头与行内控件共用同一份列定义，避免两侧列宽漂移
COLUMN_SPECS = (
    ("name", "姓名", 80),
    ("calendar", "历法", 65),
    ("solar", "公历生日", 110),
    ("lunar", "农历生日", 110),
    ("detail", "详情 / 校验", 160),
    ("category", "分类", 70),
    ("years", "推算年数", 50),
    ("remind", "提前天数", 50),
    ("order", "排序", 30),
    ("actions", "操作", 50),
)
COLUMN_WIDTH = {key: width for key, _label, width in COLUMN_SPECS}
COLUMN_PADX = 5


def configure_columns(frame):
    """按列定义设置 grid 列宽，表头与条目行调用同一函数。"""
    for index, (_key, _label, width) in enumerate(COLUMN_SPECS):
        frame.grid_columnconfigure(index, minsize=width, pad=COLUMN_PADX * 2)


class BirthdayEntry(ctk.CTkFrame):
    def __init__(
        self,
        master_app,
        scroll_frame,
        delete_callback,
        default_years=DEFAULT_YEARS,
        default_remind=DEFAULT_REMIND_DAYS,
        entry_id=None,
        **kwargs,
    ):
        super().__init__(scroll_frame, **kwargs)
        self.master_app = master_app
        self.delete_callback = delete_callback
        self.original_fg = self.cget("fg_color")
        self.entry_id = entry_id or uuid.uuid4().hex

        configure_columns(self)

        # UI 布局
        self.name_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["name"], placeholder_text="姓名"
        )
        self.name_entry.grid(row=0, column=0, padx=COLUMN_PADX, pady=10)

        self.calendar_menu = ctk.CTkOptionMenu(
            self,
            values=["农历", "公历"],
            width=COLUMN_WIDTH["calendar"],
            command=self._on_calendar_change,
        )
        self.calendar_menu.grid(row=0, column=1, padx=COLUMN_PADX, pady=10)
        self.calendar_menu.set("农历")

        self.solar_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["solar"], placeholder_text="公历 YYYY-MM-DD"
        )
        self.solar_entry.grid(row=0, column=2, padx=COLUMN_PADX, pady=10)
        self.solar_entry.bind("<FocusOut>", self.sync_to_lunar)
        self.solar_entry.bind("<Return>", self.sync_to_lunar)

        self.lunar_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["lunar"], placeholder_text="农历 YYYY-MM-DD"
        )
        self.lunar_entry.grid(row=0, column=3, padx=COLUMN_PADX, pady=10)
        self.lunar_entry.bind("<FocusOut>", self.sync_to_solar)
        self.lunar_entry.bind("<Return>", self.sync_to_solar)
        self.lunar_entry.bind("<KeyRelease>", lambda _event: self.refresh_validation())

        self.lunar_label = ctk.CTkLabel(
            self,
            width=COLUMN_WIDTH["detail"],
            text="--等待输入--",
            text_color="gray",
            anchor="w",
            justify="left",
        )
        self.lunar_label.grid(row=0, column=4, padx=COLUMN_PADX, pady=10)

        self.category_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["category"], placeholder_text="分类"
        )
        self.category_entry.grid(row=0, column=5, padx=COLUMN_PADX, pady=10)

        self.years_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["years"], placeholder_text="年"
        )
        self.years_entry.grid(row=0, column=6, padx=COLUMN_PADX, pady=10)
        self.years_entry.insert(0, str(default_years))
        self.years_entry.bind("<FocusOut>", self.refresh_validation)

        self.remind_entry = ctk.CTkEntry(
            self, width=COLUMN_WIDTH["remind"], placeholder_text="天"
        )
        self.remind_entry.grid(row=0, column=7, padx=COLUMN_PADX, pady=10)
        self.remind_entry.insert(0, str(default_remind))
        self.remind_entry.bind("<FocusOut>", self.refresh_validation)

        self.drag_handle = ctk.CTkLabel(
            self, text="☰", cursor="fleur", width=COLUMN_WIDTH["order"], text_color="gray"
        )
        self.drag_handle.grid(row=0, column=8, padx=COLUMN_PADX, pady=10)
        self.drag_handle.bind("<Button-1>", self.on_drag_start)
        self.drag_handle.bind("<B1-Motion>", self.on_drag_motion)
        self.drag_handle.bind("<ButtonRelease-1>", self.on_drag_release)

        self.delete_btn = ctk.CTkButton(
            self,
            text="删除",
            width=COLUMN_WIDTH["actions"],
            fg_color=COLOR_ERROR,
            hover_color="#C0392B",
            command=self.request_delete,
        )
        self.delete_btn.grid(row=0, column=9, padx=COLUMN_PADX, pady=10)

        self._input_widgets = (
            self.name_entry,
            self.solar_entry,
            self.lunar_entry,
            self.years_entry,
            self.remind_entry,
        )
        self._default_border = self.name_entry.cget("border_color")

    @property
    def calendar_mode(self):
        return "solar" if self.calendar_menu.get() == "公历" else "lunar"

    def collect_issues(self):
        """返回 (错误列表, 警告列表, 解析后的原始值)。"""
        errors = []
        warnings = []
        calendar = self.calendar_mode

        name = self.name_entry.get().strip()
        if not name:
            errors.append("姓名不能为空")

        solar = None
        solar_text = self.solar_entry.get().strip()
        if solar_text:
            try:
                solar = parse_solar_text(solar_text)
            except DateInputError as exc:
                errors.append(str(exc))

        lunar_info = None
        lunar_text = self.lunar_entry.get().strip()
        if lunar_text:
            try:
                lunar_info = parse_lunar_text(lunar_text)
            except DateInputError as exc:
                errors.append(str(exc))

        if calendar == "solar":
            if not solar_text:
                errors.append("公历生日不能为空")
        elif not lunar_text:
            errors.append("农历生日不能为空")

        years = None
        try:
            years = int(self.years_entry.get().strip())
            if not 1 <= years <= MAX_YEARS:
                errors.append(f"推算年数需在 1-{MAX_YEARS} 之间")
        except ValueError:
            errors.append("推算年数需为整数")

        remind = None
        try:
            remind = int(self.remind_entry.get().strip())
            if remind != NO_REMIND and not 0 <= remind <= MAX_REMIND_DAYS:
                errors.append(f"提前天数需为 0-{MAX_REMIND_DAYS}，或 {NO_REMIND} 表示不提醒")
        except ValueError:
            errors.append("提前天数需为整数（0=当天，-1=不提醒）")

        if solar and lunar_info:
            try:
                converted = Solar.fromYmd(solar.year, solar.month, solar.day).getLunar()
                expected = (
                    lunar_info[0],
                    lunar_info[1],
                    lunar_info[2],
                    lunar_info[3],
                )
                actual = (
                    converted.getYear(),
                    abs(converted.getMonth()),
                    converted.getDay(),
                    converted.getMonth() < 0,
                )
                if expected != actual:
                    warnings.append("公历与农历不一致，生成时以所选历法为准")
            except Exception:
                warnings.append("公历与农历不一致，生成时以所选历法为准")

        return errors, warnings, {
            "name": name,
            "calendar": calendar,
            "solar": solar,
            "lunar": lunar_info,
            "years": years,
            "remind": remind,
        }

    def refresh_validation(self, event=None):
        """把校验结果直接呈现在行内，取代静默失败。"""
        errors, warnings, values = self.collect_issues()

        for widget in self._input_widgets:
            try:
                widget.configure(border_color=COLOR_ERROR if errors else self._default_border)
            except Exception:
                pass

        if errors:
            text = errors[0] if len(errors) == 1 else f"{errors[0]}（共 {len(errors)} 项问题）"
            self.lunar_label.configure(text=text, text_color=COLOR_ERROR)
            return

        if warnings:
            self.set_detail_text(warnings[0], COLOR_WARN)
            return

        if values["calendar"] == "solar":
            solar = values["solar"]
            if solar is None:
                self.set_detail_text("--等待输入--", "gray")
            else:
                self.set_detail_text(f"公历 {solar.month} 月 {solar.day} 日", ("black", "white"))
            return

        text = self.lunar_entry.get().strip()
        if not text:
            self.set_detail_text("--等待输入--", "gray")
            return
        try:
            year, month, day, leap = parse_lunar_text(text)
            lunar, note = resolve_lunar(year, month, day, leap)
        except DateInputError as exc:
            self.set_detail_text(str(exc), COLOR_ERROR)
            return
        detail = lunar_display(lunar)
        if note:
            detail = f"{detail}（{note}）"
        self.set_detail_text(detail, ("black", "white"))

    def set_detail_text(self, text, color):
        self.lunar_label.configure(text=text, text_color=color)

    def _on_calendar_change(self, _value=None):
        if self.calendar_mode == "solar" and not self.solar_entry.get().strip() and self.lunar_entry.get().strip():
            self.sync_to_solar()
        elif self.calendar_mode == "lunar" and not self.lunar_entry.get().strip() and self.solar_entry.get().strip():
            self.sync_to_lunar()
        self.refresh_validation()
        self.master_app.schedule_autosave()

    def sync_to_lunar(self, event=None):
        solar_text = self.solar_entry.get().strip()
        if not solar_text:
            return
        try:
            solar = parse_solar_text(solar_text)
        except DateInputError as exc:
            self.refresh_validation()
            self.set_detail_text(str(exc), COLOR_ERROR)
            return
        lunar = Solar.fromYmd(solar.year, solar.month, solar.day).getLunar()
        self.lunar_entry.delete(0, "end")
        self.lunar_entry.insert(
            0,
            format_lunar_text(
                lunar.getYear(), abs(lunar.getMonth()), lunar.getDay(), lunar.getMonth() < 0
            ),
        )
        self.refresh_validation()

    def sync_to_solar(self, event=None):
        lunar_text = self.lunar_entry.get().strip()
        if not lunar_text:
            return
        try:
            year, month, day, leap = parse_lunar_text(lunar_text)
            lunar, _note = resolve_lunar(year, month, day, leap)
        except DateInputError:
            self.refresh_validation()
            return
        solar = lunar.getSolar()
        self.solar_entry.delete(0, "end")
        self.solar_entry.insert(
            0, f"{solar.getYear():04d}-{solar.getMonth():02d}-{solar.getDay():02d}"
        )
        self.refresh_validation()

    def on_drag_start(self, event):
        self.configure(fg_color=("#D5D8DC", "#2C3E50"))
        self.master_app.current_drag_item = self

    def on_drag_motion(self, event):
        if getattr(self.master_app, "current_drag_item", None) is not self:
            return
        pointer_y = self.winfo_pointery()
        for index, entry in enumerate(self.master_app.entries):
            if entry is self:
                continue
            top = entry.winfo_rooty()
            bottom = top + entry.winfo_height()
            if top < pointer_y < bottom:
                self_index = self.master_app.entries.index(self)
                self.master_app.entries[self_index], self.master_app.entries[index] = (
                    self.master_app.entries[index],
                    self.master_app.entries[self_index],
                )
                self.master_app.repack_entries()
                break

    def on_drag_release(self, event):
        self.configure(fg_color=self.original_fg)
        self.master_app.current_drag_item = None

    def set_config(self, years, remind_days):
        self.years_entry.delete(0, "end")
        self.years_entry.insert(0, str(years))
        self.remind_entry.delete(0, "end")
        self.remind_entry.insert(0, str(remind_days))

    def set_profile(self, calendar="lunar", category=""):
        self.calendar_menu.set("公历" if calendar == "solar" else "农历")
        if category:
            self.category_entry.delete(0, "end")
            self.category_entry.insert(0, category)

    def request_delete(self):
        """用户点击删除时先确认，避免误删。"""
        name = self.name_entry.get().strip() or "这条记录"
        if messagebox.askyesno(
            "确认删除",
            f"确定要删除「{name}」吗？删除后无法撤销。",
            parent=self.winfo_toplevel(),
        ):
            self.delete_self()

    def delete_self(self):
        self.delete_callback(self)
        self.destroy()

    def get_data(self):
        """返回该行数据，errors 非空表示不可用于生成或保存。"""
        errors, warnings, values = self.collect_issues()
        lunar_text = ""
        is_leap = False
        if values["lunar"]:
            year, month, day, leap = values["lunar"]
            lunar_text = f"{year:04d}-{month:02d}-{day:02d}"
            is_leap = leap
        return {
            "id": self.entry_id,
            "name": values["name"],
            "calendar": values["calendar"],
            "solar": values["solar"].isoformat() if values["solar"] else "",
            "lunar": lunar_text,
            "lunar_is_leap": is_leap,
            "category": self.category_entry.get().strip(),
            "years": values["years"],
            "remind_days": values["remind"],
            "errors": errors,
            "warnings": warnings,
        }

    def get_storage(self):
        """无损保存用的原始数据：即使输入尚未合法也原样落盘，避免丢失编辑内容。"""

        def as_int(widget, fallback):
            try:
                return int(widget.get().strip())
            except ValueError:
                return fallback

        lunar_text = self.lunar_entry.get().strip()
        is_leap = False
        if lunar_text:
            try:
                is_leap = parse_lunar_text(lunar_text)[3]
            except DateInputError:
                is_leap = False

        return {
            "id": self.entry_id,
            "name": self.name_entry.get().strip(),
            "calendar": self.calendar_mode,
            "solar": self.solar_entry.get().strip(),
            "lunar": lunar_text,
            "lunar_is_leap": is_leap,
            "category": self.category_entry.get().strip(),
            "years": as_int(self.years_entry, self.master_app.default_years),
            "remind_days": as_int(self.remind_entry, self.master_app.default_remind_days),
        }
