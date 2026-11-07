@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AI AGENT (BOSHQACHA KOMPYUTERLAR UCHUN)
color 0A

set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
cd /d "%TARGET_DIR%"

echo ======================================================================
echo    UZBEK CODERS - UNIVERSAL AI AGENT (HAR QANDAY KOMPYUTER UCHUN)
echo ======================================================================
echo.
echo [1/3] Eng so'nggi 100%% mukammal kod GitHub'dan yangilanmoqda...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip', '%TEMP%\master.zip'); Expand-Archive -Path '%TEMP%\master.zip' -DestinationPath '%TEMP%\extracted' -Force; Copy-Item -Path '%TEMP%\extracted\cloud-node-master\*' -Destination '%TARGET_DIR%' -Recurse -Force; Remove-Item '%TEMP%\master.zip', '%TEMP%\extracted' -Recurse -Force -ErrorAction SilentlyContinue"

echo [2/3] Kerakli kutubxonalar tekshirilmoqda...
python -c "import requests, playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python kutubxonalari o'rnatilmoqda (requests, playwright)...
    python -m pip install --quiet requests openpyxl playwright
    python -m playwright install chromium
)

echo.
echo [3/3] Agent ishga tushirilmoqda va GitHub Master Serverga ulanmoqda...
echo ======================================================================
set WORKER_COUNT=6
set HEADLESS=1
set GUI_MODE=0
python -u cluster_worker.py
pause
