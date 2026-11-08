@echo off
cd /d "d:\uzbekcodersbot"
chcp 65001 >nul
title UZBEK CODERS - SHU KOMPYUTERDA ISHLASH REJIMI (2 TA AGENT)
color 0A
echo ======================================================================
echo    UZBEK CODERS BOT - SHU KOMPYUTERDA ISHLASH REJIMI (2 TA AGENT)
echo ======================================================================
echo.
echo  [1/2] GitHub Master Serverga ulanmoqda...
echo  [2/2] 2 ta AI Agent ekranning chap va o'ng tomonida ochilmoqda...
echo.
echo  Endi Telegram botga Excel faylni tashlasangiz yoki davom ettirishni bossangiz,
echo  barcha buyurtmalar AYNAN SHU KOMPYUTERDA 2 TA AGENTDA bajariladi!
echo ======================================================================
echo.
set HEADLESS=0
set GUI_MODE=1
set WORKER_COUNT=2
python -u cluster_worker.py https://med-infringement-steven-responsible.trycloudflare.com
pause
