@echo off
title MediaFetch - Setup
chcp 65001 >nul

echo ============================================
echo   MediaFetch - Environment Setup
echo ============================================
echo.

REM --- Check Python ---
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://python.org (make sure to check 'Add Python to PATH') and re-run this setup.
    pause
    exit /b 1
)
echo [OK] Python detected

REM --- Check pip ---
python -m pip --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pip is not available.
    pause
    exit /b 1
)
echo [OK] pip detected

echo.
echo Installing / updating spotdl, yt-dlp, and dependencies...
echo.
python -m pip install --upgrade pip --quiet
python -m pip install --upgrade spotdl spotapi spotipyfree yt-dlp --quiet

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Package installation failed. Please check your internet connection.
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully.
echo.

REM --- Create default output folders ---
set "SPOTIFY_OUT=%USERPROFILE%\Music\SpotifyDownloads"
if not exist "%SPOTIFY_OUT%" (
    mkdir "%SPOTIFY_OUT%"
    echo [OK] Created folder: %SPOTIFY_OUT%
) else (
    echo [OK] Folder exists: %SPOTIFY_OUT%
)

set "YOUTUBE_OUT=%USERPROFILE%\Videos\YouTubeDownloads"
if not exist "%YOUTUBE_OUT%" (
    mkdir "%YOUTUBE_OUT%"
    echo [OK] Created folder: %YOUTUBE_OUT%
) else (
    echo [OK] Folder exists: %YOUTUBE_OUT%
)

echo.
echo ============================================
echo   Setup Complete!
echo   Double-click run.bat to launch MediaFetch.
echo ============================================
pause
