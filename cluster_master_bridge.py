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
from telegram_bot import parse_students_from_text, get_certificate_map, get_error_reason_map

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
file_lock = threading.Lock()
nodes_lock = threading.Lock()
_excel_cache = {}

cluster_nodes = {}
in_progress_students = {}
pending_screen_requests = {}  # node_id -> chat_id
_worker_assigned = {}
_sticky_workers = {}
_last_nodes_save_ts = 0.0

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

public_tunnel_url = ""
TRIED_CLUSTER_FILE = "cluster_tried_students.json"
tried_cluster_set = {"MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"}


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
        "bot_token": "8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc",
        "admin_id": 6580113791,
    }


_tg_rate_lock = threading.Lock()
_last_tg_call_ts = 0.0
_tg_ban_until = 0.0
_PIN_SYNCED = False
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
    token = cfg.get("bot_token", "8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc")
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

    students = []
    try:
        wb = load_workbook(xlsx_path, data_only=True, read_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            cells = []
            for v in row:
                if v is None:
                    continue
                if hasattr(v, "strftime"):
                    cells.append(v.strftime("%d.%m.%Y"))
                else:
                    s = str(v).strip()
                    if s:
                        cells.append(s)
            if not cells:
                continue
            line_joined = " ".join(cells)
            if any(w in line_joined.lower() for w in ("ism", "familiya", "f.i.sh", "tug'ilgan", "seriya", "coursera")):
                continue
            st_list = parse_students_from_text(" | ".join(cells))
            if st_list:
                students.extend(st_list)
        wb.close()
        if students:
            _excel_cache[xlsx_path] = (mtime, students)
    except Exception:
        pass
    return students


_state_mem_cache = {"ts": 0.0, "done": set(), "unrec": set(), "accs": {}, "orders": []}
_last_tried_save_ts = 0.0


def get_pending_cluster_task(node_id: str = "", worker_id: str = "1"):
    global _last_tried_save_ts
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
                    if mt >= 1791790000:
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
        # Uzilgan kompyuterlarning band qilgan o'quvchilarini bo'shatamiz
        for (_wnid, _wwid), _wst in list(_worker_assigned.items()):
            _nlast = cluster_nodes.get(_wnid, {}).get("last_seen", 0)
            if now - _nlast > 180:
                _worker_assigned.pop((_wnid, _wwid), None)
                _sticky_workers.pop((_wnid, _wwid), None)
                in_progress_students.pop(_wst, None)

        expired = [k for k, t in in_progress_students.items() if now - t > 240]
        for k in expired:
            in_progress_students.pop(k, None)

        # Hozir boshqa faol agentlar ishlayotgan o'quvchilar to'plami
        w_key = (node_id, str(worker_id)) if (node_id and worker_id) else None
        busy_by_others = set()
        for _ok, _ost in _worker_assigned.items():
            if _ok != w_key and _ost in in_progress_students and (now - in_progress_students.get(_ost, 0) <= 240):
                busy_by_others.add(_ost)

        # 1) Agar shu agent o'ziga biriktirilgan o'quvchini hali oxirigacha (COMPLETED/UNRECOVERABLE) yetkazmagan bo'lsa,
        # va u o'quvchi boshqa agentda band bo'lmasa, 3 urinishgacha qayta beramiz
        if w_key:
            sticky = _sticky_workers.get(w_key)
            if sticky:
                st_sticky = sticky["student"]
                sn_sticky = st_sticky["name"]
                if (
                    sn_sticky not in done_set
                    and sn_sticky not in unrec_set
                    and sn_sticky not in busy_by_others
                    and sticky.get("tries", 1) < 3
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
                    if prev_st and prev_st not in busy_by_others:
                        in_progress_students.pop(prev_st, None)
                    tried_cluster_set.add(sn_sticky)
            else:
                prev_st = _worker_assigned.pop(w_key, None)
                if prev_st and prev_st not in busy_by_others:
                    in_progress_students.pop(prev_st, None)

        # 2) Yangi o'quvchi tanlash: har bir qolgan o'quvchiga FAQAT 1 TA AGENT kiradi (40 ta agent bitta o'quvchiga tiqilmaydi!)
        # Eng kam urinilgan o'quvchi birinchi tanlanadi (round-robin)
        for pass_mode in ("FREE_ONLY", "OLDEST_IN_PROGRESS"):
            best_cand = None
            for chat_id, students in parsed_orders:
                total = len(students)
                for idx in range(total, 0, -1):
                    st = students[idx - 1]
                    s_name = st["name"]
                    if s_name in done_set or s_name in unrec_set:
                        continue
                    if s_name == "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI":
                        continue
                    if pass_mode == "FREE_ONLY" and (s_name in busy_by_others or s_name in in_progress_students):
                        continue
                    if pass_mode == "OLDEST_IN_PROGRESS":
                        # Agar o'quvchida hozir faol agent Quiz/Video/Login qilayotgan bo'lsa (<120s), ustiga 2-agentni kiritmaymiz!
                        if now - in_progress_students.get(s_name, 0) < 120:
                            continue
                    tries_c = _state_mem_cache.setdefault("try_counts", {}).get(s_name, 0)
                    last_t = in_progress_students.get(s_name, 0.0)
                    has_ac_prio = 0 if s_name in accs else 1
                    sort_key = (tries_c, last_t, has_ac_prio, -idx)
                    if best_cand is None or sort_key < best_cand[0]:
                        best_cand = (sort_key, chat_id, idx, total, st, s_name)

            if best_cand is not None:
                _, chat_id, idx, total, st, s_name = best_cand
                _state_mem_cache.setdefault("try_counts", {})[s_name] = _state_mem_cache["try_counts"].get(s_name, 0) + 1
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
            s["name"] not in done_set and s["name"] not in unrec_set and s["name"] != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"
            for _, sts in parsed_orders
            for s in sts
        )
        if has_any_remaining:
            return {"has_task": False, "all_done": False, "reason": "all_remaining_in_progress"}

    return {"has_task": False, "all_done": True}


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
            self.end_headers()
            self.wfile.write(body)
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
            cfg = load_bot_config()
            admin_id = cfg.get("admin_id", 6580113791)

            if act == "no":
                with nodes_lock:
                    pc_name = cluster_nodes.get(node_id, {}).get("pc_name", node_id)
                    cluster_nodes.pop(node_id, None)
                send_tg(admin_id, f"❌ <b>{pc_name}</b> kompyuteri rad etildi.")
                self._send_html("<h2 style='font-family:sans-serif;color:#d9534f;text-align:center;margin-top:50px;'>❌ Rad etildi! Telegramga qaytishingiz mumkin.</h2>")
                return

            with nodes_lock:
                if node_id in cluster_nodes:
                    cluster_nodes[node_id]["approved"] = True
                    cluster_nodes[node_id]["workers"] = w_cnt
                    pc_name = cluster_nodes[node_id].get("pc_name", node_id)
                else:
                    cluster_nodes[node_id] = {"pc_name": node_id, "ram_gb": 16, "workers": w_cnt, "approved": True, "last_seen": time.time()}
                    pc_name = node_id

            send_tg(
                admin_id,
                f"✅ <b>BOTINGIZGA YANGI AI AGENTLAR QO'SHILDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💻 Qo'shilgan kompyuter: <b>{pc_name}</b>\n"
                f"🤖 Qo'shilgan parallel AI Agentlar: <b>+{w_cnt} ta Agent</b>\n"
                f"🚀 Asosiy kompyuter (3 ta Agent) + {pc_name} ({w_cnt} ta Agent) = <b>Jami {3 + w_cnt} ta AI Agent</b> orqa fonda bo'linib ishni boshladi!",
            )
            self._send_html(
                f"<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head>"
                f"<body style='background:#0f172a;color:#22c55e;font-family:sans-serif;text-align:center;padding-top:60px;'>"
                f"<h1>✅ {pc_name} ({w_cnt} ta AI Agent) muvaffaqiyatli qo'shildi!</h1>"
                f"<p style='color:#cbd5e1;font-size:18px;'>Orqa fonda barcha buyurtmalarni bo'lishib bajarishni boshladi.<br>Ushbu oynani yopib Telegramga qaytishingiz mumkin.</p>"
                f"<script>setTimeout(function(){{window.close();}}, 2500);</script></body></html>"
            )
            return

        if path == "/cluster/nodes":
            with nodes_lock:
                self._send_json(cluster_nodes)
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
                if c_files:
                    sts = parse_excel_students(c_files[0][1])
                    for i_s, s_obj in enumerate(sts, 1):
                        sn = s_obj["name"]
                        if sn not in done_s and sn not in unrec_s and sn != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI":
                            rem_list.append(f"[{i_s}/{len(sts)}] {sn} ({accs_s.get(sn, {}).get('email', 'yangi')})")
            self._send_json({
                "tunnel_url": public_tunnel_url,
                "pin_synced": _PIN_SYNCED,
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
                if node_id not in cluster_nodes:
                    cluster_nodes[node_id] = {
                        "pc_name": pc_name,
                        "ram_gb": ram_gb,
                        "workers": def_workers,
                        "approved": True,
                        "last_seen": now_ts,
                        "last_prompt": now_ts,
                        "status": "Faol ishlamoqda...",
                        "notified": True,
                    }
                    save_nodes_state()
                    notify_now = True
                else:
                    cluster_nodes[node_id]["last_seen"] = now_ts
                    cluster_nodes[node_id]["ram_gb"] = ram_gb
                    if int(cluster_nodes[node_id].get("workers", 0)) < def_workers:
                        cluster_nodes[node_id]["workers"] = def_workers
                    if force_prompt and (now_ts - cluster_nodes[node_id].get("last_prompt", 0) > 15):
                        cluster_nodes[node_id]["last_prompt"] = now_ts
                        notify_now = True
                    elif not cluster_nodes[node_id].get("approved", False) and not cluster_nodes[node_id].get("notified", False):
                        cluster_nodes[node_id]["notified"] = True
                        cluster_nodes[node_id]["last_prompt"] = now_ts
                        notify_now = True
                    save_nodes_state()
                pc_idx_reg = (list(cluster_nodes.keys()).index(node_id) + 2) if node_id in cluster_nodes else 2
                approved = cluster_nodes[node_id].get("approved", False)
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
                threading.Thread(
                    target=send_tg,
                    args=(
                        admin_id,
                        f"🖥 <b>YANGI ({pc_idx_reg}-) KOMPYUTER BOTGA ULANDI!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💻 {pc_idx_reg}-Kompyuter: <b>{pc_name}</b>\n"
                        f"🧠 Operativka (RAM): <b>{ram_gb} GB</b>\n"
                        f"🤖 Tavsiya etilgan: <b>{def_workers} ta parallel AI Agent</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"❓ <b>Nechta AI Agent bo'lib beray? (Telefondan yoki kompyuterdan bitta bosing — havola ochmasdan darhol ishga tushadi!)</b>",
                        markup,
                    ),
                    daemon=True,
                ).start()

            self._send_json({"approved": approved, "workers": workers})
            return

        if path == "/cluster/pop_task":
            data = self._read_body()
            node_id = data.get("node_id", "")
            worker_id = str(data.get("worker_id", "1"))
            with nodes_lock:
                node_info = cluster_nodes.get(node_id, {})
                if node_id in cluster_nodes:
                    cluster_nodes[node_id]["last_seen"] = time.time()
            if not node_info.get("approved", False):
                self._send_json({"has_task": False, "reason": "not_approved"})
                return

            task = get_pending_cluster_task(node_id=node_id, worker_id=worker_id)
            if task.get("has_task") and node_id in cluster_nodes:
                st_n = " ".join(task.get("student", {}).get("name", "").strip().upper().split())
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
                    save_nodes_state(force=False)
            elif task.get("all_done") and node_id in cluster_nodes:
                with nodes_lock:
                    cluster_nodes[node_id]["status"] = "🟡 Bo'sh (Yangi buyurtma kutilmoqda)"
                    save_nodes_state(force=False)
            self._send_json(task)
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
                if node_id in cluster_nodes and status == "COMPLETED":
                    cluster_nodes[node_id]["completed_count"] = cluster_nodes[node_id].get("completed_count", 0) + 1
                    save_nodes_state(force=True)
                pc_idx_fin = (list(cluster_nodes.keys()).index(node_id) + 2) if node_id in cluster_nodes else 2

            idx_val = data.get("idx", "")
            tot_val = data.get("total", "")
            num_prefix = f"[{idx_val}/{tot_val}] " if (idx_val and tot_val) else ""
            pc2_tag = f"💻 {pc_idx_fin}-Kompyuter [{pc_name}] | 🤖 Agent #{worker_id}"

            if status == "COMPLETED":
                certs = get_certificate_map()
                accs = get_existing_accounts()
                ac = accs.get(s_name, {})
                c_url = certs.get(s_name, "Havola faylda")
                msg_done = (
                    f"🎉 <b>{num_prefix}MUVAFFAQIYATLI OLINDI!</b>\n"
                    f"🖥 <b>{pc2_tag}</b>\n"
                    f"👤 <b>{s_name}</b>\n"
                    f"📧 Login: <code>{ac.get('email', '—')}</code>\n"
                    f"🔑 Parol: <code>{ac.get('password', '—')}</code>\n"
                    f"🏅 Sertifikat: {c_url}"
                )
                threading.Thread(target=send_tg, args=(chat_id, msg_done), daemon=True).start()
                try:
                    cands = sorted(
                        [(os.path.getmtime(os.path.join(ORDERS_DIR, fn)), os.path.join(ORDERS_DIR, fn))
                         for fn in os.listdir(ORDERS_DIR) if fn.startswith("in_") and fn.endswith(".xlsx")],
                        reverse=True,
                    )
                    if cands:
                        all_sts = parse_excel_students(cands[0][1])
                        done_s = get_completed_students()
                        unrec_s = get_unrecoverable_students()
                        rem_s = [x for x in all_sts if x["name"] not in done_s and x["name"] not in unrec_s and x["name"] != "MUXAMMADAMINOVA IBODATOY ILXOMBEK QIZI"]
                        if all_sts and not rem_s:
                            from master_certified_pipeline import export_results_to_excel
                            out_xlsx = os.path.join(ORDERS_DIR, f"Sertifikatlar_{chat_id}_{int(time.time())}.xlsx")
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
                                            f"👥 Jami o'quvchilar: <b>{len(all_sts)} ta</b>\n"
                                            f"✅ Sertifikat olindi: <b>{done_c} ta</b>\n"
                                            f"⚠️ JSHSHIR xatoli (o'tkazib yuborilgan): <b>{unrec_c} ta</b>"
                                        ),
                                        "parse_mode": "HTML",
                                    },
                                    files={"document": _xf},
                                    timeout=30,
                                )
                except Exception:
                    pass
            elif status == "UNRECOVERABLE":
                errs = get_error_reason_map()
                msg_skip = (
                    f"⚠️ <b>{num_prefix}{s_name} — O'TKAZIB YUBORILDI! ({pc2_tag})</b>\n"
                    f"Sababi: <i>{errs.get(s_name, 'Oldin boshqa joyda roʻyxatdan oʻtgan')}</i>"
                )
                threading.Thread(target=send_tg, args=(chat_id, msg_skip), daemon=True).start()

            self._send_json({"ok": True})
            return

        if path == "/cluster/status":
            data = self._read_body()
            node_id = data.get("node_id", "")
            w_id = str(data.get("worker_id", "1"))
            status_text = data.get("status_text", "")
            now_st = time.time()
            with nodes_lock:
                if node_id in cluster_nodes:
                    cluster_nodes[node_id]["last_seen"] = now_st
                    cluster_nodes[node_id]["status"] = status_text
                    if "worker_statuses" not in cluster_nodes[node_id]:
                        cluster_nodes[node_id]["worker_statuses"] = {}
                    cluster_nodes[node_id]["worker_statuses"][w_id] = status_text
                    save_nodes_state(force=False)

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
                        new_ac_line = f"{st_name_clean} | 1-sinf | {em_clean} | @Ak101095"
                        with file_lock:
                            existing_txt = open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ACCOUNTS_FILE) else ""
                            if st_name_clean + " |" not in existing_txt:
                                with open(ACCOUNTS_FILE, "a", encoding="utf-8") as af:
                                    af.write(new_ac_line + "\n")
                        with nodes_lock:
                            _state_mem_cache["accs"][st_name_clean] = {"email": em_clean, "password": "@Ak101095"}
                            if (node_id, w_id) in _sticky_workers:
                                _sticky_workers[(node_id, w_id)]["account_line"] = new_ac_line
            except Exception as e:
                print(f"[STATUS XATO] {e}")

            self._send_json({"ok": True})
            return

        self._send_text("Not Found", 404)


