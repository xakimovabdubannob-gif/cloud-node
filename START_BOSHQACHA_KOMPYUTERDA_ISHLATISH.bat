@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
if exist "%~dp0cluster_worker.py" set "TARGET_DIR=%~dp0"
if exist "D:\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=D:\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

where curl.exe >nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/cluster_worker.py" -o "%TARGET_DIR%\cluster_worker.py" --silent
)

if not exist "%TARGET_DIR%\cluster_worker.py" (
    echo Kodlar yuklanmoqda...
    where curl.exe >nul 2>&1
    if %errorlevel% equ 0 (
        curl.exe -L "https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip" -o "%TEMP%\master.zip" --silent
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip', '%TEMP%\master.zip')"
    )
    if exist "%TEMP%\master.zip" (
        where tar.exe >nul 2>&1
        if %errorlevel% equ 0 (
            tar.exe -xf "%TEMP%\master.zip" -C "%TEMP%"
        ) else (
            powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\master.zip' -DestinationPath '%TEMP%' -Force"
        )
        if exist "%TEMP%\cloud-node-master" (
            xcopy /E /Y /Q "%TEMP%\cloud-node-master\*" "%TARGET_DIR%\" >nul 2>&1
            rd /s /q "%TEMP%\cloud-node-master" >nul 2>&1
        )
        del /f /q "%TEMP%\master.zip" >nul 2>&1
    )
)

set WORKER_COUNT=4
set HEADLESS=1
set GUI_MODE=0

start /min "" python -u "%TARGET_DIR%\cluster_worker.py"

echo ======================================================================
echo  [OK] AI AGENT ISHGA TUSHIRILDI!
echo ======================================================================
echo.
echo  Kompyuter botga ulanmoqda...
echo  Xabarlar to'g'ridan-to'g'ri Telegram botingizga yuboriladi.
echo.
echo  Ushbu oyna 3 soniyada avtomatik yopiladi...
timeout /t 3 >nul
exit