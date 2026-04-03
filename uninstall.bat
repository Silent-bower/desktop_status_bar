@echo off
chcp 65001 >nul 2>&1
title 桌面状态栏 - 卸载

echo 正在移除开机自启动...
set "VBS_FILE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DesktopStatusBar.vbs"

if exist "%VBS_FILE%" (
    del "%VBS_FILE%"
    echo ✓ 已从启动项移除
) else (
    echo   启动项不存在，无需移除
)

echo.
echo 卸载完成。状态栏文件保留在当前目录，可手动删除。
pause
