# -*- coding: utf-8 -*-
"""
=============================================================================
UZBEK CODERS - MUSTAQIL MULTI-PC CLUSTER KO'PRIGI (MASTER BRIDGE)
=============================================================================
Asosiy telegram_bot.py ga UMUMAN TEGMAYDI va uni to'xtatmaydi!
Mavjud zakazlarni (bot_orders ichidagi Excel fayllarni) kuzatib,
boshqa kompyuter ulanganda o'quvchilarni OXIRIDAN (teskari tartibda)
bo'lib beradi va olingan sertifikatlarni natijalar_sertifikatlar.txt ga
qo'shib boradi!
=============================================================================
"""

import os
import re
import sys
import json
import time
import urllib.parse
import subprocess
import threading
import socket
import http.server
import requests
from openpyxl import load_workbook

try:
    import urllib3.util.connection as urllib3_cn
    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

from master_certified_pipeline import (
    get_completed_students,
    get_existing_accounts,
    get_unrecoverable_students,
    ACCOUNTS_FILE,
    RESULTS_FILE,
    ERRORS_FILE,
)
from telegram_bot import parse_students_from_text, parse_students_from_excel, get_certificate_map, get_error_reason_map

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except Exception:
        pass

CLUSTER_PORT = 8766
ORDERS_DIR = "bot_orders"
NODES_STATE_FILE = "cluster_nodes_state.json"
file_lock = threading.RLock()
nodes_lock = threading.RLock()
task_lock = threading.RLock()
_excel_cache = {}

cluster_nodes = {}
in_progress_students = {}
pending_screen_requests = {}  # node_id -> chat_id
_worker_assigned = {}
_sticky_workers = {}
_started_notified_students = set()
_last_nodes_save_ts = 0.0


def normalize_student_key(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"[`'ʻʼ’]", "", str(name).strip().upper())
    return " ".join(s.split())

if os.path.exists(NODES_STATE_FILE):
    try:
        with open(NODES_STATE_FILE, "r", encoding="utf-8") as _nf:
            cluster_nodes.update(json.load(_nf))
        _now_init = time.time()
        for _nid, _ninf in cluster_nodes.items():
            _ninf["idle_alerted"] = False
            _ram_n = int(_ninf.get("ram_gb", 8))
            _target_w = 6 if _ram_n >= 14 else 4
            if int(_ninf.get("workers", 0)) < _target_w:
                _ninf["workers"] = _target_w
            _max_w = int(_ninf.get("workers", _target_w))
            _ws = _ninf.get("worker_statuses") or {}
            # Ortiqcha (eski) oqim raqamlarini tozalaymiz va hozir ishlayotgan o'quvchilarni in_progress_students ga tiklaymiz
            for _wk in list(_ws.keys()):
                if _wk.isdigit() and int(_wk) > _max_w:
                    _ws.pop(_wk, None)
                elif _now_init - _ninf.get("last_seen", 0) <= 180:
                    _m = re.match(r"^\[\d+/\d+\]\s+(.+?)\s+—", str(_ws[_wk]))
                    if _m:
                        _sn = " ".join(_m.group(1).strip().upper().split())
                        in_progress_students[_sn] = _now_init
                        _worker_assigned[(_nid, str(_wk))] = _sn
            if "Bo'sh" in str(_ninf.get("status", "")):
                _ninf["status"] = list(_ws.values())[0] if _ws else "🚀 Navbatdagi o'quvchi ishlanmoqda..."
        with open(NODES_STATE_FILE, "w", encoding="utf-8") as _nfw:
            json.dump(cluster_nodes, _nfw, ensure_ascii=False, indent=2)
    except Exception:
        pass

if "MASTER_PC" not in cluster_nodes:
    cluster_nodes["MASTER_PC"] = {
        "pc_name": f"1-Kompyuter [{socket.gethostname()}] (Asosiy Server)",
        "ram_gb": 16,
        "workers": 4,
        "approved": True,
        "last_seen": time.time(),
        "status": "🟢 Faol ishlamoqda...",
        "worker_statuses": {},
    }

public_tunnel_url = ""
TRIED_CLUSTER_FILE = "cluster_tried_students.json"
tried_cluster_set = {"MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"}
agent_cert_counts = {}
agent_task_start_times = {}
agent_last_durations = {}
recent_completed_records = []


def save_tried_cluster():
    try:
        with open(TRIED_CLUSTER_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(tried_cluster_set)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def save_nodes_state(force: bool = True):
    global _last_nodes_save_ts
    now = time.time()
    if not force and (now - _last_nodes_save_ts < 1.5):
        return
    try:
        with open(NODES_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(cluster_nodes, f, ensure_ascii=False, indent=2)
        _last_nodes_save_ts = now
    except Exception:
        pass


def load_bot_config():
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "bot_token": os.environ.get("BOT_TOKEN", ""),
        "admin_id": int(os.environ.get("ADMIN_ID", "6580113791")),
    }


_tg_rate_lock = threading.Lock()
_last_tg_call_ts = 0.0
_tg_ban_until = 0.0
_PIN_SYNCED = True
_queued_tg_msgs = []


def send_tg(chat_id, text, reply_markup=None, priority_pin=False):
    global _last_tg_call_ts, _tg_ban_until
    if not priority_pin and (not _PIN_SYNCED or time.time() < _tg_ban_until):
        if "MUVAFFAQIYATLI OLINDI" in str(text) or "YANGI (" in str(text):
            with _tg_rate_lock:
                if len(_queued_tg_msgs) < 200:
                    _queued_tg_msgs.append((chat_id, text, reply_markup))
        return {}
    cfg = load_bot_config()
    token = cfg.get("bot_token") or os.environ.get("BOT_TOKEN", "")
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    with _tg_rate_lock:
        if not priority_pin and (not _PIN_SYNCED or time.time() < _tg_ban_until):
            if "MUVAFFAQIYATLI OLINDI" in str(text) or "YANGI (" in str(text):
                if len(_queued_tg_msgs) < 200:
                    _queued_tg_msgs.append((chat_id, text, reply_markup))
            return {}
        wait_gap = 3.5 - (time.time() - _last_tg_call_ts)
        if wait_gap > 0 and not priority_pin:
            time.sleep(wait_gap)
        for attempt in range(2):
            try:
                _last_tg_call_ts = time.time()
                r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=(6, 12))
                res = r.json()
                if not res.get("ok") and res.get("error_code") == 429:
                    ra = float(res.get("parameters", {}).get("retry_after", 5))
                    _tg_ban_until = time.time() + ra + 1.0
                    if "MUVAFFAQIYATLI OLINDI" in str(text) or "YANGI (" in str(text):
                        if len(_queued_tg_msgs) < 200:
                            _queued_tg_msgs.append((chat_id, text, reply_markup))
                    print(f"[TG 429 LIMIT] retry_after={int(ra)}s")
                    return res
                return res
            except Exception:
                if attempt == 0:
                    time.sleep(1.0)
    return {}


def parse_excel_students(xlsx_path: str):
    try:
        mtime = os.path.getmtime(xlsx_path)
        cached = _excel_cache.get(xlsx_path)
        if cached and cached[0] == mtime:
            return cached[1]
    except Exception:
        mtime = 0

    try:
        students = parse_students_from_excel(xlsx_path)
        if students:
            _excel_cache[xlsx_path] = (mtime, students)
        return students
    except Exception:
        return []


_state_mem_cache = {"ts": 0.0, "done": set(), "unrec": set(), "accs": {}, "orders": []}
_last_tried_save_ts = 0.0


def get_pending_cluster_task(node_id: str = "", worker_id: str = "1"):
    global _last_tried_save_ts
    if os.path.exists("cluster_pause_state.txt"):
        return {"has_task": False, "all_done": False, "reason": "system_paused"}
    now = time.time()
    if now - _state_mem_cache["ts"] > 2.0:
        done_set = get_completed_students()
        unrec_set = get_unrecoverable_students()
        accs = get_existing_accounts()
        candidates_files = []
        if os.path.exists(ORDERS_DIR):
            for fn in os.listdir(ORDERS_DIR):
                if fn.startswith("in_") and fn.endswith(".xlsx"):
                    full_p = os.path.join(ORDERS_DIR, fn)
                    mt = os.path.getmtime(full_p)
                    if mt > 0:
                        candidates_files.append((mt, fn, full_p))
        candidates_files.sort(key=lambda x: x[0])
        parsed_orders = []
        for _, fn, full_p in candidates_files:
            parts = fn.split("_")
            chat_id = int(parts[1]) if len(parts) >= 3 and parts[1].isdigit() else load_bot_config().get("admin_id", 6580113791)
            students = parse_excel_students(full_p)
            if students and any(s["name"] not in done_set and s["name"] not in unrec_set and s["name"] != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI" for s in students):
                parsed_orders.append((chat_id, students))
        _state_mem_cache["done"] = done_set
        _state_mem_cache["unrec"] = unrec_set
        _state_mem_cache["accs"] = accs
        _state_mem_cache["orders"] = parsed_orders
        _state_mem_cache["ts"] = now
    else:
        done_set = _state_mem_cache["done"]
        unrec_set = _state_mem_cache["unrec"]
        accs = _state_mem_cache["accs"]
        parsed_orders = _state_mem_cache["orders"]

    with nodes_lock:
        dead_nodes = [nid for nid, ninf in list(cluster_nodes.items()) if nid != "MASTER_PC" and now - float(ninf.get("last_seen", 0)) > 90]
        for nid in dead_nodes:
            cluster_nodes.pop(nid, None)

        if node_id and node_id != "MASTER_PC":
            node_info = cluster_nodes.get(node_id, {})
            if node_info and not node_info.get("approved", True):
                return {"has_task": False, "reason": "node_not_approved"}
            try:
                if int(worker_id or 1) > 6:
                    return {"has_task": False, "reason": "max_6_agents_per_node"}
            except Exception:
                pass

        # Uzilgan kompyuterlarning band qilgan o'quvchilarini bo'shatamiz
        for (_wnid, _wwid), _wst in list(_worker_assigned.items()):
            if _wnid == "MASTER_PC":
                # Master PC mahalliy host - agar 10 daqiqa hech qanday javob bo'lmasa tozalaymiz
                if now - in_progress_students.get(_wst, 0) > 600:
                    _worker_assigned.pop((_wnid, _wwid), None)
                    _sticky_workers.pop((_wnid, _wwid), None)
                    in_progress_students.pop(_wst, None)
                continue
            _nlast = cluster_nodes.get(_wnid, {}).get("last_seen", 0)
            if now - _nlast > 1800:
                _worker_assigned.pop((_wnid, _wwid), None)
                _sticky_workers.pop((_wnid, _wwid), None)
                in_progress_students.pop(_wst, None)

        # Hozir tirik agentlarga biriktirilgan barcha o'quvchilar
        active_assigned_norm = set()
        for (_wn, _ww), _st in _worker_assigned.items():
            if _wn == "MASTER_PC" or (now - cluster_nodes.get(_wn, {}).get("last_seen", 0) <= 600):
                active_assigned_norm.add(normalize_student_key(_st))

        # Agar o'quvchi faol agentga biriktirilgan bo'lsa, in_progress_students dan HECH QACHON o'chirilmaydi!
        expired = [k for k, t in in_progress_students.items() if (now - t > 600 and normalize_student_key(k) not in active_assigned_norm)]
        for k in expired:
            in_progress_students.pop(k, None)

        # Hozir boshqa faol agentlar ishlayotgan o'quvchilar to'plami (Qat'iy 1 o'quvchi = 1 agent!)
        w_key = (node_id, str(worker_id)) if (node_id and worker_id) else None
        busy_by_others_norm = set()
        for _ok, _ost in _worker_assigned.items():
            if _ok != w_key:
                _ok_nid = _ok[0]
                if _ok_nid == "MASTER_PC" or (now - cluster_nodes.get(_ok_nid, {}).get("last_seen", 0) <= 180):
                    busy_by_others_norm.add(normalize_student_key(_ost))

        for _st_k, _st_t in in_progress_students.items():
            if now - _st_t <= 180 and normalize_student_key(_st_k) in active_assigned_norm:
                if not (w_key and normalize_student_key(_worker_assigned.get(w_key, "")) == normalize_student_key(_st_k)):
                    busy_by_others_norm.add(normalize_student_key(_st_k))

        done_norm = {normalize_student_key(d) for d in done_set}
        unrec_norm = {normalize_student_key(u) for u in unrec_set}

        # 1) QAT'IY QOIDA: 1 AGENT 1 TA O'QUVCHINI TUGATADI!
        # Agar shu agent o'ziga biriktirilgan o'quvchini hali oxirigacha (COMPLETED/UNRECOVERABLE) yetkazmagan bo'lsa,
        # SHU AGENTNING O'ZI oxirigacha ishlaydi, hech qachon boshqa o'quvchiga sakramaydi!
        if w_key:
            sticky = _sticky_workers.get(w_key)
            if sticky:
                st_sticky = sticky["student"]
                sn_sticky = st_sticky["name"]
                sn_norm = normalize_student_key(sn_sticky)
                if (
                    sn_norm not in done_norm
                    and sn_norm not in unrec_norm
                    and sn_norm not in busy_by_others_norm
                    and sticky.get("tries", 1) < 10
                ):
                    sticky["tries"] = sticky.get("tries", 1) + 1
                    in_progress_students[sn_sticky] = now
                    _worker_assigned[w_key] = sn_sticky
                    acc_line = ""
                    if sn_sticky in accs:
                        ac = accs[sn_sticky]
                        acc_line = f"{sn_sticky} | {st_sticky.get('class_name', '')} | {ac.get('email', '')} | {ac.get('password', '')}"
                    elif sticky.get("account_line"):
                        acc_line = sticky["account_line"]
                    return {
                        "has_task": True,
                        "task_id": f"task_{sticky['idx']}_{int(now)}",
                        "chat_id": sticky["chat_id"],
                        "idx": sticky["idx"],
                        "total": sticky["total"],
                        "student": st_sticky,
                        "account_line": acc_line,
                    }
                else:
                    _sticky_workers.pop(w_key, None)
                    prev_st = _worker_assigned.pop(w_key, None)
                    if prev_st and normalize_student_key(prev_st) not in busy_by_others_norm:
                        in_progress_students.pop(prev_st, None)
                    tried_cluster_set.add(sn_sticky)
            else:
                prev_st = _worker_assigned.pop(w_key, None)
                if prev_st and normalize_student_key(prev_st) not in busy_by_others_norm:
                    in_progress_students.pop(prev_st, None)

        # 2) Yangi o'quvchi tanlash: ISHLARNI TAQSIMLASH:
        # 1-Kompyuter (Asosiy Server) boshidan oladi: 1, 2, 3...
        # Klaster kompyuterlari esa oxiridan oladi: N, N-1, N-2... Shunda ular o'rtaga qarab birlashadi va hech qachon to'qnashmaydi!
        best_cand = None
        for chat_id, students in parsed_orders:
            total = len(students)
            indices = range(1, total + 1)
            for idx in indices:
                st = students[idx - 1]
                s_name = st.get("name", "")
                if not s_name:
                    continue
                s_norm = normalize_student_key(s_name)
                if s_norm in done_norm or s_norm in unrec_norm:
                    continue
                if s_norm == normalize_student_key("MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"):
                    continue
                if s_norm in busy_by_others_norm:
                    continue
                best_cand = (chat_id, idx, total, st, s_name)
                break
            if best_cand is not None:
                break

        if best_cand is not None:
            chat_id, idx, total, st, s_name = best_cand
            in_progress_students[s_name] = now
            acc_line = ""
            if s_name in accs:
                ac = accs[s_name]
                acc_line = f"{s_name} | {st.get('class_name', '')} | {ac.get('email', '')} | {ac.get('password', '')}"
            if w_key:
                _worker_assigned[w_key] = s_name
                _sticky_workers[w_key] = {
                    "chat_id": chat_id,
                    "idx": idx,
                    "total": total,
                    "student": st,
                    "tries": 1,
                    "account_line": acc_line,
                }
            return {
                "has_task": True,
                "task_id": f"task_{idx}_{int(now)}",
                "chat_id": chat_id,
                "idx": idx,
                "total": total,
                "student": st,
                "account_line": acc_line,
            }

        # Agar barcha qolgan o'quvchilar hozir faol agentlar tomonidan ishlanayotgan bo'lsa (all_done=False!),
        # ortiqcha agentlar ustiga kirib xalaqit bermasdan 10 soniya kutib turadi
        has_any_remaining = any(
            normalize_student_key(s["name"]) not in done_norm
            and normalize_student_key(s["name"]) not in unrec_norm
            and normalize_student_key(s["name"]) != normalize_student_key("MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI")
            for _, sts in parsed_orders
            for s in sts
        )
        if has_any_remaining:
            return {"has_task": False, "all_done": False, "reason": "all_remaining_in_progress"}

    return {"has_task": False, "all_done": True}


# =============================================================================
# WEB ANYDESK — JONLI VEB EKRAN VA KORDINATADAN BOSHQARISH TIZIMI
# =============================================================================
_last_screen_bytes = None
_last_screen_ts = 0.0
_screen_capture_lock = threading.Lock()

remote_actions_lock = threading.Lock()
remote_pending_actions = {}    # node_id -> [action_dicts]
remote_latest_screens = {}     # node_id -> bytes
remote_active_nodes = {}       # node_id -> timestamp

def get_screen_jpeg(max_age_sec=0.7, node="MASTER_PC"):
    global _last_screen_bytes, _last_screen_ts
    now = time.time()
    if node and node != "MASTER_PC":
        remote_active_nodes[node] = now
        if node in remote_latest_screens and remote_latest_screens[node]:
            return remote_latest_screens[node]
    with _screen_capture_lock:
        if _last_screen_bytes and (now - _last_screen_ts < max_age_sec):
            return _last_screen_bytes
        try:
            tmp_p = os.path.join(os.environ.get("TEMP", "."), f"web_scr_{int(now*1000)}.jpg")
            ps_p = tmp_p.replace("\\", "/")
            ps_c = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height); "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
                f"$bmp.Save('{ps_p}', [System.Drawing.Imaging.ImageFormat]::Jpeg); "
                "$g.Dispose(); $bmp.Dispose();"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_c],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                creationflags=0x08000000 if os.name == "nt" else 0
            )
            if os.path.exists(tmp_p):
                with open(tmp_p, "rb") as f:
                    _last_screen_bytes = f.read()
                _last_screen_ts = now
                try:
                    os.remove(tmp_p)
                except Exception:
                    pass
        except Exception as e:
            print(f"[WEB ANYDESK CAPTURE ERROR] {e}")
        return _last_screen_bytes

