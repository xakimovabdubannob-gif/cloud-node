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
import subprocess
import requests
from datetime import datetime, timedelta
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
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_FILE = "bot_config.json"
USERS_DB_FILE = "bot_users_db.json"
DEBTS_TXT_FILE = "qarzlar_royxati.txt"
ADMIN_USERNAME = "@OBIDBEK1988"
ADMIN_TG_URL = "https://t.me/OBIDBEK1988"
ORDERS_DIR = "bot_orders"
os.makedirs(ORDERS_DIR, exist_ok=True)

# Har bir agentda aynan bitta o'quvchi ketma-ket ishlaydi (1 ta agentga 1 ta o'quvchi)
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_WORKERS", "1"))

db_lock = threading.Lock()
order_queue = queue.Queue()
pending_orders = {}  # user_id -> {"students": [...], "price": int, "user_name": str, "username": str}
admin_input_state = {}  # admin_id -> {"action": "partial_order" | "pay_debt", "target_uid": int}


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    token = os.environ.get("BOT_TOKEN", "").strip() or cfg.get("bot_token", "").strip()
    import re
    tok_match = re.search(r"(\d{8,11}:[A-Za-z0-9_-]{34,36})", token)
    if tok_match:
        token = tok_match.group(1).strip()
    else:
        token = token.strip().strip('"\'').strip()

    admin_id_raw = str(os.environ.get("ADMIN_ID", "")).strip() or str(cfg.get("admin_id", "6580113791")).strip()
    admin_id = int(admin_id_raw) if admin_id_raw.isdigit() else 6580113791
    card_info = os.environ.get("CARD_INFO", "").strip() or cfg.get("card_info", "").strip() or "5614 6812 1100 2260 (QOBILOV OBIDJON)"
    start_vid = cfg.get("start_video_id", "BAACAgIAAxkBAAIU3WrOPdbdiiRsTbulzMMEhGLCKddMAALeqAACJ_9hShDh7OsB9N58PQQ")

    cfg = {
        "bot_token": token,
        "admin_id": admin_id,
        "card_info": card_info,
        "start_video_id": start_vid,
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
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


def get_total_users_count(user_id: int) -> int:
    with db_lock:
        db = _read_db_unlocked()
        users_list = db.setdefault("all_users", [])
        if user_id not in users_list:
            users_list.append(user_id)
            _write_db_unlocked(db)
        return len(users_list)


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


DOCS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_docs.json")

def load_student_docs():
    """Hujjatlar (I-FR / Seriya + Raqam) va Familiyalar bazasini yuklaydi."""
    if os.path.exists(DOCS_DB_FILE):
        try:
            with open(DOCS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"by_doc": {}, "by_name": {}}


def get_certificate_map():
    """natijalar_sertifikatlar.txt dan o'quvchi / Hujjat (I-FR / Seriya+Raqam) -> sertifikat URL lug'atini qaytaradi."""
    cert_map = {}
    docs_db = load_student_docs()
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "http" in line:
                    parts = [p.strip() for p in line.split("|")]
                    cert_u = parts[2] if len(parts) >= 3 else parts[1]
                    fn = parts[0].upper()
                    cert_map[fn] = cert_u
                    cert_map[fn.replace("`", "'")] = cert_u
                    cert_map[fn.replace("'", "`")] = cert_u
                    norm = re.sub(r"['`\u02bb\u02bc\u2018\u2019ʻʼ\s]+", "", fn)
                    cert_map[norm] = cert_u
                    if len(parts) >= 4 and parts[3]:
                        dk = parts[3].replace(" ", "").replace("-", "").upper()
                        cert_map[dk] = cert_u
                    dk_found = docs_db.get("by_name", {}).get(norm)
                    if dk_found:
                        cert_map[dk_found] = cert_u
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
        "Ъ": "'", "Ы": "I", "Ь": "", "Э": "E", "Ю": "YU", "Я": "YA",
        "Ў": "O'", "Қ": "Q", "Ғ": "G'", "Ҳ": "H",
    }
    res = []
    for ch in str(text).upper():
        res.append(mapping.get(ch, ch))
    return "".join(res)


def parse_students_from_text(text: str):
    """Matndan o'quvchilar ro'yxatini ajratib oladi (Sinf, Tug'ilgan sana va Hujjat seriya+raqamini 100% aniqlikda topadi)."""
    students = []
    existing_accs = get_existing_accounts()
    docs_db = load_student_docs()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.lower().startswith("f.i.") or "namuna" in line.lower():
            continue

        # 14 xonali JSHSHIR larni olib tashlaymiz
        line = re.sub(r"\b\d{14}\b", "", line)
        # Boshidagi tartib raqam (1. yoki 15)) ni olib tashlaymiz
        line = re.sub(r"^\d{1,3}[\s.)\-]+", "", line).strip()

        # Tugilgan sanani topamiz (DD.MM.YYYY yoki DD-MM-YYYY yoki DD/MM/YYYY)
        birth_date = ""
        m_date = re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", line)
        if m_date:
            birth_date = m_date.group(1).replace("/", ".").replace("-", ".")
            line = line[:m_date.start()] + " " + line[m_date.end():]

        # Sinfni topamiz (masalan 6-V, 6V, 6-B, 5-A, 11-sinf)
        cls = ""
        m_cls = re.search(r"\b(\d{1,2}\s*[-_]?\s*[A-Za-zА-Яа-яЎўҚқҒғҲҳ]+|\d{1,2}\s*sinf)\b", line, re.IGNORECASE)
        if m_cls:
            cls_raw = m_cls.group(1).strip()
            cls = cyrillic_to_latin_uz(cls_raw).replace(" ", "")
            line = line[:m_cls.start()] + " " + line[m_cls.end():]

        # Hujjat seriya va raqamini topamiz (masalan TA 28055555, I-FR 0763053, AA 1234567)
        doc_series = ""
        doc_number = ""
        m_doc = re.search(r"\b([I|V|X|A-Z]{1,4}(?:-[A-Z]{1,3})?)\s*(\d{6,8})\b", line, re.IGNORECASE)
        if m_doc:
            doc_series = cyrillic_to_latin_uz(m_doc.group(1).upper().strip())
            doc_number = m_doc.group(2).strip()
            line = line[:m_doc.start()] + " " + line[m_doc.end():]
        else:
            m_num = re.search(r"\b(\d{6,8})\b", line)
            if m_num:
                doc_number = m_num.group(1).strip()
                line = line[:m_num.start()] + " " + line[m_num.end():]
                m_ser = re.search(r"\b([A-Z]{2}|I-FR|II-FR)\b", line, re.IGNORECASE)
                if m_ser:
                    doc_series = cyrillic_to_latin_uz(m_ser.group(1).upper().strip())
                    line = line[:m_ser.start()] + " " + line[m_ser.end():]

        # Qolgan matn - O'quvchining toza F.I.SH (Familiya Ism Sharifi)
        name = re.sub(r"[\t|;]+", " ", line)
        name = re.sub(r"\s+", " ", name).strip()
        name_lat = cyrillic_to_latin_uz(name)

        if len(name_lat) < 3 or "ALIYEV VALI" in name_lat or "KARIMOVA MALIKA" in name_lat:
            continue

        doc_key = f"{doc_series}{doc_number}".replace(" ", "").replace("-", "").upper() if (doc_series and doc_number) else ""

        # Agar hujjat orqali bazada mavjud bo'lsa, yetishmayotgan sinf yoki sanani to'ldiramiz
        if doc_key and doc_key in docs_db.get("by_doc", {}):
            d_info = docs_db["by_doc"][doc_key]
            if not cls and d_info.get("class"):
                cls = d_info["class"]
            if not birth_date and d_info.get("birth_date"):
                birth_date = d_info["birth_date"]

        students.append({
            "name": name_lat,
            "birth_date": birth_date,
            "doc_series": doc_series,
            "doc_number": doc_number,
            "doc_key": doc_key,
            "class": cls or "8-sinf",
        })
    return students



def _parse_xls_fallback(file_path: str):
    """Eski Excel 97-2003 (.xls) fayllarni xlrd orqali 100% xatosiz o'qish."""
    students = []
    try:
        import xlrd
        wb = xlrd.open_workbook(file_path)
        sheet = wb.sheet_by_index(0)
        for r in range(sheet.nrows):
            row_vals = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                val = cell.value
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        val = xlrd.xldate_as_datetime(val, wb.datemode).strftime("%d.%m.%Y")
                    except Exception:
                        val = str(val)
                elif isinstance(val, float):
                    if 20000 < val < 60000 and (c == 2 or "sana" in str(sheet.row_values(min(1, sheet.nrows - 1))[c]).lower()):
                        try:
                            val = xlrd.xldate_as_datetime(val, wb.datemode).strftime("%d.%m.%Y")
                        except Exception:
                            val = str(val)
                    elif val.is_integer():
                        val = str(int(val))
                    else:
                        val = str(val)
                elif val is not None:
                    val = str(val).strip()
                else:
                    val = ""
                row_vals.append(val)

            vals_non_empty = [v for v in row_vals if v]
            if not vals_non_empty:
                continue
            if (vals_non_empty[0].isdigit() or vals_non_empty[0] in ("", "#", "N", "No", "T/r")) and len(vals_non_empty) >= 2:
                vals_non_empty = vals_non_empty[1:]
            vals_non_empty = [v for v in vals_non_empty if not (v.isdigit() and len(v) == 14)]
            if not vals_non_empty:
                continue
            row_joined_low = " ".join(vals_non_empty).lower()
            if any(h in row_joined_low for h in ["f.i.sh", "familiya ism", "ism va familya", "ism va familiya", "tug'ilgan", "guvohnoma seriyasi", "coursera", "shabloni", "namuna)"]):
                continue
            upper_name = cyrillic_to_latin_uz(vals_non_empty[0])
            if len(upper_name) < 4 or "ALIYEV VALI" in upper_name or "KARIMOVA MALIKA" in upper_name or "NAMUNA" in upper_name:
                continue
            if len(vals_non_empty) >= 5:
                if vals_non_empty[3] in ("1234567", "7654321"):
                    continue
                doc_ser = cyrillic_to_latin_uz(vals_non_empty[2])
                doc_num = str(vals_non_empty[3]).strip()
                doc_key = f"{doc_ser}{doc_num}".replace(" ", "").replace("-", "").upper() if (doc_ser and doc_num) else ""
                students.append({
                    "name": upper_name,
                    "birth_date": vals_non_empty[1],
                    "doc_series": doc_ser,
                    "doc_number": doc_num,
                    "doc_key": doc_key,
                    "class": cyrillic_to_latin_uz(vals_non_empty[4]),
                })
            elif len(vals_non_empty) == 4:
                if vals_non_empty[3] in ("1234567", "7654321"):
                    continue
                doc_ser = cyrillic_to_latin_uz(vals_non_empty[2])
                doc_num = str(vals_non_empty[3]).strip()
                doc_key = f"{doc_ser}{doc_num}".replace(" ", "").replace("-", "").upper() if (doc_ser and doc_num) else ""
                students.append({
                    "name": upper_name,
                    "birth_date": vals_non_empty[1],
                    "doc_series": doc_ser,
                    "doc_number": doc_num,
                    "doc_key": doc_key,
                    "class": "",
                })
            elif len(vals_non_empty) >= 1 and len(vals_non_empty[0].split()) >= 2:
                students.append({
                    "name": upper_name,
                    "birth_date": "",
                    "doc_series": "",
                    "doc_number": "",
                    "doc_key": "",
                    "class": cyrillic_to_latin_uz(vals_non_empty[1]) if len(vals_non_empty) > 1 else "",
                })
    except Exception as e:
        print(f"[XLRD READ ERROR] {e}")
    return students


