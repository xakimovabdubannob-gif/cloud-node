@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL OQIM QO'SHISH (MULTI-PC CLUSTER)
cd /d "%~dp0"

echo ======================================================================
echo 🚀 UZBEK CODERS AI - BOSHQA KOMPYUTERDAN OQIM QO'SHISH TIZIMI
echo ======================================================================
echo.
set /p W_CNT="Ushbu kompyuterda nechta parallel oqim ishlashini xohlaysiz? (16GB RAM uchun 4 yoki 5 yozing, Enter bossangiz Telegramdan tanlaysiz): "
if "%W_CNT%"=="" set W_CNT=4
set WORKER_COUNT=%W_CNT%

echo.
echo [1/3] Uyqu rejimi o'chirilmoqda (kompyuter uxlab qolmasligi uchun)...
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-dc 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0 >nul 2>&1
powercfg /setactive SCHEME_CURRENT >nul 2>&1

echo [2/3] Kerakli kutubxonalar tekshirilmoqda...
python -c "import requests, openpyxl, playwright" >nul 2>&1
if errorlevel 1 (
    echo Kutubxonalar o'rnatilmoqda (1 marta)...
    pip install requests openpyxl playwright
    playwright install chromium
)

echo [3/3] Orqa fonda (%WORKER_COUNT% ta oqim) ishga tushirilmoqda...
powershell -Command "$env:WORKER_COUNT='%WORKER_COUNT%'; $p = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source; if (-not $p) { $p = 'pythonw.exe' }; ([wmiclass]'Win32_Process').Create(\"$p -X utf8 -u `\"$PWD\cluster_worker.py`\"\", \"$PWD\") | Out-Null"

echo.
echo ======================================================================
echo ✅ MUVAFFAQIYATLI ISHGA TUSHDI!
echo 📱 Endi Telegram botingizga (@sertifikatagent_bot) qarang:
echo    Bot sizga "Yangi kompyuter ulandi — Oqimlarni bo'lib beraymi?" deb
echo    so'rov yubordi. "Ha" tugmasini bossangiz, orqa fonda ishlayveradi!
echo    Ushbu oynani yopishingiz mumkin.
echo ======================================================================
timeout /t 5
