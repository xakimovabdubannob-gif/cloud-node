@echo off
chcp 65001 >nul
title UZBEK CODERS - JONLI KO'RINADIGAN BRAUZER REJIMI
color 0A
echo ======================================================================
echo    UZBEK CODERS BOT - JONLI EKRAN VA OCHIQ BRAUZER REJIMI
echo ======================================================================
echo    Brauzer ko'zingiz oldida ochiladi va har bir qadamni ko'rasiz!
echo ======================================================================
set HEADLESS=0
set GUI_MODE=1
python master_certified_pipeline.py --gui
pause
