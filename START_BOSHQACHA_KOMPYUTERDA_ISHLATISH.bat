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

echo [1/3] Kodlar GitHub'dan avtomatik yuklanmoqda...
where curl.exe >nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -L "https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip" -o "%TEMP%\master.zip" --progress-bar
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
    echo [OK] Kodlar muvaffaqiyatli yangilandi!
) else (
    echo [DIQQAT] Internetdan yangi kod olinmadi, mavjud fayllar bilan davom etiladi...
)

echo.
echo [2/3] Kerakli kutubxonalar tekshirilmoqda...
python -c "import requests, openpyxl, playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Kerakli kutubxonalar o'rnatilmoqda (requests, openpyxl, playwright)...
    call python -m pip install requests openpyxl playwright --no-warn-script-location
)
echo [OK] Kutubxonalar tayyor!

echo.
echo [3/3] Agent ishga tushirilmoqda va GitHub Master Serverga ulanmoqda...
echo ======================================================================
set WORKER_COUNT=6
set HEADLESS=1
set GUI_MODE=0
call python -u cluster_worker.py

echo.
echo ======================================================================
echo Jarayon to'xtadi yoki tugadi. Oynani yopish uchun istalgan tugmani bosing...
echo ======================================================================
pause