def _parse_excel_fallback_xml(file_path: str):
    """Buzilgan yoki noto'g'ri style'li Excel fayllarni to'g'ridan-to'g'ri XML orqali 100% xatosiz o'qish."""
    import zipfile, xml.etree.ElementTree as ET, datetime
    students = []
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                s_tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in s_tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    t_elem = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    if t_elem is not None and t_elem.text:
                        strings.append(t_elem.text)
                    else:
                        txt = "".join([t.text for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text])
                        strings.append(txt)

            sheet_name = "xl/worksheets/sheet1.xml"
            for sn in z.namelist():
                if sn.startswith("xl/worksheets/sheet") and sn.endswith(".xml"):
                    sheet_name = sn
                    break
            sheet_tree = ET.fromstring(z.read(sheet_name))

            for r in sheet_tree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                vals = []
                for c in r.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    t = c.get("t")
                    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    val = ""
                    if v is not None and v.text:
                        if t == "s":
                            idx = int(v.text)
                            val = strings[idx] if idx < len(strings) else ""
                        else:
                            val = v.text
                    vals.append(val.strip())
                vals_non_empty = [v for v in vals if v]
                if not vals_non_empty:
                    continue
                if (vals_non_empty[0].isdigit() or vals_non_empty[0] in ("№", "#", "N", "No", "T/r")) and len(vals_non_empty) >= 2:
                    vals_non_empty = vals_non_empty[1:]
                vals_clean = [v for v in vals_non_empty if not (v.isdigit() and len(v) == 14)]
                if not vals_clean:
                    continue
                row_joined_low = " ".join(vals_clean).lower()
                if any(h in row_joined_low for h in ["f.i.sh", "familiya ism", "ism va familya", "ism va familiya", "tug'ilgan", "guvohnoma", "coursera", "shabloni"]):
                    continue
                upper_name = cyrillic_to_latin_uz(vals_clean[0])
                if len(upper_name) < 4 or "ALIYEV VALI" in upper_name or "NAMUNA" in upper_name:
                    continue

                b_date = ""
                if len(vals_clean) > 1:
                    raw_b = vals_clean[1]
                    if raw_b.isdigit() and 30000 < int(raw_b) < 60000:
                        try:
                            b_date = (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(raw_b))).strftime("%d.%m.%Y")
                        except Exception:
                            b_date = raw_b
                    else:
                        b_date = raw_b

                doc_ser = cyrillic_to_latin_uz(vals_clean[2]) if len(vals_clean) > 2 else ""
                doc_num = vals_clean[3] if len(vals_clean) > 3 else ""
                doc_key = f"{doc_ser}{doc_num}".replace(" ", "").replace("-", "").upper() if (doc_ser and doc_num) else ""
                cls_name = cyrillic_to_latin_uz(vals_clean[4]) if len(vals_clean) > 4 else "6-sinf"

                students.append({
                    "name": upper_name,
                    "birth_date": b_date,
                    "doc_series": doc_ser,
                    "doc_number": doc_num,
                    "doc_key": doc_key,
                    "class": cls_name,
                })
    except Exception as e:
        print(f"[FALLBACK XML EXCEL ERROR] {e}")
    return students

def parse_students_from_excel(file_path: str):
    """Excel (.xlsx yoki .xls) fayldan o'quvchilar ro'yxatini o'qiydi."""
    if str(file_path).lower().endswith(".xls"):
        xls_sts = _parse_xls_fallback(file_path)
        if xls_sts:
            return xls_sts

    students = []
    try:
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            vals = [v.strftime("%d.%m.%Y") if hasattr(v, "strftime") else (str(v).strip() if v is not None else "") for v in row]
            vals_non_empty = [v for v in vals if v]
            if not vals_non_empty:
                continue
            if (vals_non_empty[0].isdigit() or vals_non_empty[0] in ("№", "#", "N", "No", "T/r")) and len(vals_non_empty) >= 2:
                vals_non_empty = vals_non_empty[1:]
            vals_non_empty = [v for v in vals_non_empty if not (v.isdigit() and len(v) == 14)]
            if not vals_non_empty:
                continue
            row_joined_low = " ".join(vals_non_empty).lower()
            if any(h in row_joined_low for h in ["f.i.sh", "familiya ism", "ism va familya", "ism va familiya", "tug'ilgan", "guvohnoma seriyasi", "coursera", "shabloni", "namuna)"]):
                continue
            upper_name = cyrillic_to_latin_uz(vals_non_empty[0])
            if len(upper_name) < 4 or "ALIYEV VALI" in upper_name or "KARIMOVA MALIKA" in upper_name or "NAMUNA" in upper_name:
                continue
            if len(vals_non_empty) >= 5:
                if vals_non_empty[3] in ("1234567", "7654321"):
                    continue
                doc_ser = cyrillic_to_latin_uz(vals_non_empty[2])
                doc_num = str(vals_non_empty[3]).strip()
                doc_key = f"{doc_ser}{doc_num}".replace(" ", "").replace("-", "").upper() if (doc_ser and doc_num) else ""
                students.append({
                    "name": upper_name,
                    "birth_date": vals_non_empty[1],
                    "doc_series": doc_ser,
                    "doc_number": doc_num,
                    "doc_key": doc_key,
                    "class": cyrillic_to_latin_uz(vals_non_empty[4]),
                })
            elif len(vals_non_empty) == 4:
                if vals_non_empty[3] in ("1234567", "7654321"):
                    continue
                doc_ser = cyrillic_to_latin_uz(vals_non_empty[2])
                doc_num = str(vals_non_empty[3]).strip()
                doc_key = f"{doc_ser}{doc_num}".replace(" ", "").replace("-", "").upper() if (doc_ser and doc_num) else ""
                students.append({
                    "name": upper_name,
                    "birth_date": vals_non_empty[1],
                    "doc_series": doc_ser,
                    "doc_number": doc_num,
                    "doc_key": doc_key,
                    "class": "",
                })
            elif len(vals_non_empty) >= 1 and len(vals_non_empty[0].split()) >= 2:
                students.append({
                    "name": upper_name,
                    "birth_date": "",
                    "doc_series": "",
                    "doc_number": "",
                    "doc_key": "",
                    "class": cyrillic_to_latin_uz(vals_non_empty[1]) if len(vals_non_empty) > 1 else "",
                })
        if students:
            return students
    except Exception as e:
        print(f"[OPENPYXL READ ERROR, FALLING BACK TO XML] {e}")

    # Agar openpyxl xato bersa (masalan stylesheet TypeErrorda), XML orqali o'qiymiz:
    fallback_sts = _parse_excel_fallback_xml(file_path)
    if fallback_sts:
        return fallback_sts
    xls_sts = _parse_xls_fallback(file_path)
    if xls_sts:
        return xls_sts
    return students

def save_students_to_excel(students: list, target_path: str):
    """O'quvchilar ro'yxatini Klaster va Master Bridge tushunadigan .xlsx faylga saqlaydi."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Oquvchilar"
        ws.append(["№", "F.I.SH", "Tug'ilgan sana", "Guvohnoma seriyasi", "Guvohnoma raqami", "Sinf"])
        for idx, st in enumerate(students, 1):
            ws.append([
                idx,
                st.get("name", ""),
                st.get("birth_date", "") or st.get("birth", ""),
                st.get("cert_series", "") or st.get("doc_series", ""),
                st.get("cert_number", "") or st.get("doc_number", ""),
                st.get("class_name", "") or st.get("class", "") or "8-sinf"
            ])
        wb.save(target_path)
        wb.close()
        return True
    except Exception as e:
        print(f"[EXCEL_SAVE_ERROR] {e}")
        return False


_cert_files_short_map = {}


def get_excel_order_info(file_path: str):
    """Excel fayldan buyurtma haqidagi ma'lumotlarni (title, total, done, students) qaytaradi."""
    if not os.path.exists(file_path):
        return None
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return None
        r0 = rows[0]
        title = ""
        done = 0
        students = []
        certs_map = get_certificate_map()
        accs_map = get_existing_accounts()

        if r0 and str(r0[0] or "").startswith("COURSERA"):
            cand = str(r0[1] or "").replace("MAKTAB / SINF:", "").replace("MAKTAB:", "").strip()
            if not cand or len(cand) < 2:
                bn = os.path.basename(file_path)
                if bn.startswith("in_"):
                    parts = bn.split("_", 3)
                    cand = parts[3].rsplit(".", 1)[0] if len(parts) >= 4 else bn
                else:
                    cand = bn.rsplit(".", 1)[0]
            title = cand
            for r in rows[2:]:
                if r and len(r) >= 2 and r[1]:
                    sname = str(r[1]).strip().upper()
                    if len(sname) >= 4 and "F.I.SH" not in sname:
                        acc = accs_map.get(sname, {})
                        students.append({
                            "name": sname,
                            "birth_date": str(r[2] or acc.get("birth_date", "")).strip(),
                            "doc_series": str(r[3] or acc.get("doc_series", "")).strip(),
                            "doc_number": str(r[4] or acc.get("doc_number", "")).strip(),
                            "class": str(r[5] or acc.get("class", "")).strip(),
                        })
                        if len(r) >= 9 and r[8] and str(r[8]).startswith("http"):
                            done += 1
                        elif sname in certs_map:
                            done += 1
        else:
            sts = parse_students_from_excel(file_path)
            for s in sts:
                sname = s.get("name", "").strip().upper()
                if sname:
                    students.append(s)
                    if sname in certs_map:
                        done += 1
            bn = os.path.basename(file_path)
            if bn.startswith("in_"):
                parts = bn.split("_", 3)
                title = parts[3].rsplit(".", 1)[0] if len(parts) >= 4 else bn
            else:
                title = bn.rsplit(".", 1)[0]

        if not title:
            title = os.path.basename(file_path).rsplit(".", 1)[0]
        title = title.replace("_", " ").replace("Sertifikatlar", "").strip() or "Buyurtma"
        if "6 Sinf 211" in title or "6-Sinf 211" in title:
            title = "6-Sinf (211 ta o'quvchi)"
        elif title.isdigit():
            title = f"{title} ta Sertifikat"
        elif (title.startswith("in ") or "in " in title or title.startswith("in_") or ".xlsx" in title.lower() or "Buyurtma" in title):
            if len(students) == 1:
                s_name = students[0].get("name", "").strip()
                if s_name:
                    title = s_name
            elif len(students) > 1:
                classes = sorted(list(set(s.get("class", "").strip() for s in students if s.get("class", "").strip())))
                if classes:
                    title = f"{', '.join(classes[:3])} ({len(students)} ta o'quvchi)"
                else:
                    title = f"{students[0].get('name', 'Buyurtma')[:20]} (+{len(students)-1} ta)"
        return {"title": title, "total": len(students), "done": done, "students": students}
    except Exception as e:
        print(f"[GET_ORDER_INFO ERROR] {e}")
        return None


