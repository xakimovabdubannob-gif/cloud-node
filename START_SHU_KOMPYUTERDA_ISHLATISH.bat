@echo off
cd /d "d:\uzbekcodersbot"
chcp 65001 >nul
title UZBEK CODERS - SHU KOMPYUTERDA ISHLASH REJIMI (4 TA AGENT)
color 0A
echo ======================================================================
echo    UZBEK CODERS BOT - SHU KOMPYUTERDA ISHLASH REJIMI
echo ======================================================================
echo.
echo  [1/2] GitHub Master Serverga ulanmoqda...
echo  [2/2] Barcha 4 ta AI Agent ishga tushirilmoqda...
echo.
echo  Endi Telegram botga Excel faylni tashlasangiz,
echo  barcha buyurtmalar AYNAN SHU KOMPYUTERDA bajariladi!
echo ======================================================================
echo.
set HEADLESS=0
set GUI_MODE=1
python -u cluster_worker.py https://existence-incurred-film-cardiovascular.trycloudflare.com
pause
