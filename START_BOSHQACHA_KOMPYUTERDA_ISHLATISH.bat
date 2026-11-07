@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

echo ======================================================================
echo    UZBEK CODERS - UNIVERSAL AVTOMAT AI AGENT
echo ======================================================================
echo.

set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
cd /d "%TARGET_DIR%"

echo [1/3] Kodlar GitHub'dan avtomatik yuklab olinmoqda...
curl.exe -L "https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip" -o "%TEMP%\master.zip" --progress-bar
if exist "%TEMP%\master.zip" (
    tar.exe -xf "%TEMP%\master.zip" -C "%TEMP%"
    xcopy /E /Y /Q "%TEMP%\cloud-node-master\*" "%TARGET_DIR%\" >nul
    del /f /q "%TEMP%\master.zip" >nul 2>&1
    rd /s /q "%TEMP%\cloud-node-master" >nul 2>&1
) else (
    echo [!] curl ishlamadi, PowerShell orqali yuklanmoqda...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip', '%TEMP%\master.zip'); Expand-Archive -Path '%TEMP%\master.zip' -DestinationPath '%TEMP%\extracted' -Force; Copy-Item -Path '%TEMP%\extracted\cloud-node-master\*' -Destination '%TARGET_DIR%' -Recurse -Force; Remove-Item '%TEMP%\master.zip', '%TEMP%\extracted' -Recurse -Force -ErrorAction SilentlyContinue"
)

echo.
echo [2/3] Kutubxonalar tekshirilmoqda...
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
echo.
echo Jarayon to'xtadi. Qayta ishga tushirish uchun istalgan tugmani bosing...
pause