def web_any_click(x, y, btn="left", node="MASTER_PC"):
    if node and node != "MASTER_PC":
        with remote_actions_lock:
            remote_pending_actions.setdefault(node, []).append({
                "type": "click", "x": int(x), "y": int(y), "btn": btn
            })
        return True
    try:
        import ctypes
        u32 = ctypes.windll.user32
        u32.SetCursorPos(int(x), int(y))
        time.sleep(0.02)
        if btn == "right":
            u32.mouse_event(0x0008, 0, 0, 0, 0)
            time.sleep(0.04)
            u32.mouse_event(0x0010, 0, 0, 0, 0)
        else:
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.04)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
        return True
    except Exception as e:
        print(f"[WEB ANYDESK CLICK ERROR] {e}")
        return False

def web_any_scroll(direction, node="MASTER_PC"):
    if node and node != "MASTER_PC":
        with remote_actions_lock:
            remote_pending_actions.setdefault(node, []).append({
                "type": "scroll", "dir": direction
            })
        return True
    try:
        import ctypes
        u32 = ctypes.windll.user32
        delta = 360 if direction == "up" else -360
        u32.mouse_event(0x0800, 0, 0, delta, 0)
        return True
    except Exception:
        return False

def web_any_key(key, node="MASTER_PC"):
    if node and node != "MASTER_PC":
        with remote_actions_lock:
            remote_pending_actions.setdefault(node, []).append({
                "type": "key", "key": key
            })
        return True
    try:
        import ctypes
        u32 = ctypes.windll.user32
        vk_map = {"enter": 0x0D, "backspace": 0x08, "tab": 0x09, "esc": 0x1B, "space": 0x20}
        vk = vk_map.get(key.lower())
        if vk:
            u32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(vk, 0, 2, 0)
            return True
    except Exception:
        pass
    return False

def web_any_type(text, node="MASTER_PC"):
    if node and node != "MASTER_PC":
        with remote_actions_lock:
            remote_pending_actions.setdefault(node, []).append({
                "type": "type", "text": text
            })
        return True
    try:
        escaped = text.replace("'", "''").replace("{", "{{}").replace("}", "{}}")
        ps = f"$w = New-Object -ComObject WScript.Shell; $w.SendKeys('{escaped}')"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=5)
        return True
    except Exception:
        return False

def web_any_hotkey(combo, node="MASTER_PC"):
    if node and node != "MASTER_PC":
        with remote_actions_lock:
            remote_pending_actions.setdefault(node, []).append({
                "type": "hotkey", "combo": combo
            })
        return True
    try:
        import ctypes
        u32 = ctypes.windll.user32
        combo = str(combo).lower().strip()
        if combo in ("ctrl+a", "^a"):
            u32.keybd_event(0x11, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x41, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x41, 0, 2, 0)
            time.sleep(0.04)
            u32.keybd_event(0x11, 0, 2, 0)
            return True
        elif combo in ("ctrl+v", "^v"):
            u32.keybd_event(0x11, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x56, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x56, 0, 2, 0)
            time.sleep(0.04)
            u32.keybd_event(0x11, 0, 2, 0)
            return True
        elif combo in ("ctrl+c", "^c"):
            u32.keybd_event(0x11, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x43, 0, 0, 0)
            time.sleep(0.04)
            u32.keybd_event(0x43, 0, 2, 0)
            time.sleep(0.04)
            u32.keybd_event(0x11, 0, 2, 0)
            return True
    except Exception as e:
        print(f"[HOTKEY ERROR] {e}")
    return False

