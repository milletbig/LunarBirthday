"""界面通用小工具。"""


def center_on_parent(window, parent=None):
    """把顶层窗口真正居中到父窗口（父窗口不可用时居中到屏幕）。

    窗口装饰（边框、标题栏）会让 geometry 的外框位置与客户区错位，
    因此在首次定位前记录一次偏移并复用，保证重复调用也不会漂移。
    """
    parent = parent or window.master
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    if width <= 1:
        width = window.winfo_reqwidth()
    if height <= 1:
        height = window.winfo_reqheight()

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    if parent is not None and parent.winfo_exists():
        parent.update_idletasks()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        if parent_width > 1 and parent_height > 1:
            x = parent.winfo_rootx() + (parent_width - width) // 2
            y = parent.winfo_rooty() + (parent_height - height) // 2

    if not hasattr(window, "_decoration_offset"):
        window._decoration_offset = (
            window.winfo_rootx() - window.winfo_x(),
            window.winfo_rooty() - window.winfo_y(),
        )
    offset_x, offset_y = window._decoration_offset

    x = max(0, min(x, screen_width - width))
    y = max(0, min(y, screen_height - height))
    window.geometry(f"+{x - offset_x}+{y - offset_y}")
