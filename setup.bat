@echo off
title StreamRip Core - Setup
chcp 65001 >nul

echo ============================================
echo   StreamRip Core - Environment Setup (Windows)
echo ============================================
echo.

REM --- Check Python ---
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11+ from https://python.org (check 'Add Python to PATH') and re-run this setup.
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
echo Installing Python dependencies from requirements.txt...
echo.
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Package installation failed. Please check your internet connection.
    pause
    exit /b 1
)

echo [OK] Python dependencies installed (flask, yt-dlp, spotdl, imageio-ffmpeg for bundled ffmpeg).
echo.

REM --- Check Node / npm for Electron desktop ---
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] npm not found. Electron desktop packaging will be skipped.
    echo     Install Node.js 20 LTS from https://nodejs.org to build the .exe installer.
) else (
    echo Installing Electron dependencies...
    call npm install
    echo [OK] Node modules installed.
)
echo.

REM --- Verify bundled ffmpeg source ---
python -c "import imageio_ffmpeg; print('[OK] ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"
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
echo   Run run.bat to launch, or npm run pack for the .exe installer.
echo ============================================
pause
