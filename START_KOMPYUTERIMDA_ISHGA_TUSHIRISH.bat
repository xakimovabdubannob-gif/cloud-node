@echo off
cd /d "d:\uzbekcodersbot"
chcp 65001 >nul
title UZBEK CODERS - MAHALLIY O'ZBEKISTON SERVERI (JONLI CHROME)
color 0A
echo ======================================================================
echo    UZBEK CODERS BOT - O'ZBEKISTON MILLIY INTERNETIDA ISHLASH REJIMI
echo ======================================================================
echo.
echo  [DIQQAT] aileaders.uz davlat portali chet el serverlarini (GitHub/Azure)
echo           butunlay bloklagan (ERR_CONNECTION_TIMED_OUT).
echo.
echo  [YECHIM] Botingiz sizning shaxsiy kompyuteringizda (O'zbekiston IP)
echo           to'liq ochiq Google Chrome bilan 100%% muammosiz ishlaydi!
echo.
echo ======================================================================
echo  Bot ishga tushirilmoqda...
echo ======================================================================
set HEADLESS=0
set GUI_MODE=1
python telegram_bot.py
pause
