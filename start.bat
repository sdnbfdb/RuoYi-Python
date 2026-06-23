@echo off
chcp 65001 >nul
echo.
echo  ============================================
echo   月薪猫 ASCII Art
echo  ============================================
echo.
cd /d "%~dp0"

REM 检查 Python 是否可用
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3
    pause
    exit /b 1
)

REM 检查依赖
python -c "from PIL import Image" >nul 2>&1
if errorlevel 1 (
    echo [提示] 缺少 Pillow 库，正在安装...
    pip install Pillow numpy -q
)

REM 运行 ASCII 转换脚本
python back\ascii_cat.py

pause
