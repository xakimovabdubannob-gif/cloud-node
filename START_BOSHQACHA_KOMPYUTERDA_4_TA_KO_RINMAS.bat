@echo off
chcp 65001 >nul
title UZBEK CODERS - BOSHQACHA KOMPYUTER (4 TA AGENT YOPIQ REJIM)
color 0A

:: 1. Papkani avtomatik aniqlash (Har qanday kompyuterda ishlaydi!)
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if exist "d:\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=d:\uzbekcodersbot"
if exist "%USERPROFILE%\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

echo ======================================================================
echo    UZBEK CODERS BOT - 8GB RAM (4 TA AGENT YOPIQ REJIM)
echo ======================================================================
echo.
echo  Papka: %TARGET_DIR%
echo.

:: 2. Eski qotib qolgan profillarni tozalash (1 dan 4 gacha)
for /L %%i in (1,1,4) do (
    rd /s /q "%USERPROFILE%\.real_chrome_user_prof_%%i" >nul 2>&1
    rd /s /q "%TEMP%\clean_chrome_prof_w%%i" >nul 2>&1
)

:: 3. Python tekshiruvi
where python >nul 2>&1
if errorlevel 1 (
    echo [XATOLIK] Ushbu kompyuterda Python topilmadi!
    echo Iltimos, Python 3.10 yoki 3.11 o'rnating ("Add to PATH" belgisi bilan).
    pause
    exit /b 1
)

:: 4. Eng so'nggi xatosiz kodlarni GitHub'dan yuklab olish
echo  [YANGILANMOQDA] Eng so'nggi xatosiz kodlar GitHub'dan olinmoqda...
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_worker.py?t=%RANDOM%%RANDOM%" -o "cluster_worker.py"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py?t=%RANDOM%%RANDOM%" -o "master_certified_pipeline.py"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/bot_config.json?t=%RANDOM%%RANDOM%" -o "bot_config.json"
curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_url.txt?t=%RANDOM%%RANDOM%" -o "cluster_url.txt"
echo  [OK] Barcha kodlar eng so'nggi holatga yangilandi!
echo.

:: 5. Kutubxonalar tekshiruvi
python -c "import requests, openpyxl, playwright" >nul 2>&1
if errorlevel 1 (
    echo  [O'RNATILMOQDA] Kerakli kutubxonalar o'rnatilmoqda...
    python -m pip install --quiet --disable-pip-version-check requests openpyxl playwright pillow
    python -m playwright install chromium
    echo  [OK] Kutubxonalar tayyor!
    echo.
)

echo  [1/2] Master Server qidirilmoqda...
echo  [2/2] 4 ta AI Agent orqa fonda (yopiq brauzerda) ishga tushmoqda...
echo.
echo  Kompyuter ekrani butunlay bo'sh qoladi, 4 barobar tezlikda ishlaydi!
echo ======================================================================
echo.

set HEADLESS=1
set GUI_MODE=0
set WORKER_COUNT=4

python -u cluster_worker.py
pause
