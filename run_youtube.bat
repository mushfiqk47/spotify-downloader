@echo off
title YouTube Downloader
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw youtube_downloader.py
) else (
    python youtube_downloader.py
    if errorlevel 1 (
        echo.
        echo An error occurred while running YouTube Downloader.
        pause
    )
)