def _sync_pinned_tunnel(tunnel_url: str, admin_id: int, token: str):
    global _PIN_SYNCED, _tg_ban_until
    if not tunnel_url or not token:
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

    _PIN_SYNCED = False
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
            proc = subprocess.Popen(
                [cf_path, "tunnel", "--url", f"http://127.0.0.1:{CLUSTER_PORT}"],
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
                while proc.poll() is None:
                    time.sleep(20)
                    try:
                        c_chk = requests.get(f"{tunnel_url}/cluster/ping", timeout=6)
                        if c_chk.status_code != 200 or c_chk.text.strip() != "OK":
                            proc.terminate()
                            break
                        _sync_pinned_tunnel(tunnel_url, admin_id, token)
                    except Exception:
                        proc.terminate()
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
            res_status = process_student(target_st, status_callback=assist_update_step, headless=True, worker_id=target_wid)

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

    _bridge_lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _bridge_lock_sock.bind(("127.0.0.1", 49882))
        os.set_handle_inheritable(_bridge_lock_sock.fileno(), False)
    except OSError:
        sys.exit(0)

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

    # Agar yangilangan (v2) ko'prik allaqachon ishlab turgan bo'lsa, ortiqcha oyna xato chiqarmasdan yopiladi
    try:
        _r = requests.get(f"http://127.0.0.1:{CLUSTER_PORT}/cluster/v2_ping", timeout=2)
        if _r.status_code == 200 and _r.text.strip() == "OK_V2":
            sys.exit(0)
    except Exception:
        pass

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
    http.server.ThreadingHTTPServer.allow_reuse_address = False
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


