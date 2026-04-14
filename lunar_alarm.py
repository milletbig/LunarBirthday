import customtkinter as ctk
from tkinter import messagebox, filedialog
from lunar_python import Solar, Lunar
import datetime
import uuid
import json

# 设置主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BirthdayEntry(ctk.CTkFrame):
    def __init__(self, master_app, scroll_frame, delete_callback, default_years=50, default_remind=7, **kwargs):
        super().__init__(scroll_frame, **kwargs)
        self.master_app = master_app
        self.delete_callback = delete_callback
        self.original_fg = self.cget("fg_color")

        # UI 布局
        self.name_entry = ctk.CTkEntry(self, width=80, placeholder_text="姓名")
        self.name_entry.grid(row=0, column=0, padx=5, pady=10)

        self.solar_entry = ctk.CTkEntry(self, width=110, placeholder_text="公历 YYYY-MM-DD")
        self.solar_entry.grid(row=0, column=1, padx=5, pady=10)
        self.solar_entry.bind("<FocusOut>", self.sync_to_lunar)
        self.solar_entry.bind("<Return>", self.sync_to_lunar)

        self.lunar_entry = ctk.CTkEntry(self, width=110, placeholder_text="农历 YYYY-MM-DD")
        self.lunar_entry.grid(row=0, column=2, padx=5, pady=10)
        self.lunar_entry.bind("<FocusOut>", self.sync_to_solar)
        self.lunar_entry.bind("<Return>", self.sync_to_solar)

        self.lunar_label = ctk.CTkLabel(self, width=140, text="--等待输入--", text_color="gray", anchor="w")
        self.lunar_label.grid(row=0, column=3, padx=5, pady=10)

        self.years_entry = ctk.CTkEntry(self, width=50, placeholder_text="年")
        self.years_entry.grid(row=0, column=4, padx=5, pady=10)
        self.years_entry.insert(0, str(default_years))

        self.remind_entry = ctk.CTkEntry(self, width=50, placeholder_text="天")
        self.remind_entry.grid(row=0, column=5, padx=5, pady=10)
        self.remind_entry.insert(0, str(default_remind))

        self.drag_handle = ctk.CTkLabel(self, text="☰", cursor="fleur", width=30, text_color="gray")
        self.drag_handle.grid(row=0, column=6, padx=5, pady=10)
        self.drag_handle.bind("<Button-1>", self.on_drag_start)
        self.drag_handle.bind("<B1-Motion>", self.on_drag_motion)
        self.drag_handle.bind("<ButtonRelease-1>", self.on_drag_release)

        self.delete_btn = ctk.CTkButton(self, text="删除", width=50, fg_color="#E74C3C", 
                                        hover_color="#C0392B", command=self.delete_self)
        self.delete_btn.grid(row=0, column=7, padx=5, pady=10)

    def update_lunar_label(self):
        text = self.lunar_entry.get().strip()
        if not text:
            self.lunar_label.configure(text="--等待输入--")
            return
        try:
            parts = text.replace('/', '-').split('-')
            if len(parts) == 3:
                lunar = Lunar.fromYmd(int(parts[0]), int(parts[1]), int(parts[2]))
                l_str = f"{lunar.getYear()}{lunar.getYearInGanZhi()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
                self.lunar_label.configure(text=l_str, text_color=("black", "white"))
        except:
            self.lunar_label.configure(text="格式错误", text_color="red")

    def sync_to_lunar(self, event=None):
        text = self.solar_entry.get().strip()
        if not text: return
        try:
            parts = text.replace('/', '-').split('-')
            if len(parts) == 3:
                solar = Solar.fromYmd(int(parts[0]), int(parts[1]), int(parts[2]))
                lunar = solar.getLunar()
                self.lunar_entry.delete(0, 'end')
                self.lunar_entry.insert(0, f"{lunar.getYear()}-{lunar.getMonth():02d}-{lunar.getDay():02d}")
                self.update_lunar_label()
        except: pass

    def sync_to_solar(self, event=None):
        text = self.lunar_entry.get().strip()
        if not text: return
        try:
            parts = text.replace('/', '-').split('-')
            if len(parts) == 3:
                lunar = Lunar.fromYmd(int(parts[0]), int(parts[1]), int(parts[2]))
                solar = lunar.getSolar()
                self.solar_entry.delete(0, 'end')
                self.solar_entry.insert(0, f"{solar.getYear()}-{solar.getMonth():02d}-{solar.getDay():02d}")
                self.update_lunar_label()
        except: pass

    def on_drag_start(self, event):
        self.configure(fg_color=("#D5D8DC", "#2C3E50"))
        self.master_app.current_drag_item = self

    def on_drag_motion(self, event):
        if not hasattr(self.master_app, 'current_drag_item') or self.master_app.current_drag_item != self:
            return
        y = self.winfo_pointery()
        for i, entry in enumerate(self.master_app.entries):
            if entry == self: continue
            ey1 = entry.winfo_rooty()
            ey2 = ey1 + entry.winfo_height()
            if ey1 < y < ey2:
                idx_self = self.master_app.entries.index(self)
                self.master_app.entries[idx_self], self.master_app.entries[i] = \
                    self.master_app.entries[i], self.master_app.entries[idx_self]
                self.master_app.repack_entries()
                break

    def on_drag_release(self, event):
        self.configure(fg_color=self.original_fg)
        self.master_app.current_drag_item = None

    def set_config(self, years, remind_days):
        self.years_entry.delete(0, 'end')
        self.years_entry.insert(0, str(years))
        self.remind_entry.delete(0, 'end')
        self.remind_entry.insert(0, str(remind_days))

    def delete_self(self):
        self.delete_callback(self)
        self.destroy()

    def get_data(self):
        try:
            return {
                "name": self.name_entry.get().strip(),
                "solar": self.solar_entry.get().strip(),
                "lunar": self.lunar_entry.get().strip(),
                "years": int(self.years_entry.get().strip() or 50),
                "remind_days": int(self.remind_entry.get().strip() or 7)
            }
        except: return None


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app = app_instance
        self.title("设置")
        self.geometry("380x380")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.after(10, self.center_window)

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

        # 3. 起始年份模式 (New in 0.0.006)
        frame_start_mode = ctk.CTkFrame(self, fg_color="transparent")
        frame_start_mode.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_start_mode, text="计算起始年份:").pack(pady=(0, 5))
        
        self.start_mode_var = ctk.StringVar(value=self.app.start_year_mode)
        self.start_mode_seg = ctk.CTkSegmentedButton(frame_start_mode, 
                                                     values=["今年", "出生年"],
                                                     variable=self.start_mode_var)
        self.start_mode_seg.pack(fill="x")

        # 按钮区
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="保存默认值", width=120, command=self.save_defaults).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="同步现有条目", width=120, fg_color="#D35400", command=self.apply_to_all).pack(side="left", padx=5)

        version_label = ctk.CTkLabel(self, text="version 0.0.006", text_color="gray", font=("Arial", 10))
        version_label.pack(side="bottom", pady=10)

    def center_window(self):
        self.grab_set() 

    def save_defaults(self):
        try:
            self.app.default_years = int(self.years_input.get())
            self.app.default_remind_days = int(self.remind_input.get())
            self.app.start_year_mode = self.start_mode_var.get()
            messagebox.showinfo("成功", "默认设置已保存。")
            self.destroy()
        except: messagebox.showerror("错误", "请输入数字")

    def apply_to_all(self):
        try:
            years = int(self.years_input.get())
            remind = int(self.remind_input.get())
            self.app.start_year_mode = self.start_mode_var.get()
            for entry in self.app.entries:
                entry.set_config(years, remind)
            messagebox.showinfo("成功", "已同步所有条目设置。")
            self.destroy()
        except: messagebox.showerror("错误", "请输入数字")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("农历生日生成工具")
        self.geometry("980x680")
        
        # 配置存储
        self.default_years = 50
        self.default_remind_days = 7
        self.start_year_mode = "今年" # "今年" 或 "出生年"
        
        self.entries = []
        self.settings_window = None
        self.current_drag_item = None

        # 表头
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 0))
        headers = [("姓名", 80), ("公历生日", 110), ("农历生日", 110), ("农历详情", 140), 
                   ("推算年数", 50), ("提前天数", 50), ("排序", 30), ("操作", 40)]
        for i, (text, width) in enumerate(headers):
            ctk.CTkLabel(header_frame, text=text, width=width).grid(row=0, column=i, padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.add_btn = ctk.CTkButton(self, text="+ 添加新条目", command=self.add_entry)
        self.add_btn.pack(pady=5)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", padx=20, pady=20)

        self.settings_btn = ctk.CTkButton(bottom_frame, text="⚙️ 设置", width=70, fg_color="gray", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=(0, 10))

        self.save_btn = ctk.CTkButton(bottom_frame, text="💾 保存配置", width=90, fg_color="#27AE60", command=self.save_config)
        self.save_btn.pack(side="left", padx=(0, 10))

        self.load_btn = ctk.CTkButton(bottom_frame, text="📂 读取配置", width=90, fg_color="#F39C12", command=self.load_config)
        self.load_btn.pack(side="left")

        self.generate_btn = ctk.CTkButton(bottom_frame, text="🚀 生成 ICS 文件", width=180, height=40, font=("Arial", 14, "bold"), command=self.generate_ics)
        self.generate_btn.pack(side="right")

        self.add_entry()

    def add_entry(self, data=None):
        entry = BirthdayEntry(self, self.scroll_frame, delete_callback=self.remove_entry, 
                              default_years=self.default_years, default_remind=self.default_remind_days)
        if data:
            entry.name_entry.insert(0, data.get("name", ""))
            entry.solar_entry.insert(0, data.get("solar", ""))
            entry.lunar_entry.insert(0, data.get("lunar", ""))
            entry.set_config(data.get("years", self.default_years), data.get("remind_days", self.default_remind_days))
            entry.update_lunar_label()
        entry.pack(fill="x", pady=2)
        self.entries.append(entry)

    def repack_entries(self):
        for entry in self.entries: entry.pack_forget()
        for entry in self.entries: entry.pack(fill="x", pady=2)

    def remove_entry(self, entry):
        if entry in self.entries: self.entries.remove(entry)

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self)
        else:
            self.settings_window.focus()
            self.settings_window.lift()

    def save_config(self):
        data_to_save = {
            "default_years": self.default_years,
            "default_remind_days": self.default_remind_days,
            "start_year_mode": self.start_year_mode,
            "entries": [entry.get_data() for entry in self.entries if entry.get_data()]
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Config Files", "*.json")])
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "配置已保存。")

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Config Files", "*.json")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.default_years = data.get("default_years", 50)
            self.default_remind_days = data.get("default_remind_days", 7)
            self.start_year_mode = data.get("start_year_mode", "今年")
            for entry in list(self.entries): entry.delete_self()
            for edata in data.get("entries", []): self.add_entry(data=edata)
            if not self.entries: self.add_entry()
            messagebox.showinfo("成功", "配置已读取。")

    def generate_ics(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".ics", filetypes=[("iCalendar Files", "*.ics")])
        if not file_path: return

        ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Lunar Tool v0.0.006//CN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
        current_year = datetime.datetime.now().year

        count = 0
        for entry in self.entries:
            data = entry.get_data()
            if not data or not data["name"] or not data["lunar"]: continue
            
            try:
                parts = data["lunar"].split('-')
                birth_year = int(parts[0])
                l_month, l_day = int(parts[1]), int(parts[2])
                
                # 决定起始推算年份
                calc_start_year = current_year if self.start_year_mode == "今年" else birth_year

                for offset in range(data["years"]):
                    target_y = calc_start_year + offset
                    try:
                        l_date = Lunar.fromYmd(target_y, l_month, l_day)
                        s_date = l_date.getSolar()
                        
                        dt_start = f"{s_date.getYear():04d}{s_date.getMonth():02d}{s_date.getDay():02d}"
                        end_dt = datetime.date(s_date.getYear(), s_date.getMonth(), s_date.getDay()) + datetime.timedelta(days=1)
                        dt_end = end_dt.strftime("%Y%m%d")

                        ics_lines.extend([
                            "BEGIN:VEVENT",
                            f"UID:{uuid.uuid4().hex}",
                            f"DTSTAMP:{datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                            f"DTSTART;VALUE=DATE:{dt_start}",
                            f"DTEND;VALUE=DATE:{dt_end}",
                            f"SUMMARY:{data['name']}的农历生日",
                            f"DESCRIPTION:农历 {l_month}月{l_day}日",
                            "BEGIN:VALARM",
                            "ACTION:DISPLAY",
                            f"TRIGGER:-P{data['remind_days']}D",
                            f"DESCRIPTION:提醒：{data['name']}的农历生日快到了",
                            "END:VALARM",
                            "END:VEVENT"
                        ])
                    except: continue # 处理闰月等特殊情况
                count += 1
            except: continue

        ics_lines.append("END:VCALENDAR")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\r\n".join(ics_lines))
        messagebox.showinfo("完成", f"已成功为 {count} 个对象生成日历。")

if __name__ == "__main__":
    App().mainloop()