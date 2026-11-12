# 构建 Windows 单文件可执行程序：dist\LunarBirthday.exe
# 用法：powershell -ExecutionPolicy Bypass -File .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name LunarBirthday `
    --collect-data customtkinter `
    --hidden-import lunar_python `
    lunar_alarm.py

Write-Host "构建完成：$PSScriptRoot\dist\LunarBirthday.exe"
