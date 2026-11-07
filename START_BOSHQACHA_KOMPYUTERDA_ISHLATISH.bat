@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL AVTOMAT AGENT
color 0A

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

:: 2. Agar fayllar yo'q bo'lsa GitHub'dan olish
if not exist "%TARGET_DIR%\cluster_worker.py" (
    echo Kodlar yuklanmoqda...
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

:: 3. Pythonw (oynasiz / yashirin ishlovchi) ni aniqlash
set "PYW_CMD="
where pythonw.exe >nul 2>&1
if %errorlevel% equ 0 (
    set "PYW_CMD=pythonw.exe"
) else (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    if exist "C:\Python311\pythonw.exe" set "PYW_CMD=C:\Python311\pythonw.exe"
    if exist "C:\Python310\pythonw.exe" set "PYW_CMD=C:\Python310\pythonw.exe"
)
if "%PYW_CMD%"=="" set "PYW_CMD=python.exe"

:: 4. Oqimlar soni va yashirin rejim
set WORKER_COUNT=4
set HEADLESS=1
set GUI_MODE=0

:: 5. Butunlay orqa fonda (Диспетчер задач / Background) ishga tushirish
start "" "%PYW_CMD%" -X utf8 -u "%TARGET_DIR%\cluster_worker.py"

echo ======================================================================
echo  ✅ AI AGENT MUVAFFAQIYATLI ISHGA TUSHIRILDI!
echo ======================================================================
echo.
echo  🖥 Dastur butunlay orqa fonda (Диспетчер задач ichida) indamasdan ishlamoqda.
echo  ⚡ Oqimlar soni: 4 ta sokin parallel oqim.
echo  📱 Barcha sertifikatlar va bildirishnomalar Telegram botingizga boradi.
echo.
echo  Ushbu oyna 4 soniyadan keyin avtomatik yopiladi...
timeout /t 4 >nul
exit