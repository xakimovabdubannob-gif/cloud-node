@echo off
cd /d "%~dp0"
chcp 65001 >nul
title 16 GB KOMPYUTERGA BOSH TIZIMNI ORNATISH
color 0E
echo ======================================================================
echo    UZBEK CODERS - 16 GB KOMPYUTER UCHUN 1 MARTALIK O'RNATISH
echo ======================================================================
echo.
echo 1. Python paketlari o'rnatilmoqda...
pip install -r requirements.txt
echo.
echo 2. Playwright Chromium brauzeri o'rnatilmoqda...
python -m playwright install chromium
echo.
echo ======================================================================
echo    O'RNATISH MUVAFFAQIYATLI YAKUNLANDI!
echo    Endi "START_16GB_SERVER_6_AGENT.bat" ni bosib serverni yoqing.
echo ======================================================================
pause
