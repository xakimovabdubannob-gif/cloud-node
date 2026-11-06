# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import re
import subprocess
import requests

ANYDESK_PATHS = [
    r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
    r"C:\Program Files\AnyDesk\AnyDesk.exe",
]

DEFAULT_PASSWORD = "UzbekCoders2026!"

def get_anydesk_exe():
    for p in ANYDESK_PATHS:
        if os.path.exists(p):
            return p
    return None

def extract_id_from_conf():
    conf_paths = [
        os.path.expandvars(r"%ALLUSERSPROFILE%\AnyDesk\system.conf"),
        os.path.expandvars(r"%PROGRAMDATA%\AnyDesk\system.conf"),
        os.path.expandvars(r"%APPDATA%\AnyDesk\user.conf"),
        r"C:\ProgramData\AnyDesk\system.conf",
    ]
    for cp in conf_paths:
        if os.path.exists(cp):
            try:
                with open(cp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    m = re.search(r"ad\.anydesk\.id\s*=\s*(\d+)", content)
                    if m:
                        return m.group(1).strip()
            except Exception:
                pass
    return None

def setup_anydesk():
    exe = get_anydesk_exe()
    aid = None

    # Agar AnyDesk o'rnatilgan bo'lsa, parolni o'rnatamiz va ID ni olamiz
    if exe:
        try:
            # Parol o'rnatish
            subprocess.run(
                f'echo {DEFAULT_PASSWORD} | "{exe}" --set-password',
                shell=True,
                timeout=10,
                capture_output=True
            )
        except Exception:
            pass

        # ID olishga 5 marta urinish (xizmat ko'tarilishi uchun)
        for _ in range(5):
            try:
                p = subprocess.run([exe, "--get-id"], capture_output=True, text=True, timeout=8)
                out = p.stdout.strip()
                m = re.search(r"(\d{8,11})", out)
                if m:
                    aid = m.group(1)
                    break
            except Exception:
                pass
            time.sleep(2)

    if not aid:
        aid = extract_id_from_conf()

    if aid:
        try:
            with open("anydesk_id.txt", "w", encoding="utf-8") as f:
                f.write(f"{aid}\n{DEFAULT_PASSWORD}\n")
            with open("anydesk_info.json", "w", encoding="utf-8") as f:
                json.dump({"anydesk_id": aid, "password": DEFAULT_PASSWORD}, f, indent=2)
        except Exception:
            pass
        return aid, DEFAULT_PASSWORD

    return "", DEFAULT_PASSWORD

def notify_admin_anydesk(bot_token, admin_id, aid, pwd=DEFAULT_PASSWORD):
    if not bot_token or not admin_id or not aid:
        return False
    try:
        msg = (
            f"🖥 <b>YANGI GITHUB SERVER ANYDESK TAYYOR!</b>\n\n"
            f"🆔 <b>AnyDesk ID:</b> <code>{aid}</code>\n"
            f"🔑 <b>Parol:</b> <code>{pwd}</code>\n\n"
            f"👀 <i>AnyDesk orqali ulanib, brauzerda ro'yxatdan o'tish jarayonini jonli ko'rishingiz mumkin!</i>"
        )
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": int(admin_id),
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[NOTIFY ANYDESK ERROR] {e}")
        return False

if __name__ == "__main__":
    aid, pwd = setup_anydesk()
    print(f"AnyDesk ID: {aid}, PWD: {pwd}")
