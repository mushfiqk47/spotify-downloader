@echo off
title SpotFetch - Spotify Downloader
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw spotify_downloader.py
) else (
    python spotify_downloader.py
    if errorlevel 1 (
        echo.
        echo An error occurred while running SpotFetch.
        pause
    )
)
