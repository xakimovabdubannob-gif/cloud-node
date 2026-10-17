# -*- coding: utf-8 -*-
"""
=============================================================================
UZBEK CODERS AI AGENT - TELEGRAM BOT (v1.0)
=============================================================================
Imkoniyatlari:
1. Har bir Telegram ID uchun 1 MARTA BEPUL SINOV (1 ta o'quvchini tekshirib ko'rish uchun).
2. O'quvchilar ro'yxatini Matn (.txt), Xabar yoki Excel (.xlsx) shaklida qabul qilish.
3. Avtomatik tarif hisoblagich:
   - 1 - 25 ta o'quvchi: 4 000 so'm dan
   - 26 - 50 ta o'quvchi: 3 500 so'm dan
   - 51 - 100 ta o'quvchi: 3 000 so'm dan
   - 100 tadan ko'p: Kelishilgan narxda
4. To'lov chekini qabul qilish va Adminga "✅ Tasdiqlash / ❌ Rad etish" tugmasi bilan yuborish.
5. Core i5 / 8GB RAM uchun xavfsiz Navbat (Queue) tizimi (1 yoki 2 parallel oqimda).
6. Mijozga har bir qadamni jonli (live) aytib turish:
   - Sertifikat olinsa -> Havolasi, Login va Paroli bilan qo'shadi.
   - Oldin boshqa joyda ro'yxatdan o'tgan bo'lsa (bazada paroli yo'q bo'lsa) -> Haqiqiy sababini aytib o'tib ketadi va oxirida qayta urinmaydi.
7. Yakunda barcha ma'lumotlar (Ism-familiya, Sinf, Login, Parol, Sertifikat havolasi, Holati)
   joylangan tayyor EXCEL (.xlsx) faylni mijozga tashlab beradi!
=============================================================================
"""

import os
import re
import sys
import json
import time
import queue
import socket
import threading
import requests
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

try:
    import urllib3.util.connection as urllib3_cn
    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

# Asosiy 100% tekshiruvchi dasturimizdan funksiyalarni chaqiramiz
from master_certified_pipeline import (
    process_student,
    get_completed_students,
    get_existing_accounts,
    get_unrecoverable_students,
    export_results_to_excel,
    RESULTS_FILE,
    ERRORS_FILE,
    ACCOUNTS_FILE,
)
ACCOUNTS_FILE = globals().get("ACCOUNTS_FILE") or "akkountlar.txt"


class SafeStdout:
    def __init__(self, target_file="bot.log", fallback=None):
        self.target_file = target_file
        self.fallback = fallback
        self._f = None
        try:
            self._f = open(self.target_file, "a", encoding="utf-8", buffering=1, errors="replace")
        except Exception:
            pass

    def write(self, data):
        if self.fallback and hasattr(self.fallback, "write"):
            try:
                self.fallback.write(data)
            except Exception:
                pass
        if self._f:
            try:
                self._f.write(data)
                self._f.flush()
            except Exception:
                pass

    def flush(self):
        if self.fallback and hasattr(self.fallback, "flush"):
            try:
                self.fallback.flush()
            except Exception:
                pass
        if self._f:
            try:
                self._f.flush()
            except Exception:
                pass

if sys.stdout is None or not hasattr(sys.stdout, "write"):
    sys.stdout = SafeStdout("bot.log")
else:
    sys.stdout = SafeStdout("bot.log", fallback=sys.stdout)

if sys.stderr is None or not hasattr(sys.stderr, "write"):
    sys.stderr = SafeStdout("bot.log")
else:
    sys.stderr = SafeStdout("bot.log", fallback=sys.stderr)

import subprocess
import ctypes

def ensure_interactive_desktop():
    """Ensure the calling thread is attached to the user's interactive 'Default' desktop on WinSta0."""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if not hdesk:
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return True
    except Exception:
        pass
    return False

def take_silent_screenshot(dest_path=None):
    """Ekranda hech narsa ko'rinmaydigan, 100% orqa fonda skrinshot oluvchi funksiya."""
    if not dest_path:
        dest_path = os.path.join(os.environ.get("TEMP", "."), f"silent_scr_{int(time.time()*1000)}.png")
    ensure_interactive_desktop()
    # 1. Try PIL ImageGrab
    try:
        from PIL import ImageGrab
        im = ImageGrab.grab()
        if im and im.size[0] > 0 and im.size[1] > 0:
            im.save(dest_path, "PNG")
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 8000:
                return dest_path
    except Exception:
        pass
    # 2. Try mss
    try:
        import mss, mss.tools
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            mss.tools.to_png(shot.rgb, shot.size, output=dest_path)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 8000:
                return dest_path
    except Exception:
        pass
    # 3. Fallback to PowerShell
    try:
        ps_p = os.path.abspath(dest_path).replace("\\", "/")
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height); "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
            f"$bmp.Save('{ps_p}', [System.Drawing.Imaging.ImageFormat]::Png); "
            "$g.Dispose(); $bmp.Dispose();"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=12,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
        if os.path.exists(dest_path):
            return dest_path
    except Exception:
        pass
    return None

def move_and_click_mouse(x=None, y=None, action="click"):
    """Orqa fonda sichqonchani harakatlantirish va bosish."""
    ensure_interactive_desktop()
    try:
        user32 = ctypes.windll.user32
        if x is not None and y is not None:
            user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
        if action == "click":
            user32.mouse_event(2, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(4, 0, 0, 0, 0)
        elif action == "double_click":
            for _ in range(2):
                user32.mouse_event(2, 0, 0, 0, 0)
                time.sleep(0.05)
                user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(0.05)
        elif action == "right_click":
            user32.mouse_event(8, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(16, 0, 0, 0, 0)
        return True
    except Exception as e:
        print(f"[MOUSE XATO] {e}")
        return False

def get_cluster_tunnel_url():
    if os.path.exists("cluster_url.txt"):
        try:
            with open("cluster_url.txt", "r", encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u.startswith("https://"):
                        return u
        except Exception:
            pass
    return "http://127.0.0.1:8766"

def send_key_press(key):
    ensure_interactive_desktop()
    try:
        user32 = ctypes.windll.user32
        k_map = {
            "enter": 0x0D, "backspace": 0x08, "tab": 0x09, "esc": 0x1B,
            "space": 0x20, "win": 0x5B, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27
        }
        vk = k_map.get(key.lower())
        if vk:
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(vk, 0, 2, 0)
            return True
    except Exception:
        pass
    return False

def send_unicode_string(text):
    ensure_interactive_desktop()
    try:
        user32 = ctypes.windll.user32
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort),
                ('dwFlags', ctypes.c_ulong), ('time', ctypes.c_ulong),
                ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))
            ]
        class INPUT_I(ctypes.Union):
            _fields_ = [('ki', KEYBDINPUT)]
        class INPUT(ctypes.Structure):
            _fields_ = [('type', ctypes.c_ulong), ('ii', INPUT_I)]

        for ch in text:
            val = ord(ch)
            i1 = INPUT(); i1.type = 1; i1.ii.ki.wVk = 0; i1.ii.ki.wScan = val; i1.ii.ki.dwFlags = 0x0004
            i2 = INPUT(); i2.type = 1; i2.ii.ki.wVk = 0; i2.ii.ki.wScan = val; i2.ii.ki.dwFlags = 0x0004 | 0x0002
            events = (INPUT * 2)(i1, i2)
            user32.SendInput(2, events, ctypes.sizeof(INPUT))
            time.sleep(0.01)
        return True
    except Exception:
        return False

def build_screen_controls_keyboard(tun_url=None):
    if not tun_url:
        tun_url = get_cluster_tunnel_url()
    remote_url = f"{tun_url}/remote"
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 Yangilash (Skrin)", "callback_data": "cl_scr|MASTER_PC"},
                {"text": "📲 Web AnyDesk (Sensor)", "web_app": {"url": remote_url}}
            ],
            [
                {"text": "↖️ Tepa-Chap", "callback_data": "m_clk|200|150"},
                {"text": "⬆️ Tepa-Markaz", "callback_data": "m_clk|683|150"},
                {"text": "↗️ Tepa-O'ng", "callback_data": "m_clk|1160|150"}
            ],
            [
                {"text": "⬅️ O'rta-Chap", "callback_data": "m_clk|200|384"},
                {"text": "🎯 MARKAZ KLIK", "callback_data": "m_clk|683|384"},
                {"text": "➡️ O'rta-O'ng", "callback_data": "m_clk|1160|384"}
            ],
            [
                {"text": "↙️ Past-Chap", "callback_data": "m_clk|200|620"},
                {"text": "⬇️ Past-Markaz", "callback_data": "m_clk|683|620"},
                {"text": "↘️ Past-O'ng", "callback_data": "m_clk|1160|620"}
            ],
            [
                {"text": "✌️ 2x Klik", "callback_data": "m_dclk|683|384"},
                {"text": "🔘 O'ng tugma", "callback_data": "m_rclk|683|384"}
            ],
            [
                {"text": "↵ Enter", "callback_data": "m_key|enter"},
                {"text": "⌫ Back", "callback_data": "m_key|backspace"},
                {"text": "⎋ Esc", "callback_data": "m_key|esc"},
                {"text": "⊞ Win", "callback_data": "m_key|win"}
            ],
            [
                {"text": "🌐 Brauzerda To'liq Ekran", "url": remote_url}
            ]
        ]
    }

CONFIG_FILE = "bot_config.json"
USERS_DB_FILE = "bot_users_db.json"
DEBTS_TXT_FILE = "qarzlar_royxati.txt"
ADMIN_USERNAME = "@OBIDBEK1988"
ADMIN_TG_URL = "https://t.me/OBIDBEK1988"
ORDERS_DIR = "bot_orders"
os.makedirs(ORDERS_DIR, exist_ok=True)

# Core i5 / 8GB RAM: 2 ta parallel AI Agent lokal botda ishlaydi, qolganlari klaster orqali yordamlashadi
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))

db_lock = threading.Lock()
order_queue = queue.Queue()
pending_orders = {}  # user_id -> {"students": [...], "price": int, "user_name": str, "username": str}
admin_input_state = {}  # admin_id -> {"action": "partial_order" | "pay_debt", "target_uid": int}

# 1 O'QUVCHIGA — FAQAT 1 TA AGENT! Lokal oqimlar o'rtasida qat'iy blokirovka
_local_claimed_students = {}
_local_claimed_lock = threading.Lock()



