@echo off
chcp 65001 >nul
title UzbekCoders - 2-Kompyuterni Yangilash (Masofaviy Ekran va Boshqaruv)
color 0A

echo ======================================================================
echo    UZBEK CODERS - 2-KOMPYUTERNI BIR MARTALIK TEZKOR YANGILASH
echo ======================================================================
echo.
echo [1/3] Eskirgan worker jarayonlari to'xtatilmoqda...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*cluster_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo [2/3] Yangi masofaviy ekran va sichqoncha boshqaruv moduli yuklanmoqda...
powershell -NoProfile -Command "$work = [System.IO.Path]::Combine($env:USERPROFILE, 'UzbekCoders_Cluster_Node'); if (-not (Test-Path $work)) { New-Item -ItemType Directory -Path $work -Force | Out-Null }; $urls = @('http://192.168.1.5:8766/cluster/get_worker_py', 'https://plastic-armed-planet-flags.trycloudflare.com/cluster/get_worker_py'); $ok = $false; foreach ($u in $urls) { try { Invoke-WebRequest -Uri $u -OutFile \"$work\cluster_worker.py\" -TimeoutSec 10; if ((Get-Item \"$work\cluster_worker.py\").Length -gt 2000) { $ok = $true; break } } catch {} }; if (-not $ok) { Write-Host '[XATO] Faylni yuklab bolmadi!' -ForegroundColor Red; exit 1 }"

if errorlevel 1 (
    echo.
    echo [XATOLIK] Yangilash faylini yuklab bo'lmadi! Tarmoqni tekshiring.
    pause
    exit /b 1
)

echo [3/3] Yangilangan modul orqa fonda ishga tushirilmoqda...
powershell -NoProfile -Command "$work = [System.IO.Path]::Combine($env:USERPROFILE, 'UzbekCoders_Cluster_Node'); $py = 'pythonw.exe'; if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = 'python.exe' }; Start-Process -FilePath $py -ArgumentList '-X utf8 -u cluster_worker.py' -WorkingDirectory $work -WindowStyle Hidden"

echo.
echo ======================================================================
echo [MUVAFFAQIYATLI YANGILANDI!]
echo.
echo 2-Kompyuterga Masofaviy Ekran va Sichqoncha Boshqaruvi ulandi!
echo Endi ushbu kompyuter oldiga BORISH UMUMAN SHART EMAS!
echo Telegram bot orqali ekranni ko'rib, sichqoncha bilan bemalol boshqarasiz!
echo ======================================================================
echo.
timeout /t 6
exit /b 0
