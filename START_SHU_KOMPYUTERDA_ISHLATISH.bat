@echo off
chcp 65001 >nul
title UZBEK CODERS - 4 TA AGENT (KO'RINMAS / ORQA FONDA TEZKOR REJIM)
color 0A

:: 1. Papkani avtomatik aniqlash (Har qanday kompyuterda ishlaydi!)
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if exist "d:\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=d:\uzbekcodersbot"
if exist "%USERPROFILE%\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

echo ======================================================================
echo    UZBEK CODERS BOT - 4 TA AGENT (KO'RINMAS / ORQA FONDA REJIM)
echo ======================================================================
echo.
echo  Papka: %TARGET_DIR%
echo.

:: 2. Agar yangi kompyuterda fayllar bo'lmasa, GitHub'dan avtomat yuklab oladi
if not exist "cluster_worker.py" (
    echo  [YUKLANMOQDA] Yangi kompyuter uchun kerakli fayllar GitHub'dan olinmoqda...
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_worker.py" -o "cluster_worker.py"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py" -o "master_certified_pipeline.py"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/bot_config.json" -o "bot_config.json"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/main/cluster_url.txt" -o "cluster_url.txt"
    echo  [OK] Fayllar muvaffaqiyatli yuklandi!
    echo.
)

:: 3. Agar shu kompyuterda master bridge hali ishlamayotgan bo'lsa, o'zi avtomat fon rejimida yoqadi
if exist "cluster_master_bridge.py" (
    powershell -NoProfile -Command "try { $r = [System.Net.WebRequest]::Create('http://127.0.0.1:8766/cluster/ping').GetResponse(); exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        echo  [1/3] Master Server fonda ishga tushirilmoqda...
        start "" /min python cluster_master_bridge.py
        timeout /t 3 /nobreak >nul
    )
)

echo  [2/3] Master Server tekshirilmoqda...
echo  [3/3] 4 ta AI Agent orqa fonda (ko'rinmas rejimda) ishga tushmoqda...
echo.
echo  Brauzer oynalari kompyuterni band qilmaydi,
echo  orqa fonda 4 barobar tezlikda buyurtmalar bajariladi!
echo ======================================================================
echo.

set HEADLESS=1
set GUI_MODE=0
set WORKER_COUNT=4

python -u cluster_worker.py
pause
