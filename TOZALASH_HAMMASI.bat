@echo off
chcp 65001 >nul
title Kesh va Xatolarni Tozalash
color 0b
echo ===================================================
echo   UZBEKCODERS — BARCHA KESH VA XATOLARNI TOZALASH
echo ===================================================
echo.

echo [1/4] Qotib qolgan Chrome jarayonlari yopilmoqda...
taskkill /F /IM chrome.exe /T 2>nul
taskkill /F /IM chromedriver.exe /T 2>nul

echo [2/4] Xatolar kesh fayli (xatolar.txt) tozalanmoqda...
powershell -Command "Set-Content -Path 'xatolar.txt' -Value '# Tozalandi' -Encoding UTF8"

echo [3/4] Bot buyurtmalar navbati tozalanmoqda...
if not exist "bot_orders\archived" mkdir "bot_orders\archived"
powershell -Command "Get-ChildItem -Path 'bot_orders' -Filter 'in_*.xlsx' | Move-Item -Destination 'bot_orders\archived' -Force -ErrorAction SilentlyContinue"

echo [4/4] cluster_nodes_state yangilanmoqda...
powershell -Command "if (Test-Path 'mail_ready_students.json') { Set-Content -Path 'mail_ready_students.json' -Value '[]' -Encoding UTF8 }"

echo.
echo ===================================================
echo   BARCHA KESH VA XATOLAR MUVAFFAQIYATLI TOZALANDI!
echo ===================================================
echo.
pause
