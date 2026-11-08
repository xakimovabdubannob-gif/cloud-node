@echo off
chcp 65001 >nul
title UZBEK CODERS - BOSHQACHA KOMPYUTER (2 TA AGENT EKRANDA KO'RINADIGAN)
color 0A

:: 1. Papkani avtomatik aniqlash (Har qanday kompyuterda ishlaydi!)
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if exist "d:\uzbekcodersbot\cluster_worker.py?t=%RANDOM%%RANDOM%" set "TARGET_DIR=d:\uzbekcodersbot"
if exist "%USERPROFILE%\uzbekcodersbot\cluster_worker.py?t=%RANDOM%%RANDOM%" set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

echo ======================================================================
echo    UZBEK CODERS BOT - BOSHQACHA KOMPYUTER (2 TA AGENT KO'RINADIGAN)
echo ======================================================================
echo.
echo  Papka: %TARGET_DIR%
echo.

:: 2. Eski qotib qolgan profillarni tozalash (Muhammadumar va b. butunlay o'chadi)
rd /s /q "%USERPROFILE%\.real_chrome_user_prof_1" >nul 2>&1
rd /s /q "%USERPROFILE%\.real_chrome_user_prof_2" >nul 2>&1
rd /s /q "%USERPROFILE%\.real_chrome_user_prof_3" >nul 2>&1
rd /s /q "%USERPROFILE%\.real_chrome_user_prof_4" >nul 2>&1
rd /s /q "%TEMP%\clean_chrome_prof_w1" >nul 2>&1
rd /s /q "%TEMP%\clean_chrome_prof_w2" >nul 2>&1
rd /s /q "%TEMP%\clean_chrome_prof_w3" >nul 2>&1
rd /s /q "%TEMP%\clean_chrome_prof_w4" >nul 2>&1

:: 3. Python bor-yo'qligini tekshirish
where python >nul 2>&1
if errorlevel 1 (
    echo [XATOLIK] Ushbu kompyuterda Python topilmadi!
    echo Iltimos, https://www.python.org saytidan Python 3.10 yoki 3.11 ni o'rnating.
    echo O'rnatishda "Add python.exe to PATH" katagiga belgi qo'yishni unutmang!
    echo.
    pause
    exit /b 1
)

:: 4. Eng so'nggi 100%% xatosiz kodlarni GitHub'dan yangilab olish
echo  [YANGILANMOQDA] Eng so'nggi xatosiz kodlar GitHub'dan olinmoqda...
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_worker.py?t=%RANDOM%%RANDOM%" -o "cluster_worker.py?t=%RANDOM%%RANDOM%"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py?t=%RANDOM%%RANDOM%" -o "master_certified_pipeline.py?t=%RANDOM%%RANDOM%"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/bot_config.json?t=%RANDOM%%RANDOM%" -o "bot_config.json?t=%RANDOM%%RANDOM%"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_url.txt?t=%RANDOM%%RANDOM%" -o "cluster_url.txt?t=%RANDOM%%RANDOM%"
echo  [OK] Barcha kodlar eng so'nggi holatga yangilandi!
echo.

:: 5. Kutubxonalar tekshiruvi
python -c "import requests, openpyxl, playwright" >nul 2>&1
if errorlevel 1 (
    echo  [O'RNATILMOQDA] Bir martalik kerakli kutubxonalar o'rnatilmoqda...
    python -m pip install --quiet --disable-pip-version-check requests openpyxl playwright pillow
    python -m playwright install chromium
    echo  [OK] Kutubxonalar tayyor!
    echo.
)

echo  [1/2] Telegram / GitHub orqali Asosiy Master Server qidirilmoqda...
echo  [2/2] 2 ta Chrome oynasi ekranning chap va o'ng tomonida ochilmoqda...
echo.
echo  Jarayonni ko'z oldingizda jonli kuzatishingiz mumkin!
echo ======================================================================
echo.

set HEADLESS=0
set GUI_MODE=1
set WORKER_COUNT=2

python -u cluster_worker.py
pause
