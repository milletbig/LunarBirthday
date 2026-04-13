# 🌙 农历生日提醒生成工具 (Lunar Birthday Calendar Generator)

![Version](https://img.shields.io/badge/version-0.0.005-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-orange)

## 📖 项目简介

在现代数字生活中，主流的日历软件（如 Google Calendar、Outlook、iOS 日历等）通常很难完美支持**每年重复的农历生日提醒**。

本项目是一个基于 Python 和 CustomTkinter 开发的桌面端小工具。它可以将你亲友的农历生日，一键批量推算并转换为未来数十年（默认 50 年）的公历日期，最终生成一个标准的 `.ics` 日历文件。你只需将该文件导入手机或电脑的日历应用，即可实现完美的农历生日周期性提醒！

---

## ✨ 核心功能

- **🔄 双向自动换算**：只需输入公历或农历其一，按下回车即可自动补全另一项。
- **📅 传统农历显示**：自动解析并显示传统干支纪年与中文农历日期（如：`1992壬申年九月廿八`）。
- **⚙️ 高度可定制**：
  - 支持为每个人独立设置**推算年数**（默认 50 年）。
  - 支持设置**提前提醒天数**（默认提前 7 天通知）。
- **🖱️ 现代化交互**：基于 CustomTkinter 的深色模式 UI，支持**鼠标拖拽**对条目进行自由排序。
- **💾 配置本地存储**：支持将录入的亲友名单保存为本地 `.json` 文件，下次打开一键读取，告别重复输入。
- **🌐 跨平台兼容**：生成的 `.ics` (iCalendar) 文件支持导入苹果生态、Google 日历、Outlook 以及小米、华为等主流安卓日历。