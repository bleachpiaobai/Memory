@echo off
chcp 65001 >nul
cd /d "H:\Wallpaper"

echo ============================================
echo   壁纸自动切换工具
echo ============================================
echo.
echo 正在启动...

where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" /min pythonw "H:\Wallpaper\wallpaper_switcher.pyw"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        start "" /min python "H:\Wallpaper\wallpaper_switcher.pyw"
    ) else (
        echo [错误] 未找到 Python! 请先安装 Python 并添加到 PATH
        echo 下载: https://www.python.org/downloads/
        echo 安装时请勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
)

echo 壁纸切换工具已在后台启动!
echo 日志文件: H:\Wallpaper\wallpaper_switcher.log
echo.
echo 关闭此窗口不影响壁纸切换。
timeout /t 2 >nul
exit
