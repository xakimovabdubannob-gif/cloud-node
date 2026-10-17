# -*- coding: utf-8 -*-
import os
import sys
import time
import subprocess
import requests

ANYDESK_PATH = r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
ANYDESK_PASSWORD = "UzbekCoders2026!"

def setup_anydesk():
    """AnyDesk ni avtomatik o'rnatadi, parolini o'rnatadi va AnyDesk ID sini qaytaradi."""
    print("=" * 60)
    print("🖥 ANYDESK O'RNATISH VA SOZLASH BOSHLANMOQDA...")
    print("=" * 60)

    # 1. AnyDesk.exe borligini tekshirish, yo'q bo'lsa yuklab olish
    installer = "AnyDesk_Setup.exe"
    if not os.path.exists(ANYDESK_PATH):
        if not os.path.exists(installer):
            print("[1/4] AnyDesk rasmiy saytidan yuklab olinmoqda...")
            url = "https://download.anydesk.com/AnyDesk.exe"
            try:
                r = requests.get(url, timeout=30)
                with open(installer, "wb") as f:
                    f.write(r.content)
                print("[1/4] Yuklab olindi!")
            except Exception as e:
                print(f"[XATO] AnyDesk yuklab olinmadi: {e}")
                return None, None

        # 2. Jimjit (silent) rejimda o'rnatish
        print("[2/4] AnyDesk jimjit o'rnatilmoqda...")
        try:
            subprocess.run([installer, "--install", r"C:\Program Files (x86)\AnyDesk", "--start-with-win", "--silent"], check=False, timeout=60)
            time.sleep(5)
        except Exception as e:
            print(f"[OGOHLANTIRISH] O'rnatishda xatolik: {e}")

    anydesk_exe = ANYDESK_PATH if os.path.exists(ANYDESK_PATH) else installer
    if not os.path.exists(anydesk_exe):
        print(f"[XATO] {anydesk_exe} topilmadi!")
        return None, None

    # 3. Xizmatni yoqish va Parolni o'rnatish
    print("[3/4] Xizmat ishga tushirilmoqda va maxfiy parol o'rnatilmoqda...")
    try:
        subprocess.run(["net", "start", "AnyDesk"], capture_output=True, text=True, check=False)
    except Exception:
        pass

    try:
        p = subprocess.Popen([anydesk_exe, "--set-password"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.communicate(input=ANYDESK_PASSWORD + "\n", timeout=10)
    except Exception as e:
        print(f"[OGOHLANTIRISH] Parol o'rnatishda xato: {e}")

    # 4. AnyDesk ID ni aniqlash (10-30 soniya ichida serverdan ID oladi)
    print("[4/4] AnyDesk ID aniqlanmoqda...")
    anydesk_id = ""
    for attempt in range(12):
        time.sleep(3)
        try:
            res = subprocess.run([anydesk_exe, "--get-id"], capture_output=True, text=True, timeout=5)
            out = res.stdout.strip()
            # ID raqamlardan iborat bo'ladi (masalan: 123456789 yoki 1 234 567 890)
            clean_id = "".join(c for c in out if c.isdigit())
            if clean_id and len(clean_id) >= 8:
                anydesk_id = out
                print(f"✅ AnyDesk ID TOPILDI: {anydesk_id}")
                break
        except Exception:
            pass

    if not anydesk_id:
        # Alternativ: AnyDesk config faylidan ID ni qidiramiz
        cfg_paths = [
            os.path.expandvars(r"%APPDATA%\AnyDesk\system.conf"),
            os.path.expandvars(r"%PROGRAMDATA%\AnyDesk\system.conf"),
        ]
        for cp in cfg_paths:
            if os.path.exists(cp):
                try:
                    with open(cp, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "ad.anynet.id=" in line:
                                anydesk_id = line.split("ad.anynet.id=")[1].strip()
                                print(f"✅ AnyDesk ID configdan topildi: {anydesk_id}")
                                break
                except Exception:
                    pass
            if anydesk_id:
                break

    if anydesk_id:
        import json
        info = {
            "anydesk_id": anydesk_id,
            "password": ANYDESK_PASSWORD,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open("anydesk_info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
        with open("anydesk_id.txt", "w", encoding="utf-8") as f:
            f.write(f"{anydesk_id}\n{ANYDESK_PASSWORD}\n")
        return anydesk_id, ANYDESK_PASSWORD

    print("⚠️ AnyDesk ID olinmadi.")
    return None, ANYDESK_PASSWORD

def notify_admin_anydesk(token, admin_id, anydesk_id, password=ANYDESK_PASSWORD):
    if not token or not admin_id or not anydesk_id:
        return
    text = (
        f"🖥 <b>VIRTUAL KOMPYUTERGA JONLI ULASH TAYYOR (ANYDESK)!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>AnyDesk ID:</b> <code>{anydesk_id}</code>\n"
        f"🔑 <b>Parol:</b> <code>{password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👀 <b>Ko'rsatma:</b>\n"
        f"1. Kompyuteringizda AnyDesk dasturini oching.\n"
        f"2. Yuqoridagi <code>{anydesk_id}</code> raqamini kiriting va <b>«Ulanish»</b> bosing.\n"
        f"3. Parol so'rasa: <code>{password}</code> ni yozing.\n\n"
        f"⚡ <b>Virtual kompyuter ekrani va ochilayotgan barcha brauzerlar ko'zingiz oldida jonli ko'rinadi!</b>"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": admin_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        print("[ANYDESK NOTIFICATION] Telegram xabari yuborildi!")
    except Exception as e:
        print(f"[ANYDESK NOTIFICATION ERROR] {e}")

if __name__ == "__main__":
    aid, pwd = setup_anydesk()
    print(f"Natija: ID={aid}, PWD={pwd}")