def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("bot_token"):
                    return cfg
        except Exception:
            pass

    print("=" * 70)
    print("TELEGRAM BOT SOZLAMALARI (Bir marta kiritiladi)")
    print("=" * 70)
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        token = input("1. @BotFather dan olingan BOT TOKEN ni kiriting: ").strip()
    admin_id = os.environ.get("ADMIN_ID", "").strip()
    if not admin_id:
        admin_id = input("2. Admin Telegram ID raqamini kiriting (masalan 123456789, bo'sh qoldirsa birinchi yozgan odam admin bo'ladi): ").strip()
    card_info = input("3. To'lov uchun Karta raqami va Ismni kiriting (masalan: 8600 **** **** **** - Falonchiyev F.): ").strip()
    if not card_info:
        card_info = f"9860 **** **** **** (Admin {ADMIN_USERNAME} orqali aniqlashtiring)"

    cfg = {
        "bot_token": token,
        "admin_id": int(admin_id) if admin_id.isdigit() else 0,
        "card_info": card_info,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _read_db_unlocked():
    default_db = {"free_trial_used": [], "orders_completed": 0, "debts": {}}
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "free_trial_used" not in data:
                    data["free_trial_used"] = []
                if "orders_completed" not in data:
                    data["orders_completed"] = 0
                if "debts" not in data:
                    data["debts"] = {}
                return data
        except Exception:
            pass
    return default_db


def _write_db_unlocked(db):
    with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    # Matnli qarzlar daftarini ham yangilab qo'yamiz (o'qishga qulay bo'lishi uchun)
    try:
        with open(DEBTS_TXT_FILE, "w", encoding="utf-8") as tf:
            tf.write("=========================================================================\n")
            tf.write("              QARZDOR MIJOZLAR RO'YXATI (NASIYA VA AVANS)                \n")
            tf.write("=========================================================================\n")
            total_all_debt = 0
            idx = 0
            for uid, info in db.get("debts", {}).items():
                rem = info.get("remaining_debt", 0)
                if rem > 0:
                    idx += 1
                    total_all_debt += rem
                    uname = f"@{info.get('username')}" if info.get("username") else "—"
                    tf.write(
                        f"{idx}. {info.get('name', 'Mijoz')} ({uname} | ID: {uid})\n"
                        f"   Jami hisoblangan: {info.get('total_billed', 0):,} so'm | "
                        f"To'lagan: {info.get('total_paid', 0):,} so'm | "
                        f"QOLGAN QARZI: {rem:,} so'm\n"
                        f"   Oxirgi amal: {info.get('last_updated', '')}\n"
                        f"-------------------------------------------------------------------------\n"
                    )
            if idx == 0:
                tf.write("Hozirda qarzdor mijozlar yo'q.\n")
            else:
                tf.write(f"\nJAMI BARCHA MIJOZLARNING QARZI: {total_all_debt:,} so'm\n")
    except Exception:
        pass


def load_users_db():
    with db_lock:
        return _read_db_unlocked()


def mark_free_trial_used(user_id: int):
    with db_lock:
        db = _read_db_unlocked()
        if user_id not in db["free_trial_used"]:
            db["free_trial_used"].append(user_id)
        _write_db_unlocked(db)


def record_order_financials(user_id: int, user_name: str, username: str, order_total: int, paid_now: int, note: str = ""):
    """Mijozning to'lagan summasini va qolgan qarzini avtomatik hisoblab bazaga yozadi."""
    with db_lock:
        db = _read_db_unlocked()
        uid_key = str(user_id)
        entry = db["debts"].get(uid_key, {
            "name": user_name,
            "username": username or "",
            "total_billed": 0,
            "total_paid": 0,
            "remaining_debt": 0,
            "history": [],
        })
        entry["name"] = user_name or entry.get("name", "Mijoz")
        if username:
            entry["username"] = username
        debt_added = max(0, order_total - paid_now)
        entry["total_billed"] = entry.get("total_billed", 0) + order_total
        entry["total_paid"] = entry.get("total_paid", 0) + paid_now
        entry["remaining_debt"] = max(0, entry.get("remaining_debt", 0) + debt_added)
        ts = time.strftime("%Y-%m-%d %H:%M")
        entry["last_updated"] = ts
        entry.setdefault("history", []).append({
            "time": ts,
            "order_total": order_total,
            "paid": paid_now,
            "debt_added": debt_added,
            "note": note,
        })
        db["debts"][uid_key] = entry
        _write_db_unlocked(db)
        return entry


def record_debt_payment(user_id: int, pay_amount: int):
    """Mijoz qarzidan to'laganda (yoki to'liq yopganda) qarz qoldig'ini kamaytiradi."""
    with db_lock:
        db = _read_db_unlocked()
        uid_key = str(user_id)
        entry = db["debts"].get(uid_key)
        if not entry:
            return None
        old_rem = entry.get("remaining_debt", 0)
        actual_pay = old_rem if pay_amount <= 0 or pay_amount >= old_rem else pay_amount
        entry["total_paid"] = entry.get("total_paid", 0) + actual_pay
        entry["remaining_debt"] = max(0, old_rem - actual_pay)
        ts = time.strftime("%Y-%m-%d %H:%M")
        entry["last_updated"] = ts
        entry.setdefault("history", []).append({
            "time": ts,
            "order_total": 0,
            "paid": actual_pay,
            "debt_added": 0,
            "note": "Qarz to'lovi",
        })
        db["debts"][uid_key] = entry
        _write_db_unlocked(db)
        return entry


def get_user_debt_info(user_id: int):
    with db_lock:
        db = _read_db_unlocked()
        return db.get("debts", {}).get(str(user_id), {})


def calculate_price(count: int):
    """O'quvchilar soniga qarab narxni hisoblaydi."""
    if count <= 25:
        per_student = 4000
    elif count <= 50:
        per_student = 3500
    elif count <= 100:
        per_student = 3000
    else:
        per_student = 2800  # 100+ kelishilgan boshlang'ich narx
    return per_student, count * per_student


def get_certificate_map():
    """natijalar_sertifikatlar.txt dan o'quvchi -> sertifikat URL lug'atini qaytaradi."""
    cert_map = {}
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "http" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        cert_map[parts[0].upper()] = parts[2]
                    elif len(parts) == 2:
                        cert_map[parts[0].upper()] = parts[1]
    return cert_map


def get_error_reason_map():
    """xatolar.txt dan o'quvchi -> xato sababi lug'atini qaytaradi."""
    err_map = {}
    if os.path.exists(ERRORS_FILE):
        with open(ERRORS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2:
                        err_map[parts[0].upper()] = parts[-1]
    return err_map


def cyrillic_to_latin_uz(text: str) -> str:
    """Kirill yozuvidagi F.I.SH ni avtomatik Lotin alifbosiga o'giradi (Coursera Verify My Name uchun)."""
    mapping = {
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "YO",
        "Ж": "J", "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M",
        "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
        "Ф": "F", "Х": "X", "Ц": "TS", "Ч": "CH", "Ш": "SH", "Щ": "SH",
        "Ъ": "`", "Ы": "I", "Ь": "", "Э": "E", "Ю": "YU", "Я": "YA",
        "Ў": "O`", "Қ": "Q", "Ғ": "G`", "Ҳ": "H",
    }
    res = []
    for ch in text.upper():
        res.append(mapping.get(ch, ch))
    return "".join(res)


def save_or_update_account(full_name: str, class_name: str, email: str, password: str):
    full_name_upper = " ".join(full_name.upper().split())
    lines = []
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except Exception:
            pass
    new_lines = []
    updated = False
    for line in lines:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts and " ".join(parts[0].upper().split()) == full_name_upper:
            c_name = class_name or (parts[1] if len(parts) > 1 else "1-sinf")
            new_lines.append(f"{full_name_upper} | {c_name} | {email} | {password}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{full_name_upper} | {class_name or '1-sinf'} | {email} | {password}")
    try:
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
        print(f"[ACC SAVED] {full_name_upper} -> {email} ({password}) akkountlar.txt ga saqlandi!")
    except Exception as e:
        print(f"[ACC UPDATE ERR] {e}")


def parse_students_from_text(text: str):
    """Matndan o'quvchilar ro'yxatini ajratib oladi (14 xonali JSHSHIR, email, parol va Kirill harflarni avtomatik to'g'rilaydi)."""
    students = []
    existing_accs = get_existing_accounts()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.lower().startswith("f.i."):
            continue
        # Tab, '|' yoki ';' orqali ajratish
        parts = [p.strip() for p in re.split(r"\t|\||;", line) if p.strip()]
        # Agar 14 xonali JSHSHIR aralashgan bo'lsa, olib tashlaymiz
        parts = [p for p in parts if not (p.isdigit() and len(p) == 14)]

        # Qatorda email va parol mavjudligini aniqlash
        email_val = ""
        pwd_val = ""
        em_idx = -1
        for idx_p, p in enumerate(parts):
            if "@" in p and "." in p and not p.startswith("@"):
                email_val = p.strip()
                em_idx = idx_p
                break
        if em_idx != -1 and em_idx + 1 < len(parts):
            pwd_val = parts[em_idx + 1].strip()

        clean_parts = [p for i, p in enumerate(parts) if i not in (em_idx, em_idx + 1)] if em_idx != -1 else parts

        if clean_parts and (clean_parts[0].isdigit() or clean_parts[0] in ("№", "#", "N", "No", "T/r")) and len(clean_parts) >= 2:
            clean_parts = clean_parts[1:]

        if len(clean_parts) >= 5:
            name_lat = cyrillic_to_latin_uz(clean_parts[0])
            if "ALIYEV VALI" in name_lat or "KARIMOVA MALIKA" in name_lat or "F.I.SH" in name_lat:
                continue
            st_dict = {
                "name": name_lat,
                "birth_date": clean_parts[1],
                "doc_series": cyrillic_to_latin_uz(clean_parts[2]),
                "doc_number": clean_parts[3],
                "class": cyrillic_to_latin_uz(clean_parts[4]),
            }
            if email_val and pwd_val:
                st_dict["email"] = email_val
                st_dict["password"] = pwd_val
                save_or_update_account(name_lat, clean_parts[4], email_val, pwd_val)
            students.append(st_dict)
        elif len(clean_parts) == 4:
            name_lat = cyrillic_to_latin_uz(clean_parts[0])
            if "ALIYEV VALI" in name_lat or "KARIMOVA MALIKA" in name_lat or "F.I.SH" in name_lat:
                continue
            st_dict = {
                "name": name_lat,
                "birth_date": clean_parts[1],
                "doc_series": cyrillic_to_latin_uz(clean_parts[2]),
                "doc_number": clean_parts[3],
                "class": "1-sinf",
            }
            if email_val and pwd_val:
                st_dict["email"] = email_val
                st_dict["password"] = pwd_val
                save_or_update_account(name_lat, "1-sinf", email_val, pwd_val)
            students.append(st_dict)
        else:
            # Agar '|' bo'lmasa, probel bilan yozilgan to'liq o'quvchi qatorimi (tug'ilgan sana DD.MM.YYYY bor) yoki bazada bor ismmi tekshiramiz
            date_match = re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", line)
            if date_match:
                before_date = cyrillic_to_latin_uz(line[:date_match.start()].strip())
                before_date = re.sub(r"^\d+[\s.)]+", "", before_date).strip()
                after_date = [tok for tok in line[date_match.end():].strip().split() if not (tok.isdigit() and len(tok) == 14)]
                if len(before_date.split()) >= 2 and len(after_date) >= 2:
                    st_dict = {
                        "name": before_date,
                        "birth_date": date_match.group(1).replace("/", ".").replace("-", "."),
                        "doc_series": cyrillic_to_latin_uz(after_date[0]),
                        "doc_number": after_date[1],
                        "class": cyrillic_to_latin_uz(after_date[2]) if len(after_date) >= 3 else "1-sinf",
                    }
                    if email_val and pwd_val:
                        st_dict["email"] = email_val
                        st_dict["password"] = pwd_val
                        save_or_update_account(before_date, st_dict["class"], email_val, pwd_val)
                    students.append(st_dict)
            elif clean_parts:
                p_norm = " ".join(cyrillic_to_latin_uz(clean_parts[0]).upper().split())
                matched_acc = None
                for ex_name in existing_accs:
                    if p_norm == " ".join(ex_name.upper().split()):
                        matched_acc = ex_name
                        break
                if matched_acc or (email_val and pwd_val):
                    final_name = matched_acc or cyrillic_to_latin_uz(clean_parts[0])
                    st_dict = {
                        "name": final_name,
                        "birth_date": "",
                        "doc_series": "",
                        "doc_number": "",
                        "class": cyrillic_to_latin_uz(clean_parts[1]) if len(clean_parts) > 1 else "1-sinf",
                    }
                    if email_val and pwd_val:
                        st_dict["email"] = email_val
                        st_dict["password"] = pwd_val
                        save_or_update_account(final_name, st_dict["class"], email_val, pwd_val)
                    students.append(st_dict)

    return students



def parse_students_from_excel(file_path: str):
    """Excel (.xlsx) fayldan o'quvchilar ro'yxatini o'qiydi (sarlavha, '№' va namuna qatorlarni avtomatik tashlab ketadi)."""
    students = []
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(values_only=True):
        vals = [v.strftime("%d.%m.%Y") if hasattr(v, "strftime") else (str(v).strip() if v is not None else "") for v in row]
        vals_non_empty = [v for v in vals if v]
        if not vals_non_empty:
            continue
        # Agar 1-ustun tartib raqami (1, 2, 3...) yoki '№' bo'lsa, uni o'tkazib yuboramiz
        if (vals_non_empty[0].isdigit() or vals_non_empty[0] in ("№", "#", "N", "No", "T/r")) and len(vals_non_empty) >= 2:
            vals_non_empty = vals_non_empty[1:]
        # 14 xonali JSHSHIR ustuni bo'lsa olib tashlaymiz
        vals_non_empty = [v for v in vals_non_empty if not (v.isdigit() and len(v) == 14)]
        if not vals_non_empty:
            continue
        row_joined_low = " ".join(vals_non_empty).lower()
        if any(h in row_joined_low for h in ["f.i.sh", "familiya ism", "tug'ilgan sana", "guvohnoma seriyasi", "coursera", "shabloni", "namuna)"]):
            continue
        upper_name = cyrillic_to_latin_uz(vals_non_empty[0])
        if len(upper_name) < 4 or "ALIYEV VALI" in upper_name or "KARIMOVA MALIKA" in upper_name or "NAMUNA" in upper_name:
            continue
        if len(vals_non_empty) >= 5:
            if vals_non_empty[3] in ("1234567", "7654321"):
                continue
            students.append({
                "name": upper_name,
                "birth_date": vals_non_empty[1],
                "doc_series": cyrillic_to_latin_uz(vals_non_empty[2]),
                "doc_number": vals_non_empty[3],
                "class": cyrillic_to_latin_uz(vals_non_empty[4]),
            })
        elif len(vals_non_empty) == 4:
            if vals_non_empty[3] in ("1234567", "7654321"):
                continue
            students.append({
                "name": upper_name,
                "birth_date": vals_non_empty[1],
                "doc_series": cyrillic_to_latin_uz(vals_non_empty[2]),
                "doc_number": vals_non_empty[3],
                "class": "",
            })
        elif len(vals_non_empty) >= 1 and len(vals_non_empty[0].split()) >= 2:
            students.append({
                "name": upper_name,
                "birth_date": "",
                "doc_series": "",
                "doc_number": "",
                "class": cyrillic_to_latin_uz(vals_non_empty[1]) if len(vals_non_empty) > 1 else "",
            })
    return students


def create_template_excel(output_path: str = None):
    """Mijozlar to'ldirishi uchun chiroyli, tushunarli Excel (.xlsx) shablon yaratadi."""
    if not output_path:
        output_path = os.path.join(ORDERS_DIR, "Oquvchilar_Shablon.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "O'quvchilar ro'yxati"

    title_fill = PatternFill("solid", fgColor="1F4E78")
    header_fill = PatternFill("solid", fgColor="2F5597")
    sample_fill = PatternFill("solid", fgColor="FFF2CC")
    title_font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sample_font = Font(name="Calibri", size=11, italic=True, color="595959")
    regular_font = Font(name="Calibri", size=11)
    thin = Side(border_style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:F1")
    ws["A1"] = "COURSERA (UZBEKCODERS) SERTIFIKAT OLISH UCHUN O'QUVCHILAR SHABLONI"
    ws["A1"].fill = title_fill
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = [
        "№",
        "F.I.SH (Familiya Ism Sharif)",
        "Tug'ilgan sana (KK.OO.YYYY)",
        "Guvohnoma seriyasi",
        "Guvohnoma raqami",
        "Sinf",
    ]
    ws.append(headers)
    ws.row_dimensions[2].height = 24
    for col_idx in range(1, 7):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    samples = [
        [1, "ALIYEV VALI G'ANI O'G'LI (NAMUNA)", "15.05.2013", "I-FR", "1234567", "5-A"],
        [2, "KARIMOVA MALIKA JASUR QIZI (NAMUNA)", "20.09.2013", "I-FR", "7654321", "5-A"],
    ]
    for s_row in samples:
        ws.append(s_row)
        r_idx = ws.max_row
        ws.row_dimensions[r_idx].height = 20
        for col_idx in range(1, 7):
            c = ws.cell(row=r_idx, column=col_idx)
            c.fill = sample_fill
            c.font = sample_font
            c.border = border
            c.alignment = Alignment(horizontal="left" if col_idx == 2 else "center", vertical="center")

    # 30 ta bo'sh qator tayyor chiziqlari bilan
    for i in range(1, 31):
        ws.append([i, "", "", "", "", ""])
        r_idx = ws.max_row
        ws.row_dimensions[r_idx].height = 20
        for col_idx in range(1, 7):
            c = ws.cell(row=r_idx, column=col_idx)
            c.font = regular_font
            c.border = border
            c.alignment = Alignment(horizontal="left" if col_idx == 2 else "center", vertical="center")

    widths = [6, 38, 24, 20, 20, 12]
    for idx, w in enumerate(widths, 1):
        col_letter = chr(64 + idx)
        ws.column_dimensions[col_letter].width = w

    wb.save(output_path)
    return output_path


def generate_results_excel(students, output_path: str):
    """O'quvchilarning barcha ma'lumotlari (COURSERA SERTIFIKAT tepa qatori, №, F.I.SH, Tug'ilgan sana, I-FR, Raqami, Sinf, Pochta, Parol, Sertifikat havolasi va Sertifikat raqami) bilan Excel (.xlsx) yaratadi."""
    export_results_to_excel(students)
    return export_results_to_excel(students, output_file=output_path)


class TelegramBotServer:
    def __init__(self, cfg):
        self.token = cfg["bot_token"]
        self.admin_id = cfg.get("admin_id", 0)
        self.card_info = cfg.get("card_info", "")
        self.cfg = cfg
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.stats_lock = threading.Lock()
        self.shared_lock = threading.Lock()
        self.shared_orders = []
        self.active_worker_status = {}
        self.is_paused = False
        self.hourly_stats = {
            "window_start": time.strftime("%H:%M"),
            "orders_submitted": 0,
            "orders_approved": 0,
            "students_ordered": 0,
            "revenue_paid": 0,
            "clients_set": set(),
            "last_total_certs": len(get_completed_students()),
        }

    def send_message(self, chat_id, text, reply_markup=None):
        text_str = str(text or "")
        if len(text_str) <= 3950:
            payload = {"chat_id": chat_id, "text": text_str, "parse_mode": "HTML"}
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            for attempt in range(3):
                try:
                    r = requests.post(f"{self.api_url}/sendMessage", data=payload, timeout=(6, 12))
                    res = r.json()
                    if not res.get("ok"):
                        if res.get("error_code") == 429:
                            return res
                        p2 = dict(payload)
                        p2.pop("parse_mode", None)
                        r = requests.post(f"{self.api_url}/sendMessage", data=p2, timeout=(6, 12))
                        res = r.json()
                    return res
                except Exception as e:
                    if attempt == 2:
                        print(f"[BOT XATO] sendMessage: {e}")
                    else:
                        time.sleep(1.0)
            return {}

        chunks = []
        cur = ""
        for line in text_str.splitlines(True):
            if len(cur) + len(line) > 3800 and cur:
                chunks.append(cur)
                cur = line
            else:
                cur += line
        if cur:
            chunks.append(cur)

        last_res = {}
        for i, ch in enumerate(chunks):
            payload = {"chat_id": chat_id, "text": ch, "parse_mode": "HTML"}
            if reply_markup and i == len(chunks) - 1:
                payload["reply_markup"] = json.dumps(reply_markup)
            for attempt in range(3):
                try:
                    r = requests.post(f"{self.api_url}/sendMessage", data=payload, timeout=(6, 12))
                    last_res = r.json()
                    if not last_res.get("ok") and last_res.get("error_code") != 429:
                        p2 = dict(payload)
                        p2.pop("parse_mode", None)
                        last_res = requests.post(f"{self.api_url}/sendMessage", data=p2, timeout=(6, 12)).json()
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"[BOT XATO] sendMessage chunk: {e}")
                    else:
                        time.sleep(1.0)
        return last_res

    def edit_message(self, chat_id, message_id, text):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        try:
            requests.post(f"{self.api_url}/editMessageText", data=payload, timeout=(5, 8))
        except Exception:
            pass

    def send_document(self, chat_id, file_path, caption=""):
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"{self.api_url}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"document": f},
                    timeout=30,
                )
        except Exception as e:
            print(f"[BOT XATO] sendDocument: {e}")

    def send_photo(self, chat_id, photo_path, caption="", reply_markup=None):
        try:
            with open(photo_path, "rb") as f:
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
                if reply_markup:
                    data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
                requests.post(
                    f"{self.api_url}/sendPhoto",
                    data=data,
                    files={"photo": f},
                    timeout=35,
                )
        except Exception as e:
            print(f"[BOT XATO] sendPhoto: {e}")

    def download_file(self, file_id, dest_path):
        r = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id}, timeout=15).json()
        file_path = r["result"]["file_path"]
        dl_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        content = requests.get(dl_url, timeout=30).content
        with open(dest_path, "wb") as f:
            f.write(content)
        return dest_path

    def send_template_to_user(self, chat_id):
        tpl_path = create_template_excel()
        caption = (
            "📥 <b>TAYYOR EXCEL SHABLON (.xlsx)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Shu Excel faylni oching.\n"
            "2️⃣ Ichiga o'quvchilarning <b>F.I.SH, Tug'ilgan sanasi, Guvohnoma seriyasi va raqami hamda Sinfini</b> yozing (tepadagi sariq namuna qatorlarni o'chirib tashlasangiz ham bo'ladi).\n"
            "3️⃣ Faylni saqlab, <b>qaytarib shu yerga botga tashlang!</b>\n\n"
            "🤖 Bot avtomatik o'quvchilar sonini sanab, sertifikatlarni tayyorlab beradi!"
        )
        self.send_document(chat_id, tpl_path, caption=caption)

    def _get_latest_order_progress(self):
        done_set = get_completed_students()
        unrec_set = get_unrecoverable_students()
        accs = get_existing_accounts()
        if not os.path.exists(ORDERS_DIR):
            return None
        files = sorted(
            [os.path.join(ORDERS_DIR, f) for f in os.listdir(ORDERS_DIR) if f.startswith("in_") and f.endswith(".xlsx")],
            key=os.path.getmtime,
            reverse=True,
        )
        for fpath in files[:1]:
            sts = parse_students_from_excel(fpath)
            if sts:
                tot = len(sts)
                done_c = sum(1 for s in sts if s["name"] in done_set)
                unrec_c = sum(1 for s in sts if s["name"] in unrec_set)
                rem_c = max(0, tot - done_c - unrec_c)
                acc_c = sum(1 for s in sts if s["name"] not in done_set and s["name"] not in unrec_set and s["name"] in accs)
                return {"total": tot, "done": done_c, "unrec": unrec_c, "rem": rem_c, "acc_ready": acc_c}
        return None

    def build_hourly_analytics_text(self, reset_window: bool = False):
        with self.stats_lock:
            now_str = time.strftime("%Y-%m-%d %H:%M")
            win_start = self.hourly_stats["window_start"]
            ord_sub = self.hourly_stats["orders_submitted"]
            ord_app = self.hourly_stats["orders_approved"]
            st_ord = self.hourly_stats["students_ordered"]
            rev = self.hourly_stats["revenue_paid"]
            uniq_clients = len(self.hourly_stats["clients_set"])
            prev_certs = self.hourly_stats["last_total_certs"]

            current_total_certs = len(get_completed_students())
            certs_last_hour = max(0, current_total_certs - prev_certs)

            if reset_window:
                self.hourly_stats["window_start"] = time.strftime("%H:%M")
                self.hourly_stats["orders_submitted"] = 0
                self.hourly_stats["orders_approved"] = 0
                self.hourly_stats["students_ordered"] = 0
                self.hourly_stats["revenue_paid"] = 0
                self.hourly_stats["clients_set"] = set()
                self.hourly_stats["last_total_certs"] = current_total_certs

        ord_prog = self._get_latest_order_progress()
        ord_block = ""
        if ord_prog:
            ord_block = (
                f"📋 <b>JORIY BUYURTMA ({ord_prog['total']} TA O'QUVCHI) HOLATI:</b>\n"
                f"• ✅ Sertifikat olindi: <b>{ord_prog['done']} ta</b>\n"
                f"• ⚠️ JSHSHIR xatoli (oldin o'tgan): <b>{ord_prog['unrec']} ta</b>\n"
                f"• ⏳ Qoldi (jarayonda): <b>{ord_prog['rem']} ta</b> <i>(shundan {ord_prog['acc_ready']} tasiga pochta va Coursera ulangan!)</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
            )

        import socket
        pc1_name = socket.gethostname()
        active_lines = [f"💻 <b>1-Kompyuter [{pc1_name}]</b> (8 GB | {MAX_PARALLEL_WORKERS} Agent) — 🟢 FAOL"]
        has_pc1 = False
        for wid, st_text in sorted(self.active_worker_status.items()):
            if st_text:
                has_pc1 = True
                active_lines.append(f"   • 🤖 #{wid}: <i>{st_text[:85]}</i>")
        if not has_pc1:
            active_lines.append("   • <i>Navbatdagi o'quvchi olinmoqda...</i>")

        total_cluster_agents = 0
        if os.path.exists("cluster_nodes_state.json"):
            try:
                with open("cluster_nodes_state.json", "r", encoding="utf-8") as nf:
                    st_nodes = json.load(nf)
                for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                    if ninfo.get("approved"):
                        pc_n = ninfo.get("pc_name", nid)
                        w_cnt = int(ninfo.get("workers", 4))
                        ram_g = ninfo.get("ram_gb", 16)
                        comp_c = int(ninfo.get("completed_count", 0))
                        ago_sec = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                        if ago_sec < 120:
                            live_badge = f"🟢 FAOL ({ago_sec}s)"
                            total_cluster_agents += w_cnt
                        elif ago_sec < 600:
                            live_badge = f"🟢 FAOL ({ago_sec // 60}m)"
                            total_cluster_agents += w_cnt
                        else:
                            live_badge = f"🔴 UZILGAN ({ago_sec // 60}m oldin!)"
                        last_st = str(ninfo.get("status", "—"))[:85]
                        active_lines.append(
                            f"💻 <b>{idx_pc}-Kompyuter [{pc_n}]</b> ({ram_g}GB | {w_cnt} Agent | 🏅{comp_c} ta) — {live_badge}\n"
                            f"   └ <i>{last_st}</i>"
                        )
            except Exception:
                pass

        total_all_agents = MAX_PARALLEL_WORKERS + total_cluster_agents
        active_lines.append(
            f"\n🔥 <b>JAMI ISHLAYOTGAN KUCH: {total_all_agents} ta AI Agent</b> "
            f"(1-Komp: {MAX_PARALLEL_WORKERS} ta + Klaster: {total_cluster_agents} ta)"
        )
        active_block = "\n".join(active_lines)

        recent_certs = []
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE, "r", encoding="utf-8", errors="replace") as rf:
                    rlines = [l.strip() for l in rf.read().splitlines() if "http" in l]
                    for rl in rlines[-5:]:
                        p = [x.strip() for x in rl.split("|")]
                        recent_certs.append(f"   ✅ {p[0]} ({p[1] if len(p) > 2 else ''})")
            except Exception:
                pass
        recent_block = "\n".join(recent_certs) if recent_certs else "   —"

        report = (
            f"📊 <b>JONLI TAHLIL VA KOMPYUTERLAR HOLATI ({now_str})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{ord_block}"
            f"⚡ <b>BARCHA 13 TA KOMPYUTER VA AI AGENTLAR:</b>\n"
            f"{active_block}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>UMUMIY BAZA:</b> Jami <b>{current_total_certs} ta</b> sertifikat (Oxirgi soatda: <b>+{certs_last_hour} ta</b>)\n"
            f"🏅 <b>OXIRGI OLINGAN 5 TA SERTIFIKAT:</b>\n"
            f"{recent_block}"
        )
        return report

    def hourly_analytics_loop(self):
        ticks = 0
        while True:
            time.sleep(120)
            ticks += 1
            # Har 2 daqiqada server uxlamasligi uchun anti-sleep so'rov yuboramiz
            try:
                requests.get(f"{self.api_url}/getMe", timeout=10)
                if sys.platform != "win32":
                                        subprocess.run("tmux refresh-client 2>/dev/null || true; touch ~/.cloudshell_keepalive 2>/dev/null || true", shell=True, timeout=5)
            except Exception:
                pass
            # Har 30 daqiqada (15 * 120s = 1800s) Adminga avtomatik tahlil yuboramiz
            if ticks >= 15:
                ticks = 0
                if self.admin_id:
                    try:
                        rep = self.build_hourly_analytics_text(reset_window=True)
                        self.send_message(self.admin_id, rep)
                    except Exception as e:
                        print(f"[BOT XATO] hourly_analytics_loop: {e}")

    def handle_smart_question(self, chat_id, user_name, text):
        """Mijoz o'quvchi ro'yxati emas, savol yoki murojaat yozganda o'ylab, to'g'ri javob beradi va shablon taklif qiladi."""
        low = text.lower()
        default_markup = {
            "inline_keyboard": [
                [
                    {"text": "📥 Tayyor Excel shablonni olish (.xlsx)", "callback_data": "get_template"},
                ],
                [
                    {"text": f"👨‍💼 Admin bilan bog'lanish ({ADMIN_USERNAME})", "url": ADMIN_TG_URL},
                ],
            ]
        }

        # 1. Agar foydalanuvchi Excel shablon / namuna / qanday to'ldirish haqida so'rasa:
        if any(w in low for w in ["shablon", "excel", "exel", "excl", "jadval", "namuna", "fayl", "to'ldir", "toldir", "шаблон", "эксель", "образец"]):
            self.send_template_to_user(chat_id)
            return

        # 2. Agar narx / tarif / qancha turadi deb so'rasa:
        if any(w in low for w in ["narx", "qancha", "necha pul", "nechpul", "tarif", "skidka", "chegirma", "bepul", "цена", "сколько"]):
            reply = (
                f"💰 <b>SERTIFIKAT OLISH TARIFLARIMIZ:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• 1 – 25 ta o'quvchi: <b>4 000 so'm</b> dan\n"
                f"• 26 – 50 ta o'quvchi: <b>3 500 so'm</b> dan\n"
                f"• 51 – 100 ta o'quvchi: <b>3 000 so'm</b> dan\n"
                f"• 100 tadan ko'p: <b>Kelishilgan maxsus narxda</b>\n\n"
                f"🎁 <b>1 ta o'quvchi BEPUL:</b> Dasturimiz 100% ishlashini tekshirib ko'rishingiz uchun 1-marta 1 ta o'quvchini mutlaqo bepul qilib beramiz!\n\n"
                f"🌗 <b>50% Avans imkoniyati:</b> Boshlash uchun to'lovning 50% yarim pulini (avans) o'tkazishingiz mumkin, qolgan 50% qismi tayyor Excel jadval chiqqandan keyin to'lanadi.\n\n"
                f"📥 Ro'yxatni oson yuborish uchun pastdagi <b>«Tayyor Excel shablonni olish»</b> tugmasini bosing!"
            )
            self.send_message(chat_id, reply, reply_markup=default_markup)
            return

        # 3. Agar to'lov / avans / karta / yarim pul haqida so'rasa:
        if any(w in low for w in ["avans", "yarim", "karta", "plastik", "to'lov", "tolov", "chek", "50%", "50 foiz"]):
            reply = (
                f"💳 <b>TO'LOV VA 50% AVANS TARTIBI:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"1️⃣ Avval o'quvchilar ro'yxatini (Excel shablonda yoki matn shaklida) botga tashlaysiz.\n"
                f"2️⃣ Bot avtomatik o'quvchilar sonini sanab, <b>100% to'liq summa</b> va <b>50% yarim (avans) summani</b> chiqarib beradi.\n"
                f"3️⃣ Siz o'zingizga qulay usulda — <b>100% to'liq</b> yoki <b>50% avans</b> o'tkazib, chek skrinshotini botga tashlaysiz:\n"
                f"🏦 Karta: <code>{self.card_info}</code>\n\n"
                f"🔄 <b>Kafolat:</b> Agar ro'yxatda sertifikat olinmagan (oldin boshqa joyda ro'yxatdan o'tgan yoki o'tmagan) o'quvchi chiqsa, o'rniga boshqa o'quvchi bersangiz <b>bepul to'ldirib beriladi!</b>\n"
                f"<i>Qolgan 50% qismini barcha sertifikatlar tayyor bo'lib Excel jadval qo'lingizga tekkanda to'laysiz!</i>"
            )
            self.send_message(chat_id, reply, reply_markup=default_markup)
            return

        # 4. Agar vaqt / qachon tayyor bo'ladi / tezlik haqida so'rasa:
        if any(w in low for w in ["vaqt", "qachon", "necha daqiqa", "minut", "soat", "tez", "долго", "время", "qotib", "ishlamay"]):
            q_len = order_queue.qsize()
            est_extra = q_len * 15
            reply = (
                f"⚡ <b>ISHLASH TEZLIGI VA TAXMINIY VAQTI:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• 1 ta o'quvchiga sertifikat olishga o'rtacha <b>2 – 4 daqiqa</b> ketadi.\n"
                f"• 1 ta to'liq sinf (25–30 ta o'quvchi) odatda <b>25–40 daqiqa</b> atrofida tayyor bo'ladi (navbat ko'payganda bot sizga taxminiy chiqish vaqtini hisoblab aytadi, hozirgi navbat: <b>{q_len} ta buyurtma / +{est_extra} daqiqa</b>).\n"
                f"• ⏳ <b>Muhim eslatma:</b> Agar rasmiy sayt (aileaders.uz yoki Coursera) vaqtincha ishlamay qolsa yoki qotib qolsa, sertifikat olish biroz sekinlashishi mumkin. Sayt ishlashi bilan jarayon avtomatik davom etadi — bunday paytda sabr qilishingizni so'raymiz! 🙏\n"
                f"• 🔄 <b>100% Almashtirish kafolati:</b> Agar ro'yxatingizda sertifikat olinmagan (o'tmagan) o'quvchilar bo'lsa, ularning o'rniga boshqa o'quvchilar bersangiz <b>bepul to'ldirib beriladi!</b>\n"
                f"• 🤖 <i>Agentimiz hozirda test rejimida ishni boshladi — taklif va hamkorlik bo'lsa Adminga ({ADMIN_USERNAME}) yozishingiz mumkin!</i>"
            )
            self.send_message(chat_id, reply, reply_markup=default_markup)
            return

        # 5. Agar sertifikat haqiqiyligi / Coursera / aileaders / login-parol haqida so'rasa:
        if any(w in low for w in ["sertifikat", "haqiqiy", "coursera", "aileaders", "login", "parol", "kurs", "orginal", "original"]):
            reply = (
                f"🏅 <b>SERTIFIKAT HAQIDA MA'LUMOT:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Barcha sertifikatlar rasmiy <b>aileaders.uz</b> va <b>Coursera (DEDC dasturi — Introduction to Generative AI)</b> orqali 100% original olinadi.\n"
                f"• Har bir sertifikatning maxsus tasdiqlash havolasi (<code>coursera.org/account/accomplishments/verify/...</code>) va ID raqami bo'ladi.\n"
                f"• 🔄 <b>Kafolat:</b> Sertifikat olinmagan (o'tmagan) o'quvchilar bo'lsa, o'rniga boshqa o'quvchilar berilsa bepul to'ldirib beriladi!\n"
                f"• Ish yakunida sizga beriladigan <b>Excel (.xlsx)</b> jadvalda har bir o'quvchining:\n"
                f"  1. F.I.SH, Tug'ilgan sanasi, Guvohnoma seriya-raqami, Sinfi\n"
                f"  2. <b>Pochta (Login) va Paroli</b>\n"
                f"  3. <b>Sertifikat havolasi va Sertifikat ID raqami</b> to'liq yozib beriladi!"
            )
            self.send_message(chat_id, reply, reply_markup=default_markup)
            return

        # 6. Agar qanday ma'lumot kerakligi / metrika / guvohnoma haqida so'rasa:
        if any(w in low for w in ["nima kerak", "qanday ma'lumot", "metrika", "guvohnoma", "seriya", "tug'ilgan", "qanday yubor", "qanaqa qilib"]):
            reply = (
                f"📋 <b>SERTIFIKAT OLISH UCHUN KERAKLI MA'LUMOTLAR:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Har bir o'quvchi uchun quyidagi 5 ta ma'lumot kerak bo'ladi:\n"
                f"1️⃣ <b>F.I.SH</b> (Familiya Ism Sharif)\n"
                f"2️⃣ <b>Tug'ilgan sana</b> (masalan: <code>15.05.2013</code>)\n"
                f"3️⃣ <b>Guvohnoma (metrika) seriyasi</b> (masalan: <code>I-FR</code>, <code>I-AN</code>, <code>III-FR</code>)\n"
                f"4️⃣ <b>Guvohnoma raqami</b> (masalan: <code>1234567</code>)\n"
                f"5️⃣ <b>Sinfi</b> (masalan: <code>5-A</code>)\n\n"
                f"👇 Quyidagi <b>Excel shablonni</b> sizga yuboryapman — shuni ichini to'ldirib menga tashlasangiz eng qulayi shu!"
            )
            self.send_message(chat_id, reply, reply_markup=default_markup)
            self.send_template_to_user(chat_id)
            return

        # 7. Umumiy salomlashish yoki boshqa har qanday savol uchun aqlli yordamchi javobi:
        reply = (
            f"Assalomu alaykum, <b>{user_name}</b>! 😊\n\n"
            f"Men <b>UzbekCoders (Coursera) Avtomat Sertifikat AI Botiman</b> <i>(hozirda test rejimida ishga tushdi)</i>.\n\n"
            f"📌 <b>Sizga qanday yordam bera olaman?</b>\n"
            f"• Agar o'quvchilarga sertifikat olmoqchi bo'lsangiz, pastdagi <b>«📥 Tayyor Excel shablonni olish»</b> tugmasini bosing, shablonni to'ldirib menga yuboring.\n"
            f"• Yoki o'quvchi ma'lumotlarini oddiy xabar ko'rinishida yuboring:\n"
            f"  <code>FAMILIYA ISM SHARIF | 15.05.2013 | I-FR | 1234567 | 5-A</code>\n"
            f"• 🎁 <b>1-marta 1 ta o'quvchini tekshirib ko'rish — BEPUL!</b>\n"
            f"• 🌗 To'lovni <b>100% to'liq</b> yoki <b>50% avans (yarim pulini)</b> berib boshlashingiz mumkin (Karta: <code>{self.card_info}</code>).\n"
            f"• 🔄 <b>Kafolat:</b> Sertifikat olinmagan (o'tmagan) o'quvchilar chiqsa, o'rniga boshqa o'quvchilar berilsa <b>bepul to'ldirib beriladi!</b>\n"
            f"• ⏳ <i>Eslatma: Sayt qotib qolsa yoki sekinlashsa, sayt ishlashi bilan jarayon avtomatik davom etadi (sabr qilishingizni so'raymiz).</i>\n\n"
            f"🤝 Taklif, savol va hamkorlik bo'yicha Admin bilan bog'lanishingiz mumkin: 👉 <b>{ADMIN_USERNAME}</b>"
        )
        self.send_message(chat_id, reply, reply_markup=default_markup)

    def build_admin_approval_markup(self, target_uid: int, total_price: int):
        half_price = total_price // 2
        return {
            "inline_keyboard": [
                [
                    {"text": "✅ 100% To'liq to'landi (Boshlash)", "callback_data": f"approve_full_{target_uid}"},
                ],
                [
                    {"text": f"🌗 50% Avans to'landi ({half_price:,} so'm)", "callback_data": f"approve_half_{target_uid}"},
                ],
                [
                    {"text": "✍️ Boshqa avans kiritish", "callback_data": f"approve_custom_{target_uid}"},
                    {"text": "❌ Rad etish", "callback_data": f"reject_{target_uid}"},
                ],
            ]
        }

    def send_debts_report_to_admin(self, chat_id):
        db = load_users_db()
        debts = db.get("debts", {})
        active_debts = [(uid, info) for uid, info in debts.items() if info.get("remaining_debt", 0) > 0]
        if not active_debts:
            self.send_message(chat_id, "✅ <b>Hozirda qoldiq to'lovi bor mijozlar yo'q!</b> Barcha hisob-kitoblar toza.")
            return

        total_all = sum(info.get("remaining_debt", 0) for _, info in active_debts)
        lines = [
            "📒 <b>50% AVANS BERGAN MIJOZLAR (QOLGAN TO'LOVLAR)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        inline_rows = []
        for idx, (uid, info) in enumerate(active_debts, 1):
            name = info.get("name", "Mijoz")
            uname = f" (@{info['username']})" if info.get("username") else ""
            billed = info.get("total_billed", 0)
            paid = info.get("total_paid", 0)
            rem = info.get("remaining_debt", 0)
            upd_time = info.get("last_updated", "")
            lines.append(
                f"<b>{idx}. {name}</b>{uname} [ID: <code>{uid}</code>]\n"
                f"   • Jami buyurtma: <b>{billed:,} so'm</b>\n"
                f"   • Avans to'lagan: <b>{paid:,} so'm</b>\n"
                f"   • 🔴 <b>QOLGAN TO'LOV: {rem:,} so'm</b>\n"
                f"   • Vaqti: <i>{upd_time}</i>"
            )
            inline_rows.append([
                {"text": f"✅ {name[:14]} — To'liq to'ladi ({rem:,})", "callback_data": f"debt_clear_{uid}"},
                {"text": f"➕ Qisman to'ladi", "callback_data": f"debt_part_{uid}"},
            ])

        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💰 <b>JAMI QOLGAN TO'LOVLAR: {total_all:,} so'm</b>")
        self.send_message(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": inline_rows})

    def handle_students_submission(self, chat_id, user_name, username, students):
        if not students:
            self.send_message(
                chat_id,
                "⚠️ <b>Fayl ichida o'quvchilar ro'yxati topilmadi!</b>\n\n"
                "👇 Quyidagi tayyor <b>Excel shablonni</b> yuklab olib, shuning ichiga o'quvchilar ma'lumotlarini to'ldirib yuboring:",
            )
            self.send_template_to_user(chat_id)
            return

        with self.stats_lock:
            self.hourly_stats["orders_submitted"] += 1
            self.hourly_stats["clients_set"].add(chat_id)

        users_db = load_users_db()
        free_used = chat_id in users_db.get("free_trial_used", [])
        count = len(students)

        # Agar yuboruvchi ADMIN bo'lsa — chek so'ramasdan darhol navbatga qo'shib ishga tushiramiz!
        if self.admin_id and chat_id == self.admin_id:
            with self.stats_lock:
                self.hourly_stats["orders_approved"] += 1
                self.hourly_stats["students_ordered"] += count
            self.send_message(
                chat_id,
                f"👑 <b>ADMIN BUYURTMASI QABUL QILINDI!</b>\n\n"
                f"👥 O'quvchilar soni: <b>{count} ta</b>\n"
                f"⚡ To'lov chekisiz to'g'ridan-to'g'ri navbatga qo'shildi va ishga tushirilmoqda!",
            )
            self.enqueue_order(chat_id, user_name, students, paid_info={"total": 0, "paid": 0, "debt": 0})
            return

        # Agar foydalanuvchi hali 1 ta bepul limitidan foydalanmagan bo'lsa va 1 ta o'quvchi tashlagan bo'lsa:
        if not free_used and count == 1:
            mark_free_trial_used(chat_id)
            with self.stats_lock:
                self.hourly_stats["orders_approved"] += 1
                self.hourly_stats["students_ordered"] += 1
            self.send_message(
                chat_id,
                "🎁 <b>BEPUL SINOV FAOL!</b>\n\n"
                "Biz halol ishlaymiz — dasturimiz 100% ishlashini tekshirib ko'rishingiz uchun "
                f"<b>{students[0]['name']}</b> sertifikatini <b>BEPUL</b> tayyorlab beramiz!\n\n"
                "⏳ Navbatga qo'shildi, har bir qadamni jonli yozib turaman...",
            )
            self.enqueue_order(chat_id, user_name, students, paid_info={"total": 0, "paid": 0, "debt": 0})
            return

        # Narxni hisoblash
        per_st, total_price = calculate_price(count)
        half_price = total_price // 2
        free_note = ""
        if not free_used:
            free_note = (
                "\n💡 <i>Eslatma: Sizda 1 ta o'quvchini BEPUL tekshirib ko'rish imkoniyati bor! "
                "Agar avval tekshirib ko'rmoqchi bo'lsangiz, 1 ta o'quvchi ma'lumotini yuboring.</i>\n"
            )

        custom_note = ""
        if count > 100:
            custom_note = f"\n🤝 <i>100 tadan ko'p buyurtmalar uchun Admin ({ADMIN_USERNAME}) bilan kelishilgan chegirma amal qiladi!</i>\n"

        pending_orders[chat_id] = {
            "students": students,
            "price": total_price,
            "user_name": user_name,
            "username": username or "",
        }

        self.card_info = load_config().get("card_info", self.card_info)
        est_mins = max(3, (order_queue.qsize() * 15) + int(count * 1.5))

        msg = (
            f"📋 <b>BUYURTMA QABUL QILINDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 O'quvchilar soni: <b>{count} ta</b>\n"
            f"⏱ Taxminiy tayyor bo'lish vaqti: <b>~{est_mins} – {est_mins + 10} daqiqa</b>\n"
            f"💰 1 ta sertifikat narxi: <b>{per_st:,} so'm</b>\n"
            f"💳 100% To'liq to'lov summasi: <b>{total_price:,} so'm</b>\n"
            f"🌗 50% Avans (Yarim to'lov): <b>{half_price:,} so'm</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>To'lov uchun karta:</b>\n"
            f"<code>{self.card_info}</code>\n"
            f"{free_note}{custom_note}\n"
            f"📸 <b>100% to'liq yoki 50% yarim (avans) to'lovni amalga oshirib, chek rasmini (skrinshot) shu yerga botga yuboring!</b>\n\n"
            f"🔄 <b>Kafolat:</b> Sertifikat olinmagan (oldin ro'yxatdan o'tgan yoki o'tmagan) o'quvchilar o'rniga boshqa o'quvchilar berilsa, <b>bepul to'ldirib beriladi!</b>\n"
            f"⏳ <i>Eslatma: Sayt (aileaders.uz / Coursera) vaqtincha qotib qolsa yoki so'rov ko'payganda jarayon biroz sekinlashishi mumkin, sayt ishlashi bilan avtomatik davom etadi — sabr qilishingizni so'raymiz.</i>\n"
            f"🤖 <i>Agentimiz test rejimida ishni boshladi — taklif va hamkorlik bo'lsa Adminga ({ADMIN_USERNAME}) yozishingiz mumkin!</i>"
        )
        client_markup = {
            "inline_keyboard": [
                [
                    {"text": "📸 To'lov chekini yuborish", "callback_data": f"send_check_{chat_id}"},
                ],
                [
                    {"text": f"👨‍💼 Admin bilan bog'lanish ({ADMIN_USERNAME})", "url": ADMIN_TG_URL},
                ],
            ]
        }
        self.send_message(chat_id, msg, reply_markup=client_markup)

    def enqueue_order(self, chat_id, user_name, students, paid_info=None, silent=False):
        q_pos = order_queue.qsize() + 1
        est_mins = max(3, ((q_pos - 1) * 15) + int(len(students) * 1.2))
        if not silent:
            self.send_message(
                chat_id,
                f"🚀 <b>Buyurtmangiz navbatga qo'shildi!</b>\n"
                f"📌 Navbatdagi o'rningiz: <b>#{q_pos}</b>\n"
                f"👥 O'quvchilar soni: <b>{len(students)} ta</b>\n"
                f"⏱ Taxminiy tayyor bo'lish vaqti: <b>~{est_mins} – {est_mins + 10} daqiqa</b>\n"
                f"🤖 <i>Hozirda 3 ta AI Agent (Agent #1, Agent #2, Agent #3) ishlayapti — bo'sh AI Agentlar buyurtmangizga avtomatik parallel biriktiriladi!</i>\n\n"
                f"🤖 Agentlarimiz ishni boshlaganda har bir o'quvchining qadamlarini jonli xabar qilib turadi!\n"
                f"⏳ <i>Agar sayt vaqtincha qotib qolsa yoki sekinlashsa, sayt ishlashi bilan jarayon avtomatik davom etadi (sabr qilishingizni so'raymiz).</i>\n"
                f"🔄 <i>Sertifikat olinmagan (o'tmagan) o'quvchilar chiqsa, o'rniga boshqa o'quvchilar berilsa bepul to'ldirib beriladi!</i>",
            )
        order_queue.put({
            "chat_id": chat_id,
            "user_name": user_name,
            "students": students,
            "paid_info": paid_info or {},
            "silent": silent,
        })
        # Klaster (2-kompyuter) ham ko'rishi va yordamga kirishi uchun Excel fayl sifatida saqlaymiz:
        try:
            wb_in = Workbook()
            ws_in = wb_in.active
            ws_in.title = "Oquvchilar"
            ws_in.append(["T/r", "F.I.SH", "Tug'ilgan sana", "Seriya", "Raqam", "Sinf"])
            for _sidx, _st in enumerate(students, 1):
                ws_in.append([
                    _sidx,
                    _st.get("name", ""),
                    _st.get("birth_date", "15.05.2014"),
                    _st.get("doc_series") or _st.get("cert_series", "I-FR"),
                    _st.get("doc_number") or _st.get("cert_number", ""),
                    _st.get("class", "5-A"),
                ])
            fn_in = f"in_{chat_id}_{int(time.time())}.xlsx"
            wb_in.save(os.path.join(ORDERS_DIR, fn_in))
        except Exception as _e_sync:
            print(f"[EXCEL SYNC WARN] {_e_sync}")

    def _pop_helper_task(self):
        with self.shared_lock:
            for ctx in self.shared_orders:
                try:
                    idx, st = ctx["student_q"].get_nowait()
                    return ctx, idx, st
                except queue.Empty:
                    continue
        return None, None, None

    def _process_order_student(self, ctx: dict, idx: int, st: dict, worker_id: int):
        chat_id = ctx["chat_id"]
        total = ctx["total"]
        pass_num = ctx["pass_num"]
        user_name = ctx.get("user_name", "")
        s_name = st["name"]
        self.active_worker_status[worker_id] = f"[{idx}/{total}] {s_name} ({user_name})"

        if s_name in get_completed_students():
            if pass_num == 1 and not ctx.get("silent"):
                certs = get_certificate_map()
                accs = get_existing_accounts()
                ac = accs.get(s_name, {})
                self.send_message(
                    chat_id,
                    f"✅ <b>[{idx}/{total}] {s_name}</b>\n"
                    f"Allaqachon sertifikat olgan!\n"
                    f"📧 Login: <code>{ac.get('email', '—')}</code> | 🔑 Parol: <code>{ac.get('password', '—')}</code>\n"
                    f"🔗 <a href='{certs.get(s_name, '')}'>Sertifikatni ko'rish</a>",
                )
            return

        if s_name in get_unrecoverable_students():
            if pass_num > 1:
                return
            if total > 1 and not ctx.get("silent"):
                errs = get_error_reason_map()
                self.send_message(
                    chat_id,
                    f"⚠️ <b>[{idx}/{total}] {s_name} — O'TKAZIB YUBORILDI!</b>\n"
                    f"Sababi: <i>{errs.get(s_name, 'Oldin roʻyxatdan oʻtgan va bazada login-paroli yoʻq')}</i>\n"
                    f"❗️ Bu o'quvchini tuzatib bo'lmagani uchun oxirida qayta urinilmaydi.",
                )
                return


        # QAT'IY QOIDA: 1 O'QUVCHIGA — FAQAT 1 TA AGENT!
        s_norm = " ".join(s_name.upper().split())
        with _local_claimed_lock:
            cur_worker = _local_claimed_students.get(s_norm)
            if cur_worker is not None and cur_worker != worker_id:
                print(f"[MUTEX] {s_norm} allaqachon Agent #{cur_worker} tomonidan ishlanmoqda, Agent #{worker_id} o'tkazib yubordi!")
                if total == 1:
                    self.send_message(
                        chat_id,
                        f"⏳ <b>{s_name}</b> bo'yicha hozirda Agent #{cur_worker} ish olib bormoqda...",
                    )
                return
            _local_claimed_students[s_norm] = worker_id

        # Agar bu o'quvchi boshqa agent (klaster yoki boshqa kompyuter) tomonidan ishlanayotgan bo'lsa, ustiga kirmaymiz!
        w_tag = f"MASTER_PC_w{worker_id}"
        claimed = True
        try:
            r_cl = requests.post("http://127.0.0.1:8766/cluster/claim_student", json={
                "student_name": s_name,
                "worker_tag": w_tag,
            }, timeout=3).json()
            claimed = r_cl.get("ok", False)
        except Exception:
            claimed = True

        if not claimed:
            if total == 1:
                self.send_message(
                    chat_id,
                    f"⏳ <b>{s_name}</b> bo'yicha AI Agent ish olib bormoqda, natija kutilmoqda...",
                )
            for _w in range(8):
                time.sleep(2)
                if s_name in get_completed_students() or s_name in get_unrecoverable_students():
                    with _local_claimed_lock:
                        if _local_claimed_students.get(s_norm) == worker_id:
                            _local_claimed_students.pop(s_norm, None)
                    return
            # Boshqa agent 16 soniyada natija bermasa, MASTER_PC o'zi ishga kirishadi!
            claimed = True


        def _ensure_internet():
            while True:
                try:
                    requests.get("https://api.telegram.org", timeout=6)
                    return
                except Exception:
                    self.active_worker_status[worker_id] = f"[{idx}/{total}] {s_name} — 🌐 Internet kutilmoqda..."
                    time.sleep(5)

        try:
            _ensure_internet()

            import socket
            pc1_tag = f"💻 1-Kompyuter [{socket.gethostname()}] | 🤖 Agent #{worker_id}"
            step_history = []
            prog_res = self.send_message(
                chat_id,
                f"⏳ <b>[{idx}/{total}] {s_name}</b>\n└ {pc1_tag}\n└ 🚀 Jarayon boshlanmoqda...",
            )
            msg_id = prog_res.get("result", {}).get("message_id")

            def update_step(step_text, _cid=chat_id, _mid=msg_id, _i=idx, _t=total, _name=s_name, _hist=step_history, _wid=worker_id, _ptag=pc1_tag):
                self.active_worker_status[_wid] = f"[{_i}/{_t}] {_name} — {step_text}"
                if not _hist or _hist[-1] != step_text:
                    _hist.append(step_text)
                if _mid:
                    lines_txt = [f"⏳ <b>[{_i}/{_t}] {_name}</b>\n└ {_ptag}"]
                    for s_idx, h_line in enumerate(_hist):
                        pref = "✅" if s_idx < len(_hist) - 1 else "⏳"
                        lines_txt.append(f"  {pref} {h_line}")
                    self.edit_message(_cid, _mid, "\n".join(lines_txt))

            result_status = process_student(st, status_callback=update_step, headless=True, worker_id=worker_id)
            if result_status not in ("COMPLETED", "UNRECOVERABLE"):
                _ensure_internet()

            if result_status == "COMPLETED":
                certs = get_certificate_map()
                accs = get_existing_accounts()
                ac = accs.get(s_name, {})
                c_url = certs.get(s_name, "")
                self.send_message(
                    chat_id,
                    f"🎉 <b>[{idx}/{total}] MUVAFFAQIYATLI OLINDI!</b>\n"
                    f"🖥 <b>{pc1_tag}</b>\n"
                    f"👤 <b>{s_name}</b>\n"
                    f"📧 Login: <code>{ac.get('email', '—')}</code>\n"
                    f"🔑 Parol: <code>{ac.get('password', '—')}</code>\n"
                    f"🏅 Sertifikat: {c_url}",
                )
            elif result_status == "UNRECOVERABLE":
                errs = get_error_reason_map()
                self.send_message(
                    chat_id,
                    f"⚠️ <b>[{idx}/{total}] {s_name} — O'TKAZIB YUBORILDI! ({pc1_tag})</b>\n"
                    f"Sababi: <i>{errs.get(s_name, 'Oldin boshqa joyda roʻyxatdan oʻtgan va bazamizda login-paroli yoʻq')}</i>\n"
                    f"❗️ Bu o'quvchiga oxirida qayta urinilmaydi.",
                )
            else:
                self.send_message(
                    chat_id,
                    f"🔄 <b>[{idx}/{total}] {s_name} ({pc1_tag})</b> — 1-urinishda sertifikat chiqmadi, ro'yxat oxirida yana qayta tekshiriladi!",
                )
        finally:
            with _local_claimed_lock:
                if _local_claimed_students.get(s_norm) == worker_id:
                    _local_claimed_students.pop(s_norm, None)
            try:
                requests.post("http://127.0.0.1:8766/cluster/release_student", json={
                    "student_name": s_name,
                    "worker_tag": w_tag,
                    "status": locals().get("result_status", ""),
                }, timeout=3)
            except Exception:
                pass


    def worker_loop(self, worker_id: int):
        while True:
            if getattr(self, "is_paused", False):
                time.sleep(1.5)
                continue

            # Avval 1-chi (joriy ishlayotgan) zakazda o'quvchilar bo'lsa, barcha bo'sh Agentlar o'shani 100% tugatishga yordamlashadi!
            ctx, idx, st = self._pop_helper_task()
            if ctx is not None:
                try:
                    self._process_order_student(ctx, idx, st, worker_id)
                except Exception as e:
                    print(f"[AGENT #{worker_id} YORDAMCHI XATO] {e}")
                finally:
                    self.active_worker_status[worker_id] = ""
                    ctx["student_q"].task_done()
                continue

            try:
                order = order_queue.get_nowait()
            except queue.Empty:
                time.sleep(1.5)
                continue

            chat_id = order["chat_id"]
            students = order["students"]
            total = len(students)

            if not order.get("silent"):
                self.send_message(
                    chat_id,
                    f"⚡ <b>NAVBATINGIZ KELDI! (🤖 Agent #{worker_id} + Yordamchi AI Agentlar — 3 ta Agent ishlayapti!)</b>\n"
                    f"Jami <b>{total} ta</b> o'quvchi bo'yicha 100% sertifikat olish jarayoni boshlandi!",
                )

            # 1- va 2-bosqich aylanish (bo'sh oqimlar avtomatik parallel yordamlashadi)
            for pass_num in range(1, 3):
                done_set = get_completed_students()
                unrec_set = get_unrecoverable_students()
                if pass_num == 1:
                    rem = [s for s in students if s["name"] not in done_set]
                else:
                    rem = [s for s in students if s["name"] not in done_set and s["name"] not in unrec_set]
                if not rem:
                    break


                if pass_num > 1:
                    self.send_message(
                        chat_id,
                        f"🔄 <b>Qolib ketgan {len(rem)} ta o'quvchini qayta tekshirib 100% qilish bosqichi boshlandi...</b>\n"
                        f"<i>(Oldin boshqa joyda ro'yxatdan o'tgan va bazada paroli yo'q o'quvchilarga qayta urinilmaydi)</i>",
                    )

                student_q = queue.Queue()
                for idx, st in enumerate(students, 1):
                    student_q.put((idx, st))

                ctx = {
                    "chat_id": chat_id,
                    "user_name": order.get("user_name", ""),
                    "total": total,
                    "pass_num": pass_num,
                    "student_q": student_q,
                    "silent": order.get("silent", False),
                }
                with self.shared_lock:
                    self.shared_orders.append(ctx)

                try:
                    while True:
                        try:
                            idx, st = student_q.get_nowait()
                        except queue.Empty:
                            break
                        try:
                            self._process_order_student(ctx, idx, st, worker_id)
                        except Exception as e:
                            print(f"[OQIM #{worker_id} XATO] {e}")
                        finally:
                            self.active_worker_status[worker_id] = ""
                            student_q.task_done()

                    # Yordamga kirgan bo'sh oqimlar ham o'z o'quvchisini tugatishini kutamiz
                    student_q.join()
                finally:
                    with self.shared_lock:
                        if ctx in self.shared_orders:
                            self.shared_orders.remove(ctx)

            self.active_worker_status[worker_id] = ""
            # Yakuniy Excel (.xlsx) jadval tayyorlash va yuborish
            excel_path = os.path.join(ORDERS_DIR, f"Sertifikatlar_{chat_id}_{int(time.time())}.xlsx")
            generate_results_excel(students, excel_path)

            done_cnt = sum(1 for s in students if s["name"] in get_completed_students())
            unrec_cnt = sum(1 for s in students if s["name"] in get_unrecoverable_students())

            debt_info = get_user_debt_info(chat_id)
            rem_debt = debt_info.get("remaining_debt", 0)
            debt_footer = ""
            if rem_debt > 0:
                debt_footer = (
                    f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📒 <b>TO'LOV ESLATMASI (50% AVANS):</b>\n"
                    f"• Avans to'langan: <b>{debt_info.get('total_paid', 0):,} so'm</b>\n"
                    f"• 🔴 <b>Qolgan 50% to'lov summasi: {rem_debt:,} so'm</b>\n"
                    f"• To'lov uchun karta: <code>{self.card_info}</code>\n"
                    f"• Admin: <b>{ADMIN_USERNAME}</b>"
                )

            summary_caption = (
                f"📊 <b>BUYURTMA YAKUNLANDI! (TAYYOR EXCEL JADVAL)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 Jami o'quvchilar: <b>{total} ta</b>\n"
                f"✅ Sertifikat olindi: <b>{done_cnt} ta</b>\n"
                f"⚠️ Oldin ro'yxatdan o'tgan (bazada paroli yo'q): <b>{unrec_cnt} ta</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📎 Jadval ichida har bir o'quvchining <b>Email (Pochta), Parol, Sertifikat havolasi va Sertifikat ID raqami</b> to'liq yozilgan!"
                f"{debt_footer}"
            )
            self.send_document(chat_id, excel_path, caption=summary_caption)
            order_queue.task_done()

    def get_reply_keyboard(self, chat_id: int):
        if self.admin_id and chat_id == self.admin_id:
            return {
                "keyboard": [
                    [{"text": "🖥 Klaster (Kompyuterlar holati)"}, {"text": "📊 Tahlil va Jarayon"}],
                    [{"text": "📸 Kompyuterdan Skrinshot"}, {"text": "🖱 AnyDesk Jonli Ekran"}],
                    [{"text": "⏸ To'xtatish (Pauza)"}, {"text": "▶️ Qolgan joyidan davom ettirish"}],
                    [{"text": "🗑 Bekor qilish (Olib tashlash)"}, {"text": "🧹 Keshni tozalash"}],
                    [{"text": "⚡ Jonli Log (Console)"}, {"text": "💰 Foyda va Kassa"}],
                    [{"text": "📥 Tayyor Sertifikatlar (Excel)"}, {"text": "📄 Bo'sh Shablon (.xlsx)"}],
                    [{"text": "🖥 Qo'shimcha Oqim (Agent tanlash)"}, {"text": "🛠 AI Dasturchiga yozish (Skrinshot / Taklif)"}],
                ],
                "resize_keyboard": True,
                "is_persistent": True,
            }
        return {
            "keyboard": [
                [{"text": "📥 Excel Shablon olish"}, {"text": "📸 To'lov chekini yuborish"}],
                [{"text": "💰 Narxlar va 50% Avans"}, {"text": "👨‍💼 Admin bilan aloqa"}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }

    def resume_latest_unfinished_order(self, notify_chat_id: int = 0, manual: bool = False):
        try:
            self.is_paused = False
            try:
                requests.get("http://127.0.0.1:8766/cluster/pause?state=0", timeout=3)
            except Exception:
                pass
            active_busy = [w for w, st in self.active_worker_status.items() if st]
            if self.shared_orders and active_busy and manual:
                if notify_chat_id:
                    busy_lines = "\n".join([f"  • 🤖 Agent #{w}: <code>{ self.active_worker_status[w] }</code>" for w in sorted(active_busy)])
                    self.send_message(
                        notify_chat_id,
                        f"✅ <b>Jarayon hozir ham to'xtovsiz ishlayapti!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"{busy_lines}",
                        reply_markup=self.get_reply_keyboard(notify_chat_id),
                    )
                return True

            if not os.path.exists(ORDERS_DIR):
                return False
            files = sorted(
                [os.path.join(ORDERS_DIR, f) for f in os.listdir(ORDERS_DIR) if f.startswith("in_") and f.endswith(".xlsx")],
                key=os.path.getmtime,
                reverse=True,
            )
            done_set = get_completed_students()
            unrec_set = get_unrecoverable_students()
            for fpath in files:
                sts = parse_students_from_excel(fpath)
                if not sts:
                    continue
                rem = [s for s in sts if s["name"] not in done_set and s["name"] not in unrec_set]
                if rem:
                    bn = os.path.basename(fpath)
                    parts = bn.split("_")
                    ord_cid = int(parts[1]) if len(parts) >= 3 and parts[1].isdigit() else (self.admin_id or notify_chat_id)
                    if not self.shared_orders and order_queue.empty():
                        self.enqueue_order(ord_cid, "Admin", sts, silent=True)
                    done_c = sum(1 for s in sts if s["name"] in done_set)
                    unrec_c = sum(1 for s in sts if s["name"] in unrec_set)
                    if notify_chat_id:
                        self.send_message(
                            notify_chat_id,
                            f"▶️ <b>QOLGAN JOYIDAN DAVOM ETTIRILDI!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👥 Jami ro'yxat: <b>{len(sts)} ta</b>\n"
                            f"✅ Olingan sertifikatlar: <b>{done_c} ta</b>\n"
                            f"⚠️ O'tkazib yuborilgan (oldin ro'yxatdan o'tgan): <b>{unrec_c} ta</b>\n"
                            f"⏳ Qolgan o'quvchilar: <b>{len(rem)} ta</b> (<code>[{len(sts) - len(rem) + 1}/{len(sts)}] {rem[0]['name']}</code> dan boshlab)\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🚀 <b>{MAX_PARALLEL_WORKERS} ta asosiy AI Agent + Qo'shimcha oqim</b> qolgan joyidan ishni davom ettirmoqda!",
                            reply_markup=self.get_reply_keyboard(notify_chat_id),
                        )
                    return True
            if manual and notify_chat_id:
                self.send_message(
                    notify_chat_id,
                    "🎉 <b>Barcha buyurtmalar 100% yakunlangan!</b> Qolib ketgan o'quvchilar yo'q.",
                    reply_markup=self.get_reply_keyboard(notify_chat_id),
                )
        except Exception as e:
            print(f"[RESUME XATO] {e}")
        return False

    def pause_process(self, chat_id: int):
        self.is_paused = True
        try:
            requests.get("http://127.0.0.1:8766/cluster/pause?state=1", timeout=3)
        except Exception:
            pass
        self.send_message(
            chat_id,
            "⏸ <b>JARAYON VAQTINCHA TO'XTATILDI (PAUZA)!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛑 Barcha AI Agentlar va ulangan qo'shimcha kompyuterlar to'xtatildi.\n"
            "⏱ O'quvchilar ro'yxati va qilingan ishlar o'z joyida to'liq saqlandi.\n\n"
            "▶️ Qaytadan ishga tushirish uchun pastdagi <b>«▶️ Qolgan joyidan davom ettirish»</b> tugmasini bosing.",
            reply_markup=self.get_reply_keyboard(chat_id),
        )

    def cancel_active_order(self, chat_id: int):
        import shutil
        self.is_paused = False
        while not order_queue.empty():
            try:
                order_queue.get_nowait()
                order_queue.task_done()
            except Exception:
                break
        with self.shared_lock:
            self.shared_orders.clear()
        with _local_claimed_lock:
            _local_claimed_students.clear()
        self.active_worker_status.clear()

        archived_dir = os.path.join(ORDERS_DIR, "archived")
        os.makedirs(archived_dir, exist_ok=True)
        archived_count = 0
        if os.path.exists(ORDERS_DIR):
            for fn in os.listdir(ORDERS_DIR):
                if fn.startswith("in_") and (fn.endswith(".xlsx") or fn.endswith(".txt")):
                    src = os.path.join(ORDERS_DIR, fn)
                    dst = os.path.join(archived_dir, fn)
                    try:
                        shutil.move(src, dst)
                        archived_count += 1
                    except Exception:
                        pass

        try:
            requests.get("http://127.0.0.1:8766/cluster/clear_orders", timeout=3)
        except Exception:
            pass

        self.send_message(
            chat_id,
            "🗑 <b>BUYURTMA NAVBATDAN TO'LIQ OLIB TASHLANDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>{archived_count} ta</b> faol buyurtma fayli arxivga olindi.\n"
            "🛑 Barcha AI Agentlar va kompyuterlar bo'shatildi.\n\n"
            "📥 Endi xohlagan vaqtingizda yangi Excel shablon yoki ro'yxat tashlashingiz mumkin!",
            reply_markup=self.get_reply_keyboard(chat_id),
        )

    def clear_cache_keep_accounts(self, chat_id: int):
        import shutil
        accs_count = 0
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace") as af:
                    accs_count = len([x for x in af.read().splitlines() if x.strip() and "|" in x])
            except Exception:
                pass

        # 1. Eski navbatdagi buyurtmalarni to'liq tozalaymiz
        self.is_paused = False
        while not order_queue.empty():
            try:
                order_queue.get_nowait()
                order_queue.task_done()
            except Exception:
                break
        with self.shared_lock:
            self.shared_orders.clear()
        with _local_claimed_lock:
            _local_claimed_students.clear()
        self.active_worker_status.clear()


        # 2. Xatolar jurnalini arxivlab tozalaymiz (familya, ism, seriya, IFR blokirovkalar yechiladi)
        err_cleared = 0
        if os.path.exists(ERRORS_FILE):
            try:
                with open(ERRORS_FILE, "r", encoding="utf-8", errors="replace") as ef:
                    err_cleared = len(ef.read().splitlines())
                backup_p = f"xatolar_backup_{int(time.time())}.txt"
                shutil.copyfile(ERRORS_FILE, backup_p)
                with open(ERRORS_FILE, "w", encoding="utf-8") as ef:
                    ef.write("# Xatolar kesh tozalandi\n")
            except Exception as e:
                print(f"[CACHE ERR CLEAR] {e}")

        # 3. Faol in_*.xlsx yoki in_*.txt fayllarni arxivga olamiz
        archived_dir = os.path.join(ORDERS_DIR, "archived")
        os.makedirs(archived_dir, exist_ok=True)
        if os.path.exists(ORDERS_DIR):
            for fn in os.listdir(ORDERS_DIR):
                if fn.startswith("in_") and (fn.endswith(".xlsx") or fn.endswith(".txt")):
                    src = os.path.join(ORDERS_DIR, fn)
                    dst = os.path.join(archived_dir, fn)
                    try:
                        shutil.move(src, dst)
                    except Exception:
                        pass

        # 4. Klasterdagi bandliklar va keshni tozalaymiz
        try:
            requests.get("http://127.0.0.1:8766/cluster/clear_cache", timeout=3)
        except Exception:
            pass
        try:
            requests.get("http://127.0.0.1:8766/cluster/clear_orders", timeout=3)
        except Exception:
            pass

        self.send_message(
            chat_id,
            "🧹 <b>KESH MUVAFFAQIYATLI TOZALANDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>O'quvchilar xatoliklar jurnali ({err_cleared} ta yozuv) tozalandi:</b>\n"
            "• Familiya, ism, seriya, IFR bo'yicha oldingi blokirovkalar yechildi.\n"
            "• Navbatdagi eski buyurtmalar to'xtatildi va tozalandi.\n\n"
            f"🔐 <b>AKKAUNTLAR BAZASI 100% SAQLAB QOLINDI:</b>\n"
            f"• <b>{accs_count} ta</b> o'quvchining email (pochta) va parollari to'liq saqlandi!\n\n"
            "📥 <b>Qayta ishlash uchun:</b>\n"
            "O'sha Excel faylni yoki o'quvchi ma'lumotlarini chatga tashlang — bot saqlangan login va parollarni avtomatik topadi, qaytadan ro'yxatdan o'tmasdan to'g'ridan-to'g'ri sertifikat olishga kirishadi!",
            reply_markup=self.get_reply_keyboard(chat_id),
        )


    def build_ai_dev_smart_answer(self, text: str) -> str:
        done_tot = len(get_completed_students())
        ord_prog = self._get_latest_order_progress()
        ord_txt = ""
        if ord_prog:
            ord_txt = (
                f"📋 <b>Yangi zakaz ({ord_prog['total']} ta o'quvchi) bo'yicha aniq hisobot:</b>\n"
                f"• ✅ Sertifikat olinganlar: <b>{ord_prog['done']} ta</b>\n"
                f"• ⚠️ JSHSHIR xatoli (oldin o'tgan): <b>{ord_prog['unrec']} ta</b>\n"
                f"• ⏳ Qolgan o'quvchilar: <b>{ord_prog['rem']} ta</b> (ulardan <b>{ord_prog['acc_ready']} tasiga</b> pochta va Coursera DEDC ulangan!)\n\n"
            )

        import socket
        pc1_name = socket.gethostname()
        busy_pc1 = [f"🤖 #{w}: <i>{st_v[:80]}</i>" for w, st_v in sorted(self.active_worker_status.items()) if st_v]
        pc_lines = [f"• 💻 <b>1-Komp [{pc1_name}]</b> (3 Agent): " + (" | ".join(busy_pc1) if busy_pc1 else "Ishlayapti")]

        if os.path.exists("cluster_nodes_state.json"):
            try:
                with open("cluster_nodes_state.json", "r", encoding="utf-8") as nf:
                    st_nodes = json.load(nf)
                for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                    if ninfo.get("approved"):
                        pc_n = ninfo.get("pc_name", nid)
                        pc_w = int(ninfo.get("workers", 4))
                        comp_c = int(ninfo.get("completed_count", 0))
                        pc_ago = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                        st_b = "🟢 Faol" if pc_ago < 120 else f"🔴 Uzilgan ({pc_ago // 60}m)"
                        last_s = str(ninfo.get("status", "—"))[:75]
                        pc_lines.append(f"• 💻 <b>{idx_pc}-Komp [{pc_n}]</b> ({pc_w} Agent | 🏅{comp_c} ta | {st_b}): <i>{last_s}</i>")
            except Exception:
                pass

        return (
            f"{ord_txt}"
            f"📊 <b>Barcha 13 ta kompyuterning hozirgi soniyadagi holati (Bazada jami {done_tot} ta sertifikat):</b>\n"
            + "\n".join(pc_lines)
        )

    def send_cluster_agent_selector(self, chat_id: int):
        st_nodes = {}
        if os.path.exists("cluster_nodes_state.json"):
            try:
                with open("cluster_nodes_state.json", "r", encoding="utf-8") as nf:
                    st_nodes = json.load(nf)
            except Exception:
                st_nodes = {}
        if not st_nodes:
            st_nodes = {
                "DESKTOP-EKA9GM2-60DD": {
                    "pc_name": "DESKTOP-EKA9GM2-60DD",
                    "ram_gb": 16,
                    "workers": 6,
                }
            }

        now_ts = time.time()
        online_list = []
        idle_list = []
        offline_list = []
        for pc_idx, (node_id, ninfo) in enumerate(st_nodes.items(), start=2):
            pc_name = ninfo.get("pc_name", node_id)
            ram_gb = ninfo.get("ram_gb", 16)
            w_cnt = int(ninfo.get("workers", 4))
            ago_s = max(0, int(now_ts - float(ninfo.get("last_seen", 0))))
            if not ninfo.get("approved", True) or w_cnt == 0:
                idle_list.append(f"• 🟡 <b>{pc_idx}-Kompyuter [{pc_name}]</b> ({ram_gb} GB) — To'xtatilgan (0 Agent)")
            elif ago_s < 120:
                online_list.append(f"• 🟢 <b>{pc_idx}-Kompyuter [{pc_name}]</b> ({ram_gb} GB | {w_cnt} Agent) — Ishlayapti ({ago_s}s oldin)")
            else:
                offline_list.append(f"• 🔴 <b>{pc_idx}-Kompyuter [{pc_name}]</b> ({ram_gb} GB) — UZILGAN / O'CHIQ ({ago_s // 60} daqiqa oldin!)")

        summary_msg = (
            f"📡 <b>BARCHA KOMPYUTERLAR ALOQA VA FAOLLIK XULOSASI:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>Faol ishlayotganlar ({len(online_list) + 1} ta):</b>\n"
            f"• 🟢 <b>1-Kompyuter [Asosiy Server]</b> (8 GB | 3 Agent) — Ishlayapti\n"
            + ("\n".join(online_list) + "\n" if online_list else "")
            + (f"\n🟡 <b>Bo'sh / To'xtatilganlar ({len(idle_list)} ta):</b>\n" + "\n".join(idle_list) + "\n" if idle_list else "")
            + (f"\n🔴 <b>Uzilgan yoki O'chiq kompyuterlar ({len(offline_list)} ta):</b>\n" + "\n".join(offline_list) + "\n" if offline_list else "\n✅ <b>Uzilgan kompyuterlar yo'q!</b>\n")
        )
        self.send_message(chat_id, summary_msg, reply_markup=self.get_reply_keyboard(chat_id))

        for pc_idx, (node_id, ninfo) in enumerate(st_nodes.items(), start=2):
            pc_name = ninfo.get("pc_name", node_id)
            ram_gb = ninfo.get("ram_gb", 16)
            def_workers = int(ninfo.get("workers", 4))
            comp_c = int(ninfo.get("completed_count", 0))
            ago_s = max(0, int(now_ts - float(ninfo.get("last_seen", 0))))
            if not ninfo.get("approved", True) or def_workers == 0:
                state_str = "🟡 BO'SH / TO'XTATILGAN"
            elif ago_s < 120:
                state_str = f"🟢 FAOL ISHLAYAPTI ({ago_s} soniya oldin)"
            else:
                state_str = f"🔴 ALOQADAN UZILGAN YOKI O'CHIQ ({ago_s // 60} daqiqa oldin to'xtagan!)"

            last_st = ninfo.get("status", "—")
            markup = {
                "inline_keyboard": [
                    [
                        {"text": f"✅ Ha ({def_workers} ta Agent bo'linsin)", "callback_data": f"cl_set|{node_id}|{def_workers}"},
                    ],
                    [
                        {"text": "🤖 1 Agent", "callback_data": f"cl_set|{node_id}|1"},
                        {"text": "🤖 2 Agent", "callback_data": f"cl_set|{node_id}|2"},
                        {"text": "🤖 3 Agent", "callback_data": f"cl_set|{node_id}|3"},
                        {"text": "🤖 4 Agent", "callback_data": f"cl_set|{node_id}|4"},
                        {"text": "🤖 5 Agent", "callback_data": f"cl_set|{node_id}|5"},
                    ],
                    [
                        {"text": "🤖 6 Agent", "callback_data": f"cl_set|{node_id}|6"},
                        {"text": "🤖 7 Agent", "callback_data": f"cl_set|{node_id}|7"},
                        {"text": "🤖 8 Agent", "callback_data": f"cl_set|{node_id}|8"},
                        {"text": "🤖 9 Agent", "callback_data": f"cl_set|{node_id}|9"},
                        {"text": "🤖 10 Agent", "callback_data": f"cl_set|{node_id}|10"},
                    ],
                    [
                        {"text": "❌ Yo'q, to'xtatish", "callback_data": f"cl_set|{node_id}|0"},
                    ],
                ]
            }
            self.send_message(
                chat_id,
                f"🖥 <b>{pc_idx}-KOMPYUTER (OQIM) BOSHQARUVI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💻 {pc_idx}-Kompyuter: <b>{pc_name}</b>\n"
                f"📡 Holati: <b>{state_str}</b>\n"
                f"🧠 Operativka (RAM): <b>{ram_gb} GB</b> | 🏅 Olingan: <b>{comp_c} ta</b>\n"
                f"🤖 Hozirgi tanlangan oqim: <b>{def_workers} ta parallel AI Agent</b>\n"
                f"📋 Oxirgi jarayon: <i>{last_st}</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❓ <b>Nechta AI Agent bo'lib beray? (Bitta bosing — darhol o'zgaradi!)</b>",
                reply_markup=markup,
            )

    def send_profit_report_to_admin(self, chat_id: int):
        db = load_users_db()
        debts = db.get("debts", {})
        total_billed = sum(info.get("total_billed", 0) for info in debts.values())
        total_paid = sum(info.get("total_paid", 0) for info in debts.values())
        total_rem = sum(info.get("remaining_debt", 0) for info in debts.values())
        total_certs = len(get_completed_students())
        with self.stats_lock:
            hr_rev = self.hourly_stats["revenue_paid"]
            hr_ord = self.hourly_stats["orders_approved"]
            hr_st = self.hourly_stats["students_ordered"]

        msg = (
            f"💰 <b>FOYDA VA KASSA HISOBOTI (ADMIN)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Sof tushgan naqd/karta puli (Kassa):</b> <b>{total_paid:,} so'm</b>\n"
            f"🌗 <b>50% Avansdan kelishi kerak qoldiq:</b> <b>{total_rem:,} so'm</b>\n"
            f"📈 <b>Jami buyurtmalar umumiy aylanmasi:</b> <b>{total_billed:,} so'm</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>Oxirgi 1 soat ichida:</b>\n"
            f"• Tasdiqlangan zakazlar: <b>{hr_ord} ta</b> ({hr_st} ta o'quvchi)\n"
            f"• Tushgan to'lov: <b>+{hr_rev:,} so'm</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏅 <b>Bazadagi jami tayyor sertifikatlar:</b> <b>{total_certs} ta</b>\n"
            f"🏦 <b>Joriy to'lov kartasi:</b> <code>{self.card_info}</code>"
        )
        self.send_message(chat_id, msg, reply_markup=self.get_reply_keyboard(chat_id))

    def send_live_console_log(self, chat_id: int):
        import socket
        pc1_name = socket.gethostname()
        pc_lines = [f"=== 💻 1-KOMPYUTER [{pc1_name}] (3 ta AI Agent) ==="]
        for wid, st_txt in sorted(self.active_worker_status.items()):
            if st_txt:
                pc_lines.append(f"🤖 Agent #{wid}: {st_txt[:95]}")

        if os.path.exists("cluster_nodes_state.json"):
            try:
                with open("cluster_nodes_state.json", "r", encoding="utf-8") as nf:
                    st_nodes = json.load(nf)
                for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                    if ninfo.get("approved"):
                        pc_n = ninfo.get("pc_name", nid)
                        w_cnt = int(ninfo.get("workers", 4))
                        comp_c = int(ninfo.get("completed_count", 0))
                        ago_s = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                        st_tag = f"🟢 FAOL ({ago_s}s)" if ago_s < 120 else f"🔴 UZILGAN ({ago_s // 60}m)"
                        pc_lines.append(f"\n=== 💻 {idx_pc}-KOMPYUTER [{pc_n}] ({w_cnt} Agent | 🏅{comp_c} ta | {st_tag}) ===")
                        w_statuses = ninfo.get("worker_statuses") or {}
                        shown_w = 0
                        for wid_s in sorted(w_statuses.keys(), key=lambda x: int(x) if str(x).isdigit() else 99):
                            if int(wid_s) <= w_cnt:
                                pc_lines.append(f"🤖 Agent #{wid_s}: {str(w_statuses[wid_s])[:90]}")
                                shown_w += 1
                        if shown_w == 0 and ninfo.get("status"):
                            pc_lines.append(f"🤖 Holat: {str(ninfo.get('status'))[:90]}")
            except Exception:
                pass

        body_clean = "\n".join(pc_lines).replace("<", "&lt;").replace(">", "&gt;")
        msg = (
            f"🖥 <b>JONLI SERVER KONSOLI (BARCHA 13 TA KOMPYUTER):</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<code>{body_clean[:3600]}</code>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "🔄 Logni yangilash (Refresh)", "callback_data": "refresh_log"}],
                [{"text": "📊 Tahlilni ko'rish", "callback_data": "refresh_tahlil"}],
            ]
        }
        self.send_message(chat_id, msg, reply_markup=markup)

    def run_forever(self):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            except Exception:
                pass
        # Shablon faylni oldindan tayyorlab qo'yamiz
        create_template_excel()

        # Worker oqimlarni ishga tushiramiz
        for w_i in range(1, MAX_PARALLEL_WORKERS + 1):
            t = threading.Thread(target=self.worker_loop, args=(w_i,), daemon=True)
            t.start()

        # Har soatlik tahlil (analytics) oqimini ishga tushiramiz
        analytics_thread = threading.Thread(target=self.hourly_analytics_loop, daemon=True)
        analytics_thread.start()

        # Qo'shimcha kompyuterlar ko'prigi (cluster_master_bridge.py) doimiy avtomatik ishlashini ta'minlaymiz
        def _cluster_bridge_watchdog():
            import subprocess
            while True:
                try:
                    r = requests.get("http://127.0.0.1:8766/cluster/ping", timeout=3)
                    if r.status_code == 200:
                        time.sleep(20)
                        continue
                except Exception:
                    pass
                try:
                    bridge_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cluster_master_bridge.py")
                    if os.path.exists(bridge_py):
                        subprocess.Popen(
                            [sys.executable, "-u", bridge_py],
                            cwd=os.path.dirname(os.path.abspath(__file__)),
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=0x08000000 if sys.platform == "win32" else 0,
                        )
                except Exception:
                    pass
                time.sleep(20)

        threading.Thread(target=_cluster_bridge_watchdog, daemon=True).start()

        # Admin ga bot tayyor ekanligini bildiramiz (avtomat buyurtmani boshlab yubormaydi)
        if self.admin_id:
            try:
                if os.path.exists("startup_orders.json"):
                    os.remove("startup_orders.json")
            except Exception as e:
                print(f"[STARTUP WARN] {e}")
            try:
                self.resume_latest_unfinished_order(notify_chat_id=self.admin_id, manual=False)
            except Exception as e:
                print(f"[STARTUP RESUME WARN] {e}")

        print("=" * 70)
        print(f"🤖 UZBEK CODERS TELEGRAM BOT ISHGA TUSHDI! (Parallel oqimlar: {MAX_PARALLEL_WORKERS} ta)")
        print(f"👨‍💼 Admin aloqa: {ADMIN_USERNAME} | Soatlik tahlil: YOQILGAN")
        print("Telegramdan botga /start yoki /tahlil deb yozishingiz mumkin!")
        print("=" * 70)

        while True:
            try:
                resp = requests.get(
                    f"{self.api_url}/getUpdates",
                    params={"offset": self.offset, "timeout": 20},
                    timeout=(6, 26),
                ).json()
                for upd in resp.get("result", []):
                    self.offset = upd["update_id"] + 1
                    threading.Thread(target=self.process_update, args=(upd,), daemon=True).start()
            except Exception as e:
                time.sleep(1.5)

    def approve_and_start_order(self, admin_chat_id, target_uid: int, paid_now: int, mode_label: str):
        order_info = pending_orders.pop(target_uid, None)
        if not order_info:
            self.send_message(admin_chat_id, "⚠️ Bu buyurtma allaqachon tasdiqlangan yoki topilmadi.")
            return

        total_price = order_info["price"]
        user_name = order_info["user_name"]
        username = order_info.get("username", "")
        debt_added = max(0, total_price - paid_now)

        with self.stats_lock:
            self.hourly_stats["orders_approved"] += 1
            self.hourly_stats["students_ordered"] += len(order_info["students"])
            self.hourly_stats["revenue_paid"] += paid_now

        fin_entry = record_order_financials(
            target_uid,
            user_name,
            username,
            order_total=total_price,
            paid_now=paid_now,
            note=f"{len(order_info['students'])} ta o'quvchi ({mode_label})",
        )

        admin_msg = (
            f"✅ <b>Buyurtma tasdiqlandi va ish boshlandi!</b>\n"
            f"👤 Mijoz: <b>{user_name}</b> (ID: <code>{target_uid}</code>)\n"
            f"📋 Holat: <b>{mode_label}</b>\n"
            f"💰 Jami buyurtma summasi: <b>{total_price:,} so'm</b>\n"
            f"💵 Hozir to'landi (Avans): <b>{paid_now:,} so'm</b>\n"
            f"🌗 Ish bitgach to'lanadigan qismi: <b>{debt_added:,} so'm</b>"
        )
        self.send_message(admin_chat_id, admin_msg)

        if debt_added == 0:
            client_msg = (
                f"✅ <b>To'lovingiz ({paid_now:,} so'm) 100% to'liq tasdiqlandi!</b>\n"
                f"🤖 AI Agentimiz ishni boshlamoqda..."
            )
        else:
            client_msg = (
                f"✅ <b>Buyurtmangiz 50% AVANS to'lovi bilan tasdiqlandi!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Jami buyurtma summasi: <b>{total_price:,} so'm</b>\n"
                f"💵 Qabul qilingan avans: <b>{paid_now:,} so'm</b>\n"
                f"🌗 Ish yakunida to'lanadigan qolgan qismi: <b>{debt_added:,} so'm</b>\n"
                f"👨‍💼 Admin: <b>{ADMIN_USERNAME}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 AI Agentimiz hoziroq sertifikatlarni tayyorlashni boshlamoqda!"
            )

        self.send_message(target_uid, client_msg)
        self.enqueue_order(
            target_uid,
            user_name,
            order_info["students"],
            paid_info={"total": total_price, "paid": paid_now, "debt": debt_added},
        )

    def send_screenshot_menu(self, chat_id):
        import socket
        pc1_name = socket.gethostname()
        tun_url = get_cluster_tunnel_url()
        remote_url = f"{tun_url}/remote"
        rows = [
            [{"text": f"💻 1-Kompyuter [{pc1_name}] (Lokal / Asosiy)", "callback_data": "cl_scr|MASTER_PC"}]
        ]
        if os.path.exists("cluster_nodes_state.json"):
            try:
                st_nodes = json.load(open("cluster_nodes_state.json", "r", encoding="utf-8"))
                for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                    pc_n = ninfo.get("pc_name", nid)
                    ago_s = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                    badge = "🟢" if ago_s < 180 else "🔴"
                    rows.append([{"text": f"💻 {idx_pc}-Kompyuter [{pc_n}] ({badge})", "callback_data": f"cl_scr|{nid}"}])
            except Exception:
                pass
        rows.append([{"text": "📲 AnyDesk Jonli Boshqarish (Sensor)", "web_app": {"url": remote_url}}])
        self.send_message(
            chat_id,
            "📸 <b>QAYSI KOMPYUTER EKRANINI KO'RMOQCHISIZ?</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Kerakli kompyuterni tanlang — uning ekrani olinadi va boshqaruv knopkalari chiqadi:</i>",
            reply_markup={"inline_keyboard": rows}
        )

    def process_update(self, upd):
        # 1. Inline tugmalar bosilganda (Mijoz yoki Admin)
        if "callback_query" in upd:
            cb = upd["callback_query"]
            data = cb.get("data", "")
            from_id = cb["from"]["id"]

            if data.startswith("cl_set|"):
                try:
                    _, n_id, w_str = data.split("|", 2)
                    w_val = int(w_str)
                    act_val = "yes" if w_val > 0 else "no"
                    import urllib.parse
                    q_n = urllib.parse.quote(n_id)
                    requests.get(f"http://127.0.0.1:8766/cluster/approve?node={q_n}&w={w_val}&act={act_val}", timeout=5)
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": f"✅ {n_id}: {w_val} ta AI Agent o'rnatildi!"},
                        timeout=5,
                    )
                except Exception as e:
                    print(f"[CL_SET XATO] {e}")
                return

            if data == "get_template":
                self.send_template_to_user(from_id)
                return

            if data in ("refresh_log", "open_cluster", "refresh_tahlil"):
                try:
                    prog = self._get_latest_order_progress() or {}
                    d_c = prog.get("done", len(get_completed_students()))
                    t_c = prog.get("total", 577)
                    r_c = prog.get("remaining", 0)
                    last_nm = "—"
                    if os.path.exists(RESULTS_FILE):
                        with open(RESULTS_FILE, "r", encoding="utf-8", errors="replace") as _rf:
                            _lns = [x.strip() for x in _rf.read().splitlines() if "http" in x]
                            if _lns:
                                last_nm = _lns[-1].split("|")[0].strip()[:28]
                    alert_txt = (
                        f"📊 JONLI HOLAT ({time.strftime('%H:%M:%S')}):\n"
                        f"✅ Sertifikat: {d_c}/{t_c} ta (Jami baza: {len(get_completed_students())} ta)\n"
                        f"⏳ Qoldi: {r_c} ta\n"
                        f"🏅 Oxirgi: {last_nm}"
                    )[:198]
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": alert_txt, "show_alert": True},
                        timeout=5,
                    )
                except Exception:
                    pass

            if data == "refresh_log":
                self.send_live_console_log(from_id)
                return

            if data == "open_cluster":
                self.send_cluster_agent_selector(from_id)
                return

            if data == "refresh_tahlil":
                rep = self.build_hourly_analytics_text(reset_window=False)
                self.send_message(
                    from_id,
                    rep,
                    reply_markup={
                        "inline_keyboard": [
                            [{"text": "🔄 Yangilash", "callback_data": "refresh_tahlil"}, {"text": "⚡ Jonli Log", "callback_data": "refresh_log"}],
                            [{"text": "🖥 Klaster (Kompyuterlar holati)", "callback_data": "open_cluster"}],
                        ]
                    },
                )
                return

            # Mijoz "📸 To'lov chekini yuborish" tugmasini bosganda
            if data.startswith("send_check_") or data.startswith("credit_req_"):
                target_uid = int(data.split("_")[2])
                self.card_info = load_config().get("card_info", self.card_info)
                order_info = pending_orders.get(target_uid)
                if not order_info:
                    self.send_message(
                        from_id,
                        f"📸 <b>TO'LOV CHEKINI YUBORISH:</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏦 Karta: <code>{self.card_info}</code>\n\n"
                        f"To'lovni (100% to'liq yoki 50% avans) amalga oshirib, <b>chek rasmini (skrinshot) shu yerga chatga tashlang!</b>\n"
                        f"<i>(Agar o'quvchilar ro'yxatini hali tashlamagan bo'lsangiz, avval Excel shablon yoki ro'yxatni yuboring).</i>",
                    )
                    return
                half_p = order_info["price"] // 2
                self.send_message(
                    from_id,
                    f"📸 <b>TO'LOV CHEKINI YUBORISH:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 O'quvchilar soni: <b>{len(order_info['students'])} ta</b>\n"
                    f"💳 100% To'liq to'lov: <b>{order_info['price']:,} so'm</b>\n"
                    f"🌗 Yoki 50% Avans (Yarim to'lov): <b>{half_p:,} so'm</b>\n"
                    f"🏦 Karta: <code>{self.card_info}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 <b>To'lovni o'tkazib, chek rasmini (skrinshotini) shu yerga botga yuboring!</b>\n"
                    f"<i>Admin tasdiqlashi bilan bot darhol sertifikatlarni tayyorlashni boshlaydi (50% avans to'lasangiz, qolgan 50% qismi tayyor Excel jadval chiqqach to'lanadi).</i>",
                )
                return

            # Admin tasdiqlash tugmalari
            if data.startswith("approve_full_"):
                target_uid = int(data.split("_")[2])
                order_info = pending_orders.get(target_uid)
                if order_info:
                    self.approve_and_start_order(from_id, target_uid, paid_now=order_info["price"], mode_label="100% To'liq to'lov")
                else:
                    self.send_message(from_id, "⚠️ Bu buyurtma allaqachon tasdiqlangan yoki topilmadi.")
                return

            if data.startswith("approve_half_"):
                target_uid = int(data.split("_")[2])
                order_info = pending_orders.get(target_uid)
                if order_info:
                    half_p = order_info["price"] // 2
                    self.approve_and_start_order(from_id, target_uid, paid_now=half_p, mode_label="50% Yarim to'lov (Avans)")
                else:
                    self.send_message(from_id, "⚠️ Bu buyurtma allaqachon tasdiqlangan yoki topilmadi.")
                return

            if data.startswith("approve_custom_"):
                target_uid = int(data.split("_")[2])
                order_info = pending_orders.get(target_uid)
                if order_info:
                    admin_input_state[from_id] = {"action": "partial_order", "target_uid": target_uid}
                    self.send_message(
                        from_id,
                        f"✍️ <b>{order_info['user_name']}</b> jami <b>{order_info['price']:,} so'm</b> dan qancha avans to'ladi?\n\n"
                        f"Faqat raqam bilan yozib yuboring (masalan: <code>{order_info['price'] // 2}</code>):",
                    )
                else:
                    self.send_message(from_id, "⚠️ Bu buyurtma allaqachon tasdiqlangan yoki topilmadi.")
                return

            if data.startswith("approve_"):
                target_uid = int(data.split("_")[1])
                order_info = pending_orders.get(target_uid)
                if order_info:
                    self.approve_and_start_order(from_id, target_uid, paid_now=order_info["price"], mode_label="100% To'liq to'lov")
                else:
                    self.send_message(from_id, "⚠️ Bu buyurtma allaqachon tasdiqlangan yoki topilmadi.")
                return

            if data.startswith("reject_"):
                target_uid = int(data.split("_")[1])
                pending_orders.pop(target_uid, None)
                self.send_message(from_id, f"❌ Foydalanuvchi ({target_uid}) buyurtmasi rad etildi.")
                self.send_message(target_uid, f"❌ <b>To'lov tasdiqlanmadi.</b> Iltimos, qayta tekshirib yuboring yoki Admin bilan bog'laning: {ADMIN_USERNAME}")
                return

            # Admin qolgan 50% to'lovni yopish tugmalari
            if data.startswith("debt_clear_"):
                target_uid = int(data.split("_")[2])
                entry = record_debt_payment(target_uid, pay_amount=0)
                if entry:
                    self.send_message(from_id, f"✅ <b>{entry.get('name')}</b> ning qolgan to'lovi to'liq qabul qilindi! (Qoldiq: 0 so'm)")
                    self.send_message(target_uid, "✅ <b>Qolgan to'lovingiz to'liq qabul qilindi!</b> Hamkorligingiz uchun rahmat! 🤝")
                return

            if data.startswith("debt_part_"):
                target_uid = int(data.split("_")[2])
                d_info = get_user_debt_info(target_uid)
                admin_input_state[from_id] = {"action": "pay_debt", "target_uid": target_uid}
                self.send_message(
                    from_id,
                    f"💵 <b>{d_info.get('name', 'Mijoz')}</b> qolgan to'lovidan (<b>{d_info.get('remaining_debt', 0):,} so'm</b>) hozir qancha to'ladi?\n\n"
                    f"Summani raqam bilan yozib yuboring (masalan: <code>50000</code>):",
                )
                return

            if data.startswith("cl_scr|"):
                _, n_id = data.split("|", 1)
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": "📸 Yashirin skrinshot olinmoqda..."}, timeout=4)
                except Exception:
                    pass

                def _do_scr():
                    if n_id == "MASTER_PC" or n_id == "1":
                        scr_f = take_silent_screenshot()
                        if scr_f:
                            import socket
                            h_name = socket.gethostname()
                            inline_ctrl = build_screen_controls_keyboard()
                            caption = (
                                f"📸 <b>1-Kompyuter [{h_name}] (Lokal) Ekrani</b>\n"
                                f"⏱ Vaqt: <code>{time.strftime('%H:%M:%S')}</code> | 🖥 O'lcham: <code>1366x768</code>\n\n"
                                f"👇 <b>Quyidagi knopkalar bilan to'liq boshqaring:</b>\n"
                                f"• <b>9 ta hudud:</b> Tepa, Markaz, Past, Chap, O'ng\n"
                                f"• <b>Maxsus:</b> ✌️ 2x Klik, 🔘 O'ng tugma, ↵ Enter, ⌫ Back, ⎋ Esc, ⊞ Win\n"
                                f"• <b>Aniq koordinata:</b> <code>/click 500 300</code>\n"
                                f"• <b>Matn yozish:</b> <code>/type matn</code>\n"
                                f"• <b>Sensorli AnyDesk:</b> <i>«📲 Web AnyDesk (Sensor)»</i> knopkasi"
                            )
                            self.send_photo(from_id, scr_f, caption=caption, reply_markup=inline_ctrl)
                            try:
                                os.remove(scr_f)
                            except Exception:
                                pass
                        else:
                            self.send_message(from_id, "⚠️ Skrinshot olib bo'lmadi.")
                    else:
                        try:
                            import urllib.parse
                            q_n = urllib.parse.quote(n_id)
                            requests.get(f"http://127.0.0.1:8766/cluster/request_screenshot?node={q_n}&chat_id={from_id}", timeout=5)
                            def _check_reply():
                                time.sleep(7.0)
                                try:
                                    r = requests.get(f"http://127.0.0.1:8766/cluster/check_screen_req?node={q_n}", timeout=3).json()
                                    if r.get("take_screenshot"):
                                        self.send_message(
                                            from_id,
                                            f"⏳ <b>{n_id}</b> kompyuteridan skrinshot kutilmoqda...\n"
                                            f"💡 <i>Agar skrinshot kelmasa, 2-kompyuterda quyidagi buyruqni bir marta bosing:</i>\n"
                                            f"<code>powershell -Command \"irm http://192.168.1.5:8766/update | iex\"</code>"
                                        )
                                except Exception:
                                    pass
                            threading.Thread(target=_check_reply, daemon=True).start()
                        except Exception:
                            pass
                threading.Thread(target=_do_scr, daemon=True).start()
                return

            if data.startswith("n_clk|") or data.startswith("n_dclk|") or data.startswith("n_rclk|"):
                parts = data.split("|")
                action_type = "click"
                if parts[0] == "n_dclk":
                    action_type = "double_click"
                elif parts[0] == "n_rclk":
                    action_type = "right_click"
                n_node = parts[1]
                n_x = int(parts[2]) if len(parts) > 2 else None
                n_y = int(parts[3]) if len(parts) > 3 else None
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": f"🖱 {n_node}: Bosilmoqda ({n_x}, {n_y})..."}, timeout=3)
                except Exception:
                    pass
                try:
                    requests.post("http://127.0.0.1:8766/cluster/queue_node_action", json={"node_id": n_node, "action": action_type, "x": n_x, "y": n_y, "chat_id": from_id}, timeout=4)
                except Exception:
                    pass
                return

            if data.startswith("n_key|"):
                parts = data.split("|")
                n_node = parts[1]
                key_name = parts[2]
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": f"⌨️ {key_name.upper()} ({n_node}) bosilmoqda..."}, timeout=3)
                except Exception:
                    pass
                try:
                    requests.post("http://127.0.0.1:8766/cluster/queue_node_action", json={"node_id": n_node, "action": "key", "key": key_name, "chat_id": from_id}, timeout=4)
                except Exception:
                    pass
                return

            if data == "scr_list":
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"]}, timeout=2)
                except Exception:
                    pass
                self.send_screenshot_menu(from_id)
                return

            if data.startswith("m_clk|") or data.startswith("m_dclk|") or data.startswith("m_rclk|"):
                parts = data.split("|")
                action_type = "click"
                if parts[0] == "m_dclk":
                    action_type = "double_click"
                elif parts[0] == "m_rclk":
                    action_type = "right_click"
                m_x = int(parts[1]) if len(parts) > 1 else None
                m_y = int(parts[2]) if len(parts) > 2 else None
                move_and_click_mouse(m_x, m_y, action=action_type)
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": f"🖱 Sichqoncha bosildi ({m_x}, {m_y})!"}, timeout=3)
                except Exception:
                    pass

                def _do_after_click():
                    time.sleep(0.8)
                    scr_f = take_silent_screenshot()
                    if scr_f:
                        inline_ctrl = build_screen_controls_keyboard()
                        self.send_photo(from_id, scr_f, caption=f"🖱 <b>Sichqoncha bosildi ({m_x}, {m_y})</b>\n⏱ <code>{time.strftime('%H:%M:%S')}</code>", reply_markup=inline_ctrl)
                        try:
                            os.remove(scr_f)
                        except Exception:
                            pass
                threading.Thread(target=_do_after_click, daemon=True).start()
                return

            if data.startswith("m_key|"):
                key_name = data.split("|")[1]
                send_key_press(key_name)
                try:
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": f"⌨️ {key_name.upper()} bosildi!"}, timeout=3)
                except Exception:
                    pass

                def _do_after_key():
                    time.sleep(0.5)
                    scr_f = take_silent_screenshot()
                    if scr_f:
                        inline_ctrl = build_screen_controls_keyboard()
                        caption = (
                            f"⌨️ <b>{key_name.upper()} bosildi</b>\n"
                            f"⏱ <code>{time.strftime('%H:%M:%S')}</code> | 🖥 <code>1366x768</code>"
                        )
                        self.send_photo(from_id, scr_f, caption=caption, reply_markup=inline_ctrl)
                        try:
                            os.remove(scr_f)
                        except Exception:
                            pass
                threading.Thread(target=_do_after_key, daemon=True).start()
                return

            return

        msg = upd.get("message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        user_name = msg["from"].get("first_name", "Foydalanuvchi")
        username = msg["from"].get("username", "")
        text = (msg.get("text") or "").strip()

        # Handle video messages with caption containing student data
        if msg.get("video"):
            video = msg["video"]
            file_id = video["file_id"]
            # Download video to temporary path (optional)
            video_path = os.path.join("tmp", f"video_{chat_id}_{int(time.time())}.mp4")
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            self.download_file(file_id, video_path)
            caption = msg.get("caption", "").strip()
            if caption:
                students = parse_students_from_text(caption)
                if students:
                    self.handle_students_submission(chat_id, user_name, username, students)
                    return
            self.send_message(chat_id, "⚠️ Video qabul qilindi, lekin captionda amal qiluvchi o'quvchi ma'lumotlari topilmadi.", reply_markup=self.get_reply_keyboard(chat_id))
            return

        # Agar admin_id hali 0 bo'lsa, birinchi yozgan odamni Admin qilib saqlaymiz
        if not self.admin_id:
            self.admin_id = chat_id
            self.cfg["admin_id"] = chat_id
            save_config(self.cfg)
            print(f"[ADMIN SAQLANDI] Sizning Telegram ID: {chat_id}")

        # Admin AI Dasturchiga yozish tugmasini bosganda:
        if text in ("🛠 AI Dasturchiga yozish (Skrinshot / Taklif)", "/ai", "/dev"):
            admin_input_state[chat_id] = {"action": "ai_dev_note"}
            self.send_message(
                chat_id,
                "🛠 <b>AI DASTURCHIGA XABAR YOKI SKRINSHOT YUBORISH:</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✍️ Qanday yangilik, o'zgartirish yoki kamchilik borligini oddiy matn qilib yozing yoki <b>skrinshot (rasm)</b> tashlang!\n\n"
                "⚡ <i>Kompyuterga va AI Agentlarga umuman nagruzka (yuklama) tushirmaydi — yozganlaringiz va skrinshotlaringiz to'g'ridan-to'g'ri AI Dasturchi qutisiga saqlanadi!</i>",
                reply_markup=self.get_reply_keyboard(chat_id),
            )
            return

        known_buttons = (
            "🖥 Klaster (Kompyuterlar holati)",
            "📊 Tahlil va Jarayon",
            "📸 Kompyuterdan Skrinshot",
            "🖱 AnyDesk Jonli Ekran",
            "🖥 AnyDesk Jonli Ekran",
            "⚡ Jonli Log (Console)",
            "💰 Foyda va Kassa",
            "🌗 50% Avanslar",
            "📥 Tayyor Sertifikatlar (Excel)",
            "📄 Bo'sh Shablon (.xlsx)",
            "⏸ To'xtatish (Pauza)",
            "▶️ Qolgan joyidan davom ettirish",
            "🗑 Bekor qilish (Olib tashlash)",
            "🧹 Keshni tozalash",
            "🖥 Qo'shimcha Oqim (Agent tanlash)",
            "🛠 AI Dasturchiga yozish (Skrinshot / Taklif)",
            "📥 Excel Shablon olish",
            "📸 To'lov chekini yuborish",
            "💰 Narxlar va 50% Avans",
            "👨‍💼 Admin bilan aloqa",
        )
        if text in known_buttons or text.startswith("/"):
            admin_input_state.pop(chat_id, None)

        # Admin avans summasini yoki AI Dasturchiga xabar kiritayotgan bo'lsa:
        if chat_id in admin_input_state and text and not text.startswith("/"):
            st_cur = admin_input_state.get(chat_id, {})
            if st_cur.get("action") == "ai_dev_note" and text not in known_buttons:
                inbox_file = "ai_feedback_inbox.json"
                items = []
                if os.path.exists(inbox_file):
                    try:
                        with open(inbox_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                    except Exception:
                        items = []
                items.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "text",
                    "text": text,
                })
                with open(inbox_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                print(f"[AI-DASTURCHI-XABAR] {text}")
                smart_ans = self.build_ai_dev_smart_answer(text)
                self.send_message(
                    chat_id,
                    f"🛠 <b>AI DASTURCHIDAN JONLI JAVOB VA MASLAHAT:</b>\n"
                    f"📝 Sizning xabaringiz: <i>«{text}»</i>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{smart_ans}",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
                return

            digits = re.sub(r"[^\d]", "", text)
            if digits.isdigit() and st_cur.get("action") in ("partial_order", "pay_debt"):
                amount = int(digits)
                state = admin_input_state.pop(chat_id)
                target_uid = state["target_uid"]
                if state["action"] == "partial_order":
                    self.approve_and_start_order(chat_id, target_uid, paid_now=amount, mode_label=f"Avans to'lov ({amount:,} so'm)")
                elif state["action"] == "pay_debt":
                    entry = record_debt_payment(target_uid, pay_amount=amount)
                    if entry:
                        rem = entry.get("remaining_debt", 0)
                        self.send_message(
                            chat_id,
                            f"✅ <b>{entry.get('name')}</b> qolgan to'lovidan <b>{amount:,} so'm</b> qabul qilindi!\n"
                            f"🔴 Qolgan summa: <b>{rem:,} so'm</b>",
                        )
                        self.send_message(
                            target_uid,
                            f"💵 <b>{amount:,} so'm to'lovingiz qabul qilindi!</b>\n"
                            f"📒 Qolgan to'lov summasi: <b>{rem:,} so'm</b>",
                        )
                return

        # Doimiy Pastki Knopkalar (Reply Keyboard) va Buyruqlar:
        t_low = text.lower().strip()
        if text in ("⏸ To'xtatish (Pauza)", "/stop", "/pause") or t_low in ("to'xtatish", "toxtatish", "pauza", "pause", "stop"):
            admin_input_state.pop(chat_id, None)
            self.pause_process(chat_id)
            return

        if text in ("▶️ Qolgan joyidan davom ettirish", "/davom", "/resume") or t_low in ("davom", "davom ettirish", "resume"):
            admin_input_state.pop(chat_id, None)
            self.resume_latest_unfinished_order(notify_chat_id=chat_id, manual=True)
            return

        if text in ("🗑 Bekor qilish (Olib tashlash)", "/cancel", "/delete") or t_low in ("bekor qilish", "olib tashlash", "cancel", "ochirish"):
            admin_input_state.pop(chat_id, None)
            self.cancel_active_order(chat_id)
            return

        if text in ("🧹 Keshni tozalash", "/clear_cache", "/kesh") or t_low in ("kesh", "keshni tozalash", "clear cache"):
            admin_input_state.pop(chat_id, None)
            self.clear_cache_keep_accounts(chat_id)
            return

        if text in ("📸 Kompyuterdan Skrinshot", "/screen", "/skrin"):
            admin_input_state.pop(chat_id, None)
            self.send_screenshot_menu(chat_id)
            return

        if text in ("🖱 AnyDesk Jonli Ekran", "🖥 AnyDesk Jonli Ekran", "/anydesk", "/remote"):
            tun_url = get_cluster_tunnel_url()
            remote_url = f"{tun_url}/remote"
            import socket
            pc1_name = socket.gethostname()
            rows = [
                [{"text": "📲 AnyDesk Jonli Boshqarish (Ilova ichida)", "web_app": {"url": remote_url}}],
                [{"text": "🌐 Brauzerda Ochish (AnyDesk)", "url": remote_url}],
                [{"text": f"💻 1-Kompyuter [{pc1_name}] (Lokal Ekran)", "callback_data": "cl_scr|MASTER_PC"}]
            ]
            if os.path.exists("cluster_nodes_state.json"):
                try:
                    st_nodes = json.load(open("cluster_nodes_state.json", "r", encoding="utf-8"))
                    for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                        pc_n = ninfo.get("pc_name", nid)
                        ago_s = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                        badge = "🟢" if ago_s < 180 else "🔴"
                        rows.append([{"text": f"💻 {idx_pc}-Kompyuter [{pc_n}] ({badge})", "callback_data": f"cl_scr|{nid}"}])
                except Exception:
                    pass
            self.send_message(
                chat_id,
                "🖥 <b>ANYDESK JONLI EKRAN VA MASOFAVIY BOSHQARISH</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "👇 <b>Quyidagi tugmalardan birini tanlang:</b>\n"
                "• <b>📲 AnyDesk Jonli Boshqarish</b> — sensor orqali ekranga teginib boshqarish.\n"
                "• Yoki kompyuterni tanlab, Telegramdagi knopkalar orqali boshqarish.",
                reply_markup={"inline_keyboard": rows}
            )
            return

        if text.startswith("/click") or text.startswith("/rclick") or text.startswith("/dclick"):
            c_parts = text.split()
            if len(c_parts) >= 3 and c_parts[1].isdigit() and c_parts[2].isdigit():
                cx, cy = int(c_parts[1]), int(c_parts[2])
                c_act = "click"
                if text.startswith("/rclick"):
                    c_act = "right_click"
                elif text.startswith("/dclick"):
                    c_act = "double_click"
                move_and_click_mouse(cx, cy, action=c_act)
                self.send_message(chat_id, f"🖱 Sichqoncha X={cx}, Y={cy} nuqtaga bosildi!")

                def _send_after_cmd():
                    time.sleep(0.8)
                    scr_f = take_silent_screenshot()
                    if scr_f:
                        inline_ctrl = build_screen_controls_keyboard()
                        caption = f"🖱 <b>Sichqoncha bosildi ({cx}, {cy})</b>\n⏱ <code>{time.strftime('%H:%M:%S')}</code>"
                        self.send_photo(chat_id, scr_f, caption=caption, reply_markup=inline_ctrl)
                        try:
                            os.remove(scr_f)
                        except Exception:
                            pass
                threading.Thread(target=_send_after_cmd, daemon=True).start()
                return

        if text.startswith("/type "):
            type_text = text[6:]
            if type_text:
                send_unicode_string(type_text)
                self.send_message(chat_id, f"⌨️ Kompyuterga matn yozildi: <code>{type_text}</code>")
                def _send_after_type():
                    time.sleep(0.5)
                    scr_f = take_silent_screenshot()
                    if scr_f:
                        inline_ctrl = build_screen_controls_keyboard()
                        caption = f"⌨️ <b>«{type_text[:20]}» yozilgandan keyingi ekran:</b>\n⏱ <code>{time.strftime('%H:%M:%S')}</code>"
                        self.send_photo(chat_id, scr_f, caption=caption, reply_markup=inline_ctrl)
                        try:
                            os.remove(scr_f)
                        except Exception:
                            pass
                threading.Thread(target=_send_after_type, daemon=True).start()
                return

        if text in ("🖥 Klaster (Kompyuterlar holati)", "🖥 Qo'shimcha Oqim (Agent tanlash)", "/klaster", "/oqim", "/cluster"):
            admin_input_state.pop(chat_id, None)
            self.send_cluster_agent_selector(chat_id)
            return

        if text in ("📊 Tahlil va Jarayon", "/tahlil", "/holat", "/stat"):
            admin_input_state.pop(chat_id, None)
            rep = self.build_hourly_analytics_text(reset_window=False)
            self.send_message(
                chat_id,
                rep,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔄 Tahlilni yangilash", "callback_data": "refresh_tahlil"}, {"text": "⚡ Jonli Log (Console)", "callback_data": "refresh_log"}],
                        [{"text": "🖥 Klaster (Kompyuterlar holati)", "callback_data": "open_cluster"}],
                    ]
                },
            )
            return

        if text in ("💰 Foyda va Kassa", "/foyda", "/kassa"):
            admin_input_state.pop(chat_id, None)
            self.send_profit_report_to_admin(chat_id)
            return

        if text in ("⚡ Jonli Log (Console)", "/log", "/console"):
            admin_input_state.pop(chat_id, None)
            self.send_live_console_log(chat_id)
            return

        if text in ("🌗 50% Avanslar", "/avanslar", "/qarzlar"):
            admin_input_state.pop(chat_id, None)
            self.send_debts_report_to_admin(chat_id)
            return

        if text in ("📥 Tayyor Sertifikatlar (Excel)", "/sertifikatlar"):
            out_all = export_results_to_excel()
            if os.path.exists(out_all):
                self.send_document(chat_id, out_all, caption=f"📊 <b>Bazadagi barcha tayyor sertifikatlar ({len(get_completed_students())} ta)</b>")
            else:
                self.send_message(chat_id, "⚠️ Hozircha tayyor sertifikatlar fayli topilmadi.")
            return

        if text in ("📄 Bo'sh Shablon (.xlsx)", "📥 Excel Shablon olish", "/shablon", "/excel"):
            self.send_template_to_user(chat_id)
            return

        if text == "📸 To'lov chekini yuborish":
            self.card_info = load_config().get("card_info", self.card_info)
            order_info = pending_orders.get(chat_id)
            if order_info:
                half_p = order_info["price"] // 2
                self.send_message(
                    chat_id,
                    f"📸 <b>TO'LOV CHEKINI YUBORISH:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 O'quvchilar soni: <b>{len(order_info['students'])} ta</b>\n"
                    f"💳 100% To'liq to'lov: <b>{order_info['price']:,} so'm</b>\n"
                    f"🌗 Yoki 50% Avans (Yarim to'lov): <b>{half_p:,} so'm</b>\n"
                    f"🏦 Karta: <code>{self.card_info}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 <b>To'lovni o'tkazib, chek rasmini (skrinshotini) shu yerga botga yuboring!</b>\n"
                    f"<i>Admin tasdiqlashi bilan bot darhol sertifikatlarni tayyorlashni boshlaydi.</i>",
                )
            else:
                self.send_message(
                    chat_id,
                    f"📸 <b>TO'LOV CHEKINI YUBORISH:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏦 Karta: <code>{self.card_info}</code>\n\n"
                    f"👇 <b>To'lovni amalga oshirib, chek rasmini (skrinshotini) shu yerga chatga yuboring!</b>\n"
                    f"<i>(Agar yangi buyurtma bermoqchi bo'lsangiz, avval o'quvchilar ro'yxatini yoki to'ldirilgan Excel shablonni tashlang).</i>",
                )
            return

        if text == "💰 Narxlar va 50% Avans":
            self.handle_smart_question(chat_id, user_name, "narxi qancha")
            return

        if text == "👨‍💼 Admin bilan aloqa":
            self.send_message(chat_id, f"👨‍💼 <b>Admin bilan bog'lanish:</b> {ADMIN_USERNAME}", reply_markup={"inline_keyboard": [[{"text": f"👨‍💼 Adminga yozish ({ADMIN_USERNAME})", "url": ADMIN_TG_URL}]]})
            return

        if text.startswith("/start"):
            self.card_info = load_config().get("card_info", self.card_info)
            users_db = load_users_db()
            free_avail = "🎁 <b>Sizda 1 ta BEPUL sinov imkoniyati bor!</b>" if chat_id not in users_db.get("free_trial_used", []) else "✅ <i>Bepul sinovdan foydalangansiz</i>"
            welcome = (
                f"Assalomu alaykum, <b>{user_name}</b>! 👋\n\n"
                f"🤖 <b>UzbekCoders (Coursera) 100% Avtomat Sertifikat AI Agentiga xush kelibsiz!</b>\n"
                f"<i>(Agentimiz test rejimida ishni boshladi — taklif va hamkorlik bo'lsa Adminga {ADMIN_USERNAME} yozishingiz mumkin!)</i>\n\n"
                f"{free_avail}\n"
                f"<i>Biz halol ishlaymiz — dasturimizni tekshirib ko'rishingiz uchun 1 ta o'quvchini mutlaqo BEPUL qilib beramiz!</i>\n\n"
                f"💰 <b>Tariflarimiz:</b>\n"
                f"• 1 – 25 ta o'quvchi: <b>4 000 so'm</b> dan\n"
                f"• 26 – 50 ta o'quvchi: <b>3 500 so'm</b> dan\n"
                f"• 51 – 100 ta o'quvchi: <b>3 000 so'm</b> dan\n"
                f"• 100 tadan ko'p: <b>Kelishilgan narxda</b>\n\n"
                f"🌗 <b>To'lov tartibi (100% yoki 50% Avans):</b>\n"
                f"Buyurtma summasini <b>100% to'liq</b> yoki <b>50% yarim pulini (avans)</b> o'tkazib, chekni botga yuborishingiz mumkin (qolgan 50% qismi tayyor sertifikatlar chiqqach to'lanadi).\n"
                f"🏦 <b>Karta:</b> <code>{self.card_info}</code>\n\n"
                f"🔄 <b>100% Almashtirish kafolati:</b>\n"
                f"Agar ro'yxatingizda sertifikat olinmagan (oldin ro'yxatdan o'tgan yoki o'tmagan) o'quvchilar chiqsa, ularning o'rniga boshqa o'quvchilar berilsa <b>bepul to'ldirib beriladi!</b>\n\n"
                f"⏳ <b>Eslatma:</b> Sayt (aileaders.uz / Coursera) ishlamay qolsa, qotib qolsa yoki so'rov ko'payganda sertifikat olish biroz sekinlashishi mumkin (sayt ishlashi bilan avtomatik davom etadi — sabr qilishingizni so'raymiz. Buyurtma berilganda taxminiy tayyor bo'lish vaqti aytiladi).\n\n"
                f"📥 <b>Buyurtma berish uchun:</b>\n"
                f"Pastdagi <b>«📥 Excel Shablon olish»</b> tugmasini bosib shablonni to'ldirib yuboring yoki oddiy xabar ko'rinishida tashlang:\n"
                f"<code>FAMILIYA ISM SHARIF | 12.10.2015 | I-FR | 923446 | 5-V</code>\n\n"
                f"📊 Yakunda har bir o'quvchining <b>Email, Parol, Sertifikat havolasi va ID raqami</b> yozilgan tayyor <b>Excel (.xlsx)</b> jadvalni olasiz!"
            )
            self.send_message(chat_id, welcome, reply_markup=self.get_reply_keyboard(chat_id))
            return

        # 2. Agar foydalanuvchi rasm / skrinshot yuborgan bo'lsa
        if "photo" in msg:
            photo_id = msg["photo"][-1]["file_id"]
            uname_str = f"@{username}" if username else "—"
            # Agar rasm yuboruvchi ADMIN bo'lsa — uni AI Dasturchi uchun skrinshot sifatida saqlaymiz!
            if self.admin_id and chat_id == self.admin_id:
                admin_input_state.pop(chat_id, None)
                cap_txt = (msg.get("caption") or "").strip()
                img_path = self.download_file(photo_id, os.path.join(ORDERS_DIR, f"ai_screen_{int(time.time())}.jpg"))
                inbox_file = "ai_feedback_inbox.json"
                items = []
                if os.path.exists(inbox_file):
                    try:
                        with open(inbox_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                    except Exception:
                        items = []
                items.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "screenshot",
                    "image_path": img_path,
                    "caption": cap_txt,
                })
                with open(inbox_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                smart_ans = self.build_ai_dev_smart_answer(cap_txt or "skrinshot")
                self.send_message(
                    chat_id,
                    f"🛠 <b>AI DASTURCHIDAN SKRINSHOT TAHLILI VA JAVOB:</b>\n"
                    f"🖼 Fayl: <code>{os.path.basename(img_path)}</code>\n"
                    f"📝 Savol/Izoh: <i>{cap_txt or 'Skrinshot yuborildi'}</i>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{smart_ans}",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
                return

            if chat_id in pending_orders:
                order_info = pending_orders[chat_id]
                caption = (
                    f"💳 <b>YANGI TO'LOV CHEKI KELDI!</b>\n"
                    f"👤 Mijoz: <b>{user_name}</b> ({uname_str} | ID: <code>{chat_id}</code>)\n"
                    f"👥 O'quvchilar soni: <b>{len(order_info['students'])} ta</b>\n"
                    f"💰 100% Jami summa: <b>{order_info['price']:,} so'm</b>\n"
                    f"🌗 50% Avans summasi: <b>{order_info['price'] // 2:,} so'm</b>\n\n"
                    f"Mijoz 100% to'liq to'ladimi yoki 50% avans o'tkazdimi?"
                )
                markup = self.build_admin_approval_markup(chat_id, order_info["price"])
                requests.post(
                    f"{self.api_url}/sendPhoto",
                    data={"chat_id": self.admin_id, "photo": photo_id, "caption": caption, "parse_mode": "HTML", "reply_markup": json.dumps(markup)},
                    timeout=15,
                )
                self.send_message(
                    chat_id,
                    f"⏳ <b>To'lov cheki qabul qilindi!</b> Admin ({ADMIN_USERNAME}) tasdiqlashi bilan AI Agentimiz darhol ishni boshlaydi.",
                )
            else:
                d_info = get_user_debt_info(chat_id)
                rem_d = d_info.get("remaining_debt", 0)
                caption = (
                    f"📸 <b>MIJOZDAN TO'LOV CHEKI KELDI!</b>\n"
                    f"👤 Mijoz: <b>{user_name}</b> ({uname_str} | ID: <code>{chat_id}</code>)\n"
                    f"📒 Qolgan avans qoldig'i: <b>{rem_d:,} so'm</b>"
                )
                markup = {"inline_keyboard": [[{"text": f"✅ Qolgan to'lovni yopish ({rem_d:,} so'm)", "callback_data": f"debt_clear_{chat_id}"}]]} if rem_d > 0 else {}
                data_payload = {"chat_id": self.admin_id, "photo": photo_id, "caption": caption, "parse_mode": "HTML"}
                if markup:
                    data_payload["reply_markup"] = json.dumps(markup)
                requests.post(f"{self.api_url}/sendPhoto", data=data_payload, timeout=15)
                self.send_message(chat_id, f"✅ <b>To'lov chekingiz Adminga ({ADMIN_USERNAME}) yuborildi!</b>")
            return

        # 3. Agar foydalanuvchi .xlsx yoki .txt fayl tashlagan bo'lsa
        if "document" in msg:
            doc = msg["document"]
            fname = doc.get("file_name", "").lower()
            if fname.endswith(".xlsx"):
                local_p = self.download_file(doc["file_id"], os.path.join(ORDERS_DIR, f"in_{chat_id}_{int(time.time())}.xlsx"))
                students = parse_students_from_excel(local_p)
                self.handle_students_submission(chat_id, user_name, username, students)
                return
            elif fname.endswith(".txt") or fname.endswith(".csv"):
                local_p = self.download_file(doc["file_id"], os.path.join(ORDERS_DIR, f"in_{chat_id}_{int(time.time())}.txt"))
                with open(local_p, "r", encoding="utf-8", errors="replace") as f:
                    students = parse_students_from_text(f.read())
                self.handle_students_submission(chat_id, user_name, username, students)
                return

        # 4. Agar foydalanuvchi matn yuborgan bo'lsa: avval o'quvchi ro'yxatimi yoki savolmi tekshiramiz
        if text:
            students = parse_students_from_text(text)
            if students:
                self.handle_students_submission(chat_id, user_name, username, students)
            else:
                self.handle_smart_question(chat_id, user_name, text)


if __name__ == "__main__":
    _bot_lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _bot_lock_sock.bind(("127.0.0.1", 49880))
    except OSError:
        print("[!] Boshqa bot nusxasi allaqachon ishlab turibdi. Chiqilmoqda.")
        sys.exit(0)
    try:
        config = load_config()
        bot_server = TelegramBotServer(config)
        bot_server.run_forever()
    except BaseException:
        import traceback
        try:
            with open("tg_crash.log", "a", encoding="utf-8") as cf:
                cf.write(f"\n--- CRASH AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                traceback.print_exc(file=cf)
        except Exception:
            pass
