@echo off
cd /d "%~dp0"
chcp 65001 >nul
title UZBEK CODERS - 16GB SUPER SERVER (6 TA AI AGENT)
color 0B
echo ======================================================================
echo    UZBEK CODERS BOT - 16 GB SUPER SERVER (6 TA AI AGENT)
echo ======================================================================
echo.
echo  [PARALLEL OQIMLAR] 6 ta AI Agent orqa fonda (yashirin) ishlaydi.
echo  [EKRAN] Brauzerlar ekranni to'smaydi, fonda mustaqil ishlaydi.
echo  [INTERNET] O'zbekiston milliy interneti (VPN'siz).
echo.
echo ======================================================================
echo  1. Eng so'nggi 100%% mukammal kod tortib olinmoqda...
echo ======================================================================
git pull origin master
echo.
echo ======================================================================
echo  2. Server va 6 ta Agent ishga tushirilmoqda...
echo ======================================================================
set MAX_WORKERS=6
set HEADLESS=1
set GUI_MODE=0
python telegram_bot.py
pause
