"""生成前预览窗口：先看清要写入什么，再决定保存。"""

import customtkinter as ctk

from .helpers import center_on_parent


class PreviewWindow(ctk.CTkToplevel):
    """生成前预览：先看清要写入什么，再决定保存。"""

    def __init__(self, master, events, stats, on_save):
        super().__init__(master)
        self.on_save = on_save
        self.title("生成预览")
        self.geometry("660x540")
        self.transient(master)
        self.resizable(False, False)

        grouped = {}
        for event in events:
            grouped.setdefault(event["person"], []).append(event)

        summary = f"将生成 {stats['events']} 条事件，覆盖 {len(grouped)} 人"
        if stats["past"]:
            summary += f"，已跳过 {stats['past']} 条历史事件"
        if stats.get("fallback"):
            summary += f"，{stats['fallback']} 条日期补偿"
        ctk.CTkLabel(self, text=summary, font=("Arial", 14, "bold")).pack(pady=(16, 6), padx=20, anchor="w")

        textbox = ctk.CTkTextbox(self, width=600, height=330)
        textbox.pack(padx=20, pady=6, fill="both", expand=True)
        rows = []
        for person, person_events in grouped.items():
            person_events.sort(key=lambda item: item["date"])
            samples = " / ".join(item["date"].isoformat() for item in person_events[:3])
            category = person_events[0].get("category", "")
            prefix = f"[{category}] " if category else ""
            rows.append(f"{prefix}{person}（{len(person_events)} 次）：{samples} …")
        textbox.insert("1.0", "\n".join(rows))
        notes = stats.get("notes", [])
        if notes:
            textbox.insert("end", "\n\n提示：\n" + "\n".join(notes[:8]))
            if len(notes) > 8:
                textbox.insert("end", f"\n… 另有 {len(notes) - 8} 条")
        textbox.configure(state="disabled")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=14)
        ctk.CTkButton(buttons, text="保存 ICS", width=130, fg_color="#27AE60", command=self._save).pack(
            side="left", padx=8
        )
        ctk.CTkButton(buttons, text="取消", width=90, fg_color="gray", command=self.destroy).pack(
            side="left", padx=8
        )
        self.after(120, self._show_centered)

    def _show_centered(self):
        center_on_parent(self, self.master)
        self.grab_set()

    def _save(self):
        self.destroy()
        self.on_save()
