@echo off
cd /d "d:\uzbekcodersbot"
chcp 65001 >nul
title UZBEK CODERS - 4 TA AGENT (KO'RINMAS / ORQA FONDA TEZKOR REJIM)
color 0A
echo ======================================================================
echo    UZBEK CODERS BOT - 4 TA AGENT (KO'RINMAS / ORQA FONDA REJIM)
echo ======================================================================
echo.
echo  [1/2] GitHub Master Serverga ulanmoqda...
echo  [2/2] 4 ta AI Agent orqa fonda (ko'rinmas rejimda) ishga tushmoqda...
echo.
echo  Brauzer oynalari kompyuterni va ekranni band qilmaydi,
echo  orqa fonda 4 barobar tezlikda buyurtmalar bajariladi!
echo  Jarayonni Telegram botingizda jonli kuzatishingiz mumkin.
echo ======================================================================
echo.
set HEADLESS=1
set GUI_MODE=0
set WORKER_COUNT=4
python -u cluster_worker.py https://med-infringement-steven-responsible.trycloudflare.com
pause
