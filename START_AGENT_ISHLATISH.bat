@echo off
chcp 65001 >nul
title UZBEK CODERS - AI AGENT WORKER (UZBEKISTON MILLIY IP)
color 0A

if exist "%~dp0cluster_worker.py" (
    cd /d "%~dp0"
) else if exist "D:\uzbekcodersbot\cluster_worker.py" (
    cd /d "D:\uzbekcodersbot"
) else if exist "%USERPROFILE%\UzbekCoders_Cluster_Node\cluster_worker.py" (
    cd /d "%USERPROFILE%\UzbekCoders_Cluster_Node"
)

echo ======================================================================
echo    UZBEK CODERS - AI AGENT (UZBEKISTON MILLIY IP)
echo ======================================================================
echo.
echo  [VAZIFA] GitHub Cloud Master Serverga avtomatik ulanish va
echo           buyurtmalarni 6 ta oqimda parallel bajarish.
echo  [EKRAN]  Orqa fonda (yashirin) ishlaydi, ekranni to'smaydi.
echo.
echo ======================================================================
echo  1. Eng so'nggi kod tekshirilmoqda...
echo ======================================================================
where git >nul 2>&1
if %errorlevel% equ 0 (
    git pull origin master 2>nul
)
echo.
echo ======================================================================
echo  2. Agent ishga tushirilmoqda va GitHub Master Serverga ulanmoqda...
echo ======================================================================
set WORKER_COUNT=6
set HEADLESS=1
set GUI_MODE=0
python -u cluster_worker.py
pause
