@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

echo ======================================================================
echo    UZBEK CODERS - UNIVERSAL AI AGENT (UZBEKISTON MILLIY IP)
echo ======================================================================
echo.

:: 1. Loyiha papkasini aniqlash va o'tish
set "TARGET_DIR=%~dp0"
if not exist "%TARGET_DIR%cluster_worker.py" (
    if exist "%USERPROFILE%\uzbekcodersbot\cluster_worker.py" (
        set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
    ) else if exist "D:\uzbekcodersbot\cluster_worker.py" (
        set "TARGET_DIR=D:\uzbekcodersbot"
    ) else (
        set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
    )
)

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

:: 2. Agar fayllar hali bo'lmasa yoki yangilash kerak bo'lsa
if not exist "%TARGET_DIR%\cluster_worker.py" (
    echo [1/2] Kerakli kodlar bir marta GitHub'dan olinmoqda...
    where curl.exe >nul 2>&1
    if %errorlevel% equ 0 (
        curl.exe -L "https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip" -o "%TEMP%\master.zip" --silent --show-error
    ) else (
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip', '%TEMP%\master.zip')"
    )

    if exist "%TEMP%\master.zip" (
        where tar.exe >nul 2>&1
        if %errorlevel% equ 0 (
            tar.exe -xf "%TEMP%\master.zip" -C "%TEMP%"
        ) else (
            powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\master.zip' -DestinationPath '%TEMP%' -Force"
        )
        if exist "%TEMP%\cloud-node-master" (
            xcopy /E /Y /Q "%TEMP%\cloud-node-master\*" "%TARGET_DIR%\" >nul 2>&1
            rd /s /q "%TEMP%\cloud-node-master" >nul 2>&1
        )
        del /f /q "%TEMP%\master.zip" >nul 2>&1
        echo [OK] Kodlar muvaffaqiyatli saqlandi!
    )
) else (
    echo [1/2] Kodlar mavjud va tekshirildi.
)

:: 3. Python dasturini aniqlash
set "PY_CMD="
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if exist "C:\Python311\python.exe" set "PY_CMD=C:\Python311\python.exe"
    if exist "C:\Python310\python.exe" set "PY_CMD=C:\Python310\python.exe"
)
if "%PY_CMD%"=="" set "PY_CMD=python"

echo.
echo [2/2] Agent ishga tushirilmoqda va GitHub Master Serverga ulanmoqda...
echo ======================================================================
set WORKER_COUNT=6
set HEADLESS=1
set GUI_MODE=0

"%PY_CMD%" -u cluster_worker.py

echo.
echo ======================================================================
echo Dastur to'xtadi. Oynani yopish uchun istalgan tugmani bosing...
echo ======================================================================
pause