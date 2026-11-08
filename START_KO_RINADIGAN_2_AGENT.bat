@echo off
chcp 65001 >nul
title UZBEK CODERS - 2 TA AGENT (KO'RINADIGAN / EKRANDA REJIM)
color 0B

:: 1. Papkani avtomatik aniqlash (Har qanday kompyuterda ishlaydi!)
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if exist "d:\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=d:\uzbekcodersbot"
if exist "%USERPROFILE%\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

echo ======================================================================
echo    UZBEK CODERS BOT - 2 TA AGENT (KO'RINADIGAN REJIM)
echo ======================================================================
echo.
echo  Papka: %TARGET_DIR%
echo.

:: 2. Agar yangi kompyuterda fayllar bo'lmasa, GitHub'dan avtomat yuklab oladi
if not exist "cluster_worker.py" (
    echo  [YUKLANMOQDA] Yangi kompyuter uchun kerakli fayllar GitHub'dan olinmoqda...
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/cluster_worker.py" -o "cluster_worker.py"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py" -o "master_certified_pipeline.py"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/bot_config.json" -o "bot_config.json"
    curl.exe -sL "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/cluster_url.txt" -o "cluster_url.txt"
    echo  [OK] Fayllar muvaffaqiyatli yuklandi!
    echo.
)

echo  [1/2] GitHub Master Serverga ulanmoqda...
echo  [2/2] 2 ta Chrome oynasi ekranning chap va o'ng tomonida ochilmoqda...
echo.
echo  Jarayonni ko'z oldingizda jonli kuzatishingiz mumkin!
echo ======================================================================
echo.

set HEADLESS=0
set GUI_MODE=1
set WORKER_COUNT=2

python -u cluster_worker.py https://med-infringement-steven-responsible.trycloudflare.com
pause