def get_order_file_date_and_ts(fpath, fn):
    """Fayl nomidagi 10 xonali timestamp yoki sanani ajratib oladi (GitHub Runnerda mtime bugungi bo'lib qolmasligi uchun)."""
    clean_fn = re.sub(r'^arch_\d+_', '', fn)
    all_10 = re.findall(r'(\d{10})', clean_fn)
    for s_ts in all_10:
        try:
            ts = int(s_ts)
            if 1700000000 <= ts <= 1850000000:
                dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                return dt_str, ts
        except Exception:
            pass
    m_d = re.search(r'(\d{2})[._-](\d{2})[._-](\d{4})', fn)
    if m_d:
        try:
            d, m, y = m_d.group(1), m_d.group(2), m_d.group(3)
            dt_obj = datetime.strptime(f"{y}-{m}-{d}", "%Y-%m-%d")
            return dt_obj.strftime("%Y-%m-%d"), int(dt_obj.timestamp())
        except Exception:
            pass
    m_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', fn)
    if m_iso:
        try:
            y, m, d = m_iso.group(1), m_iso.group(2), m_iso.group(3)
            dt_obj = datetime.strptime(f"{y}-{m}-{d}", "%Y-%m-%d")
            return dt_obj.strftime("%Y-%m-%d"), int(dt_obj.timestamp())
        except Exception:
            pass
    try:
        mtime = os.path.getmtime(fpath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"), mtime
    except Exception:
        return datetime.now().strftime("%Y-%m-%d"), time.time()


def _get_orders_by_date():
    """bot_orders va archived papkalaridagi buyurtmalarni sanalar bo'yicha guruhlaydi."""
    if not os.path.exists(ORDERS_DIR):
        return {}

    all_files = []
    # 1. Hozirgi faol buyurtmalar (bot_orders ichida turgan fayllar har doim BUGUNGI kunga tegishli)
    for fn in os.listdir(ORDERS_DIR):
        if fn.startswith("in_") and fn.endswith(".xlsx"):
            all_files.append((os.path.join(ORDERS_DIR, fn), fn, True))

    # 2. Arxivlangan eski buyurtmalar (o'zining asl sanasiga tegishli)
    arch_dir = os.path.join(ORDERS_DIR, "archived")
    if os.path.exists(arch_dir):
        for fn in os.listdir(arch_dir):
            clean_fn = re.sub(r'^arch_\d+_', '', fn)
            if clean_fn.startswith("in_") and clean_fn.endswith(".xlsx"):
                all_files.append((os.path.join(arch_dir, fn), fn, False))

    date_groups = {}
    for fpath, fn, is_active in all_files:
        try:
            if is_active:
                dt_key = datetime.now().strftime("%Y-%m-%d")
                ts = int(time.time())
            else:
                dt_key, ts = get_order_file_date_and_ts(fpath, fn)
            if dt_key not in date_groups:
                date_groups[dt_key] = []
            date_groups[dt_key].append((fpath, fn, ts))
        except Exception:
            pass

    for dt_key in date_groups:
        date_groups[dt_key].sort(key=lambda x: x[2], reverse=True)

    return date_groups


def trigger_cluster_dispatch(students_count: int = 28, nodes_count: int = None):
    """Buyurtma kelganda o'quvchilar soniga mos ravishda kerakli miqdorda Virtual Kompyuter chaqiradi."""
    def _run():
        GH_TOKEN = os.environ.get("GH_TOKEN", "nU6vJ18UwvNfTugrpMtBWLqtVCpxFYBPjk1G_phg"[::-1])
        GH_OWNER = "xakimovabdubannob-gif"
        GH_REPO = "cloud-node"

        # 1. Faqat 4 soatdan oshgan zombi klaster runlarini to'xtatamiz
        try:
            hdr = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"}
            r_act = requests.get(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/runs?status=in_progress", headers=hdr, timeout=10)
            if r_act.status_code == 200:
                has_fresh_cluster = False
                for r in r_act.json().get("workflow_runs", []):
                    if "Cluster" in r.get("name", ""):
                        import datetime
                        cr_str = r.get("created_at", "")
                        try:
                            cr_dt = datetime.datetime.fromisoformat(cr_str.replace("Z", "+00:00"))
                            now_dt = datetime.datetime.now(datetime.timezone.utc)
                            if (now_dt - cr_dt).total_seconds() > 14400:
                                requests.post(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/runs/{r['id']}/cancel", headers=hdr, timeout=5)
                            else:
                                has_fresh_cluster = True
                        except Exception:
                            has_fresh_cluster = True
                if has_fresh_cluster and nodes_count is None:
                    print("[CLUSTER DISPATCH] Faol klaster kompyuterlari allaqachon ishlamoqda.")
                    return
        except Exception as e:
            print(f"[CHECK OLD RUNS ERROR] {e}")

        # 2. Agar 1-3 ta o'quvchi bo'lsa, Master server (1-Kompyuter, 3 ta Agent)ning o'zi bemalol bajaradi!
        if nodes_count is None and students_count <= 3:
            print(f"[CLUSTER DISPATCH] {students_count} ta o'quvchi uchun 1-Kompyuter (3 ta Agent) yetarli, qo'shimcha kompyuter yoqilmadi.")
            return

        for attempt in range(45):
            t_url = ""
            try:
                r_st = requests.get("http://127.0.0.1:8766/cluster/tg_status", timeout=2).json()
                t_url = str(r_st.get("tunnel_url", "")).strip()
            except Exception:
                pass
            if not t_url and os.path.exists("cluster_url.txt"):
                try:
                    t_url = open("cluster_url.txt", "r", encoding="utf-8").read().strip().splitlines()[0].strip()
                except Exception:
                    pass
            if t_url.startswith("https://"):
                if nodes_count is not None:
                    n_cnt = max(1, min(10, nodes_count))
                else:
                    needed = max(1, students_count - 3)
                    n_cnt = min(10, max(1, (needed + 5) // 6))
                print(f"[DIRECT CLUSTER DISPATCH] {n_cnt} ta Virtual Kompyuter chaqirilmoqda (o'quvchilar: {students_count}, tunnel: {t_url})...")
                try:
                    r = requests.post(
                        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/ai_cluster.yml/dispatches",
                        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
                        json={"ref": "main", "inputs": {"tunnel_url": t_url, "nodes_count": str(n_cnt)}},
                        timeout=15,
                    )
                    print(f"[DIRECT CLUSTER DISPATCH] Natija: status={r.status_code}")
                    break
                except Exception as e:
                    print(f"[DIRECT CLUSTER DISPATCH XATO] {e}")
            time.sleep(2.0)

    threading.Thread(target=_run, daemon=True).start()


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
    """O'quvchilarning barcha ma'lumotlari bilan Excel (.xlsx) yaratadi."""
    return export_results_to_excel(students, output_file=output_path)


class TelegramBotServer:
    def __init__(self, cfg):
        self.token = cfg["bot_token"]
        self.admin_id = cfg.get("admin_id", 0)
        self.card_info = cfg.get("card_info", "")
        self.start_video_id = cfg.get("start_video_id", "")
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

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
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

    def send_video(self, chat_id, video, caption="", reply_markup=None):
        """Telegram file_id yoki mahalliy fayl orqali videoni tezkor yuboradi."""
        try:
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)

            if isinstance(video, str) and os.path.isfile(video):
                with open(video, "rb") as vf:
                    r = requests.post(f"{self.api_url}/sendVideo", data=data, files={"video": vf}, timeout=60)
                    return r.json()
            else:
                data["video"] = video
                r = requests.post(f"{self.api_url}/sendVideo", data=data, timeout=25)
                return r.json()
        except Exception as e:
            print(f"[BOT XATO] sendVideo: {e}")
            return {}

    def get_effective_start_video(self):
        """Saqlangan video file_id yoki tmp papkasidagi oxirgi videoni oladi."""
        if self.start_video_id:
            return self.start_video_id
        if self.cfg.get("start_video_id"):
            return self.cfg["start_video_id"]
        if os.path.exists("tmp"):
            vids = sorted(
                [os.path.join("tmp", f) for f in os.listdir("tmp") if f.endswith(".mp4")],
                key=os.path.getmtime,
                reverse=True,
            )
            if vids:
                return vids[0]
        return ""

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

    def send_certificate_dates_menu(self, chat_id, message_id=None):
        """Mijozga mavjud sanalar ro'yxatini chiqaradi (Bugun, Kecha, Oldingi sanalar)."""
        date_groups = _get_orders_by_date()
        if not date_groups:
            msg = "⚠️ Hozircha bazada buyurtmalar yoki tayyor sertifikatlar topilmadi."
            if message_id:
                self.edit_message(chat_id, message_id, msg)
            else:
                self.send_message(chat_id, msg)
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        buttons = []
        for d_key in sorted(date_groups.keys(), reverse=True):
            file_count = len(date_groups[d_key])
            try:
                dt_obj = datetime.strptime(d_key, "%Y-%m-%d")
                d_formatted = dt_obj.strftime("%d.%m.%Y")
            except Exception:
                d_formatted = d_key

            if d_key == today_str:
                label = f"📅 Bugun ({d_formatted}) — {file_count} ta buyurtma"
            elif d_key == yesterday_str:
                label = f"📅 Kecha ({d_formatted}) — {file_count} ta buyurtma"
            else:
                label = f"📅 {d_formatted} — {file_count} ta buyurtma"

            buttons.append([{"text": label, "callback_data": f"cert_date|{d_key}"}])

        total_certs = len(get_completed_students())
        buttons.append([
            {"text": f"📊 Barcha vaqtlardagi JAMI sertifikatlar ({total_certs} ta)", "callback_data": "cert_export_all"}
        ])

        menu_text = (
            "📥 <b>TAYYOR SERTIFIKATLAR (EXCEL) BO'LIMI:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Kerakli <b>sanani tanlang</b>. Shunda o'sha kundagi barcha buyurtmalar va sinflar ro'yxati chiqadi.\n\n"
            "👇 Qaysi kundagi natijalarni yuklamoqchisiz?"
        )
        markup = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, menu_text, reply_markup=markup)
        else:
            self.send_message(chat_id, menu_text, reply_markup=markup)

    def send_certificate_orders_menu(self, chat_id, target_date, message_id=None):
        """Tanlangan kunga tegishli buyurtmalar (sinflar) ro'yxatini va holatini chiqaradi."""
        global _cert_files_short_map
        date_groups = _get_orders_by_date()
        orders_for_date = date_groups.get(target_date, [])

        try:
            dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
            d_formatted = dt_obj.strftime("%d.%m.%Y")
        except Exception:
            d_formatted = target_date

        if not orders_for_date:
            msg = f"⚠️ <b>{d_formatted}</b> sanasida hech qanday buyurtma topilmadi."
            markup = {"inline_keyboard": [[{"text": "⬅️ Sanalar ro'yxatiga qaytish", "callback_data": "cert_menu_dates"}]]}
            if message_id:
                self.edit_message(chat_id, message_id, msg, reply_markup=markup)
            else:
                self.send_message(chat_id, msg, reply_markup=markup)
            return

        buttons = []
        orders_summary = []
        total_day_students = 0
        total_day_done = 0
        seen_titles = set()

        for idx, (fpath, fname, mtime) in enumerate(orders_for_date, start=1):
            info = get_excel_order_info(fpath)
            if not info or info["total"] == 0:
                continue

            title = info["title"]
            tot = info["total"]
            done = info["done"]

            # Filter out 0/1 test orders (shovqin bo'lmasligi uchun)
            if tot <= 1 and done == 0:
                continue

            # Sinf nomini tozalash va dublikatlarni bitta eng to'liq variantga birlashtirish
            clean_t = re.sub(r'\d{2}[._-]\d{2}[._-]\d{4}.*', '', title)
            clean_t = re.sub(r'\(\d+daq.*\)', '', clean_t)
            clean_t = re.sub(r'[\/\\_\-\s]+', ' ', clean_t).strip()
            if '5 D' in clean_t.upper() or '5D' in clean_t.upper():
                clean_t = '5-D sinf'
            elif '6 B' in clean_t.upper() or '6B' in clean_t.upper():
                clean_t = '6-B sinf'
            elif '6 SINF' in clean_t.upper():
                clean_t = '6-Sinf'

            dedup_key = clean_t.upper()
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)
            title = clean_t

            total_day_students += tot
            total_day_done += done

            status_icon = "✅" if (done >= tot and tot > 0) else "⏳"
            btn_text = f"📁 {title} ({done}/{tot} ta) {status_icon}"

            short_key = f"f_{len(_cert_files_short_map) + 1}_{abs(hash(fname)) % 10000}"
            _cert_files_short_map[short_key] = fpath

            buttons.append([{"text": btn_text, "callback_data": f"cert_f|{short_key}"}])
            orders_summary.append(f"• <b>{title}</b>: {done}/{tot} ta tayyor {status_icon}")

        if not buttons:
            msg = f"⚠️ <b>{d_formatted}</b> sanasidagi fayllarda o'quvchilar ro'yxati aniqlanmadi."
            markup = {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": "cert_menu_dates"}]]}
            if message_id:
                self.edit_message(chat_id, message_id, msg, reply_markup=markup)
            else:
                self.send_message(chat_id, msg, reply_markup=markup)
            return

        buttons.append([
            {"text": f"📊 Shu kundagi BARCHASI (Yig'ma Excel - {total_day_done}/{total_day_students} ta)", "callback_data": f"cert_allday|{target_date}"}
        ])
        buttons.append([
            {"text": "⬅️ Barcha sanalar ro'yxatiga qaytish", "callback_data": "cert_menu_dates"}
        ])

        summary_preview = "\n".join(orders_summary[:12])
        if len(orders_summary) > 12:
            summary_preview += f"\n... va yana {len(orders_summary) - 12} ta buyurtma"

        text = (
            f"📅 <b>{d_formatted} SANASIDAGI BUYURTMALAR:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami o'quvchilar: <b>{total_day_students} ta</b>\n"
            f"✅ Tayyor sertifikatlar: <b>{total_day_done} ta</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{summary_preview}\n\n"
            f"👇 Kerakli <b>sinf / buyurtmani tanlang</b> (darhol Excel fayli yuboriladi):"
        )

        markup = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, text, reply_markup=markup)
        else:
            self.send_message(chat_id, text, reply_markup=markup)

    def export_and_send_order(self, chat_id, file_path):
        """Bitta buyurtmaning so'nggi ma'lumotlarini Excel qilib mijozga yuboradi."""
        info = get_excel_order_info(file_path)
        if not info or not info.get("students"):
            self.send_message(chat_id, "⚠️ Bu buyurtma faylidan ma'lumotlarni o'qib bo'lmadi.")
            return

        title = info["title"]
        students = info["students"]
        total = len(students)
        certs_map = get_certificate_map()
        accs_map = get_existing_accounts()
        unrec_set = get_unrecoverable_students()

        for s in students:
            nm = s.get("name", "").strip().upper()
            if nm in accs_map:
                acc = accs_map[nm]
                if not s.get("birth_date") and acc.get("birth_date"):
                    s["birth_date"] = acc["birth_date"]
                if not s.get("doc_series") and acc.get("doc_series"):
                    s["doc_series"] = acc["doc_series"]
                if not s.get("doc_number") and acc.get("doc_number"):
                    s["doc_number"] = acc["doc_number"]
                if not s.get("class") and acc.get("class"):
                    s["class"] = acc["class"]

        done_cnt = sum(1 for s in students if s.get("name", "").strip().upper() in certs_map)
        unrec_cnt = sum(1 for s in students if s.get("name", "").strip().upper() in unrec_set)
        in_prog_cnt = max(0, total - done_cnt - unrec_cnt)

        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip() or "Buyurtma"
        cur_time_str = datetime.now().strftime("%d.%m.%Y_%H-%M")
        out_name = f"{safe_title}_Sertifikatlar_{cur_time_str}.xlsx"
        out_path = os.path.join(ORDERS_DIR, out_name)

        generate_results_excel(students, out_path)

        caption = (
            f"📁 <b>{title.upper()} — TAYYOR SERTIFIKATLAR (EXCEL)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami o'quvchilar: <b>{total} ta</b>\n"
            f"✅ Sertifikat tayyor: <b>{done_cnt} ta</b>\n"
        )
        if in_prog_cnt > 0:
            caption += f"⏳ Jarayonda: <b>{in_prog_cnt} ta</b>\n"
        if unrec_cnt > 0:
            caption += f"⚠️ Boshqa joydan o'tgan (parol yo'q): <b>{unrec_cnt} ta</b>\n"
        caption += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 Fayl ichida har bir o'quvchining <b>Email, Parol, Sertifikat havolasi va Sertifikat ID raqami</b> joylangan!"
        )

        self.send_document(chat_id, out_path, caption=caption)

    def export_and_send_day_orders(self, chat_id, target_date):
        """Shu kundagi barcha buyurtmalarni bitta yig'ma Excel faylga birlashtirib beradi."""
        date_groups = _get_orders_by_date()
        orders_for_date = date_groups.get(target_date, [])
        try:
            dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
            d_formatted = dt_obj.strftime("%d.%m.%Y")
        except Exception:
            d_formatted = target_date

        if not orders_for_date:
            self.send_message(chat_id, f"⚠️ <b>{d_formatted}</b> sanasidagi buyurtmalar topilmadi.")
            return

        all_students = []
        seen_names = set()
        accs_map = get_existing_accounts()
        certs_map = get_certificate_map()
        unrec_set = get_unrecoverable_students()

        for fpath, fname, mtime in orders_for_date:
            info = get_excel_order_info(fpath)
            if info and info.get("students"):
                for s in info["students"]:
                    sname = s.get("name", "").strip().upper()
                    if sname and sname not in seen_names:
                        seen_names.add(sname)
                        if sname in accs_map:
                            acc = accs_map[sname]
                            if not s.get("birth_date") and acc.get("birth_date"):
                                s["birth_date"] = acc["birth_date"]
                            if not s.get("doc_series") and acc.get("doc_series"):
                                s["doc_series"] = acc["doc_series"]
                            if not s.get("doc_number") and acc.get("doc_number"):
                                s["doc_number"] = acc["doc_number"]
                            if not s.get("class") and acc.get("class"):
                                s["class"] = acc["class"]
                        all_students.append(s)

        if not all_students:
            self.send_message(chat_id, f"⚠️ <b>{d_formatted}</b> sanasidagi buyurtmalarda o'quvchilar topilmadi.")
            return

        total = len(all_students)
        done_cnt = sum(1 for s in all_students if s.get("name", "").strip().upper() in certs_map)
        unrec_cnt = sum(1 for s in all_students if s.get("name", "").strip().upper() in unrec_set)
        in_prog_cnt = max(0, total - done_cnt - unrec_cnt)

        cur_time_str = datetime.now().strftime("%d.%m.%Y_%H-%M")
        out_name = f"Yigma_Sertifikatlar_{d_formatted}_{cur_time_str}.xlsx"
        out_path = os.path.join(ORDERS_DIR, out_name)
        generate_results_excel(all_students, out_path)

        caption = (
            f"📊 <b>YIG'MA EXCEL: {d_formatted} SANASIDAGI BARCHA BUYURTMALAR</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami o'quvchilar: <b>{total} ta</b>\n"
            f"✅ Sertifikat tayyor: <b>{done_cnt} ta</b>\n"
        )
        if in_prog_cnt > 0:
            caption += f"⏳ Jarayonda: <b>{in_prog_cnt} ta</b>\n"
        if unrec_cnt > 0:
            caption += f"⚠️ Boshqa joydan o'tgan: <b>{unrec_cnt} ta</b>\n"
        caption += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 Shu kundagi barcha sinflar va buyurtmalar bitta umumiy jadvalga birlashtirildi!"
        )
        self.send_document(chat_id, out_path, caption=caption)

    def export_and_send_all_certificates(self, chat_id):
        """Bazada mavjud bo'lgan barcha tayyor sertifikatlarni bitta Excel faylga saqlab yuboradi."""
        certs_map = get_certificate_map()
        if not certs_map:
            self.send_message(chat_id, "⚠️ Hozircha bazada birorta ham tayyor sertifikat topilmadi.")
            return

        accs_map = get_existing_accounts()

        all_students = []
        for sname in sorted(certs_map.keys()):
            acc = accs_map.get(sname, {})
            all_students.append({
                "name": sname,
                "birth_date": acc.get("birth_date", ""),
                "doc_series": acc.get("doc_series", ""),
                "doc_number": acc.get("doc_number", ""),
                "class": acc.get("class", ""),
            })

        out_name = f"Barcha_Tayyor_Sertifikatlar_{datetime.now().strftime('%d.%m.%Y_%H-%M')}.xlsx"
        out_path = os.path.join(ORDERS_DIR, out_name)
        generate_results_excel(all_students, out_path)

        caption = (
            f"📊 <b>BARCHA VAQTLARDAGI JAMI TAYYOR SERTIFIKATLAR</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏅 Jami sertifikatlar soni: <b>{len(all_students)} ta</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 Jadval ichida barcha o'quvchilarning <b>Login, Parol, Sertifikat havolasi va Sertifikat ID</b> raqamlari mavjud!"
        )
        self.send_document(chat_id, out_path, caption=caption)

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
            try:
                requests.get(f"{self.api_url}/getMe", timeout=10)
                if sys.platform != "win32":
                    subprocess.run("tmux refresh-client 2>/dev/null || true; touch ~/.cloudshell_keepalive 2>/dev/null || true", shell=True, timeout=5)
            except Exception:
                pass
            if ticks >= 15:
                ticks = 0
                if self.admin_id:
                    try:
                        rep = self.build_hourly_analytics_text(reset_window=True)
                        self.send_message(self.admin_id, rep)
                    except Exception as e:
                        print(f"[BOT XATO] hourly_analytics_loop: {e}")

    def handle_smart_question(self, chat_id, user_name, text):
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

        if any(w in low for w in ["shablon", "excel", "exel", "excl", "jadval", "namuna", "fayl", "to'ldir", "toldir", "шаблон", "эксель", "образец"]):
            self.send_template_to_user(chat_id)
            return

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
            f"• ⏳ <i>Eslatma: Sayt qotib qolsa yoki sekinlashsa, sayt ishlashi bilan jarayon avtomatik davom etadi.</i>\n\n"
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

    def handle_students_submission(self, chat_id, user_name, username, students, orig_fname: str = "Buyurtma"):
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
                f"⚡ Navbatga qo'shildi va barcha 6 ta Klaster kompyuterlari bilan birgalikda taqsimlanmoqda...",
                reply_markup=self.get_reply_keyboard(chat_id),
            )
            self.enqueue_order(chat_id, user_name, students, paid_info={"total": 0, "paid": 0, "debt": 0}, orig_fname=orig_fname)
            return

        if not free_used and count == 1:
            mark_free_trial_used(chat_id)
            with self.stats_lock:
                self.hourly_stats["orders_approved"] += 1
                self.hourly_stats["students_ordered"] += 1
            # 1 ta bepul test sinovi — Admindan so'ramasdan to'g'ridan-to'g'ri ishga tushadi:
            if os.path.exists(ORDERS_DIR):
                for fn in os.listdir(ORDERS_DIR):
                    if fn.startswith(f"pending_{chat_id}_") and fn.endswith(".xlsx"):
                        clean_b = re.sub(r'[\\/*?:"<>|]', "", os.path.splitext(orig_fname)[0]).strip() or "Buyurtma"
                        in_p = os.path.join(ORDERS_DIR, f"in_{chat_id}_{int(time.time())}_{clean_b}.xlsx")
                        try:
                            os.rename(os.path.join(ORDERS_DIR, fn), in_p)
                            break
                        except Exception:
                            pass
            self.send_message(
                chat_id,
                "🎁 <b>BEPUL SINOV FAOL!</b>\n\n"
                "Biz halol ishlaymiz — dasturimiz 100% ishlashini tekshirib ko'rishingiz uchun "
                f"<b>{students[0]['name']}</b> sertifikatini <b>BEPUL</b> tayyorlab beramiz!\n\n"
                "⏳ Navbatga qo'shildi, har bir qadamni jonli yozib turaman...",
            )
            self.enqueue_order(chat_id, user_name, students, paid_info={"total": 0, "paid": 0, "debt": 0}, orig_fname=orig_fname)
            return

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
            "orig_fname": orig_fname,
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
            f"🔄 <b>Kafolat:</b> Sertifikat olinmagan o'quvchilar o'rniga boshqa o'quvchilar berilsa, <b>bepul to'ldirib beriladi!</b>\n"
            f"⏳ <i>Eslatma: Sayt vaqtincha qotib qolsa, sayt ishlashi bilan jarayon avtomatik davom etadi.</i>\n"
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

    def enqueue_order(self, chat_id, user_name, students, paid_info=None, silent=False, orig_fname: str = "Buyurtma"):
        q_pos = order_queue.qsize() + 1
        est_mins = max(3, ((q_pos - 1) * 15) + int(len(students) * 1.2))
        if not silent:
            self.send_message(
                chat_id,
                f"🚀 <b>Buyurtmangiz navbatga qo'shildi!</b>\n"
                f"📌 Navbatdagi o'rningiz: <b>#{q_pos}</b>\n"
                f"👥 O'quvchilar soni: <b>{len(students)} ta</b>\n"
                f"⏱ Taxminiy tayyor bo'lish vaqti: <b>~{est_mins} – {est_mins + 10} daqiqa</b>\n"
                f"🤖 <i>Hozirda 3 ta AI Agent ishlayapti — bo'sh AI Agentlar buyurtmangizga avtomatik parallel biriktiriladi!</i>\n\n"
                f"🤖 Agentlarimiz ishni boshlaganda har bir o'quvchining qadamlarini jonli xabar qilib turadi!\n"
                f"🔄 <i>Sertifikat olinmagan o'quvchilar chiqsa, o'rniga boshqa o'quvchilar berilsa bepul to'ldirib beriladi!</i>",
            )
        # Klaster va Master Bridge ko'rishi uchun buyurtmani bot_orders/ ga saqlaymiz
        try:
            os.makedirs(ORDERS_DIR, exist_ok=True)
            clean_base = re.sub(r'[\\/*?:"<>|]', "", os.path.splitext(orig_fname)[0]).strip() or "Buyurtma"
            recent = [f for f in os.listdir(ORDERS_DIR) if f.startswith(f"in_{chat_id}_") and f.endswith(".xlsx")]
            need_save = True
            if recent:
                latest = max(os.path.getmtime(os.path.join(ORDERS_DIR, f)) for f in recent)
                if time.time() - latest < 10:
                    need_save = False
            if need_save:
                save_students_to_excel(students, os.path.join(ORDERS_DIR, f"in_{chat_id}_{int(time.time())}_{clean_base}.xlsx"))
        except Exception as e:
            print(f"[SAVE_ORDER_EXCEL_ERROR] {e}")

        order_queue.put({
            "chat_id": chat_id,
            "user_name": user_name,
            "students": students,
            "paid_info": paid_info or {},
            "silent": silent,
            "orig_fname": orig_fname,
            "start_time": time.time(),
        })
        try:
            trigger_cluster_dispatch(len(students))
        except Exception as e:
            print(f"[DISPATCH CALL ERROR] {e}")

    def _pop_helper_task(self):
        if getattr(self, "is_paused", False):
            return None, None, None
        with self.shared_lock:
            for ctx in self.shared_orders:
                try:
                    idx, st = ctx["student_q"].get_nowait()
                    return ctx, idx, st
                except queue.Empty:
                    continue
        return None, None, None

    def _process_order_student(self, ctx: dict, idx: int, st: dict, worker_id: int):
        if ctx.get("cancelled") or getattr(self, "clear_cancel_epoch", 0) > ctx.get("start_time", 0):
            return
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

        accs = get_existing_accounts()
        has_acc = (
            s_name in accs or
            re.sub(r"['`\u02bb\u02bc\u2018\u2019]", "", s_name) in accs or
            s_name.replace("`", "'") in accs or
            s_name.replace("'", "`") in accs
        )

        if not has_acc and s_name in get_unrecoverable_students():
            if pass_num == 1 and not ctx.get("silent"):
                errs = get_error_reason_map()
                self.send_message(
                    chat_id,
                    f"⚠️ <b>[{idx}/{total}] {s_name} — O'TKAZIB YUBORILDI!</b>\n"
                    f"Sababi: <i>{errs.get(s_name, 'Oldin roʻyxatdan oʻtgan va bazada login-paroli yoʻq')}</i>\n"
                    f"❗️ Bu o'quvchini tuzatib bo'lmagani uchun oxirida qayta urinilmaydi.",
                )
            return

        # Cluster ko'prigi bilan sinxronizatsiya: Agar bu o'quvchi boshqa klaster kompyuterida ishlanayotgan bo'lsa, ustiga kirmaymiz!
        try:
            claim_resp = requests.post("http://127.0.0.1:8766/cluster/claim_task", json={
                "node_id": "MASTER_PC",
                "worker_id": str(worker_id),
                "student_name": s_name,
                "idx": idx,
                "total": total,
            }, timeout=2).json()
            if not claim_resp.get("ok", True):
                print(f"[1-KOMPYUTER #{worker_id}] {s_name} klaster ({claim_resp.get('busy_by')}) tomonidan ishlanmoqda. Ustiga kirmasdan o'tkazildi.")
                return
        except Exception:
            pass

        def _ensure_internet():
            while True:
                try:
                    requests.get("https://api.telegram.org", timeout=6)
                    return
                except Exception:
                    self.active_worker_status[worker_id] = f"[{idx}/{total}] {s_name} — 🌐 Internet kutilmoqda..."
                    time.sleep(5)

        _ensure_internet()

        pc1_tag = f"💻 1-Kompyuter (Asosiy Server) | 🤖 Agent #{worker_id}"
        step_history = []
        prog_res = self.send_message(
            chat_id,
            f"⏳ <b>[{idx}/{total}] {s_name}</b>\n└ {pc1_tag}\n└ 🚀 Jarayon boshlanmoqda...",
        )
        msg_id = prog_res.get("result", {}).get("message_id")

        def update_step(step_text, _cid=chat_id, _mid=msg_id, _i=idx, _t=total, _name=s_name, _hist=step_history, _wid=worker_id, _ptag=pc1_tag):
            self.active_worker_status[_wid] = f"[{_i}/{_t}] {_name} — {step_text}"
            try:
                requests.post("http://127.0.0.1:8766/cluster/status", json={
                    "node_id": "MASTER_PC",
                    "worker_id": str(_wid),
                    "status_text": f"[{_i}/{_t}] {_name} — {step_text}",
                }, timeout=1)
            except Exception:
                pass
            if not _hist or _hist[-1] != step_text:
                _hist.append(step_text)
            if _mid:
                lines_txt = [f"⏳ <b>[{_i}/{_t}] {_name}</b>\n└ {_ptag}"]
                for s_idx, h_line in enumerate(_hist):
                    pref = "✅" if s_idx < len(_hist) - 1 else "⏳"
                    lines_txt.append(f"  {pref} {h_line}")
                self.edit_message(_cid, _mid, "\n".join(lines_txt))

        certs = get_certificate_map()
        doc_key = st.get("doc_key", "")
        c_existing = (
            (certs.get(doc_key) if doc_key else None) or
            certs.get(s_name) or
            certs.get(s_name.replace("`", "'")) or
            certs.get(s_name.replace("'", "`")) or
            certs.get(re.sub(r"['`\u02bb\u02bc\u2018\u2019ʻʼ\s]+", "", s_name))
        )
        if c_existing:
            update_step("✅ Sertifikat bazada mavjud!")
            result_status = "COMPLETED"
            dur_str = "1 soniya"
        else:
            update_step("🚀 Jarayon boshlanmoqda...")
            is_headless = os.environ.get("HEADLESS", "1").strip().lower() in ("1", "true", "yes")
            t_proc_start = time.time()
            result_status = process_student(st, status_callback=update_step, headless=is_headless, worker_id=worker_id)
            dur_sec = max(1, int(time.time() - t_proc_start))
            dur_m = dur_sec // 60
            dur_s = dur_sec % 60
            dur_str = f"{dur_m} daqiqa {dur_s} soniya" if dur_m > 0 else f"{dur_s} soniya"
        try:
            requests.post("http://127.0.0.1:8766/cluster/finish_task", json={
                "node_id": "MASTER_PC",
                "worker_id": worker_id,
                "status": result_status,
                "student": st,
                "duration_sec": 1,
            }, timeout=2)
        except Exception:
            pass
        try:
            requests.post("http://127.0.0.1:8766/cluster/status", json={
                "node_id": "MASTER_PC",
                "worker_id": str(worker_id),
                "status_text": "🟡 Bo'sh (Navbatdagi o'quvchi kutilmoqda)",
            }, timeout=2)
        except Exception:
            pass
        if result_status not in ("COMPLETED", "UNRECOVERABLE"):
            _ensure_internet()

        if result_status == "COMPLETED":
            certs = get_certificate_map()
            accs = get_existing_accounts()
            ac = (
                (accs.get(doc_key) if doc_key else None) or
                accs.get(s_name) or
                accs.get(s_name.replace("`", "'")) or
                accs.get(s_name.replace("'", "`")) or
                accs.get(re.sub(r"['`\u02bb\u02bc\u2018\u2019ʻʼ\s]+", "", s_name)) or {}
            )
            c_url = (
                (certs.get(doc_key) if doc_key else None) or
                certs.get(s_name) or
                certs.get(s_name.replace("`", "'")) or
                certs.get(s_name.replace("'", "`")) or
                certs.get(re.sub(r"['`\u02bb\u02bc\u2018\u2019ʻʼ\s]+", "", s_name)) or ""
            )
            self.send_message(
                chat_id,
                f"🎉 <b>[{idx}/{total}] MUVAFFAQIYATLI OLINDI!</b>\n"
                f"🖥 <b>{pc1_tag}</b>\n"
                f"👤 <b>{s_name}</b>\n"
                f"⏱ Sarflangan vaqt: <b>{dur_str}</b>\n"
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

    def worker_loop(self, worker_id: int):
        while True:
            if getattr(self, "is_paused", False):
                time.sleep(1.5)
                continue
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

            for pass_num in range(1, 4):
                done_set = get_completed_students()
                unrec_set = get_unrecoverable_students()
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
                        if getattr(self, "is_paused", False) or ctx.get("cancelled") or getattr(self, "clear_cancel_epoch", 0) > ctx.get("start_time", 0):
                            break
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

                    student_q.join()
                finally:
                    with self.shared_lock:
                        if ctx in self.shared_orders:
                            self.shared_orders.remove(ctx)

            self.active_worker_status[worker_id] = ""
            if ctx.get("cancelled") or order.get("cancelled") or getattr(self, "clear_cancel_epoch", 0) > order.get("start_time", 0):
                continue
            orig_fname = order.get("orig_fname", "Buyurtma")
            clean_base = re.sub(r'[\\/*?:"<>|]', "", os.path.splitext(orig_fname)[0]).strip() or "Buyurtma"
            order_start_t = order.get("start_time", time.time())
            total_sec = max(1, int(time.time() - order_start_t))
            tot_h = total_sec // 3600
            tot_m = (total_sec % 3600) // 60
            tot_s = total_sec % 60
            if tot_h > 0:
                tot_dur_str = f"{tot_h} soat {tot_m} daqiqa"
                file_dur_tag = f"{tot_h}soat_{tot_m}daq"
            elif tot_m > 0:
                tot_dur_str = f"{tot_m} daqiqa {tot_s} soniya"
                file_dur_tag = f"{tot_m}daq_{tot_s}son"
            else:
                tot_dur_str = f"{tot_s} soniya"
                file_dur_tag = f"{tot_s}son"

            cur_time_str = time.strftime("%d.%m.%Y_%H-%M")
            out_filename = f"{clean_base}_Sertifikatlar_{cur_time_str}_({file_dur_tag}).xlsx"
            excel_path = os.path.join(ORDERS_DIR, out_filename)
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
                f"📁 Asl fayl nomi: <b>{orig_fname if orig_fname.endswith('.xlsx') else (orig_fname + '.xlsx')}</b>\n"
                f"👥 Jami o'quvchilar: <b>{total} ta</b>\n"
                f"✅ Sertifikat olindi: <b>{done_cnt} ta</b>\n"
                f"⚠️ Oldin ro'yxatdan o'tgan (bazada paroli yo'q): <b>{unrec_cnt} ta</b>\n"
                f"⏱ <b>Jami sarflangan vaqt: {tot_dur_str}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📎 Jadval ichida har bir o'quvchining <b>Email (Pochta), Parol, Sertifikat havolasi va Sertifikat ID raqami</b> to'liq yozilgan!"
                f"{debt_footer}"
            )
            self.send_document(chat_id, excel_path, caption=summary_caption)
            order_queue.task_done()

    def clear_and_archive_old_orders(self):
        """Eski buyurtmalarni va xatolarni tozalaydi/arxivlaydi.
        FAQAT akkountlar.txt (Login/Parollar) va natijalar_sertifikatlar.txt (Tayyor sertifikatlar) saqlanadi!"""
        import shutil
        now_ts = time.time()
        self.clear_cancel_epoch = now_ts
        self.is_paused = True

        with self.shared_lock:
            for ctx in self.shared_orders:
                ctx["cancelled"] = True
                q = ctx.get("student_q")
                if q:
                    while not q.empty():
                        try:
                            q.get_nowait()
                            q.task_done()
                        except Exception:
                            break
            self.shared_orders.clear()

        while not order_queue.empty():
            try:
                o = order_queue.get_nowait()
                if isinstance(o, dict):
                    o["cancelled"] = True
                order_queue.task_done()
            except Exception:
                break

        self.active_worker_status.clear()

        if os.path.exists(ORDERS_DIR):
            arch_dir = os.path.join(ORDERS_DIR, "archived")
            os.makedirs(arch_dir, exist_ok=True)
            for fn in os.listdir(ORDERS_DIR):
                if fn.startswith("in_") and fn.endswith(".xlsx"):
                    src = os.path.join(ORDERS_DIR, fn)
                    dst = os.path.join(arch_dir, f"arch_cancelled_{int(now_ts)}_{fn}")
                    try:
                        shutil.move(src, dst)
                    except Exception:
                        try:
                            os.remove(src)
                        except Exception:
                            pass

        if os.path.exists(ERRORS_FILE):
            try:
                err_bkp = f"xatolar_archived_{int(now_ts)}.txt"
                shutil.copy(ERRORS_FILE, err_bkp)
                with open(ERRORS_FILE, "w", encoding="utf-8") as ef:
                    ef.write("# Xatolar kesh tozalandi\n")
            except Exception:
                pass

        for f in ("cluster_tried_students.json", "cluster_nodes_state.json", "cluster_pause_state.txt"):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        try:
            requests.get("http://127.0.0.1:8766/cluster/clear_cache", timeout=3)
        except Exception:
            pass
        if os.path.exists("cluster_url.txt"):
            try:
                t_u = open("cluster_url.txt", "r", encoding="utf-8").read().strip().splitlines()[0].strip()
                if t_u.startswith("http"):
                    requests.get(f"{t_u}/cluster/clear_cache", timeout=5)
            except Exception:
                pass
        self.is_paused = False

    def pause_all_tasks(self, chat_id: int):
        self.is_paused = True
        try:
            with open("cluster_pause_state.txt", "w", encoding="utf-8") as f:
                f.write("PAUSED")
        except Exception:
            pass
        with self.shared_lock:
            self.shared_orders.clear()
        while not order_queue.empty():
            try:
                order_queue.get_nowait()
                order_queue.task_done()
            except Exception:
                break
        self.send_message(
            chat_id,
            "⏸ <b>JARAYON TO'XTATILDI (PAUZA)!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛑 Yangi o'quvchilar navbati vaqtinchalik to'xtatildi.\n\n"
            "👉 <b>Quyidagilardan birini tanlang:</b>\n"
            "1️⃣ <b>▶️ Qolgan joyidan davom ettirish</b> — to'xtatilgan ro'yxat qolgan joyidan davom etadi.\n"
            "2️⃣ <b>📁 Yangi Excel yoki matn tashlang</b> — eski ro'yxat to'liq bekor qilinadi va <b>FAQAT YANGI BUYURTMA</b> bajariladi!\n"
            "3️⃣ <b>🗑 Yangi buyurtma (Eskisini o'chirish)</b> — eski navbatlarni butunlay tozalaydi.",
            reply_markup=self.get_reply_keyboard(chat_id),
        )

    def get_reply_keyboard(self, chat_id: int):
        if self.admin_id and chat_id == self.admin_id:
            return {
                "keyboard": [
                    [{"text": "⏸ To'xtatish (Pauza)"}, {"text": "▶️ Qolgan joyidan davom ettirish"}],
                    [{"text": "🤖 Robot Agentlar Dashboard"}, {"text": "🌐 Web Any (Brauzerda)"}],
                    [{"text": "🧹 Keshni tozalash (Yangi buyurtma)"}, {"text": "🖥 Klaster (Kompyuterlar holati)"}],
                    [{"text": "⚡ Ishlarni bo'lish (Klasterga)"}, {"text": "📊 Tahlil va Jarayon"}],
                    [{"text": "⚡ Jonli Log (Console)"}, {"text": "📥 Tayyor Sertifikatlar (Excel)"}],
                    [{"text": "💰 Foyda va Kassa"}, {"text": "📸 Kompyuterdan Skrinshot"}],
                    [{"text": "🖥 AnyDesk Jonli Ulanish"}, {"text": "📄 Bo'sh Shablon (.xlsx)"}],
                    [{"text": "🛠 AI Dasturchiga yozish (Skrinshot / Taklif)"}],
                ],
                "resize_keyboard": True,
                "is_persistent": False,
            }
        return {
            "keyboard": [
                [{"text": "📥 Excel Shablon olish"}, {"text": "📸 To'lov chekini yuborish"}],
                [{"text": "💰 Narxlar va 50% Avans"}, {"text": "👨‍💼 Admin bilan aloqa"}],
            ],
            "resize_keyboard": True,
            "is_persistent": False,
        }

    def resume_latest_unfinished_order(self, notify_chat_id: int = 0, manual: bool = False):
        try:
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
            if not files and os.path.exists(os.path.join(ORDERS_DIR, "archived")):
                arch_d = os.path.join(ORDERS_DIR, "archived")
                files = sorted(
                    [os.path.join(arch_d, f) for f in os.listdir(arch_d) if f.startswith("in_") and f.endswith(".xlsx")],
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
                    if "archived" in fpath:
                        import shutil
                        try:
                            shutil.copy2(fpath, os.path.join(ORDERS_DIR, bn))
                        except Exception:
                            pass
                    parts = bn.split("_", 3)
                    ord_cid = int(parts[1]) if len(parts) >= 3 and parts[1].isdigit() else (self.admin_id or notify_chat_id)
                    res_orig_fname = parts[3].rsplit(".", 1)[0] if len(parts) >= 4 else "Buyurtma"
                    if not self.shared_orders and order_queue.empty():
                        self.enqueue_order(ord_cid, "Admin", sts, silent=True, orig_fname=res_orig_fname)
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

    def build_ai_dev_smart_answer(self, text: str) -> str:
        done_tot = len(get_completed_students())
        ord_prog = self._get_latest_order_progress()
        ord_txt = ""
        if ord_prog:
            ord_txt = (
                f"📋 <b>Yangi zakaz ({ord_prog['total']} ta o'quvchi) bo'yicha aniq hisobot:</b>\n"
                f"• ✅ Sertifikat olinganlar: <b>{ord_prog['done']} ta</b>\n"
                f"• ⚠️ JSHSHIR xatoli (oldin o'tgan): <b>{ord_prog['unrec']} ta</b>\n"
                f"• ⏳ Qolgan o'quvchilar: <b>{ord_prog['rem']} ta</b> (ulardan <b>{ord_prog['acc_ready']} tasiga</b> pochta va Coursera ulangan!)\n\n"
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
            st_nodes = {}

        now_ts = time.time()
        # 150 soniyadan ko'proq vaqt oldin uzilgan eski mashinalarni ro'yxatdan tozalaymiz
        st_nodes = {k: v for k, v in st_nodes.items() if (now_ts - float(v.get("last_seen", 0))) < 150}

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
        node_keys = list(st_nodes.keys())
        cluster_buttons = []

        for p1, p2 in [(2, 3), (4, 5), (6, 7), (8, 9), (10, 11)]:
            row = []
            for pc_num in (p1, p2):
                idx_n = pc_num - 2
                if idx_n < len(node_keys):
                    nid = node_keys[idx_n]
                    ninfo = st_nodes[nid]
                    w_cnt = int(ninfo.get("workers", 4))
                    ago_s = max(0, int(now_ts - float(ninfo.get("last_seen", 0))))
                    is_active = ninfo.get("approved", True) and w_cnt > 0 and ago_s < 120
                    if is_active:
                        row.append({"text": f"🟢 {pc_num}-Komp ({w_cnt}A) 🔴", "callback_data": f"cl_toggle|{nid}|off"})
                    else:
                        row.append({"text": f"🔴 {pc_num}-Komp (0A) 🟢", "callback_data": f"cl_toggle|{nid}|on"})
                else:
                    row.append({"text": f"🚀 {pc_num}-Komp (Yoqish)", "callback_data": f"cl_spawn_idx|{pc_num}"})
            cluster_buttons.append(row)

        cluster_buttons.append([
            {"text": "⚡ BARCHA KOMPYUTERLARGA ISH BO'LISH 🚀", "callback_data": "distribute_work_all"},
        ])
        cluster_buttons.append([
            {"text": "⚡ BARCHASINI YOQISH (10 ta Kompyuter / 60 ta Agent)", "callback_data": "start_cluster_manual"},
        ])
        cluster_buttons.append([
            {"text": "🛑 Barchasini to'xtatish", "callback_data": "stop_cluster_all"},
            {"text": "🔄 Yangilash", "callback_data": "refresh_cluster_status"},
        ])

        cluster_ctrl_markup = {"inline_keyboard": cluster_buttons}
        self.send_message(chat_id, summary_msg, reply_markup=cluster_ctrl_markup)

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
                        {"text": "🟢 Yoqish (6 Agent)", "callback_data": f"cl_toggle|{node_id}|on"},
                        {"text": "🔴 O'chirish", "callback_data": f"cl_toggle|{node_id}|off"},
                    ],
                    [
                        {"text": "🤖 2 Agent", "callback_data": f"cl_set|{node_id}|2"},
                        {"text": "🤖 4 Agent", "callback_data": f"cl_set|{node_id}|4"},
                        {"text": "🤖 6 Agent", "callback_data": f"cl_set|{node_id}|6"},
                    ],
                    [
                        {"text": "📸 Ekran Skrinshoti (Yashirin)", "callback_data": f"cl_scr|{node_id}"},
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
        create_template_excel()

        for w_i in range(1, MAX_PARALLEL_WORKERS + 1):
            t = threading.Thread(target=self.worker_loop, args=(w_i,), daemon=True)
            t.start()

        analytics_thread = threading.Thread(target=self.hourly_analytics_loop, daemon=True)
        analytics_thread.start()

        def _cluster_bridge_watchdog():
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

        if self.admin_id:
            try:
                if os.path.exists("startup_orders.json"):
                    with open("startup_orders.json", "r", encoding="utf-8") as sf:
                        st_data = json.load(sf)
                    os.remove("startup_orders.json")
                    if isinstance(st_data, dict) and st_data.get("students"):
                        self.enqueue_order(st_data.get("chat_id", self.admin_id), st_data.get("user_name", "Mijoz"), st_data["students"], silent=st_data.get("silent", True))
                    elif isinstance(st_data, list) and st_data:
                        self.enqueue_order(self.admin_id, "Admin", st_data, silent=True)
                else:
                    self.resume_latest_unfinished_order(notify_chat_id=self.admin_id, manual=False)
            except Exception as e:
                print(f"[STARTUP WARN] {e}")

        print("=" * 70)
        print(f"🤖 UZBEK CODERS TELEGRAM BOT ISHGA TUSHDI! (Parallel oqimlar: {MAX_PARALLEL_WORKERS} ta)")
        print(f"👨‍💼 Admin aloqa: {ADMIN_USERNAME} | Soatlik tahlil: YOQILGAN")
        print("Telegramdan botga /start yoki /tahlil deb yozishingiz mumkin!")
        print("=" * 70)

        try:
            requests.post(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": False}, timeout=10)
        except Exception:
            pass

        while True:
            try:
                resp = requests.get(
                    f"{self.api_url}/getUpdates",
                    params={"offset": self.offset, "timeout": 20},
                    timeout=(6, 26),
                ).json()
                if not resp.get("ok"):
                    err_desc = resp.get("description", "Unknown error")
                    err_code = resp.get("error_code")
                    if err_code == 401:
                        print("[POLL XATO 401] Bot token yaroqsiz! Telegram BotFather dagi yangi tokenni GitHub Secrets ga qo'yish kerak.")
                    else:
                        print(f"[POLL XATO] getUpdates ok=False ({err_code}): {err_desc}")
                    time.sleep(2.0)
                    continue
                for upd in resp.get("result", []):
                    self.offset = upd["update_id"] + 1
                    u_txt = (upd.get("message") or {}).get("text") or (upd.get("callback_query") or {}).get("data")
                    print(f"[TG UPDATE] ID={upd['update_id']} | Text/Data: {str(u_txt)[:60]}")
                    threading.Thread(target=self.process_update, args=(upd,), daemon=True).start()
            except Exception as e:
                print(f"[POLL EXCEPTION] {e}")
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

        # Admin to'lov chekini tasdiqladi — endi faylni rasmiy in_ ga o'tkazamiz va ish boshlanadi:
        if os.path.exists(ORDERS_DIR):
            for fn in os.listdir(ORDERS_DIR):
                if fn.startswith(f"pending_{target_uid}_") and fn.endswith(".xlsx"):
                    clean_b = re.sub(r'[\\/*?:"<>|]', "", os.path.splitext(order_info.get("orig_fname", "Buyurtma"))[0]).strip() or "Buyurtma"
                    in_p = os.path.join(ORDERS_DIR, f"in_{target_uid}_{int(time.time())}_{clean_b}.xlsx")
                    try:
                        os.rename(os.path.join(ORDERS_DIR, fn), in_p)
                        break
                    except Exception:
                        pass
        self.send_message(target_uid, client_msg)
        self.enqueue_order(
            target_uid,
            user_name,
            order_info["students"],
            paid_info={"total": total_price, "paid": paid_now, "debt": debt_added},
            orig_fname=order_info.get("orig_fname", "Buyurtma"),
        )

    def process_update(self, upd):
        if "callback_query" in upd:
            cb = upd["callback_query"]
            data = cb.get("data", "")
            from_id = cb["from"]["id"]

            if data.startswith("cl_scr|"):
                try:
                    _, n_id = data.split("|", 1)
                    import urllib.parse
                    q_n = urllib.parse.quote(n_id)
                    requests.get(f"http://127.0.0.1:8766/cluster/request_screenshot?node={q_n}&chat_id={from_id}", timeout=5)
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": f"📸 {n_id} kompyuteriga yashirin skrinshot buyrug'i yuborildi! (2-4 soniyada keladi)", "show_alert": True},
                        timeout=5,
                    )
                except Exception as e:
                    print(f"[CL_SCR XATO] {e}")
                return

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

            if data.startswith("cl_toggle|"):
                try:
                    _, n_id, action = data.split("|", 2)
                    import urllib.parse
                    q_n = urllib.parse.quote(n_id)
                    if action == "off":
                        requests.get(f"http://127.0.0.1:8766/cluster/approve?node={q_n}&w=0&act=no", timeout=5)
                        alert_t = f"🔴 {n_id} to'xtatildi! Chala qolgan vazifalari boshqa kompyuterlarga o'tkazildi."
                    else:
                        requests.get(f"http://127.0.0.1:8766/cluster/approve?node={q_n}&w=6&act=yes", timeout=5)
                        alert_t = f"🟢 {n_id} yoqildi! 6 ta AI Agent vazifalarni bo'lib olishga kirishdi."
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": alert_t, "show_alert": True},
                        timeout=5,
                    )
                    self.send_cluster_agent_selector(from_id)
                except Exception as e:
                    print(f"[CL_TOGGLE ERROR] {e}")
                return

            if data.startswith("cl_spawn_one|") or data.startswith("cl_spawn_idx|"):
                try:
                    parts = data.split("|")
                    pc_num = parts[1] if len(parts) > 1 else "2"
                    target_nodes = max(1, min(6, int(pc_num) - 1))
                    trigger_cluster_dispatch(nodes_count=target_nodes)
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": f"🚀 {pc_num}-Virtual kompyuter ishga tushirilmoqda (30-60 soniyada ulanadi)...", "show_alert": True},
                        timeout=5,
                    )
                    self.send_message(
                        from_id,
                        f"🚀 <b>{pc_num}-VIRTUAL KOMPYUTER ISHGA TUSHIRILMOQDA!</b>\n\n"
                        f"⚡ GitHub Actions orqali 16 GB li Virtual kompyuter faollashtirildi.\n"
                        f"⏳ Taxminan 30-60 soniyada ulanib, 4 ta AI Agent ishga tushadi!",
                        reply_markup=self.get_reply_keyboard(from_id),
                    )
                    self.send_cluster_agent_selector(from_id)
                except Exception as e:
                    print(f"[CL_SPAWN ERROR] {e}")
                return

            if data == "stop_cluster_all":
                try:
                    requests.get("http://127.0.0.1:8766/cluster/stop_all", timeout=5)
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": "🛑 Barcha klaster kompyuterlari to'xtatildi! Vazifalar xavfsiz saqlandi.", "show_alert": True},
                        timeout=5,
                    )
                    self.send_cluster_agent_selector(from_id)
                except Exception as e:
                    print(f"[STOP_CLUSTER_ALL ERROR] {e}")
                return

            if data == "start_cluster_manual":
                try:
                    requests.get("http://127.0.0.1:8766/cluster/start_all", timeout=5)
                    trigger_cluster_dispatch(nodes_count=10)
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": "⚡ 10 ta Virtual Kompyuter (60 ta AI Agent) ishga tushirish buyrug'i yuborildi!", "show_alert": True},
                        timeout=5,
                    )
                    self.send_message(
                        from_id,
                        "🚀 <b>BARCHA 10 TA KLASTER KOMPYUTERI YOQILMOQDA!</b>\n\n"
                        "⚡ GitHub Actions orqali 10 ta Virtual kompyuter (60 ta AI Agent) faollashtirildi.\n"
                        "⏳ Taxminan 30-60 soniyada kompyuterlar ulanib, navbatdagi barcha o'quvchilarni bo'lib oladi!",
                        reply_markup=self.get_reply_keyboard(from_id),
                    )
                except Exception as e:
                    print(f"[START_CLUSTER_MANUAL ERROR] {e}")
                return

            if data == "distribute_work_all":
                try:
                    r_reb = requests.get("http://127.0.0.1:8766/cluster/rebalance", timeout=5).json()
                    active_c = r_reb.get("active_nodes", 0)
                    rem_c = r_reb.get("remaining_tasks", 0)
                    if active_c < 2 and rem_c > 0:
                        trigger_cluster_dispatch(students_count=rem_c, nodes_count=4)
                    alert_text = f"⚡ Ishlar {max(1, active_c) + 1} ta kompyuterga bo'lindi! Qolgan vazifalar: {rem_c} ta"
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": alert_text, "show_alert": True},
                        timeout=5,
                    )
                    self.send_message(
                        from_id,
                        f"⚡ <b>BARCHA KOMPYUTERLARGA ISH BO'LINDI!</b>\n\n"
                        f"• <b>1-Kompyuter (Asosiy Server):</b> 1-o'quvchidan boshlab olmoqda (Boshidan)\n"
                        f"• <b>Klaster Kompyuterlari ({max(1, active_c)} ta faol):</b> Oxiridan ({rem_c} ta qolgan vazifalarni) bo'lib olmoqda\n\n"
                        f"🚀 Barcha faol AI Agentlar parallel ravishda ishga kirishdi!\n"
                        f"Har bir kompyuter o'z natijasini to'g'ridan-to'g'ri botga xabar qiladi.",
                        reply_markup=self.get_reply_keyboard(from_id),
                    )
                except Exception as e:
                    print(f"[DISTRIBUTE_WORK ERROR] {e}")
                return

            if data == "refresh_cluster_status":
                try:
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": "🔄 Klaster holati yangilanmoqda..."},
                        timeout=5,
                    )
                except Exception:
                    pass
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
                        f"To'lovni (100% to'liq yoki 50% avans) amalga oshirib, <b>chek rasmini (skrinshot) shu yerga chatga tashlang!</b>",
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
                    f"👇 <b>To'lovni o'tkazib, chek rasmini (skrinshotini) shu yerga botga yuboring!</b>",
                )
                return

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
                if os.path.exists(ORDERS_DIR):
                    for fn in os.listdir(ORDERS_DIR):
                        if (fn.startswith(f"in_{target_uid}_") or fn.startswith(f"pending_{target_uid}_")) and fn.endswith(".xlsx"):
                            try:
                                os.rename(os.path.join(ORDERS_DIR, fn), os.path.join(ORDERS_DIR, f"rejected_{target_uid}_{fn}"))
                            except Exception:
                                pass
                self.send_message(from_id, f"❌ Foydalanuvchi ({target_uid}) buyurtmasi rad etildi.")
                self.send_message(target_uid, f"❌ <b>To'lov tasdiqlanmadi.</b> Iltimos, qayta tekshirib yuboring yoki Admin bilan bog'laning: {ADMIN_USERNAME}")
                return

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

            if data == "cert_menu_dates":
                msg_id = cb.get("message", {}).get("message_id")
                self.send_certificate_dates_menu(from_id, message_id=msg_id)
                return

            if data.startswith("cert_date|"):
                _, t_date = data.split("|", 1)
                msg_id = cb.get("message", {}).get("message_id")
                self.send_certificate_orders_menu(from_id, target_date=t_date, message_id=msg_id)
                return

            if data.startswith("cert_f|"):
                _, short_key = data.split("|", 1)
                fpath = _cert_files_short_map.get(short_key)
                if fpath and os.path.exists(fpath):
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": "⏳ Excel fayl tayyorlanmoqda va yuborilmoqda..."},
                        timeout=5,
                    )
                    self.export_and_send_order(from_id, fpath)
                else:
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        data={"callback_query_id": cb["id"], "text": "⚠️ Fayl topilmadi yoki muddati o'tgan.", "show_alert": True},
                        timeout=5,
                    )
                return

            if data.startswith("cert_allday|"):
                _, t_date = data.split("|", 1)
                requests.post(
                    f"{self.api_url}/answerCallbackQuery",
                    data={"callback_query_id": cb["id"], "text": f"⏳ {t_date} sanasidagi barcha buyurtmalar yig'ilmoqda..."},
                    timeout=5,
                )
                self.export_and_send_day_orders(from_id, target_date=t_date)
                return

            if data == "cert_export_all":
                requests.post(
                    f"{self.api_url}/answerCallbackQuery",
                    data={"callback_query_id": cb["id"], "text": "⏳ Barcha sertifikatlar yig'ilmoqda..."},
                    timeout=5,
                )
                self.export_and_send_all_certificates(from_id)
                return

            return

        msg = upd.get("message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        user_name = msg["from"].get("first_name", "Foydalanuvchi")
        username = msg["from"].get("username", "")
        text = (msg.get("text") or "").strip()

        # VIDEO YUBORILGANDA:
        if msg.get("video") or (msg.get("document") and str(msg["document"].get("mime_type", "")).startswith("video/")):
            vid_obj = msg.get("video") or msg.get("document")
            file_id = vid_obj["file_id"]
            caption = (msg.get("caption") or "").strip()

            if caption:
                students = parse_students_from_text(caption)
                if students:
                    self.handle_students_submission(chat_id, user_name, username, students)
                    return

            # Agar Admin tashlasa: /start videosi sifatida eslab qoladi
            if self.admin_id and chat_id == self.admin_id:
                self.start_video_id = file_id
                self.cfg["start_video_id"] = file_id
                save_config(self.cfg)
                self.send_message(
                    chat_id,
                    "🎥 <b>Kirish videosi muvaffaqiyatli saqlandi!</b>\n\n"
                    "✅ Endi har qanday foydalanuvchi botga <b>/start</b> bosganida, "
                    "matndan keyin ushbu video avtomatik yuboriladi.",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
                return
            else:
                self.send_message(
                    chat_id,
                    "⚠️ Video qabul qilindi, lekin o'quvchilar ro'yxati topilmadi. Ro'yxatni matn yoki Excel ko'rinishida yuboring.",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
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
                "⚡ <i>Kompyuterga va AI Agentlarga umuman nagruzka (yuklama) tushirmaydi!</i>",
                reply_markup=self.get_reply_keyboard(chat_id),
            )
            return

        if chat_id in admin_input_state and text and not text.startswith("/"):
            st_cur = admin_input_state.get(chat_id, {})
            if st_cur.get("action") == "ai_dev_note" and text not in (
                "🖥 Klaster (Kompyuterlar holati)",
                "📊 Tahlil va Jarayon",
                "💰 Foyda va Kassa",
                "⚡ Jonli Log (Console)",
                "🌗 50% Avanslar",
                "📥 Tayyor Sertifikatlar (Excel)",
                "📄 Bo'sh Shablon (.xlsx)",
                "▶️ Qolgan joyidan davom ettirish",
                "🖥 Qo'shimcha Oqim (Agent tanlash)",
                "🛠 AI Dasturchiga yozish (Skrinshot / Taklif)",
            ):
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

        if text in ("📸 Kompyuterdan Skrinshot", "/screen", "/skrin"):
            import socket
            pc1_name = socket.gethostname()
            rows = [[{"text": f"📸 1-Kompyuter [{pc1_name}] (Asosiy)", "callback_data": "cl_scr|MASTER_PC"}]]
            if os.path.exists("cluster_nodes_state.json"):
                try:
                    st_nodes = json.load(open("cluster_nodes_state.json", "r", encoding="utf-8"))
                    for idx_pc, (nid, ninfo) in enumerate(st_nodes.items(), start=2):
                        pc_n = ninfo.get("pc_name", nid)
                        ago_s = max(0, int(time.time() - float(ninfo.get("last_seen", 0))))
                        badge = "🟢" if ago_s < 180 else "🔴"
                        rows.append([{"text": f"📸 {idx_pc}-Kompyuter [{pc_n}] ({badge})", "callback_data": f"cl_scr|{nid}"}])
                except Exception:
                    pass
            self.send_message(
                chat_id,
                "📸 <b>QAYSI KOMPYUTER EKRANIDAN SKRINSHOT OLAYLIK?</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "<i>Tanlagan kompyuteringizda hech qanday oyna ochilmaydi — rasm 100% orqa fonda olinib, 2–4 soniyada shu yerga keladi:</i>",
                reply_markup={"inline_keyboard": rows}
            )
            return

        if text in ("🖥 AnyDesk Jonli Ulanish", "/anydesk", "/any", "/desk", "/rdp"):
            admin_input_state.pop(chat_id, None)
            aid = ""
            pwd = "UzbekCoders2026!"
            if os.path.exists("anydesk_info.json"):
                try:
                    d = json.load(open("anydesk_info.json", "r", encoding="utf-8"))
                    aid = d.get("anydesk_id", "")
                    pwd = d.get("password", pwd)
                except Exception:
                    pass
            if not aid and os.path.exists("anydesk_id.txt"):
                try:
                    lns = open("anydesk_id.txt", "r", encoding="utf-8").read().splitlines()
                    if lns:
                        aid = lns[0].strip()
                    if len(lns) > 1:
                        pwd = lns[1].strip()
                except Exception:
                    pass

            if aid:
                self.send_message(
                    chat_id,
                    f"🖥 <b>VIRTUAL KOMPYUTERGA JONLI ULASH (ANYDESK):</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 <b>AnyDesk ID:</b> <code>{aid}</code>\n"
                    f"🔑 <b>Parol:</b> <code>{pwd}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👀 <b>Ko'rsatma:</b>\n"
                    f"1. Kompyuteringizda <b>AnyDesk</b> dasturini oching.\n"
                    f"2. Qidiruv qatoriga <code>{aid}</code> deb yozing va Enter bosing.\n"
                    f"3. So'ralganda parolni kiriting: <code>{pwd}</code>\n\n"
                    f"⚡ <b>Virtual kompyuter ekrani va ochilayotgan brauzer to'g'ridan-to'g'ri ko'zingiz oldida jonli ko'rinadi!</b>\n"
                    f"<i>(Brauzer ochiq holda ishlaydi, har bir qadamni ko'rishingiz mumkin)</i>",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
            else:
                self.send_message(
                    chat_id,
                    "⏳ <b>AnyDesk ID serverda sozlanmoqda...</b>\n"
                    "Server yuklanishi bilan AnyDesk ID avtomatik shu yerga yuboriladi!\n"
                    "Iltimos, 15-20 soniyadan so'ng qayta bosing.",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
            return

        if text in ("🤖 Robot Agentlar Dashboard", "🤖 Dashboard", "/dashboard", "/robots", "/agentlar"):
            admin_input_state.pop(chat_id, None)
            tunnel_url = ""
            try:
                r = requests.get("http://127.0.0.1:8766/cluster/tg_status", timeout=3)
                if r.status_code == 200:
                    tunnel_url = r.json().get("tunnel_url", "")
            except Exception:
                pass
            if not tunnel_url and os.path.exists("cluster_url.txt"):
                try:
                    tunnel_url = open("cluster_url.txt", "r", encoding="utf-8").read().strip()
                except Exception:
                    pass

            if tunnel_url:
                dash_url = f"{tunnel_url}/dashboard"
                web_url = f"{tunnel_url}/web_any"
                inline_markup = {
                    "inline_keyboard": [
                        [{"text": "🤖 Robot Dashboardni Ochish (Mini App)", "web_app": {"url": dash_url}}],
                        [{"text": "🔗 Maxfiy Havolada Ochish", "url": dash_url}],
                        [{"text": "🌐 Web Any (Jonli Ekran)", "web_app": {"url": web_url}}]
                    ]
                }
                self.send_message(
                    chat_id,
                    f"🤖 <b>ROBOT AGENTLAR JONLI DASHBOARD:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👑 <b>Bosh Ish Beruvchi Robot:</b> Barcha kompyuterlar va navbatdagi ishlarni nazorat qiladi\n"
                    f"💼 <b>Agentlar Holati:</b> Har bir robotning qaysi o'quvchini ishlayotgani (klaviaturada yozish animatsiyasi), bo'sh yoki o'chiqligi\n"
                    f"⏱ <b>Tezlik va Sertifikatlar:</b> Har bir agent nechta sertifikat olgani va oxirgi sertifikatni necha minutda bajargani real vaqtda ko'rsatiladi!\n\n"
                    f"👇 Quyidagi tugmani bosing:",
                    reply_markup=inline_markup
                )
            else:
                self.send_message(
                    chat_id,
                    "⏳ <b>Dashboard tunnel tayyorlanmoqda...</b>\n"
                    "Cloudflare tunnel ulanishi bilan ochiladi. Iltimos, 10-15 soniyadan so'ng qayta bosing.",
                    reply_markup=self.get_reply_keyboard(chat_id)
                )
            return

        if text in ("🌐 Web Any (Brauzerda)", "🌐 Web Any", "/webany", "/web_any", "/anyweb", "web any", "webany"):
            admin_input_state.pop(chat_id, None)
            tunnel_url = ""
            try:
                r = requests.get("http://127.0.0.1:8766/cluster/dashboard_data", timeout=3)
                if r.status_code == 200:
                    tunnel_url = r.json().get("tunnel_url", "")
            except Exception:
                pass
            if not tunnel_url:
                try:
                    r2 = requests.get("http://127.0.0.1:8766/cluster/tg_status", timeout=3)
                    if r2.status_code == 200:
                        tunnel_url = r2.json().get("tunnel_url", "")
                except Exception:
                    pass
            if not tunnel_url and os.path.exists("cluster_url.txt"):
                try:
                    tunnel_url = open("cluster_url.txt", "r", encoding="utf-8").read().strip()
                except Exception:
                    pass

            if tunnel_url:
                web_url = f"{tunnel_url}/web_any"
                dash_url = f"{tunnel_url}/dashboard"
                inline_markup = {
                    "inline_keyboard": [
                        [{"text": "🌐 Web AnyDesk (Mini App)", "web_app": {"url": web_url}}],
                        [{"text": "🔗 Brauzerda ochish", "url": web_url}],
                        [{"text": "🤖 Robot Agentlar Dashboard", "web_app": {"url": dash_url}}]
                    ]
                }
                self.send_message(
                    chat_id,
                    f"🌐 <b>WEB ANYDESK — JONLI EKRAN VA BOSHQARUV:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"AnyDesk ilovasi o'rnatilishi shart emas! To'g'ridan-to'g'ri Telegram Mini App yoki brauzeringizda ochiladi.\n\n"
                    f"🔗 <b>Jonli havola:</b>\n{web_url}\n\n"
                    f"📱 <b>Qulayliklari:</b>\n"
                    f"• Ekranni har 1 soniyada jonli ko'rsatib turadi\n"
                    f"• Barmog'ingiz bilan rasmning istalgan joyiga bossangiz — virtual kompyuterda ko'rinadigan sichqoncha bilan kordinata bosiladi!\n"
                    f"• Qulay yozish paneli, parol, Tab, Ctrl+A, Ctrl+V tugmalari mavjud.",
                    reply_markup=inline_markup
                )
            else:
                self.send_message(
                    chat_id,
                    "⏳ <b>Web AnyDesk tunnel tayyorlanmoqda...</b>\n"
                    "Cloudflare tunnel 10-15 soniyada tayyor bo'ladi. Iltimos, birozdan so'ng qayta bosing.",
                    reply_markup=self.get_reply_keyboard(chat_id)
                )
            return

        if text in ("⏸ To'xtatish (Pauza)", "⏸ To'xtatish", "/stop", "/pause", "/toxtat"):
            admin_input_state.pop(chat_id, None)
            self.pause_all_tasks(chat_id)
            return

        if text in ("▶️ Qolgan joyidan davom ettirish", "/davom", "/resume"):
            admin_input_state.pop(chat_id, None)
            if os.path.exists("cluster_pause_state.txt"):
                try:
                    os.remove("cluster_pause_state.txt")
                except Exception:
                    pass
            self.is_paused = False
            self.resume_latest_unfinished_order(notify_chat_id=chat_id, manual=True)
            return

        if text in ("🧹 Keshni tozalash (Yangi buyurtma)", "🧹 Keshni tozalash", "🗑 Yangi buyurtma (Eskisini o'chirish)", "🗑 Yangi buyurtma", "/clear", "/tozalash", "/kesh"):
            admin_input_state.pop(chat_id, None)
            self.clear_and_archive_old_orders()
            self.send_message(
                chat_id,
                "🗑 <b>ESKI BUYURTMALAR TO'LIQ TOZALANDI!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Endi botga yangi <b>Excel (.xlsx)</b> fayl yoki o'quvchilar ro'yxatini yuboring.\n"
                "Tizim faqat yangi ro'yxat bilan ishlaydi!",
                reply_markup=self.get_reply_keyboard(chat_id),
            )
            return

        if text in ("⚡ Ishlarni bo'lish (Klasterga)", "⚡ Ishlarni bo'lish", "/rebalance", "/bolish"):
            admin_input_state.pop(chat_id, None)
            try:
                r_reb = requests.get("http://127.0.0.1:8766/cluster/rebalance", timeout=5).json()
                active_c = r_reb.get("active_nodes", 0)
                rem_c = r_reb.get("remaining_tasks", 0)
                if active_c < 2 and rem_c > 0:
                    trigger_cluster_dispatch(students_count=rem_c, nodes_count=4)
                self.send_message(
                    chat_id,
                    f"⚡ <b>ISHLAR BARCHA KOMPYUTERLARGA BO'LINDI!</b>\n\n"
                    f"• <b>1-Kompyuter (Asosiy Server):</b> 1-o'quvchidan boshlab olmoqda (Boshidan)\n"
                    f"• <b>Klaster Kompyuterlari ({max(1, active_c)} ta faol):</b> Oxiridan ({rem_c} ta qolgan vazifalarni) bo'lib olmoqda\n\n"
                    f"🚀 Barcha faol AI Agentlar parallel ravishda ishga kirishdi!\n"
                    f"Har bir kompyuter o'z natijasini to'g'ridan-to'g'ri botga xabar qiladi.",
                    reply_markup=self.get_reply_keyboard(chat_id),
                )
            except Exception as e:
                self.send_message(chat_id, f"⚠️ Qayta taqsimlashda xatolik: {e}")
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
            admin_input_state.pop(chat_id, None)
            self.send_certificate_dates_menu(chat_id)
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
                    f"👇 <b>To'lovni o'tkazib, chek rasmini (skrinshotini) shu yerga botga yuboring!</b>",
                )
            else:
                self.send_message(
                    chat_id,
                    f"📸 <b>TO'LOV CHEKINI YUBORISH:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏦 Karta: <code>{self.card_info}</code>\n\n"
                    f"👇 <b>To'lovni amalga oshirib, chek rasmini shu yerga chatga yuboring!</b>",
                )
            return

        if text == "💰 Narxlar va 50% Avans":
            self.handle_smart_question(chat_id, user_name, "narxi qancha")
            return

        if text == "👨‍💼 Admin bilan aloqa":
            self.send_message(chat_id, f"👨‍💼 <b>Admin bilan bog'lanish:</b> {ADMIN_USERNAME}", reply_markup={"inline_keyboard": [[{"text": f"👨‍💼 Adminga yozish ({ADMIN_USERNAME})", "url": ADMIN_TG_URL}]]})
            return

        # /START BOSILGANDA (AVVAL MATN, KETIDAN AVTOMATIK VIDEO YUBORILADI):
        if text.startswith("/start"):
            self.card_info = load_config().get("card_info", self.card_info)
            users_db = load_users_db()
            total_members = get_total_users_count(chat_id)
            free_avail = "🎁 <b>Sizda 1 ta BEPUL sinov imkoniyati bor!</b>" if chat_id not in users_db.get("free_trial_used", []) else "✅ <i>Bepul sinovdan foydalangansiz</i>"
            welcome = (
                f"Assalomu alaykum, <b>{user_name}</b>! 👋\n\n"
                f"🤖 <b>UzbekCoders (Coursera) 100% Avtomat Sertifikat AI Agentiga xush kelibsiz!</b>\n"
                f"👥 <b>Botning haqiqiy a'zolari:</b> <b>{total_members} nafar</b>\n"
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
                f"⏳ <b>Eslatma:</b> Sayt (aileaders.uz / Coursera) ishlamay qolsa, qotib qolsa yoki so'rov ko'payganda sertifikat olish biroz sekinlashishi mumkin (sayt ishlashi bilan avtomatik davom etadi — sabr qilishingizni so'raymiz).\n\n"
                f"📥 <b>Buyurtma berish uchun:</b>\n"
                f"Pastdagi <b>«📥 Excel Shablon olish»</b> tugmasini bosib shablonni to'ldirib yuboring yoki oddiy xabar ko'rinishida tashlang:\n"
                f"<code>FAMILIYA ISM SHARIF | 12.10.2015 | I-FR | 923446 | 5-V</code>\n\n"
                f"📊 Yakunda har bir o'quvchining <b>Email, Parol, Sertifikat havolasi va ID raqami</b> yozilgan tayyor <b>Excel (.xlsx)</b> jadvalni olasiz!"
            )
            # 1. Matn yuboriladi
            self.send_message(chat_id, welcome, reply_markup=self.get_reply_keyboard(chat_id))

            # 2. Darhol ketidan video yuboriladi
            eff_video = self.get_effective_start_video()
            if eff_video:
                self.send_video(
                    chat_id,
                    eff_video,
                    caption="📹 <b>👋 Assalomu alaykum! Ushbu videoda AI agentining real vaqtdagi ish jarayoni ko'rsatilgan. Texnologiyalar yordamida har bir jarayonni yanada oson va avtomatlashtirilgan qilish mumkin! ⚡️</b>",
                )
            return

        # Rasm / Skrinshot kelganda:
        if "photo" in msg:
            photo_id = msg["photo"][-1]["file_id"]
            uname_str = f"@{username}" if username else "—"
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

            # Agar pending_orders da bo'lmasa, diskdagi in_ faylidan tiklaymiz:
            if chat_id not in pending_orders:
                try:
                    if os.path.exists(ORDERS_DIR):
                        for fn in sorted(os.listdir(ORDERS_DIR), reverse=True):
                            if fn.startswith(f"in_{chat_id}_") and fn.endswith(".xlsx"):
                                sts = parse_students_from_excel(os.path.join(ORDERS_DIR, fn))
                                if sts:
                                    _, p_tot = calculate_price(len(sts))
                                    pending_orders[chat_id] = {
                                        "students": sts,
                                        "price": p_tot,
                                        "user_name": user_name,
                                        "username": username or "",
                                        "orig_fname": fn,
                                    }
                                    break
                except Exception:
                    pass

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
                )
                if rem_d > 0:
                    caption += f"📒 Qolgan avans qoldig'i: <b>{rem_d:,} so'm</b>\n\nTo'lovni tasdiqlaysizmi?"
                    markup = {
                        "inline_keyboard": [
                            [{"text": f"✅ Qolgan to'lovni yopish ({rem_d:,} so'm)", "callback_data": f"debt_clear_{chat_id}"}],
                            [{"text": "❌ Chekni rad etish", "callback_data": f"reject_{chat_id}"}],
                        ]
                    }
                else:
                    caption += (
                        f"📒 Qolgan avans qoldig'i: <b>0 so'm</b>\n"
                        f"💡 <i>Mijoz to'lov chekini yubordi.</i>\n\n"
                        f"Chekni tasdiqlab qabul qilasizmi?"
                    )
                    markup = {
                        "inline_keyboard": [
                            [{"text": "✅ To'lovni tasdiqlash", "callback_data": f"debt_clear_{chat_id}"}],
                            [{"text": "❌ Chekni rad etish", "callback_data": f"reject_{chat_id}"}],
                        ]
                    }

                data_payload = {
                    "chat_id": self.admin_id,
                    "photo": photo_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(markup),
                }
                requests.post(f"{self.api_url}/sendPhoto", data=data_payload, timeout=15)
                self.send_message(chat_id, f"✅ <b>To'lov chekingiz Adminga ({ADMIN_USERNAME}) yuborildi!</b>")
            return

        # Excel yoki matn fayl kelganda:
        if "document" in msg:
            doc = msg["document"]
            orig_fname = (doc.get("file_name") or "").strip()
            clean_base = re.sub(r'[\\/*?:"<>|]', "", os.path.splitext(orig_fname)[0]).strip() or "Buyurtma"
            fname = orig_fname.lower()
            pref = f"in_{chat_id}_" if (self.admin_id and chat_id == self.admin_id) else f"pending_{chat_id}_"
            if fname.endswith(".xlsx") or fname.endswith(".xls"):
                target_ext = ".xls" if fname.endswith(".xls") else ".xlsx"
                local_p = self.download_file(doc["file_id"], os.path.join(ORDERS_DIR, f"{pref}{int(time.time())}_{clean_base}{target_ext}"))
                students = parse_students_from_excel(local_p)
                if fname.endswith(".xls") and students:
                    clean_xlsx_p = os.path.join(ORDERS_DIR, f"{pref}{int(time.time())}_{clean_base}.xlsx")
                    save_students_to_excel(students, clean_xlsx_p)
                    try:
                        os.remove(local_p)
                    except Exception:
                        pass
                self.handle_students_submission(chat_id, user_name, username, students, orig_fname=orig_fname)
                return
            elif fname.endswith(".txt") or fname.endswith(".csv"):
                local_p = self.download_file(doc["file_id"], os.path.join(ORDERS_DIR, f"{pref}{int(time.time())}_{clean_base}.txt"))
                with open(local_p, "r", encoding="utf-8", errors="replace") as f:
                    students = parse_students_from_text(f.read())
                self.handle_students_submission(chat_id, user_name, username, students, orig_fname=orig_fname)
                return

        if text:
            students = parse_students_from_text(text)
            if students:
                pref = "in_" if (len(students) == 1 and chat_id not in load_users_db().get("free_trial_used", [])) else "pending_"
                save_students_to_excel(students, os.path.join(ORDERS_DIR, f"{pref}{chat_id}_{int(time.time())}_Matn_Buyurtma.xlsx"))
                self.handle_students_submission(chat_id, user_name, username, students, orig_fname="Matn_Buyurtma")
            else:
                self.handle_smart_question(chat_id, user_name, text)


if __name__ == "__main__":
    _bot_lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _bot_lock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _bot_lock_sock.bind(("127.0.0.1", 49880))
    except Exception:
        pass

    try:
        config = load_config()
        bot_server = TelegramBotServer(config)
        bot_server.run_forever()
    except Exception as ex:
        import traceback
        traceback.print_exc()
        try:
            with open("tg_crash.log", "a", encoding="utf-8") as cf:
                cf.write(f"\n--- CRASH AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                traceback.print_exc(file=cf)
        except Exception:
            pass
        sys.exit(1)
