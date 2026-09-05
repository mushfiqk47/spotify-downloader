@echo off
title MediaFetch
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw main.py
) else (
    python main.py
    if errorlevel 1 (
        echo.
        echo An error occurred while running MediaFetch.
        pause
    )
)
