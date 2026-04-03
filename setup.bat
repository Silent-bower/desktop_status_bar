@echo off
chcp 65001 >nul 2>&1
title 桌面状态栏 - 安装程序

echo ══════════════════════════════════════
echo   桌面状态栏 安装程序
echo ══════════════════════════════════════
echo.

:: Step 1: Install Python dependency
echo [1/3] 安装 Python 依赖 (psutil)...
pip install psutil -q
if %errorlevel% neq 0 (
    echo      ✗ psutil 安装失败，请检查 Python 环境
    pause
    exit /b 1
)
echo      ✓ psutil 已安装

:: Step 2: Create startup VBS launcher
echo [2/3] 设置开机自启动...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_DIR%\DesktopStatusBar.vbs"
set "SCRIPT_DIR=%~dp0"

:: Use PowerShell to create the VBS file with an explicit pythonw path
powershell -NoProfile -Command ^
  "$python = (Get-Command python.exe -ErrorAction Stop).Source; $pythonw = Join-Path (Split-Path $python) 'pythonw.exe'; if (-not (Test-Path $pythonw)) { $pythonw = 'pythonw.exe' }; $script = Join-Path '%SCRIPT_DIR%' 'status_bar.pyw'; $vbs = @('Set oShell = CreateObject(""WScript.Shell"")', 'oShell.Run """"' + $pythonw + '"" ""' + $script + '"""", 0, False') -join [Environment]::NewLine; Set-Content -Path '%VBS_FILE%' -Value $vbs -Encoding Default"

if exist "%VBS_FILE%" (
    echo      ✓ 已添加到启动项
) else (
    echo      ✗ 启动项创建失败，请手动将 status_bar.pyw 添加到启动文件夹
    echo        启动文件夹: %STARTUP_DIR%
)

:: Step 3: Launch now
echo [3/3] 启动状态栏...
echo.
start "" pythonw "%~dp0status_bar.pyw"

echo ══════════════════════════════════════
echo   安装完成！
echo.
echo   • 状态栏已启动，显示在屏幕右侧
echo   • 已设置开机自动启动
echo   • 可通过编辑 config.json 自定义配置
echo   • 拖动标题栏可移动位置
echo   • 点击 ✕ 关闭状态栏
echo ══════════════════════════════════════
echo.
pause
