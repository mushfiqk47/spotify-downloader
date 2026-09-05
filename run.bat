@echo off
title StreamRip Core
chcp 65001 >nul
cd /d "%~dp0"

REM Prefer Electron desktop shell, fall back to browser mode.
if exist "node_modules\electron\dist\electron.exe" (
    echo Starting StreamRip Core Desktop Window...
    call npm start
    goto :eof
)

echo Electron not installed. Launching in default browser...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please run setup.bat first.
    pause
    exit /b 1
)
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running StreamRip Core.
    pause
)
