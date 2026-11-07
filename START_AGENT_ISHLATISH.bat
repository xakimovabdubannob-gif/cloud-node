@echo off
cd /d "%~dp0"
chcp 65001 >nul
title UZBEK CODERS - AI AGENT WORKER (UZBEKISTON MILLIY IP)
color 0A
echo ======================================================================
echo    UZBEK CODERS - AI AGENT (UZBEKISTON MILLIY IP)
echo ======================================================================
echo.
echo  [VAZIFA] GitHub Cloud Master Serverga avtomatik ulanish va
echo           buyurtmalarni 6 ta oqimda parallel bajarish.
echo  [EKRAN]  Orqa fonda (yashirin) ishlaydi, ekranni to'smaydi.
echo.
echo ======================================================================
echo  1. Eng so'nggi 100%% mukammal kod yangilanmoqda...
echo ======================================================================
git pull origin master
echo.
echo ======================================================================
echo  2. Agent ishga tushirilmoqda va GitHub Master Serverga ulanmoqda...
echo ======================================================================
set WORKER_COUNT=6
set HEADLESS=1
set GUI_MODE=0
python -u cluster_worker.py
pause
