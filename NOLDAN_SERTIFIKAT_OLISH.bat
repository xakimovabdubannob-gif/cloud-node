@echo off
chcp 65001 >nul
title NOLDAN SERTIFIKAT OLISH (YAKKA TARTIBDA)
color 0A

echo ======================================================================
echo    UZBEK CODERS - YAKKA TARTIBDA NOLDAN SERTIFIKAT OLISH
echo ======================================================================
echo.
echo  Bu dastur orqali qotib qolgan o'quvchini:
echo  1. Aileaders'dan eski profilini o'chiradi
echo  2. Yangi toza pochta bilan NOLDAN ro'yxatdan o'tkazadi
echo  3. Brauzerni ko'zingiz oldida ochib, 4 ta testni yechadi
echo  4. Ismini toza tasdiqlab, tayyor sertifikatini olib beradi!
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

%PY_CMD% -u noldan_yakka_tartibda.py

echo.
echo Jarayon yakunlandi.
pause
