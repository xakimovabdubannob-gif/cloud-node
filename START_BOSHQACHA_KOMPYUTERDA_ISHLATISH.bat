@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
if exist "%~dp0cluster_worker.py?t=%RANDOM%%RANDOM%" set "TARGET_DIR=%~dp0"
if exist "D:\uzbekcodersbot\cluster_worker.py?t=%RANDOM%%RANDOM%" set "TARGET_DIR=D:\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

where curl.exe >nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py?t=%RANDOM%%RANDOM%" -o "%TARGET_DIR%\master_certified_pipeline.py?t=%RANDOM%%RANDOM%" --silent
    curl.exe -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/cluster_worker.py?t=%RANDOM%%RANDOM%" -o "%TARGET_DIR%\cluster_worker.py?t=%RANDOM%%RANDOM%" --silent
)

set WORKER_COUNT=6
set HEADLESS=0
set GUI_MODE=1

start "" python -u "%TARGET_DIR%\cluster_worker.py?t=%RANDOM%%RANDOM%"

echo ======================================================================
echo  [OK] CHROME OCHIQ HOLATDA 6 TA AGENT BILAN ISHGA TUSHIRILDI!
echo ======================================================================
echo.
echo  Ekranda Chrome oynalari jonli ko'rinib ishlaydi.
echo  Ushbu oyna 3 soniyada yopiladi...
timeout /t 3 >nul
exit