@echo off
chcp 65001 >nul
title PASPORTDAN NOLDAN SERTIFIKAT OLISH (11.12.2026)
color 0A

echo ======================================================================
echo    UZBEK CODERS - 11.12.2026 PASPORTDAN NOLDAN SERTIFIKAT OLISH
echo ======================================================================
echo.
echo  Ushbu dastur 100%% aniq ishlagan oxirgi algoritm bo'yicha ishlaydi:
echo  1. Aileaders'dan eski qotib qolgan pasport profilini tozalaydi
echo  2. Yangi toza pochta bilan NOLDAN ro'yxatdan o'tkazadi
echo  3. Coursera DEDC homiyligiga ulaydi (bepul)
echo  4. 'Choose a program' va 'Recovery email' oynalarini avtomatik chetlab o'tadi
echo  5. 4 ta testni 100%% yechib, videolarni tugatadi
echo  6. Ismni rasmiy tasdiqlab (Verify My Name), tayyor sertifikat havolasini oladi!
echo.
echo ======================================================================

cd /d "%~dp0"

set PY_CMD=python
where python >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" (
        set PY_CMD="C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        set PY_CMD="C:\Python311\python.exe"
    )
)

%PY_CMD% -u "%~dp0pasportdan_noldan_olish_11_12_2026.py"

echo.
echo Jarayon yakunlandi.
pause