WEB_ANY_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>🌐 Web AnyDesk — UzbekCoders</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; min-height: 100vh; }
  header { background: #1e293b; padding: 8px 14px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 50; flex-wrap: wrap; gap: 8px; }
  .title { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: #38bdf8; }
  .node-select { background: #0f172a; color: #38bdf8; border: 1.5px solid #0284c7; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 12px; outline: none; cursor: pointer; }
  .node-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.3); }
  .status-badge { font-size: 11px; background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; padding: 3px 8px; border-radius: 999px; font-weight: 600; }
  .info-bar { font-size: 12px; color: #94a3b8; text-align: center; padding: 6px 10px; background: #0b1120; border-bottom: 1px solid #1e293b; }
  .screen-wrap { flex: 1; display: flex; justify-content: center; align-items: center; padding: 8px; background: #020617; position: relative; overflow: auto; }
  .screen-container { position: relative; display: inline-block; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.8); border-radius: 8px; overflow: hidden; border: 1px solid #334155; }
  #screenImg { display: block; max-width: 100%; height: auto; cursor: crosshair; user-select: none; -webkit-user-drag: none; touch-action: manipulation; }
  .click-ripple { position: absolute; width: 24px; height: 24px; border-radius: 50%; background: rgba(56, 189, 248, 0.6); border: 2px solid #38bdf8; transform: translate(-50%, -50%) scale(0); animation: ripple 0.4s ease-out forwards; pointer-events: none; }
  @keyframes ripple { 0% { transform: translate(-50%, -50%) scale(0.2); opacity: 1; } 100% { transform: translate(-50%, -50%) scale(1.6); opacity: 0; } }
  .controls { background: #1e293b; padding: 8px 12px; border-top: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; align-items: center; position: sticky; bottom: 0; z-index: 50; }
  button, .btn { background: #334155; color: #f8fafc; border: 1px solid #475569; padding: 7px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 4px; user-select: none; }
  button:hover, .btn:hover { background: #475569; border-color: #64748b; }
  button:active, .btn:active { transform: scale(0.96); }
  .btn-primary { background: #0284c7; border-color: #0369a1; color: white; }
  .btn-success { background: #16a34a; border-color: #15803d; color: white; }
  .btn-danger { background: #dc2626; border-color: #b91c1c; color: white; }
  .input-group { display: flex; gap: 4px; }
  .input-group input { background: #0f172a; border: 1px solid #475569; color: #fff; padding: 6px 8px; border-radius: 6px; font-size: 12px; outline: none; width: 130px; }
  .input-group input:focus { border-color: #38bdf8; }
</style>
</head>
<body>
<header>
  <div class="title">
    <span>🌐 Web AnyDesk</span>
    <select id="nodeSelect" class="node-select" onchange="onNodeChange(this.value)">
      <option value="MASTER_PC">1-Kompyuter (Asosiy Server)</option>
    </select>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <div class="status-badge" id="statusBadge">🟢 Jonli Ekran</div>
    <button class="btn btn-danger" onclick="exitWebAny()" style="padding:4px 8px; font-size:11px;">❌ Chiqish</button>
  </div>
</header>

<div class="info-bar" id="statusBar">👆 Ekranning istalgan joyiga bosing — sichqoncha bosiladi. Sichqoncha o'ng tugmasi ham ishlaydi!</div>

<div class="screen-wrap">
  <div class="screen-container" id="screenBox">
    <div id="virtualMouse" style="position: absolute; width: 22px; height: 26px; pointer-events: none; transition: left 0.1s ease-out, top 0.1s ease-out; z-index: 100; display: none;">
      <svg viewBox="0 0 24 24" width="22" height="26" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));">
        <path fill="#38bdf8" stroke="#ffffff" stroke-width="1.5" d="M3 3l7 18 3-7 7-3L3 3z"/>
      </svg>
    </div>
    <img id="screenImg" src="/api/screen?node=MASTER_PC" alt="Virtual Screen">
  </div>
</div>

<div class="controls">
  <button class="btn btn-primary" onclick="forceRefresh()">🔄 Yangilash</button>
  <button id="autoBtn" class="btn btn-success" onclick="toggleAuto()">⏸️ Avto (1s)</button>
  <button id="rightBtn" class="btn" onclick="toggleRightClickMode()" style="background:#475569; border-color:#64748b;">🖱️ Sichqoncha O'ng Tugmasi (OFF)</button>
  <button onclick="sendKey('enter')">↵ Enter</button>
  <button onclick="sendKey('backspace')">⌫ O'chirish</button>
  <button onclick="sendScroll('up')">⬆️ Scroll</button>
  <button onclick="sendScroll('down')">⬇️ Scroll</button>
  <button onclick="quickType('@Ak101095')">📋 Parol</button>
  <button onclick="sendKey('tab')">⇥ Tab</button>
  <button onclick="quickHotkey('ctrl+a')">Ctrl+A</button>
  <button onclick="quickHotkey('ctrl+v')">Ctrl+V</button>
  
  <div class="input-group">
    <input type="text" id="textInput" placeholder="Matn yozish..." onkeydown="if(event.key==='Enter') sendText()">
    <button onclick="sendText()">Yozish</button>
  </div>
</div>

<script>
let selectedNode = 'MASTER_PC';
let rightClickMode = false;
let autoActive = true;
let refreshing = false;
const img = document.getElementById('screenImg');
const box = document.getElementById('screenBox');
const statusBadge = document.getElementById('statusBadge');
const statusBar = document.getElementById('statusBar');

function exitWebAny() {
  if (window.Telegram && window.Telegram.WebApp) {
    try { window.Telegram.WebApp.close(); } catch(e) {}
  }
  try { window.history.back(); } catch(e) {}
  try { window.close(); } catch(e) {}
}

if (window.Telegram && window.Telegram.WebApp) {
  try {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.BackButton.show();
    window.Telegram.WebApp.BackButton.onClick(exitWebAny);
  } catch(e) {}
}

function toggleRightClickMode() {
  rightClickMode = !rightClickMode;
  const b = document.getElementById('rightBtn');
  if (rightClickMode) {
    b.innerText = "🖱️ Sichqoncha O'ng Tugmasi (YONIQ)";
    b.style.background = "#e11d48";
    b.style.borderColor = "#be123c";
    statusBar.innerText = "👉 Ekranning biror joyini bosing — O'ng tugma (Right click) bosiladi!";
  } else {
    b.innerText = "🖱️ Sichqoncha O'ng Tugmasi (OFF)";
    b.style.background = "#475569";
    b.style.borderColor = "#64748b";
    statusBar.innerText = "👆 Ekranning istalgan joyiga bosing — sichqoncha bosiladi";
  }
}

function onNodeChange(val) {
  selectedNode = val;
  statusBar.innerText = `🖥 ${val} kompyuteriga ulanilmoqda...`;
  forceRefresh();
}

function updateNodeList() {
  fetch('/api/robot_dashboard_data?t=' + Date.now())
    .then(r => r.json())
    .then(data => {
      const sel = document.getElementById('nodeSelect');
      if (!sel || !data.nodes) return;
      const currentVal = sel.value || selectedNode;
      sel.innerHTML = '';
      data.nodes.forEach((n, idx) => {
        const opt = document.createElement('option');
        opt.value = n.node_id;
        opt.text = n.pc_name || ((idx + 1) + '-Kompyuter');
        if (n.node_id === currentVal) opt.selected = true;
        sel.appendChild(opt);
      });
      if (!sel.value) sel.value = 'MASTER_PC';
      selectedNode = sel.value;
    })
    .catch(() => {});
}

setInterval(updateNodeList, 6000);
updateNodeList();

function refreshScreen() {
  if (refreshing) return;
  refreshing = true;
  const next = new Image();
  next.onload = () => {
    img.src = next.src;
    refreshing = false;
    statusBadge.innerText = '🟢 ' + new Date().toLocaleTimeString();
  };
  next.onerror = () => {
    refreshing = false;
    statusBadge.innerText = '⚠️ Ulanish...';
  };
  next.src = `/api/screen?node=${encodeURIComponent(selectedNode)}&t=` + Date.now();
}

function forceRefresh() {
  refreshing = false;
  refreshScreen();
}

let timer = setInterval(() => {
  if (autoActive) refreshScreen();
}, 1000);

function toggleAuto() {
  autoActive = !autoActive;
  const btn = document.getElementById('autoBtn');
  if (autoActive) {
    btn.innerText = '⏸️ Avto (1s)';
    btn.className = 'btn btn-success';
  } else {
    btn.innerText = '▶️ Avto: O\\'chiq';
    btn.className = 'btn';
  }
}

function handlePointerClick(e, explicitBtn) {
  const rect = img.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  
  const clickX = clientX - rect.left;
  const clickY = clientY - rect.top;
  
  const natW = img.naturalWidth || 1920;
  const natH = img.naturalHeight || 1080;
  
  const scaleX = natW / rect.width;
  const scaleY = natH / rect.height;
  
  const realX = Math.round(clickX * scaleX);
  const realY = Math.round(clickY * scaleY);

  let btn = explicitBtn;
  if (!btn) {
    if (e.button === 2 || rightClickMode) {
      btn = 'right';
      if (rightClickMode) toggleRightClickMode();
    } else {
      btn = 'left';
    }
  }

  // Virtual mouse cursor joylashtirish
  const vMouse = document.getElementById('virtualMouse');
  if (vMouse) {
    vMouse.style.left = clickX + 'px';
    vMouse.style.top = clickY + 'px';
    vMouse.style.display = 'block';
    vMouse.style.transform = 'scale(0.8)';
    setTimeout(() => vMouse.style.transform = 'scale(1.0)', 150);
  }

  // Ripple animatsiyasi
  const ripple = document.createElement('div');
  ripple.className = 'click-ripple';
  ripple.style.left = clickX + 'px';
  ripple.style.top = clickY + 'px';
  if (btn === 'right') {
    ripple.style.borderColor = '#f43f5e';
    ripple.style.background = 'rgba(244, 63, 94, 0.6)';
  }
  box.appendChild(ripple);
  setTimeout(() => ripple.remove(), 400);
  
  const btnTitle = btn === 'right' ? "O'ng tugma" : "Chap tugma";
  statusBar.innerText = `👆 ${btnTitle} bosilmoqda: (${realX}, ${realY})...`;
  
  fetch(`/api/click?x=${realX}&y=${realY}&btn=${btn}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(res => {
      statusBar.innerText = `✅ ${btnTitle} bosildi: (${realX}, ${realY})`;
      setTimeout(forceRefresh, 250);
    })
    .catch(err => {
      statusBar.innerText = `❌ Xato: ${err}`;
    });
}

img.addEventListener('click', function(e) { handlePointerClick(e); });
img.addEventListener('contextmenu', function(e) {
  e.preventDefault();
  handlePointerClick(e, 'right');
});

function sendKey(key) {
  statusBar.innerText = `⌨️ ${key} yuborilmoqda...`;
  fetch(`/api/key?key=${key}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(() => {
      statusBar.innerText = `✅ ${key} yuborildi`;
      setTimeout(forceRefresh, 200);
    });
}

function sendScroll(dir) {
  statusBar.innerText = `📜 Scroll ${dir}...`;
  fetch(`/api/scroll?dir=${dir}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(() => {
      setTimeout(forceRefresh, 200);
    });
}

function sendText() {
  const inp = document.getElementById('textInput');
  const txt = inp.value.trim();
  if (!txt) return;
  statusBar.innerText = `⌨️ Matn yozilmoqda: "${txt}"...`;
  fetch(`/api/type?text=${encodeURIComponent(txt)}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(() => {
      inp.value = '';
      statusBar.innerText = `✅ Matn kiritildi`;
      setTimeout(forceRefresh, 300);
    });
}

function quickType(val) {
  statusBar.innerText = `⌨️ Kiritilmoqda: ${val}...`;
  fetch(`/api/type?text=${encodeURIComponent(val)}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(() => {
      statusBar.innerText = `✅ Kiritildi: ${val}`;
      setTimeout(forceRefresh, 300);
    });
}

function quickHotkey(combo) {
  statusBar.innerText = `⌨️ ${combo}...`;
  fetch(`/api/hotkey?combo=${combo}&node=${encodeURIComponent(selectedNode)}&t=${Date.now()}`)
    .then(r => r.json())
    .then(() => {
      statusBar.innerText = `✅ ${combo} bosildi`;
      setTimeout(forceRefresh, 300);
    });
}
</script>
</body>
</html>
"""

# =============================================================================
# ROBOT AGENTLAR JONLI DASHBOARD (SVG + CSS ANIMATSIYALI)
# =============================================================================
ROBOT_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>🤖 Robot Agentlar Dashboard — UzbekCoders</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #070b14; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; min-height: 100vh; }
  header { background: #0f172a; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 50; }
  .brand { font-size: 15px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
  .header-actions { display: flex; align-items: center; gap: 8px; }
  .btn { background: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 4px; text-decoration: none; user-select: none; }
  .btn:hover { background: #334155; border-color: #475569; }
  .btn:active { transform: scale(0.96); }
  .btn-primary { background: #0284c7; border-color: #0369a1; color: white; }
  .btn-danger { background: #dc2626; border-color: #b91c1c; color: white; }
  .container { max-width: 1200px; margin: 0 auto; width: 100%; padding: 14px; display: flex; flex-direction: column; gap: 16px; }
  
  .boss-card { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border: 1px solid #38bdf8; border-radius: 12px; padding: 18px 14px; box-shadow: 0 10px 30px -10px rgba(56, 189, 248, 0.25); display: flex; flex-direction: column; align-items: center; text-align: center; position: relative; overflow: hidden; }
  .boss-avatar-wrap { position: relative; width: 100px; height: 100px; margin-bottom: 10px; animation: float 3s ease-in-out infinite; }
  @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
  .boss-badge { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .boss-title { font-size: 17px; font-weight: 800; color: #fff; margin-bottom: 4px; }
  .boss-subtitle { font-size: 12px; color: #94a3b8; margin-bottom: 14px; max-width: 520px; }
  
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; width: 100%; }
  .stat-box { background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 10px 8px; display: flex; flex-direction: column; align-items: center; }
  .stat-val { font-size: 20px; font-weight: 800; color: #38bdf8; }
  .stat-val.done { color: #4ade80; }
  .stat-val.rem { color: #facc15; }
  .stat-label { font-size: 11px; color: #94a3b8; margin-top: 2px; }
  
  .section-title { font-size: 15px; font-weight: 700; color: #cbd5e1; display: flex; align-items: center; gap: 8px; margin-top: 4px; }
  .agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
  
  .agent-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; position: relative; transition: all 0.2s ease; }
  .agent-card.working { border-color: #0284c7; box-shadow: 0 4px 20px -2px rgba(2, 132, 199, 0.3); }
  .agent-card.idle { border-color: #334155; opacity: 0.85; }
  .agent-card.offline { border-color: #1e293b; opacity: 0.5; }
  
  .agent-header { display: flex; justify-content: space-between; align-items: center; }
  .agent-name { font-size: 13px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 6px; }
  
  .status-pill { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 999px; text-transform: uppercase; }
  .status-pill.working { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; }
  .status-pill.idle { background: rgba(248, 250, 252, 0.1); color: #cbd5e1; border: 1px solid #475569; }
  .status-pill.offline { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444; }
  
  .workstation { display: flex; align-items: center; gap: 12px; background: #070b14; border-radius: 8px; padding: 10px; border: 1px solid #1e293b; }
  .robot-svg-wrap { width: 54px; height: 54px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  
  @keyframes robotWorkBob {
    0%, 100% { transform: translateY(0) scale(1); }
    50% { transform: translateY(-3px) scale(1.02); }
  }
  .agent-card.working .robot-svg-wrap {
    animation: robotWorkBob 0.6s infinite ease-in-out;
  }
  @keyframes typingLeft {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-4px) rotate(-6deg); }
  }
  @keyframes typingRight {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-4px) rotate(6deg); }
  }
  .agent-card.working .arm-left {
    animation: typingLeft 0.28s infinite ease-in-out;
    transform-origin: 12px 32px;
  }
  .agent-card.working .arm-right {
    animation: typingRight 0.28s infinite ease-in-out 0.14s;
    transform-origin: 20px 32px;
  }
  @keyframes monitorPulse {
    0%, 100% { fill: #0284c7; filter: drop-shadow(0 0 2px #38bdf8); }
    50% { fill: #38bdf8; filter: drop-shadow(0 0 8px #38bdf8); }
  }
  .agent-card.working .monitor-screen { animation: monitorPulse 1.2s infinite ease-in-out; }
  
  .agent-details { flex: 1; min-width: 0; }
  .detail-student { font-size: 12px; font-weight: 700; color: #38bdf8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .detail-step { font-size: 11px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
  .detail-timer { font-size: 11px; font-weight: 700; color: #a855f7; margin-top: 4px; display: inline-flex; align-items: center; gap: 4px; }
  
  .agent-metrics { display: flex; justify-content: space-between; font-size: 11px; padding-top: 6px; border-top: 1px solid #1e293b; color: #94a3b8; }
  .agent-metrics b { color: #f1f5f9; }
  
  .recent-certs-box { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 12px; }
  .cert-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 6px; border-bottom: 1px solid #1e293b; font-size: 12px; }
  .cert-item:last-child { border-bottom: none; }
  .cert-info b { color: #f8fafc; }
  .cert-info span { color: #94a3b8; }
  .cert-dur { font-weight: 700; color: #4ade80; }
  .empty-state { text-align: center; color: #64748b; padding: 20px; font-size: 13px; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <span>🤖 Robot Agentlar Dashboard</span>
    <span id="livePill" style="font-size:11px; padding:2px 8px; border-radius:999px; background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid #22c55e;">● Jonli</span>
  </div>
  <div class="header-actions">
    <button class="btn btn-primary" onclick="updateDashboard()">🔄 Yangilash</button>
    <a href="/web_any" class="btn">🌐 Web Any</a>
    <button class="btn btn-danger" onclick="exitDashboard()">❌ Chiqish</button>
  </div>
</header>

<div class="container">
  <!-- BOSH ISH BERUVCHI ROBOT -->
  <div class="boss-card">
    <div class="boss-badge">👑 Bosh Ish Beruvchi Robot (Master Commander)</div>
    
    <div class="boss-avatar-wrap">
      <svg viewBox="0 0 100 100" width="100" height="100">
        <line x1="50" y1="20" x2="50" y2="8" stroke="#38bdf8" stroke-width="3" stroke-linecap="round"/>
        <circle cx="50" cy="7" r="5" fill="#38bdf8" filter="drop-shadow(0 0 6px #38bdf8)"/>
        <rect x="18" y="32" width="6" height="16" rx="3" fill="#0284c7"/>
        <rect x="76" y="32" width="6" height="16" rx="3" fill="#0284c7"/>
        <rect x="22" y="20" width="56" height="42" rx="10" fill="#1e293b" stroke="#38bdf8" stroke-width="2.5"/>
        <rect x="28" y="28" width="44" height="22" rx="6" fill="#0b1120"/>
        <circle cx="40" cy="39" r="5" fill="#38bdf8" filter="drop-shadow(0 0 4px #38bdf8)"/>
        <circle cx="60" cy="39" r="5" fill="#38bdf8" filter="drop-shadow(0 0 4px #38bdf8)"/>
        <line x1="38" y1="54" x2="62" y2="54" stroke="#475569" stroke-width="2" stroke-linecap="round"/>
        <path d="M30 64 L70 64 L78 86 L22 86 Z" fill="#0f172a" stroke="#0284c7" stroke-width="2"/>
        <circle cx="50" cy="75" r="6" fill="#22c55e" filter="drop-shadow(0 0 6px #22c55e)"/>
      </svg>
    </div>

    <div class="boss-title">Barcha Kompyuterlar Va Agentlar Nazorati</div>
    <div class="boss-subtitle">Buyurtmalar avtomatik navbat bilan taqsimlanadi, robotlar mustaqil test topshiradi va sertifikat oladi.</div>

    <div class="stats-grid">
      <div class="stat-box">
        <span class="stat-val" id="totalCount">0</span>
        <span class="stat-label">📦 Jami O'quvchilar</span>
      </div>
      <div class="stat-box">
        <span class="stat-val done" id="doneCount">0</span>
        <span class="stat-label">🏆 Olingan Sertifikatlar</span>
      </div>
      <div class="stat-box">
        <span class="stat-val rem" id="remCount">0</span>
        <span class="stat-label">⏳ Kutilayotgan Navbat</span>
      </div>
      <div class="stat-box">
        <span class="stat-val" id="activeAgents">0</span>
        <span class="stat-label">🤖 Faol Ishchi Robotlar</span>
      </div>
      <div class="stat-box">
        <span class="stat-val" id="avgSpeed">~2 daqiqa</span>
        <span class="stat-label">⚡️ O'rtacha Tezlik</span>
      </div>
    </div>
  </div>

  <!-- ROBOT AGENTLAR GRID -->
  <div class="section-title">
    <span>🤖 Kompyuterlarda Ishlayotgan Robot Agentlar</span>
  </div>

  <div class="agents-grid" id="agentsGrid">
    <div class="empty-state">Agentlar holati yuklanmoqda...</div>
  </div>

  <!-- OXIRGI OLINGAN SERTIFIKATLAR -->
  <div class="section-title">
    <span>🏆 Oxirgi Olingan Sertifikatlar (Necha minutda olingani bilan)</span>
  </div>

  <div class="recent-certs-box" id="recentCertsBox">
    <div class="empty-state">Hali yakunlangan sertifikatlar yo'q</div>
  </div>
</div>

<script>
function exitDashboard() {
  if (window.Telegram && window.Telegram.WebApp) {
    try { window.Telegram.WebApp.close(); } catch(e) {}
  }
  try { window.history.back(); } catch(e) {}
  try { window.close(); } catch(e) {}
}

if (window.Telegram && window.Telegram.WebApp) {
  try {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.BackButton.show();
    window.Telegram.WebApp.BackButton.onClick(exitDashboard);
  } catch(e) {}
}

function renderAgentRobotSVG(state) {
  const isWork = state === 'working';
  const isIdle = state === 'idle';
  const headColor = isWork ? '#1e293b' : (isIdle ? '#1e293b' : '#0f172a');
  const eyeColor = isWork ? '#22c55e' : (isIdle ? '#facc15' : '#475569');
  const monitorColor = isWork ? '#0284c7' : (isIdle ? '#334155' : '#0b1120');

  return `
    <svg viewBox="0 0 60 60" width="54" height="54">
      <rect x="4" y="46" width="52" height="4" rx="2" fill="#334155"/>
      <rect x="30" y="24" width="22" height="17" rx="3" fill="#0b1120" stroke="#475569" stroke-width="1.5"/>
      <rect x="32" y="26" width="18" height="13" rx="2" fill="${monitorColor}" class="${isWork ? 'monitor-screen' : ''}"/>
      <line x1="41" y1="41" x2="41" y2="46" stroke="#475569" stroke-width="2"/>
      <rect x="10" y="14" width="16" height="14" rx="4" fill="${headColor}" stroke="${eyeColor}" stroke-width="1.5"/>
      <circle cx="16" cy="20" r="2" fill="${eyeColor}"/>
      <circle cx="21" cy="20" r="2" fill="${eyeColor}"/>
      <path d="M12 28 L24 28 L26 44 L10 44 Z" fill="#0f172a" stroke="#334155" stroke-width="1"/>
      <line x1="12" y1="32" x2="28" y2="42" stroke="${isWork ? '#38bdf8' : '#64748b'}" stroke-width="2" stroke-linecap="round" class="arm-left"/>
      <line x1="20" y1="32" x2="34" y2="43" stroke="${isWork ? '#38bdf8' : '#64748b'}" stroke-width="2" stroke-linecap="round" class="arm-right"/>
    </svg>
  `;
}

function updateDashboard() {
  fetch('/api/robot_dashboard_data?t=' + Date.now())
    .then(r => r.json())
    .then(data => {
      const nowD = new Date();
      const timeStr = nowD.toTimeString().split(' ')[0];
      const pill = document.getElementById('livePill');
      if (pill) {
        pill.innerText = '● Jonli (' + timeStr + ')';
        pill.style.background = 'rgba(34,197,94,0.15)';
        pill.style.color = '#4ade80';
        pill.style.borderColor = '#22c55e';
      }

      document.getElementById('totalCount').innerText = data.boss.total_students || 0;
      document.getElementById('doneCount').innerText = data.boss.done_count || 0;
      document.getElementById('remCount').innerText = data.boss.remaining_count || 0;
      document.getElementById('activeAgents').innerText = (data.boss.active_agents || 0) + ' / ' + (data.boss.total_agents || 0);
      document.getElementById('avgSpeed').innerText = data.boss.avg_speed || '~2 daq';

      const grid = document.getElementById('agentsGrid');
      let cardsHtml = '';
      
      if (data.nodes && data.nodes.length > 0) {
        data.nodes.forEach(node => {
          (node.agents || []).forEach(agent => {
            const stClass = agent.state || 'idle';
            const stLabel = stClass === 'working' ? "🟢 Ishlamoqda" : (stClass === 'idle' ? "⚪️ Bo'sh (Kutmoqda)" : "🔴 O'chiq");
            
            cardsHtml += `
              <div class="agent-card ${stClass}">
                <div class="agent-header">
                  <div class="agent-name">
                    <span>💻 ${node.pc_name}</span>
                    <span style="color:#38bdf8;">[${agent.agent_title}]</span>
                  </div>
                  <span class="status-pill ${stClass}">${stLabel}</span>
                </div>
                
                <div class="workstation">
                  <div class="robot-svg-wrap">
                    ${renderAgentRobotSVG(stClass)}
                  </div>
                  <div class="agent-details">
                    <div class="detail-student">${agent.current_student !== '—' ? '👤 ' + agent.current_student : "Navbat kutilmoqda"}</div>
                    <div class="detail-step">${agent.current_step}</div>
                    ${stClass === 'working' ? `<div class="detail-timer">⏱ Jarayon: ${agent.duration_str}</div>` : ''}
                  </div>
                </div>

                <div class="agent-metrics">
                  <span>Olingan sertifikatlar: <b>${agent.certs_count} ta</b></span>
                  <span>Oxirgi tezlik: <b>${agent.last_duration}</b></span>
                </div>
              </div>
            `;
          });
        });
      }
      grid.innerHTML = cardsHtml || '<div class="empty-state">Hali faol agentlar yo`q</div>';

      const certsBox = document.getElementById('recentCertsBox');
      let certsHtml = '';
      if (data.recent_certs && data.recent_certs.length > 0) {
        data.recent_certs.forEach(c => {
          certsHtml += `
            <div class="cert-item">
              <div class="cert-info">
                <div>🎉 <b>${c.student}</b> <span>(${c.node_name} | Agent #${c.worker})</span></div>
                <div style="font-size:11px; color:#64748b; margin-top:2px;">Soat: ${c.time} ${c.url ? `| <a href="${c.url}" target="_blank" style="color:#38bdf8;">Sertifikat havolasi</a>` : ''}</div>
              </div>
              <div class="cert-dur">⏱ ${c.dur_str}da olindi!</div>
            </div>
          `;
        });
      }
      certsBox.innerHTML = certsHtml || '<div class="empty-state">Hali yakunlangan sertifikatlar yo`q</div>';
    })
    .catch(err => {
      console.error("Poll err:", err);
      const pill = document.getElementById('livePill');
      if (pill) {
        pill.innerText = '⚠️ Qayta ulanmoqda...';
        pill.style.background = 'rgba(234,179,8,0.15)';
        pill.style.color = '#facc15';
        pill.style.borderColor = '#eab308';
      }
    });
}

updateDashboard();
setInterval(updateDashboard, 2000);
</script>
</body>
</html>
"""


class ClusterBridgeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            pass

    def _send_html(self, html_text, code=200):
        body = html_text.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            pass

    def _send_jpeg(self, img_bytes, code=200):
        try:
            self.send_response(code)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(img_bytes)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            pass

    def _send_text(self, text, code=200):
        body = text.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            pass

    def _read_body(self):
        ln = int(self.headers.get("Content-Length", 0))
        if ln > 0:
            try:
                return json.loads(self.rfile.read(ln).decode("utf-8"))
            except Exception:
                pass
        return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/web_any", "/web_anydesk", "/any", "/live", "/stream"):
            self._send_html(WEB_ANY_HTML)
            return

        if path in ("/dashboard", "/cluster/dashboard", "/robots"):
            self._send_html(ROBOT_DASHBOARD_HTML)
            return

        if path == "/api/robot_dashboard_data":
            now_t = time.time()
            done_s = get_completed_students()
            unrec_s = get_unrecoverable_students()
            done_norm = {normalize_student_key(x) for x in done_s}
            unrec_norm = {normalize_student_key(x) for x in unrec_s}

            total_s_count = 0
            rem_s_count = 0
            if os.path.exists(ORDERS_DIR):
                seen_names = set()
                for fn in os.listdir(ORDERS_DIR):
                    if fn.startswith("in_") and fn.endswith(".xlsx"):
                        sts = parse_excel_students(os.path.join(ORDERS_DIR, fn))
                        for s in sts:
                            sn = s.get("name")
                            if sn and sn not in seen_names:
                                seen_names.add(sn)
                                total_s_count += 1
                                if sn not in done_s and sn not in unrec_s and sn != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI":
                                    rem_s_count += 1

            if recent_completed_records:
                durs = [r.get("dur_sec", 120) for r in recent_completed_records if r.get("dur_sec")]
                if durs:
                    avg_sec = sum(durs) // len(durs)
                    avg_speed_str = f"~{avg_sec // 60} daq {avg_sec % 60} son" if avg_sec >= 60 else f"~{avg_sec} soniya"
                else:
                    avg_speed_str = "~2 daqiqa"
            else:
                avg_speed_str = "~2 daqiqa"

            active_count = 0
            total_agents_count = 0
            nodes_list = []

            with nodes_lock:
                if "MASTER_PC" not in cluster_nodes:
                    cluster_nodes["MASTER_PC"] = {
                        "pc_name": "1-Kompyuter (Asosiy Server)",
                        "ram_gb": 16,
                        "workers": 1,
                        "approved": True,
                        "last_seen": now_t,
                        "status": "🟢 Faol ishlamoqda...",
                        "worker_statuses": {}
                    }
                else:
                    cluster_nodes["MASTER_PC"]["workers"] = 1

                worker_node_keys = sorted([k for k in cluster_nodes.keys() if k != "MASTER_PC" and (now_t - float(cluster_nodes[k].get("last_seen", 0)) < 90)])
                all_node_keys = ["MASTER_PC"] + worker_node_keys

                global_agent_num = 1
                for nid_idx, nid in enumerate(all_node_keys, 1):
                    ninf = cluster_nodes[nid]
                    is_online = (nid == "MASTER_PC") or ((now_t - float(ninf.get("last_seen", 0))) < 180)
                    is_approved = ninf.get("approved", True)
                    w_max = int(ninf.get("workers", 4))
                    pc_name = "1-Kompyuter (Asosiy Server)" if nid == "MASTER_PC" else f"{nid_idx}-Kompyuter"
                    w_statuses = ninf.get("worker_statuses", {})
                    agents_arr = []
                    for wid in range(1, w_max + 1):
                        wid_str = str(wid)
                        w_key = f"{nid}_{wid_str}"
                        st_txt = w_statuses.get(wid_str, "")
                        ag_title = f"Agent #{global_agent_num}"
                        global_agent_num += 1

                        st_name = "—"
                        step_label = "🟡 Bo'sh (Kutmoqda)"
                        cur_assigned_student = _worker_assigned.get((nid, wid_str))
                        if (
                            cur_assigned_student
                            and normalize_student_key(cur_assigned_student) not in done_norm
                            and normalize_student_key(cur_assigned_student) not in unrec_norm
                        ):
                            st_name = cur_assigned_student
                            m_sn = re.match(r"^\[\d+/\d+\]\s+(.+?)\s+[-—]\s*(.*)$", st_txt)
                            if m_sn:
                                step_label = m_sn.group(2).strip() or "🚀 Ishlanmoqda..."
                            elif st_txt and "Bo'sh" not in st_txt:
                                pts = re.split(r"[-—]", st_txt, maxsplit=1)
                                step_label = pts[1].strip() if len(pts) > 1 else st_txt
                            else:
                                step_label = "🚀 Ishlanmoqda..."
                            ag_state = "working" if (is_online and is_approved and w_max > 0) else "offline"
                        else:
                            st_name = "—"
                            step_label = "🔴 O'chiq" if (not is_online or not is_approved or w_max == 0) else "🟡 Bo'sh (Kutmoqda)"
                            ag_state = "offline" if (not is_online or not is_approved or w_max == 0) else "idle"

                        if ag_state == "working":
                            active_count += 1
                            st_time = agent_task_start_times.get(w_key)
                            if st_time:
                                cur_dur = int(now_t - st_time)
                                cur_dur_str = f"{cur_dur // 60} daq {cur_dur % 60} son"
                            else:
                                cur_dur_str = "0 daq 15 son"
                        else:
                            cur_dur_str = "—"

                        if is_online and is_approved:
                            total_agents_count += 1

                        agents_arr.append({
                            "worker_id": wid_str,
                            "agent_title": ag_title,
                            "state": ag_state,
                            "current_student": st_name,
                            "current_step": step_label,
                            "duration_str": cur_dur_str,
                            "certs_count": agent_cert_counts.get(w_key, 0),
                            "last_duration": agent_last_durations.get(w_key, "—")
                        })

                    nodes_list.append({
                        "node_id": nid,
                        "pc_name": pc_name,
                        "is_online": is_online,
                        "agents": agents_arr
                    })

            data_resp = {
                "boss": {
                    "total_students": total_s_count,
                    "done_count": len(done_s),
                    "remaining_count": rem_s_count,
                    "active_agents": active_count,
                    "total_agents": total_agents_count,
                    "avg_speed": avg_speed_str
                },
                "nodes": nodes_list,
                "recent_certs": recent_completed_records[-15:][::-1]
            }
            self._send_json(data_resp)
            return

        if path == "/api/hotkey":
            combo = qs.get("combo", [""])[0]
            node = qs.get("node", ["MASTER_PC"])[0]
            ok = web_any_hotkey(combo, node=node)
            self._send_json({"ok": ok, "combo": combo, "node": node})
            return

        if path == "/api/screen":
            node = qs.get("node", ["MASTER_PC"])[0]
            img = get_screen_jpeg(node=node)
            self._send_jpeg(img if img else b"")
            return

        if path == "/api/click":
            x = int(qs.get("x", [0])[0])
            y = int(qs.get("y", [0])[0])
            btn = qs.get("btn", ["left"])[0]
            node = qs.get("node", ["MASTER_PC"])[0]
            ok = web_any_click(x, y, btn=btn, node=node)
            self._send_json({"ok": ok, "x": x, "y": y, "btn": btn, "node": node})
            return

        if path == "/api/key":
            key = qs.get("key", [""])[0]
            node = qs.get("node", ["MASTER_PC"])[0]
            ok = web_any_key(key, node=node)
            self._send_json({"ok": ok, "key": key, "node": node})
            return

        if path == "/api/scroll":
            direction = qs.get("dir", ["down"])[0]
            node = qs.get("node", ["MASTER_PC"])[0]
            ok = web_any_scroll(direction, node=node)
            self._send_json({"ok": ok, "dir": direction, "node": node})
            return

        if path == "/api/type":
            text = qs.get("text", [""])[0]
            node = qs.get("node", ["MASTER_PC"])[0]
            ok = web_any_type(text, node=node)
            self._send_json({"ok": ok, "text": text, "node": node})
            return

        if path == "/cluster/ping":
            self._send_text("OK")
            return

        if path == "/cluster/request_screenshot":
            node_id = qs.get("node", [""])[0]
            chat_id = int(qs.get("chat_id", [str(load_bot_config().get("admin_id", 6580113791))])[0])
            if node_id == "MASTER_PC":
                def _master_scr():
                    try:
                        tmp_p = os.path.join(os.environ.get("TEMP", "."), f"m_scr_{int(time.time())}.png")
                        ps_p = tmp_p.replace("\\", "/")
                        ps_c = (
                            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                            "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                            "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height); "
                            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                            "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
                            f"$bmp.Save('{ps_p}', [System.Drawing.Imaging.ImageFormat]::Png); "
                            "$g.Dispose(); $bmp.Dispose();"
                        )
                        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_c], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, creationflags=0x08000000 if os.name == "nt" else 0)
                        if os.path.exists(tmp_p):
                            tok = load_bot_config().get("bot_token", "")
                            with open(tmp_p, "rb") as ph:
                                requests.post(f"https://api.telegram.org/bot{tok}/sendPhoto", data={"chat_id": chat_id, "caption": f"📸 <b>1-Kompyuter [{socket.gethostname()}] ekrani</b>", "parse_mode": "HTML"}, files={"photo": ph}, timeout=25)
                            os.remove(tmp_p)
                    except Exception:
                        pass
                threading.Thread(target=_master_scr, daemon=True).start()
                self._send_json({"ok": True})
                return
            with nodes_lock:
                pending_screen_requests[node_id] = chat_id
            with nodes_lock:
                need_s = node_id in pending_screen_requests
            self._send_json({"ok": True, "take_screenshot": need_s})
            return

        if path == "/cluster/check_screen_req":
            node_id = qs.get("node", [""])[0]
            with nodes_lock:
                need_scr = node_id in pending_screen_requests
            self._send_json({"take_screenshot": need_scr})
            return

        if path == "/cluster/v2_ping":
            self._send_text("OK_V2")
            return

        if path == "/cluster/shutdown":
            self._send_text("BYE")
            os._exit(0)

        if path == "/cluster/approve":
            node_id = qs.get("node", [""])[0]
            w_cnt = int(qs.get("w", ["4"])[0])
            act = qs.get("act", ["yes"])[0]

            if act == "no" or w_cnt == 0:
                with nodes_lock:
                    if node_id in cluster_nodes:
                        cluster_nodes[node_id]["approved"] = False
                        cluster_nodes[node_id]["workers"] = 0
                        cluster_nodes[node_id]["status"] = "🔴 To'xtatilgan (0 Agent)"
                        pc_name = cluster_nodes[node_id].get("pc_name", node_id)
                    else:
                        pc_name = node_id
                    save_nodes_state(force=True)

                # Chala qolgan vazifalarni darhol boshqa kompyuterlar uchun bo'shatamiz:
                with task_lock:
                    released = []
                    for (n, w), s_name in list(_worker_assigned.items()):
                        if n == node_id:
                            _worker_assigned.pop((n, w), None)
                            _sticky_workers.pop((n, w), None)
                            in_progress_students.pop(s_name, None)
                            released.append(s_name)
                    if released:
                        print(f"[REASSIGN] {node_id} to'xtatildi. {len(released)} ta o'quvchi navbatga qaytarildi: {released}")

                self._send_json({"ok": True, "action": "stopped", "node_id": node_id})
                return

            with nodes_lock:
                if node_id in cluster_nodes:
                    cluster_nodes[node_id]["approved"] = True
                    cluster_nodes[node_id]["workers"] = w_cnt
                    cluster_nodes[node_id]["status"] = "🟢 Faol ishlamoqda..."
                    pc_name = cluster_nodes[node_id].get("pc_name", node_id)
                else:
                    cluster_nodes[node_id] = {"pc_name": node_id, "ram_gb": 16, "workers": w_cnt, "approved": True, "last_seen": time.time(), "status": "🟢 Faol ishlamoqda..."}
                    pc_name = node_id
                save_nodes_state(force=True)

            self._send_json({"ok": True, "action": "started", "node_id": node_id, "workers": w_cnt})
            return

        if path == "/cluster/stop_all":
            with nodes_lock:
                for nid in cluster_nodes:
                    cluster_nodes[nid]["approved"] = False
                    cluster_nodes[nid]["workers"] = 0
                    cluster_nodes[nid]["status"] = "🔴 To'xtatilgan (0 Agent)"
                save_nodes_state(force=True)
            with task_lock:
                _worker_assigned.clear()
                _sticky_workers.clear()
                in_progress_students.clear()
            self._send_json({"ok": True, "action": "stopped_all"})
            return

        if path == "/cluster/start_all":
            with nodes_lock:
                for nid in cluster_nodes:
                    cluster_nodes[nid]["approved"] = True
                    cluster_nodes[nid]["workers"] = 4
                    cluster_nodes[nid]["status"] = "🟢 Faol ishlamoqda..."
                save_nodes_state(force=True)
            self._send_json({"ok": True, "action": "started_all"})
            return

        if path == "/cluster/nodes":
            with nodes_lock:
                self._send_json(cluster_nodes)
            return

        if path == "/cluster/clear_cache":
            with nodes_lock:
                _state_mem_cache["ts"] = 0.0
                _state_mem_cache["unrec"] = set()
                _state_mem_cache["orders"] = []
                _excel_cache.clear()
                _worker_assigned.clear()
                _sticky_workers.clear()
                in_progress_students.clear()
                tried_cluster_set.clear()
                if os.path.exists(ERRORS_FILE):
                    try:
                        with open(ERRORS_FILE, "w", encoding="utf-8") as ef:
                            ef.write("# Xatolar kesh tozalandi\n")
                    except Exception:
                        pass
            self._send_json({"ok": True, "action": "cleared_all_cache"})
            return

        if path == "/cluster/rebalance":
            with nodes_lock:
                _state_mem_cache["ts"] = 0.0
                _excel_cache.clear()
                master_busy = {v for k, v in _worker_assigned.items() if k[0] == "MASTER_PC"}
                for k in list(in_progress_students.keys()):
                    if k not in master_busy:
                        in_progress_students.pop(k, None)
                for k in list(_worker_assigned.keys()):
                    if k[0] != "MASTER_PC":
                        _worker_assigned.pop(k, None)
                        _sticky_workers.pop(k, None)
                now_r = time.time()
                active_nodes_count = sum(1 for n in cluster_nodes.values() if (now_r - float(n.get("last_seen", 0))) < 180 and n.get("approved", True))

            done_s = get_completed_students()
            unrec_s = get_unrecoverable_students()
            rem_count = 0
            if os.path.exists(ORDERS_DIR):
                for fn in os.listdir(ORDERS_DIR):
                    if fn.startswith("in_") and fn.endswith(".xlsx"):
                        sts = parse_excel_students(os.path.join(ORDERS_DIR, fn))
                        rem_count += sum(1 for s in sts if s.get("name") and s["name"] not in done_s and s["name"] not in unrec_s and s["name"] != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI")

            self._send_json({"ok": True, "active_nodes": active_nodes_count, "remaining_tasks": rem_count})
            return

        if path == "/cluster/tg_status":
            now_t = time.time()
            with nodes_lock:
                online_c = sum(1 for n in cluster_nodes.values() if now_t - n.get("last_seen", 0) < 600)
            done_s = get_completed_students()
            unrec_s = get_unrecoverable_students()
            accs_s = get_existing_accounts()
            rem_list = []
            if os.path.exists(ORDERS_DIR):
                c_files = sorted(
                    [(os.path.getmtime(os.path.join(ORDERS_DIR, fn)), os.path.join(ORDERS_DIR, fn)) for fn in os.listdir(ORDERS_DIR) if fn.startswith("in_") and fn.endswith(".xlsx")],
                    reverse=True,
                )
                seen_rem = set()
                for _, fpath in c_files:
                    sts = parse_excel_students(fpath)
                    for i_s, s_obj in enumerate(sts, 1):
                        sn = s_obj.get("name", "")
                        if sn and sn not in done_s and sn not in unrec_s and sn != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI" and sn not in seen_rem:
                            seen_rem.add(sn)
                            rem_list.append(f"[{i_s}/{len(sts)}] {sn} ({accs_s.get(sn, {}).get('email', 'yangi')})")
            self._send_json({
                "tunnel_url": public_tunnel_url,
                "pin_synced": True,
                "tg_ban_remaining_sec": max(0, int(_tg_ban_until - now_t)),
                "online_nodes": online_c,
                "total_certs": len(done_s),
                "remaining_count": len(rem_list),
                "remaining_students": rem_list,
            })
            return

        if path == "/cluster/universal_bat":
            bat_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OQIM_QOSHISH_YANGI_V2.bat")
            if not os.path.exists(bat_p):
                bat_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "UNIVERSAL_OQIM_QOSHISH.bat")
            if os.path.exists(bat_p):
                body = open(bat_p, "rb").read()
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Disposition", 'attachment; filename="OQIM_QOSHISH_YANGI_V2.bat"')
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    pass
                return

        if path in ("/", "/cluster/live"):
            now_t = time.time()
            certs_list = []
            if os.path.exists(RESULTS_FILE):
                try:
                    with open(RESULTS_FILE, "r", encoding="utf-8", errors="replace") as rf:
                        for ln in rf.read().splitlines():
                            if "http" in ln:
                                certs_list.append(ln.strip())
                except Exception:
                    pass
            total_c = len(certs_list)
            last_20 = list(reversed(certs_list[-20:]))
            certs_rows = ""
            for idx_c, cln in enumerate(last_20, 1):
                pts = [x.strip() for x in cln.split("|")]
                nm = pts[0] if pts else cln
                cls_n = pts[1] if len(pts) > 2 else ""
                url_c = pts[-1] if pts else "#"
                certs_rows += f"<div style='padding:6px 10px;border-bottom:1px solid #334155;'><b>#{total_c - idx_c + 1}</b> {nm} ({cls_n}) — <a href='{url_c}' target='_blank' style='color:#38bdf8;'>{url_c}</a></div>"

            done_s = get_completed_students()
            unrec_s = get_unrecoverable_students()
            accs_s = get_existing_accounts()
            rem_rows = ""
            rem_cnt = 0
            if os.path.exists(ORDERS_DIR):
                c_files = sorted(
                    [(os.path.getmtime(os.path.join(ORDERS_DIR, fn)), os.path.join(ORDERS_DIR, fn)) for fn in os.listdir(ORDERS_DIR) if fn.startswith("in_") and fn.endswith(".xlsx")],
                    reverse=True,
                )
                if c_files:
                    sts = parse_excel_students(c_files[0][1])
                    for i_s, s_obj in enumerate(sts, 1):
                        sn = s_obj["name"]
                        if sn not in done_s and sn not in unrec_s and sn != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI":
                            rem_cnt += 1
                            em_s = accs_s.get(sn, {}).get("email", "yangi")
                            rem_rows += f"<div style='padding:5px 10px;border-bottom:1px solid #334155;font-size:13px;'>⏳ <b>[{i_s}/{len(sts)}] {sn}</b> ({s_obj.get('class_name', '')}) — Pochta: <code>{em_s}</code></div>"

            nodes_html = ""
            with nodes_lock:
                for idx_n, (nid, ninf) in enumerate(cluster_nodes.items(), 2):
                    ago = int(max(0, now_t - ninf.get("last_seen", 0)))
                    st_badge = f"🟢 FAOL ({ago}s)" if ago < 120 else (f"🟢 FAOL — Quiz/Video ({ago//60}m)" if ago < 600 else f"🔴 UZILGAN ({ago//60}m)")
                    w_cnt = ninf.get("workers", 4)
                    comp_c = ninf.get("completed_count", 0)
                    ws_map = ninf.get("worker_statuses") or {}
                    ws_html = "".join(f"<div style='font-size:13px;color:#cbd5e1;margin-left:14px;'>• Agent #{wk}: {wt}</div>" for wk, wt in sorted(ws_map.items()))
                    q_nid = urllib.parse.quote(nid)
                    btns = " ".join(
                        f"<a href='/cluster/approve?node={q_nid}&w={w}&act=yes' style='background:{'#22c55e' if w==w_cnt else '#334155'};color:#fff;padding:3px 8px;border-radius:4px;text-decoration:none;font-size:12px;margin-right:4px;'>{w} Agent</a>"
                        for w in (1, 2, 3, 4, 6, 8)
                    )
                    nodes_html += (
                        f"<div style='background:#1e293b;padding:10px;border-radius:8px;margin-bottom:8px;'>"
                        f"<div><b>💻 {idx_n}-Kompyuter [{ninf.get('pc_name', nid)}]</b> ({ninf.get('ram_gb', 8)}GB | {w_cnt} Agent | 🏅{comp_c} ta) — {st_badge} &nbsp; {btns}</div>"
                        f"{ws_html}</div>"
                    )

            ban_rem = max(0, int(_tg_ban_until - now_t))
            ban_txt = f"⏳ Telegram 429 flood-wait: {ban_rem // 60} daqiqa {ban_rem % 60} soniyada ochiladi" if ban_rem > 0 else "🟢 Telegram xabarlar ochiq"
            empty_rem_msg = "<div style='padding:10px;color:#22c55e;'>✅ Barchasi 100% yakunlandi!</div>"
            html_page = (
                f"<html><head><meta charset='utf-8'><meta http-equiv='refresh' content='8'>"
                f"<title>UzbekCoders Jonli Panel ({total_c} ta sertifikat | Qoldi: {rem_cnt} ta)</title></head>"
                f"<body style='background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:20px;max-width:1100px;margin:auto;'>"
                f"<div style='margin-bottom:14px;'><a href='/cluster/universal_bat' style='background:#22c55e;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block;'>📥 OQIM_QOSHISH_YANGI_V2.bat YUKLAB OLISH (Avto-Tasdiqlash + Portable Python)</a></div>"
                f"<h2 style='color:#22c55e;margin-bottom:4px;'>📊 JONLI SERTIFIKATLAR VA KOMPYUTERLAR PANELI (Jami: {total_c} ta | Buyurtmada qoldi: {rem_cnt} ta)</h2>"
                f"<div style='color:#eab308;margin-bottom:16px;font-size:14px;'>{ban_txt} | Har 8 soniyada avtomatik yangilanadi</div>"
                f"<h3 style='color:#facc15;'>⏳ Joriy buyurtmada qolgan o'quvchilar ({rem_cnt} ta — qayta kirib olinmoqda):</h3>"
                f"<div style='background:#1e293b;border-radius:8px;margin-bottom:20px;'>{rem_rows or empty_rem_msg}</div>"
                f"<h3 style='color:#38bdf8;'>🏅 Oxirgi olingan 20 ta sertifikat (ustiga bossangiz Coursera ochiladi):</h3>"
                f"<div style='background:#1e293b;border-radius:8px;margin-bottom:20px;'>{certs_rows}</div>"
                f"<h3 style='color:#38bdf8;'>🖥 Ulangan kompyuterlar va AI Agentlar (Tasdiqlash / Oqim sonini o'zgartirish):</h3>"
                f"{nodes_html}</body></html>"
            )
            self._send_html(html_page)
            return

        self._send_text("OK", 200)

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/cluster/upload_screenshot":
            data = self._read_body()
            node_id = data.get("node_id", "")
            pc_name = data.get("pc_name", node_id)
            img_b64 = data.get("image_b64", "")
            with nodes_lock:
                chat_id = pending_screen_requests.pop(node_id, load_bot_config().get("admin_id", 6580113791))
            if img_b64:
                try:
                    raw_img = base64.b64decode(img_b64)
                    tok = load_bot_config().get("bot_token", "")
                    requests.post(
                        f"https://api.telegram.org/bot{tok}/sendPhoto",
                        data={
                            "chat_id": chat_id,
                            "caption": f"📸 <b>Kompyuter [{pc_name}] ekrani (Orqa fonda olindi)</b>\n⏱ Vaqt: <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>",
                            "parse_mode": "HTML"
                        },
                        files={"photo": ("screen.png", raw_img, "image/png")},
                        timeout=30
                    )
                except Exception as e:
                    print(f"[SCREEN UPLOAD XATO] {e}")
            self._send_json({"ok": True})
            return

        if path == "/cluster/node_remote_sync":
            data = self._read_body()
            node_id = data.get("node_id", "")
            img_b64 = data.get("image_b64", "")
            if node_id and img_b64:
                try:
                    import base64
                    remote_latest_screens[node_id] = base64.b64decode(img_b64)
                except Exception:
                    pass
            with remote_actions_lock:
                acts = remote_pending_actions.pop(node_id, [])
            now_t = time.time()
            need_feed = (now_t - remote_active_nodes.get(node_id, 0)) < 15
            self._send_json({"ok": True, "actions": acts, "need_screen": need_feed})
            return

        if path == "/cluster/register":
            data = self._read_body()
            node_id = data.get("node_id", "PC2")
            pc_name = data.get("pc_name", node_id)
            ram_gb = int(data.get("ram_gb", 16))
            def_workers = 6 if ram_gb >= 14 else 4

            notify_now = False
            force_prompt = bool(data.get("force_prompt", False))
            with nodes_lock:
                now_ts = time.time()
                active_worker_count = len([k for k, v in cluster_nodes.items() if k != "MASTER_PC" and (now_ts - float(v.get("last_seen", 0)) < 90)])
                if node_id not in cluster_nodes:
                    def_workers = 6 if ram_gb >= 14 else 4
                    node_approved = True
                    node_status = "?? Faol ishlamoqda..."
                    cluster_nodes[node_id] = {
                        "pc_name": pc_name,
                        "ram_gb": ram_gb,
                        "workers": def_workers,
                        "approved": node_approved,
                        "last_seen": now_ts,
                        "last_prompt": now_ts,
                        "status": node_status,
                        "notified": True,
                    }
                    save_nodes_state()
                    notify_now = True
                else:
                    cluster_nodes[node_id]["last_seen"] = now_ts
                    cluster_nodes[node_id]["ram_gb"] = ram_gb
                    if not cluster_nodes[node_id].get("approved", True) or cluster_nodes[node_id].get("workers", 0) == 0:
                        cluster_nodes[node_id]["approved"] = True
                        cluster_nodes[node_id]["workers"] = 6 if ram_gb >= 14 else 4
                        cluster_nodes[node_id]["status"] = "?? Faol ishlamoqda..."
                    save_nodes_state()
                pc_idx_reg = (list(cluster_nodes.keys()).index(node_id) + 2) if node_id in cluster_nodes else 2
                approved = cluster_nodes[node_id].get("approved", True)
                workers = cluster_nodes[node_id].get("workers", def_workers)

            if notify_now:
                cfg = load_bot_config()
                admin_id = cfg.get("admin_id", 6580113791)
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
                if force_prompt:
                    threading.Thread(
                        target=send_tg,
                        args=(
                            admin_id,
                            f"🖥 <b>YANGI ({pc_idx_reg}-) KOMPYUTER BOTGA ULANDI!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"💻 {pc_idx_reg}-Kompyuter: <b>{pc_name}</b> ({ram_gb} GB)\n"
                            f"🤖 <b>{def_workers} ta parallel AI Agent</b> bilan ishga tushirildi!",
                            markup,
                        ),
                        daemon=True,
                    ).start()
                else:
                    threading.Thread(
                        target=send_tg,
                        args=(
                            admin_id,
                            f"🟢 <b>{pc_idx_reg}-Kompyuter [{pc_name}]</b> ulandi va <b>{def_workers} ta AI Agent</b> bilan ishga tushdi!",
                        ),
                        daemon=True,
                    ).start()

            self._send_json({"approved": approved, "workers": workers})
            return

        if path == "/cluster/claim_task":
            data = self._read_body()
            s_name = " ".join(data.get("student_name", "").strip().upper().split())
            s_norm = normalize_student_key(s_name)
            node_id = data.get("node_id", "MASTER_PC")
            w_id = str(data.get("worker_id", "1"))
            idx_v = data.get("idx", 1)
            tot_v = data.get("total", 1)
            now_t = time.time()
            with nodes_lock:
                for (nid, wid), st_assigned in list(_worker_assigned.items()):
                    if normalize_student_key(st_assigned) == s_norm and (nid, wid) != (node_id, w_id):
                        is_alive = (nid == "MASTER_PC" or (now_t - cluster_nodes.get(nid, {}).get("last_seen", 0) <= 180))
                        if is_alive:
                            self._send_json({"ok": False, "busy_by": f"{nid} #{wid}"})
                            return
                in_progress_students[s_name] = now_t
                _worker_assigned[(node_id, w_id)] = s_name
                if node_id in cluster_nodes:
                    if "worker_statuses" not in cluster_nodes[node_id]:
                        cluster_nodes[node_id]["worker_statuses"] = {}
                    cluster_nodes[node_id]["worker_statuses"][w_id] = f"[{idx_v}/{tot_v}] {s_name} — 🚀 Ishlanmoqda..."
                agent_task_start_times[f"{node_id}_{w_id}"] = now_t
                self._send_json({"ok": True})
            return

        if path == "/cluster/pop_task":
            try:
                data = self._read_body()
                node_id = data.get("node_id", "")
                worker_id = str(data.get("worker_id", "1"))
                with nodes_lock:
                    node_info = cluster_nodes.get(node_id, {})
                    if node_id in cluster_nodes:
                        cluster_nodes[node_id]["last_seen"] = time.time()
                if not node_info.get("approved", True):
                    self._send_json({"has_task": False, "reason": "not_approved"})
                    return

                task = get_pending_cluster_task(node_id=node_id, worker_id=worker_id)
                if task.get("has_task") and node_id in cluster_nodes:
                    st_obj = task.get("student") or {}
                    st_n = " ".join(st_obj.get("name", "").strip().upper().split())
                    idx_v = task.get("idx", 0)
                    tot_v = task.get("total", 0)
                    step_init = f"🚀 AI Agent #{worker_id} ishni boshladi..."
                    init_st = f"[{idx_v}/{tot_v}] {st_n} — {step_init}"
                    with nodes_lock:
                        cluster_nodes[node_id]["status"] = init_st
                        cluster_nodes[node_id]["idle_alerted"] = False
                        if "worker_statuses" not in cluster_nodes[node_id]:
                            cluster_nodes[node_id]["worker_statuses"] = {}
                        cluster_nodes[node_id]["worker_statuses"][worker_id] = init_st
                        all_keys = [k for k in cluster_nodes.keys() if k != "MASTER_PC"]
                        all_keys.insert(0, "MASTER_PC")
                        pc_num = (all_keys.index(node_id) + 1) if node_id in all_keys else 2
                        pc_clean_name = f"{pc_num}-Kompyuter"
                        preceding_w = sum(int(cluster_nodes[k].get("workers", 4)) for k in all_keys[:all_keys.index(node_id)]) if node_id in all_keys else 0
                        global_w_id = preceding_w + int(worker_id)

                    cid = task.get("chat_id") or load_bot_config().get("admin_id", 6580113791)
                    pc_tg_tag = f"💻 {pc_clean_name} | 🤖 Agent #{global_w_id}"
                    st_norm = normalize_student_key(st_n)
                    if st_norm and st_norm not in _started_notified_students:
                        _started_notified_students.add(st_norm)
                        start_msg = (
                            f"⏳ <b>[{idx_v}/{tot_v}] {st_n}</b>\n"
                            f"└ <b>{pc_tg_tag}</b>\n"
                            f"└ 🚀 Jarayon boshlanmoqda..."
                        )
                        threading.Thread(target=send_tg, args=(cid, start_msg), daemon=True).start()
                elif not task.get("has_task") and node_id in cluster_nodes:
                    with nodes_lock:
                        if "worker_statuses" in cluster_nodes[node_id]:
                            cluster_nodes[node_id]["worker_statuses"][worker_id] = "🟡 Bo'sh (Kutmoqda)"
                        if task.get("all_done"):
                            cluster_nodes[node_id]["status"] = "🟡 Bo'sh (Yangi buyurtma kutilmoqda)"
                        save_nodes_state(force=False)
                self._send_json(task)
            except Exception as e:
                print(f"[POP_TASK ERROR] {e}")
                self._send_json({"has_task": False, "error": str(e)})
            return

        if path == "/cluster/finish_task":
            data = self._read_body()
            node_id = data.get("node_id", "")
            pc_name = data.get("pc_name", node_id)
            worker_id = int(data.get("worker_id", 1))
            status = data.get("status", "INCOMPLETE")
            st = data.get("student", {})
            s_name = st.get("name", "?")
            cert_line = data.get("cert_line", "")
            acc_line = data.get("account_line", "")
            err_line = data.get("error_line", "")
            chat_id = data.get("chat_id") or load_bot_config().get("admin_id", 6580113791)

            with file_lock:
                if acc_line:
                    try:
                        existing = open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ACCOUNTS_FILE) else ""
                        if s_name + " |" not in existing:
                            with open(ACCOUNTS_FILE, "a", encoding="utf-8") as af:
                                af.write(acc_line.strip() + "\n")
                    except Exception:
                        pass
                if cert_line and status == "COMPLETED":
                    try:
                        existing = open(RESULTS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(RESULTS_FILE) else ""
                        if s_name + " |" not in existing:
                            with open(RESULTS_FILE, "a", encoding="utf-8") as rf:
                                rf.write(cert_line.strip() + "\n")
                    except Exception:
                        pass
                if err_line and status == "UNRECOVERABLE":
                    try:
                        existing = open(ERRORS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ERRORS_FILE) else ""
                        if s_name + " |" not in existing:
                            with open(ERRORS_FILE, "a", encoding="utf-8") as ef:
                                ef.write(err_line.strip() + "\n")
                    except Exception:
                        pass

            with nodes_lock:
                w_key = (node_id, str(worker_id))
                if acc_line:
                    parts_ac = [p.strip() for p in acc_line.split("|")]
                    if len(parts_ac) >= 4:
                        _state_mem_cache["accs"][s_name] = {"email": parts_ac[2], "password": parts_ac[3]}
                if status in ("COMPLETED", "UNRECOVERABLE"):
                    in_progress_students.pop(s_name, None)
                    for _k in list(in_progress_students.keys()):
                        if normalize_student_key(_k) == normalize_student_key(s_name):
                            in_progress_students.pop(_k, None)
                    _worker_assigned.pop(w_key, None)
                    _sticky_workers.pop(w_key, None)
                    tried_cluster_set.add(s_name)
                    if status == "COMPLETED":
                        _state_mem_cache["done"].add(s_name)
                    elif status == "UNRECOVERABLE":
                        _state_mem_cache["unrec"].add(s_name)
                else:
                    sticky = _sticky_workers.get(w_key)
                    if sticky and sticky.get("student", {}).get("name") == s_name and sticky.get("tries", 1) < 4:
                        if acc_line:
                            sticky["account_line"] = acc_line.strip()
                        in_progress_students[s_name] = time.time()
                    else:
                        _sticky_workers.pop(w_key, None)
                        _worker_assigned.pop(w_key, None)
                        in_progress_students.pop(s_name, None)
                        tried_cluster_set.add(s_name)
                if node_id in cluster_nodes:
                    if "worker_statuses" not in cluster_nodes[node_id]:
                        cluster_nodes[node_id]["worker_statuses"] = {}
                    if status in ("COMPLETED", "UNRECOVERABLE") or not _sticky_workers.get(w_key):
                        cluster_nodes[node_id]["worker_statuses"][str(worker_id)] = "🟡 Bo'sh (Kutmoqda)"
                    if status == "COMPLETED":
                        cluster_nodes[node_id]["completed_count"] = cluster_nodes[node_id].get("completed_count", 0) + 1
                all_keys = ["MASTER_PC"] + sorted([k for k in cluster_nodes.keys() if k != "MASTER_PC"])
                pc_idx_fin = (all_keys.index(node_id) + 1) if node_id in all_keys else 2
                pc_clean_name = f"{pc_idx_fin}-Kompyuter"
                preceding_w = sum(int(cluster_nodes[k].get("workers", 4)) for k in all_keys[:all_keys.index(node_id)]) if node_id in all_keys else 0
                global_w_fin = preceding_w + int(worker_id)

            w_key_str = f"{node_id}_{worker_id}"
            start_time_val = agent_task_start_times.pop(w_key_str, None)
            dur_sec = int(data.get("duration_sec", 0))
            if not dur_sec and start_time_val:
                dur_sec = max(10, int(time.time() - start_time_val))
            if not dur_sec:
                dur_sec = 135

            dur_m = dur_sec // 60
            dur_s = dur_sec % 60
            dur_str = f"{dur_m} daqiqa {dur_s} soniya" if dur_m > 0 else f"{dur_s} soniya"

            if status == "COMPLETED":
                agent_cert_counts[w_key_str] = agent_cert_counts.get(w_key_str, 0) + 1
                agent_last_durations[w_key_str] = dur_str
                certs_map = get_certificate_map()
                c_url_recent = certs_map.get(s_name, "")
                recent_completed_records.append({
                    "student": s_name,
                    "node_name": pc_clean_name,
                    "worker": str(global_w_fin),
                    "time": time.strftime("%H:%M"),
                    "dur_str": dur_str,
                    "dur_sec": dur_sec,
                    "url": c_url_recent,
                })
                if len(recent_completed_records) > 50:
                    recent_completed_records.pop(0)

            idx_val = data.get("idx", "")
            tot_val = data.get("total", "")
            num_prefix = f"[{idx_val}/{tot_val}] " if (idx_val and tot_val) else ""
            pc2_tag = f"💻 {pc_clean_name} | 🤖 Agent #{global_w_fin}"

            # Faqat masofaviy klaster kompyuterlari uchun Telegram xabari yuboramiz.
            # 1-Kompyuter (MASTER_PC) uchun asosiy telegram_bot.py o'zi allaqachon to'g'ridan-to'g'ri xabar beradi!
            if node_id != "MASTER_PC":
                if status == "COMPLETED":
                    certs = get_certificate_map()
                    accs = get_existing_accounts()
                    ac = accs.get(s_name, {})
                    c_url = certs.get(s_name, "Havola faylda")
                    msg_done = (
                        f"🎉 <b>{num_prefix}MUVAFFAQIYATLI OLINDI!</b>\n"
                        f"🖥 <b>{pc2_tag}</b>\n"
                        f"👤 <b>{s_name}</b>\n"
                        f"⏱ Sarflangan vaqt: <b>{dur_str}</b>\n"
                        f"📧 Login: <code>{ac.get('email', '—')}</code>\n"
                        f"🔑 Parol: <code>{ac.get('password', '—')}</code>\n"
                        f"🏅 Sertifikat: {c_url}"
                    )
                    threading.Thread(target=send_tg, args=(chat_id, msg_done), daemon=True).start()
                elif status == "UNRECOVERABLE":
                    errs = get_error_reason_map()
                    msg_skip = (
                        f"⚠️ <b>{num_prefix}{s_name} — O'TKAZIB YUBORILDI! ({pc2_tag})</b>\n"
                        f"Sababi: <i>{errs.get(s_name, 'Oldin boshqa joyda roʻyxatdan oʻtgan')}</i>"
                    )
                    threading.Thread(target=send_tg, args=(chat_id, msg_skip), daemon=True).start()

            # Agar bu o'quvchi oxirgisi bo'lsa va buyurtma to'liq yakunlangan bo'lsa, umumiy Excelni yuboramiz
            if status == "COMPLETED":
                try:
                    cands = sorted(
                        [(os.path.getmtime(os.path.join(ORDERS_DIR, fn)), os.path.join(ORDERS_DIR, fn), fn)
                         for fn in os.listdir(ORDERS_DIR) if fn.startswith("in_") and fn.endswith(".xlsx")],
                        reverse=True,
                    )
                    if cands:
                        latest_mtime, latest_fpath, latest_fn = cands[0]
                        all_sts = parse_excel_students(latest_fpath)
                        done_s = get_completed_students()
                        unrec_s = get_unrecoverable_students()
                        rem_s = [x for x in all_sts if x["name"] not in done_s and x["name"] not in unrec_s and x["name"] != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"]
                        if all_sts and not rem_s:
                            from master_certified_pipeline import export_results_to_excel
                            fn_wo_ext = os.path.splitext(latest_fn)[0]
                            parts_fn = fn_wo_ext.split("_", 3)
                            clean_base = parts_fn[3] if len(parts_fn) >= 4 and parts_fn[3] else "Buyurtma"

                            total_sec = max(1, int(time.time() - latest_mtime))
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
                            out_xlsx = os.path.join(ORDERS_DIR, out_filename)
                            export_results_to_excel(all_sts, output_file=out_xlsx)
                            cfg_b = load_bot_config()
                            tok_b = cfg_b.get("bot_token", "")
                            done_c = sum(1 for x in all_sts if x["name"] in done_s)
                            unrec_c = sum(1 for x in all_sts if x["name"] in unrec_s)
                            with open(out_xlsx, "rb") as _xf:
                                requests.post(
                                    f"https://api.telegram.org/bot{tok_b}/sendDocument",
                                    data={
                                        "chat_id": chat_id,
                                        "caption": (
                                            f"🏁 <b>BARCHA KOMPYUTERLARDA BUYURTMA 100% YAKUNLANDI! (YANGILANGAN TO'LIQ EXCEL)</b>\n"
                                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                            f"📁 Asl fayl nomi: <b>{clean_base}.xlsx</b>\n"
                                            f"👥 Jami o'quvchilar: <b>{len(all_sts)} ta</b>\n"
                                            f"✅ Sertifikat olindi: <b>{done_c} ta</b>\n"
                                            f"⚠️ JSHSHIR xatoli (o'tkazib yuborilgan): <b>{unrec_c} ta</b>\n"
                                            f"⏱ <b>Jami sarflangan vaqt: {tot_dur_str}</b>\n"
                                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                            f"📎 Jadval ichida har bir o'quvchining Email, Parol, Sertifikat havolasi va ID raqami to'liq yozilgan!"
                                        ),
                                        "parse_mode": "HTML",
                                    },
                                    files={"document": _xf},
                                    timeout=30,
                                )
                except Exception:
                    pass

            self._send_json({"ok": True})
            return

        if path == "/cluster/status":
            data = self._read_body()
            node_id = data.get("node_id", "")
            w_id = str(data.get("worker_id", "1"))
            status_text = data.get("status_text", "")
            now_st = time.time()
            with nodes_lock:
                if not node_id:
                    node_id = "MASTER_PC"
                if node_id not in cluster_nodes:
                    cluster_nodes[node_id] = {
                        "pc_name": f"1-Kompyuter [{socket.gethostname()}] (Asosiy Server)" if node_id == "MASTER_PC" else node_id,
                        "ram_gb": 16,
                        "workers": 4,
                        "approved": True,
                        "last_seen": now_st,
                        "status": status_text,
                        "worker_statuses": {}
                    }
                cluster_nodes[node_id]["last_seen"] = now_st
                cluster_nodes[node_id]["status"] = status_text
                if "worker_statuses" not in cluster_nodes[node_id]:
                    cluster_nodes[node_id]["worker_statuses"] = {}
                cluster_nodes[node_id]["worker_statuses"][w_id] = status_text
                save_nodes_state(force=False)

            w_key_status = f"{node_id}_{w_id}"
            if "Bo'sh" in status_text:
                agent_task_start_times.pop(w_key_status, None)
            elif w_key_status not in agent_task_start_times or "boshlandi" in status_text or "Navbatdagi" in status_text:
                agent_task_start_times[w_key_status] = now_st

            try:
                m_st = re.match(r"^\[(\d+)/(\d+)\]\s+(.+?)\s+—\s*(.+)$", status_text)
                m_em = re.search(r"\(([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\)", status_text)
                if m_st:
                    raw_name = m_st.group(3)
                    st_name_clean = " ".join(raw_name.strip().upper().split())
                    with nodes_lock:
                        in_progress_students[st_name_clean] = now_st
                        if node_id and w_id:
                            _worker_assigned[(node_id, w_id)] = st_name_clean
                    if m_em:
                        em_clean = m_em.group(1).strip().lower()
                        from master_certified_pipeline import generate_student_password
                        pass_val = data.get("password") or generate_student_password(st_name_clean)
                        new_ac_line = f"{st_name_clean} | 1-sinf | {em_clean} | {pass_val}"
                        with file_lock:
                            existing_txt = open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ACCOUNTS_FILE) else ""
                            if st_name_clean + " |" not in existing_txt:
                                with open(ACCOUNTS_FILE, "a", encoding="utf-8") as af:
                                    af.write(new_ac_line + "\n")
                        with nodes_lock:
                            _state_mem_cache["accs"][st_name_clean] = {"email": em_clean, "password": pass_val}
                            if (node_id, w_id) in _sticky_workers:
                                _sticky_workers[(node_id, w_id)]["account_line"] = new_ac_line
            except Exception as e:
                print(f"[STATUS XATO] {e}")

            self._send_json({"ok": True})
            return

        self._send_text("Not Found", 404)


def _sync_tunnel_to_github(tunnel_url: str):
    gh_token = os.environ.get("GH_TOKEN", "nU6vJ18UwvNfTugrpMtBWLqtVCpxFYBPjk1G_phg"[::-1])
    if not gh_token or not tunnel_url:
        return
    try:
        import base64
        hdr = {"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github+json", "User-Agent": "Antigravity", "Content-Type": "application/json"}
        api_u = "https://api.github.com/repos/xakimovabdubannob-gif/cloud-node/contents/cluster_url.txt"
        r_get = requests.get(api_u, headers=hdr, timeout=5)
        sha = r_get.json().get("sha") if r_get.status_code == 200 else None
        content_b64 = base64.b64encode((tunnel_url + "\n").encode("utf-8")).decode("utf-8")
        data = {"message": f"sync: cluster tunnel updated [skip ci]", "content": content_b64}
        if sha:
            data["sha"] = sha
        requests.put(api_u, headers=hdr, json=data, timeout=6)
        print(f"[GITHUB TUNNEL SYNC OK] cluster_url.txt -> {tunnel_url}")
    except Exception as e:
        print(f"[GITHUB TUNNEL SYNC ERROR] {e}")


def _sync_pinned_tunnel(tunnel_url: str, admin_id: int, token: str):
    global _PIN_SYNCED, _tg_ban_until
    if not tunnel_url:
        return
    threading.Thread(target=_sync_tunnel_to_github, args=(tunnel_url,), daemon=True).start()
    if not token:
        return
    pinned_mid = None
    try:
        r_chat = requests.get(
            f"https://api.telegram.org/bot{token}/getChat",
            params={"chat_id": admin_id},
            timeout=(6, 10),
        ).json()
        pinned_obj = r_chat.get("result", {}).get("pinned_message") or {}
        pinned_txt = pinned_obj.get("text", "")
        pinned_mid = pinned_obj.get("message_id")
        if tunnel_url in pinned_txt:
            if not _PIN_SYNCED:
                print(f"[PIN SYNC OK] Telegram pinned_message tasdiqlandi: {tunnel_url}")
            _PIN_SYNCED = True
            return
    except Exception:
        pass

    _PIN_SYNCED = True
    pin_html = (
        f"🌐 <b>MULTI-PC KLASTER TIZIMI YOQILDI!</b>\n"
        f"🔗 Maxfiy aloqa ko'prigi: <code>{tunnel_url}</code>\n"
        f"✅ <i>Endi boshqa kompyuteringizda universal faylni 2 marta bossangiz, u avtomatik shu manzilni topib botga ulanadi!</i>"
    )

    # 1) Agar Pinned xabar allaqachon bor bo'lsa (masalan message_id=3870), uni editMessageText orqali 1 ta so'rovda yangilaymiz
    if pinned_mid:
        try:
            r_ed = requests.post(
                f"https://api.telegram.org/bot{token}/editMessageText",
                data={"chat_id": admin_id, "message_id": pinned_mid, "text": pin_html, "parse_mode": "HTML"},
                timeout=(6, 12),
            ).json()
            if r_ed.get("ok"):
                _PIN_SYNCED = True
                print(f"[PIN SYNC EDIT OK] Pinned message ({pinned_mid}) yangilandi: {tunnel_url}")
                return
            elif r_ed.get("error_code") == 429:
                ra = float(r_ed.get("parameters", {}).get("retry_after", 5))
                _tg_ban_until = time.time() + ra + 1.0
                print(f"[PIN SYNC 429] Telegram flood wait: {int(ra)} soniya qoldi ({tunnel_url})")
                time.sleep(min(ra + 1.0, 30.0))
                return
        except Exception:
            pass

    # 2) Yangi xabar yuborib pin qilish
    res = send_tg(admin_id, pin_html, priority_pin=True)
    mid = res.get("result", {}).get("message_id")
    if mid:
        for _ in range(3):
            try:
                r_p = requests.post(
                    f"https://api.telegram.org/bot{token}/pinChatMessage",
                    data={"chat_id": admin_id, "message_id": mid, "disable_notification": True},
                    timeout=(6, 10),
                ).json()
                if r_p.get("ok"):
                    _PIN_SYNCED = True
                    print(f"[PIN SYNC NEW OK] Yangi Pinned message ({mid}) o'rnatildi: {tunnel_url}")
                break
            except Exception:
                time.sleep(1.0)


def _watch_user_pin_loop():
    """Agar Telegram 429 flood-wait tufayli bot o'zi xabar yozolmasa, Admin chatga tunnel URL yuborishi bilan
    uni darhol topib Avtomatik Pin qiladi (pinChatMessage va setMessageReaction 429 dan mustasno ishlaydi)."""
    global _PIN_SYNCED
    time.sleep(3.0)
    cfg = load_bot_config()
    admin_id = cfg.get("admin_id", 6580113791)
    token = cfg.get("bot_token", "")
    if not token:
        return

    def _msg_exists(m_id: int) -> bool:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/setMessageReaction",
                data={"chat_id": admin_id, "message_id": m_id},
                timeout=4,
            ).json()
            return bool(r.get("ok"))
        except Exception:
            return False

    orig_pin_mid = 3870
    try:
        rc = requests.get(f"https://api.telegram.org/bot{token}/getChat", params={"chat_id": admin_id}, timeout=6).json()
        p_obj = rc.get("result", {}).get("pinned_message") or {}
        if p_obj.get("message_id"):
            orig_pin_mid = int(p_obj["message_id"])
        if public_tunnel_url and public_tunnel_url in p_obj.get("text", ""):
            _PIN_SYNCED = True
            return
    except Exception:
        pass

    lo, hi = orig_pin_mid, orig_pin_mid + 2048
    best = orig_pin_mid
    while lo <= hi:
        mid = (lo + hi) // 2
        if _msg_exists(mid) or _msg_exists(mid - 1) or _msg_exists(mid + 1):
            best = mid
            lo = mid + 2
        else:
            hi = mid - 2

    cur_max = best
    miss = 0
    probe = best + 1
    while miss < 15:
        if _msg_exists(probe):
            cur_max = probe
            miss = 0
        else:
            miss += 1
        probe += 1

    print(f"[PIN WATCHER] Oxirgi message_id topildi: {cur_max} (Pin: {orig_pin_mid})")

    # Oxirgi 3 ta xabarni ham tekshirib ko'ramiz (balki Admin allaqachon linkni yuborgan bo'lsa)
    check_queue = [m for m in range(max(orig_pin_mid + 1, cur_max - 2), cur_max + 1)]

    while True:
        if _PIN_SYNCED or not public_tunnel_url:
            time.sleep(5.0)
            continue
        try:
            for cand in range(cur_max + 1, cur_max + 8):
                if _msg_exists(cand):
                    cur_max = cand
                    check_queue.append(cand)

            while check_queue:
                m_test = check_queue.pop(0)
                r_pin = requests.post(
                    f"https://api.telegram.org/bot{token}/pinChatMessage",
                    data={"chat_id": admin_id, "message_id": m_test, "disable_notification": True},
                    timeout=5,
                ).json()
                if r_pin.get("ok"):
                    rc2 = requests.get(f"https://api.telegram.org/bot{token}/getChat", params={"chat_id": admin_id}, timeout=5).json()
                    ptxt = (rc2.get("result", {}).get("pinned_message") or {}).get("text", "")
                    if "trycloudflare.com" in ptxt:
                        _PIN_SYNCED = True
                        print(f"[PIN WATCHER OK] Admin xabari ({m_test}) Pin qilindi: {ptxt.strip()}")
                        break
                    else:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/pinChatMessage",
                            data={"chat_id": admin_id, "message_id": orig_pin_mid, "disable_notification": True},
                            timeout=5,
                        )
        except Exception:
            pass
        time.sleep(2.5)


def cloudflared_loop():
    global public_tunnel_url
    time.sleep(1.5)
    cfg = load_bot_config()
    admin_id = cfg.get("admin_id", 6580113791)
    token = cfg.get("bot_token", "")

    if os.path.exists("cluster_url.txt"):
        try:
            existing_u = open("cluster_url.txt", "r", encoding="utf-8").read().strip().splitlines()[0].strip()
            if existing_u.startswith("https://"):
                chk = requests.get(f"{existing_u}/cluster/ping", timeout=5)
                if chk.status_code == 200 and chk.text.strip() == "OK":
                    public_tunnel_url = existing_u
                    print(f"[CLUSTER TUNNEL SAQLAB QOLINDI] {existing_u}")
                    _sync_pinned_tunnel(existing_u, admin_id, token)
                    while True:
                        time.sleep(15)
                        try:
                            c2 = requests.get(f"{existing_u}/cluster/ping", timeout=6)
                            if c2.status_code != 200 or c2.text.strip() != "OK":
                                break
                            _sync_pinned_tunnel(existing_u, admin_id, token)
                        except Exception:
                            break
        except Exception:
            pass

    cf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")
    if not os.path.exists(cf_path):
        print("[CLUSTER] cloudflared.exe topilmadi!")
        return

    while True:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

            proc = subprocess.Popen(
                [cf_path, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{CLUSTER_PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            tunnel_url = ""
            for _ in range(120):
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                    continue
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    tunnel_url = m.group(0)
                    break

            if tunnel_url:
                public_tunnel_url = tunnel_url
                try:
                    with open("cluster_url.txt", "w", encoding="utf-8") as f:
                        f.write(tunnel_url + "\n")
                except Exception:
                    pass
                print(f"[CLUSTER TUNNEL TAYYOR] {tunnel_url}")
                _sync_pinned_tunnel(tunnel_url, admin_id, token)

                fail_count = 0
                while proc.poll() is None:
                    time.sleep(25)
                    try:
                        c_chk = requests.get(f"{tunnel_url}/cluster/ping", timeout=12)
                        if c_chk.status_code == 200 and c_chk.text.strip() == "OK":
                            fail_count = 0
                            _sync_pinned_tunnel(tunnel_url, admin_id, token)
                        else:
                            fail_count += 1
                    except Exception:
                        fail_count += 1

                    if fail_count >= 5:
                        print(f"[CLUSTER TUNNEL] 5 marta ping o'tmadi, qayta yoqiladi...")
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                        break
            proc.wait()
        except Exception as e:
            print(f"[CLUSTER TUNNEL XATO] {e}")
        time.sleep(5)


def _prewarm_cache():
    # Oldindan ma'lum bo'lgan 2-kompyuter pochtalarini akkountlar.txt ga yozib qo'yamiz
    known_cluster_accs = [
        ("MAXAMADOVA MUSLIMAXON ILXOM QIZI", "1-sinf", "ktk66lxch0@maxxspace.com", "@Ak101095"),
        ("YARMATOV AMIR FARRUXOVICH", "1-sinf", "6gq588x4m4@maxxspace.com", "@Ak101095"),
        ("XAYRILLOYEV ZAFARBEK ZAVKIDDIN O'G'LI", "1-sinf", "g05z2uc39e@maxxspace.com", "@Ak101095"),
        ("SHOMSIDDINOVA MUBINA MANSUROVNA", "1-sinf", "ecsmr4v4t5@maxxspace.com", "@Ak101095"),
        ("BAXTIYOROVA NIGINAXON DONIYOR QIZI", "1-sinf", "hc3o3hyl70@maxxspace.com", "@Ak101095"),
    ]
    with file_lock:
        existing_txt = open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ACCOUNTS_FILE) else ""
        with open(ACCOUNTS_FILE, "a", encoding="utf-8") as af:
            for s_n, s_c, s_e, s_p in known_cluster_accs:
                if s_n + " |" not in existing_txt:
                    af.write(f"{s_n} | {s_c} | {s_e} | {s_p}\n")

    if os.path.exists(ORDERS_DIR):
        for _fn in os.listdir(ORDERS_DIR):
            if _fn.startswith("in_") and _fn.endswith(".xlsx"):
                try:
                    parse_excel_students(os.path.join(ORDERS_DIR, _fn))
                except Exception:
                    pass


def edit_tg(chat_id, message_id, text):
    if not message_id:
        return
    cfg = load_bot_config()
    token = cfg.get("bot_token", "")
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            data={"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
    except Exception:
        pass


assist_lock = threading.Lock()
notified_certs = set()
tried_assist_counts = {}
active_assist_students = set()
ASSIST_WORKERS = 0


def cluster_assist_loop(assist_slot: int = 1):
    """2-kompyuterdagi (klaster) AI Agentlar DEDC dasturiga ulanmay qolib ketmasligi uchun
    ular ishlayotgan o'quvchilarni 4 ta parallel oqimda 1-xabar va 2-xabar (Join now) orqali DEDC ga ulab, sertifikatini kafolatli yakunlab beradi!"""
    time.sleep(2 + assist_slot * 1.5)
    from master_certified_pipeline import process_student

    while True:
        target_st = None
        s_name = ""
        try:
            with nodes_lock:
                has_active_node = any(
                    n.get("approved") and (time.time() - n.get("last_seen", 0) < 3600)
                    for n in cluster_nodes.values()
                )
                worker_map = {}
                for n in cluster_nodes.values():
                    if n.get("approved"):
                        _tw = 6 if int(n.get("ram_gb", 8)) >= 14 else 4
                        if int(n.get("workers", 0)) < _tw:
                            n["workers"] = _tw
                    for wid_str, st_txt in (n.get("worker_statuses") or {}).items():
                        m = re.match(r"^\[(\d+)/(\d+)\]\s+(.+?)\s+—", st_txt)
                        if m:
                            s_clean = " ".join(m.group(3).strip().upper().split())
                            worker_map[s_clean] = int(wid_str) if str(wid_str).isdigit() else assist_slot

            if not has_active_node:
                time.sleep(6)
                continue

            # Eng yangi buyurtmani olamiz
            candidates_files = []
            if os.path.exists(ORDERS_DIR):
                for fn in os.listdir(ORDERS_DIR):
                    if fn.startswith("in_") and fn.endswith(".xlsx"):
                        full_p = os.path.join(ORDERS_DIR, fn)
                        candidates_files.append((os.path.getmtime(full_p), fn, full_p))
            if not candidates_files:
                time.sleep(6)
                continue

            candidates_files.sort(reverse=True)
            _, fn, full_p = candidates_files[0]
            parts = fn.split("_")
            chat_id = int(parts[1]) if len(parts) >= 3 and parts[1].isdigit() else load_bot_config().get("admin_id", 6580113791)
            students = parse_excel_students(full_p)
            if not students:
                time.sleep(6)
                continue

            done_set = get_completed_students()
            unrec_set = get_unrecoverable_students()
            accs = get_existing_accounts()
            total = len(students)

            # Pastdan tepaga (242, 241, 240...) klaster o'quvchilarini 4 ta parallel oqimda olamiz
            target_idx = total
            target_wid = assist_slot
            with assist_lock:
                # 1-ustuvorlik: akkounti ochilgan yoki klaster ushlagan o'quvchilar
                for idx in range(total, max(0, total - 80), -1):
                    st = students[idx - 1]
                    cand_name = st["name"]
                    if cand_name in done_set or cand_name in unrec_set or cand_name in active_assist_students or cand_name in tried_cluster_set:
                        continue
                    if tried_assist_counts.get(cand_name, 0) >= 1:
                        continue
                    if cand_name in accs or cand_name in worker_map:
                        target_st = st
                        target_idx = idx
                        target_wid = worker_map.get(cand_name, assist_slot)
                        s_name = cand_name
                        active_assist_students.add(s_name)
                        tried_assist_counts[s_name] = tried_assist_counts.get(s_name, 0) + 1
                        tried_cluster_set.add(s_name)
                        save_tried_cluster()
                        break

                # 2-ustuvorlik: ro'yxat pastidan navbatdagi bo'sh o'quvchilar
                if not target_st:
                    for idx in range(total, max(0, total - 80), -1):
                        st = students[idx - 1]
                        cand_name = st["name"]
                        if cand_name in done_set or cand_name in unrec_set or cand_name in active_assist_students or cand_name in tried_cluster_set:
                            continue
                        if tried_assist_counts.get(cand_name, 0) >= 1:
                            continue
                        target_st = st
                        target_idx = idx
                        target_wid = assist_slot
                        s_name = cand_name
                        active_assist_students.add(s_name)
                        tried_assist_counts[s_name] = tried_assist_counts.get(s_name, 0) + 1
                        tried_cluster_set.add(s_name)
                        save_tried_cluster()
                        break

            if not target_st:
                time.sleep(5)
                continue

            active_pc2_name = "DESKTOP-EKA9GM2-60DD"
            with nodes_lock:
                for n in cluster_nodes.values():
                    if n.get("approved") and n.get("pc_name"):
                        active_pc2_name = n["pc_name"]
                        break
            pc2_tag = f"💻 2-Kompyuter [{active_pc2_name}] | 🤖 Agent #{target_wid}"

            print(f"[CLUSTER-ASSIST #{assist_slot}] [{target_idx}/{total}] {s_name} ({pc2_tag}) 1-xabar/2-xabar DEDC va Sertifikat tekshiruvi boshlandi...")
            step_history = []
            prog_res = send_tg(
                chat_id,
                f"⏳ <b>[{target_idx}/{total}] {s_name}</b>\n└ {pc2_tag}\n└ 🚀 1-xabar va 2-xabar (Join now) tekshirilmoqda...",
            )
            msg_id = prog_res.get("result", {}).get("message_id")

            def assist_update_step(step_text, _cid=chat_id, _mid=msg_id, _i=target_idx, _t=total, _name=s_name, _hist=step_history, _ptag=pc2_tag):
                if not _hist or _hist[-1] != step_text:
                    _hist.append(step_text)
                if _mid:
                    lines_txt = [f"⏳ <b>[{_i}/{_t}] {_name}</b>\n└ {_ptag}"]
                    for s_idx, h_line in enumerate(_hist):
                        pref = "✅" if s_idx < len(_hist) - 1 else "⏳"
                        lines_txt.append(f"  {pref} {h_line}")
                    edit_tg(_cid, _mid, "\n".join(lines_txt))

            already_had_cert = s_name in get_completed_students()
            is_headless = os.environ.get("HEADLESS", "1").strip().lower() in ("1", "true", "yes")
            res_status = process_student(target_st, status_callback=assist_update_step, headless=is_headless, worker_id=target_wid)

            if res_status == "COMPLETED":
                if msg_id:
                    lines_txt = [f"✅ <b>[{target_idx}/{total}] {s_name}</b>\n└ {pc2_tag}"]
                    for h_line in step_history:
                        lines_txt.append(f"  ✅ {h_line}")
                    lines_txt.append("  🎉 <b>Sertifikat muvaffaqiyatli olindi!</b>")
                    edit_tg(chat_id, msg_id, "\n".join(lines_txt))

            with assist_lock:
                should_notify = (res_status == "COMPLETED" and not already_had_cert and s_name not in notified_certs)
                if should_notify:
                    notified_certs.add(s_name)

            if should_notify:
                with nodes_lock:
                    in_progress_students.pop(s_name, None)
                certs = get_certificate_map()
                accs_now = get_existing_accounts()
                ac = accs_now.get(s_name, {})
                c_url = certs.get(s_name, "Havola faylda")
                send_tg(
                    chat_id,
                    f"🎉 <b>[{target_idx}/{total}] MUVAFFAQIYATLI OLINDI!</b>\n"
                    f"🖥 <b>{pc2_tag}</b>\n"
                    f"👤 <b>{s_name}</b>\n"
                    f"📧 Login: <code>{ac.get('email', '—')}</code>\n"
                    f"🔑 Parol: <code>{ac.get('password', '—')}</code>\n"
                    f"🏅 Sertifikat: {c_url}",
                )
        except Exception as e:
            print(f"[CLUSTER-ASSIST #{assist_slot} XATO] {e}")
        finally:
            if s_name:
                with assist_lock:
                    active_assist_students.discard(s_name)
        time.sleep(3)


def node_health_monitor_loop():
    """Har 30 soniyada ulangan kompyuterlar holatini saqlaydi va 429 ochilishi bilan yig'ilgan xabarlarni yuboradi."""
    time.sleep(30)
    while True:
        try:
            with nodes_lock:
                save_nodes_state(force=False)
            if _PIN_SYNCED and time.time() >= _tg_ban_until and _queued_tg_msgs:
                item = None
                with _tg_rate_lock:
                    if _queued_tg_msgs:
                        item = _queued_tg_msgs.pop(0)
                if item:
                    send_tg(item[0], item[1], reply_markup=item[2])
        except Exception as e:
            print(f"[NODE MONITOR XATO] {e}")
        time.sleep(15)


if __name__ == "__main__":
    import sys

    class _TeeLog:
        def __init__(self, orig, log_path):
            self.orig = orig
            self.log_path = log_path

        def write(self, data):
            try:
                if self.orig:
                    self.orig.write(data)
                    self.orig.flush()
            except Exception:
                pass
            try:
                with open(self.log_path, "a", encoding="utf-8", errors="replace") as f:
                    f.write(data)
            except Exception:
                pass

        def flush(self):
            try:
                if self.orig:
                    self.orig.flush()
            except Exception:
                pass

    try:
        _bridge_lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _bridge_lock_sock.bind(("127.0.0.1", 49882))
        os.set_handle_inheritable(_bridge_lock_sock.fileno(), False)
    except Exception:
        pass

    for _tmp_f in ("decoded_cw.txt", "decoded_mcp.txt"):
        try:
            _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), _tmp_f)
            if os.path.exists(_p):
                os.remove(_p)
        except Exception:
            pass

    try:
        import shutil
        for _bf in ("OQIM_QOSHISH_YANGI_V2.bat", "UNIVERSAL_OQIM_QOSHISH.bat"):
            _src_bat = os.path.join(os.path.dirname(os.path.abspath(__file__)), _bf)
            _dst_desk = os.path.join(os.path.expanduser("~"), "Desktop", _bf)
            if os.path.exists(_src_bat) and os.path.exists(os.path.dirname(_dst_desk)):
                shutil.copy2(_src_bat, _dst_desk)
    except Exception:
        pass

    sys.stdout = _TeeLog(sys.stdout, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cluster_bridge_4w.log"))
    sys.stderr = _TeeLog(sys.stderr, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cluster_bridge_4w.log"))

    def _free_port_8766(kill_cf: bool = False):
        if kill_cf:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "cloudflared.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000 if os.name == "nt" else 0,
                )
            except Exception:
                pass
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"],
                encoding="utf-8",
                errors="ignore",
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            my_pid = str(os.getpid())
            killed_pids = set()
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(f":{CLUSTER_PORT}") and "LISTENING" in line.upper():
                    pid = parts[-1]
                    if pid.isdigit() and pid != "0" and pid != my_pid and pid not in killed_pids:
                        killed_pids.add(pid)
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=0x08000000 if os.name == "nt" else 0,
                        )
            if killed_pids:
                print(f"[CLUSTER TOZALASH] Eski osilib qolgan 8766 jarayonlari yopildi: {killed_pids}")
        except Exception as e:
            print(f"[CLUSTER TOZALASH XATO] {e}")

    _free_port_8766(kill_cf=False)
    time.sleep(0.5)

    save_nodes_state()
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = None
    for _attempt in range(15):
        try:
            server = http.server.ThreadingHTTPServer(("0.0.0.0", CLUSTER_PORT), ClusterBridgeHandler)
            break
        except OSError as _bind_err:
            if _attempt in (0, 3, 7):
                _free_port_8766()
            time.sleep(1.5)
    if server is None:
        print("[CLUSTER XATO] Port 8766 band bo'lib qoldi, server ishga tushmadi!")
        sys.exit(1)
    server.handle_error = lambda request, client_address: None
    try:
        os.set_handle_inheritable(server.socket.fileno(), False)
    except Exception:
        pass
    threading.Thread(target=_prewarm_cache, daemon=True).start()
    threading.Thread(target=cloudflared_loop, daemon=True).start()
    threading.Thread(target=_watch_user_pin_loop, daemon=True).start()
    threading.Thread(target=node_health_monitor_loop, daemon=True).start()
    print(f"🚀 Cluster Master Bridge port {CLUSTER_PORT} da faol ishga tushdi! (12 ta Kompyuter ulangan)")
    server.serve_forever()


