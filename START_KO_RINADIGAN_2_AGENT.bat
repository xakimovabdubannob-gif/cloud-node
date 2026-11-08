@echo off
cd /d "d:\uzbekcodersbot"
chcp 65001 >nul
title UZBEK CODERS - 2 TA AGENT (KO'RINADIGAN / EKRANDA KUZATISH REJIMI)
color 0B
echo ======================================================================
echo    UZBEK CODERS BOT - 2 TA AGENT (KO'RINADIGAN REJIM)
echo ======================================================================
echo.
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
