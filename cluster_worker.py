# -*- coding: utf-8 -*-
"""
=============================================================================
UZBEK CODERS AI AGENT - UNIVERSAL MULTI-PC CLUSTER WORKER
=============================================================================
Boshqa kompyuterda ikki marta bosilganda orqa fonda ishga tushib, asosiy botga
avtomatik ulanadi va Admin Telegramda ruxsat bergan oqim sonida (3, 4, 5, 6 ta)
buyurtmalarni bo'lishib parallel bajaradi!
=============================================================================
"""

import os
import sys
import json
import time
import socket
import uuid
import threading
import subprocess
import requests

try:
    from master_certified_pipeline import (
        process_student,
        get_completed_students,
        get_existing_accounts,
        get_unrecoverable_students,
        ACCOUNTS_FILE,
        RESULTS_FILE,
        ERRORS_FILE,
    )
except Exception:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "requests", "openpyxl", "playwright", "selenium", "undetected-chromedriver", "setuptools"], check=False)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    from master_certified_pipeline import (
        process_student,
        get_completed_students,
        get_existing_accounts,
        get_unrecoverable_students,
        ACCOUNTS_FILE,
        RESULTS_FILE,
        ERRORS_FILE,
    )


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except Exception:
        pass


def get_ram_gb() -> int:
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return max(4, round(stat.ullTotalPhys / (1024 ** 3)))
        except Exception:
            pass
    return 16


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


class ClusterWorkerNode:
    def __init__(self):
        cfg = load_bot_config()
        self.token = os.environ.get("BOT_TOKEN") or cfg.get("bot_token", "")
        self.admin_id = int(os.environ.get("ADMIN_ID", str(cfg.get("admin_id", 6580113791))))
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        mac_tail = hex(uuid.getnode())[-4:].upper()
        self.pc_name = f"{socket.gethostname()}-{mac_tail}"
        self.node_id = self.pc_name.replace(" ", "_")[:28]
        self.ram_gb = get_ram_gb()
        default_w = int(os.environ.get("WORKER_COUNT", "4" if self.ram_gb >= 12 else "3"))
        self.target_workers = default_w
        self.approved = False
        self.master_url = ""
        self.active_threads = {}
        self.lock = threading.Lock()

    def discover_master_url(self) -> str:
        candidates = []
        if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
            candidates.append(sys.argv[1].strip())
        if os.path.exists("cluster_url.txt"):
            try:
                with open("cluster_url.txt", "r", encoding="utf-8") as f:
                    for ln in f.read().splitlines():
                        if ln.strip().startswith("http"):
                            candidates.append(ln.strip())
            except Exception:
                pass

        # Telegram Admin Chat Pinned xabaridan asosiy kompyuter manzilini o'qiymiz
        try:
            r = requests.get(f"{self.api_url}/getChat", params={"chat_id": self.admin_id}, timeout=10).json()
            pinned_txt = r.get("result", {}).get("pinned_message", {}).get("text", "")
            for part in pinned_txt.split():
                if part.startswith("http://") or part.startswith("https://"):
                    u = part.strip().rstrip("|,;")
                    if u not in candidates:
                        candidates.append(u)
        except Exception:
            pass

        for url in candidates:
            try:
                res = requests.get(f"{url}/cluster/ping", timeout=5)
                if res.status_code == 200 and res.text.strip() == "OK":
                    return url
            except Exception:
                continue
        return ""

    def edit_tg_message(self, chat_id, message_id, text):
        if not message_id:
            return
        try:
            requests.post(
                f"{self.api_url}/editMessageText",
                data={"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"},
                timeout=8,
            )
        except Exception:
            pass

    def send_tg_message(self, chat_id, text):
        try:
            r = requests.post(
                f"{self.api_url}/sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            return r.json()
        except Exception:
            return {}

    def get_student_cert_line(self, s_name: str) -> str:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, "r", encoding="utf-8", errors="replace") as f:
                for ln in f.read().splitlines():
                    if ln.strip().startswith(s_name + " |"):
                        return ln.strip()
        return ""

    def get_student_acc_line(self, s_name: str) -> str:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="replace") as f:
                for ln in f.read().splitlines():
                    if ln.strip().startswith(s_name + " |"):
                        return ln.strip()
        return ""

    def get_student_err_line(self, s_name: str) -> str:
        if os.path.exists(ERRORS_FILE):
            with open(ERRORS_FILE, "r", encoding="utf-8", errors="replace") as f:
                for ln in f.read().splitlines():
                    if ln.strip().startswith(s_name + " |"):
                        return ln.strip()
        return ""

    def worker_thread_fn(self, local_wid: int):
        while True:
            if not self.approved or local_wid > self.target_workers or not self.master_url:
                time.sleep(2)
                continue

            try:
                r = requests.post(
                    f"{self.master_url}/cluster/pop_task",
                    json={"node_id": self.node_id, "worker_id": local_wid},
                    timeout=10,
                )
                data = r.json()
            except Exception:
                time.sleep(3)
                continue

            if not data.get("has_task"):
                time.sleep(2)
                continue

            task_id = data["task_id"]
            chat_id = data["chat_id"]
            idx = data["idx"]
            total = data["total"]
            st = data["student"]
            s_name = st["name"]
            acc_line_from_master = data.get("account_line", "")

            if acc_line_from_master and s_name not in get_existing_accounts():
                with self.lock:
                    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as af:
                        af.write(acc_line_from_master.strip() + "\n")

            step_history = []

            def update_step(step_text, _i=idx, _t=total, _name=s_name, _hist=step_history, _w=local_wid):
                if not _hist or _hist[-1] != step_text:
                    _hist.append(step_text)
                try:
                    requests.post(
                        f"{self.master_url}/cluster/status",
                        json={"node_id": self.node_id, "worker_id": _w, "status_text": f"[{_i}/{_t}] {_name} — {step_text}"},
                        timeout=6,
                    )
                except Exception:
                    pass

            status = "INCOMPLETE"
            try:
                status = process_student(st, status_callback=update_step, headless=True, worker_id=local_wid)
            except Exception as e:
                print(f"[CLUSTER WORKER #{local_wid} XATO] {e}")

            payload = {
                "task_id": task_id,
                "chat_id": chat_id,
                "idx": idx,
                "total": total,
                "node_id": self.node_id,
                "pc_name": self.pc_name,
                "worker_id": local_wid,
                "status": status,
                "student": st,
                "account_line": self.get_student_acc_line(s_name),
                "cert_line": self.get_student_cert_line(s_name),
                "error_line": self.get_student_err_line(s_name),
            }
            for _ in range(5):
                try:
                    requests.post(f"{self.master_url}/cluster/finish_task", json=payload, timeout=15)
                    break
                except Exception:
                    time.sleep(2)

    def run_forever(self):
        print("=" * 70)
        print(f"🖥 UNIVERSAL CLUSTER WORKER ISHGA TUSHDI: {self.pc_name} (RAM: {self.ram_gb} GB)")
        print("Asosiy bot serveri qidirilmoqda...")
        print("=" * 70)

        for wid in range(1, 11):
            t = threading.Thread(target=self.worker_thread_fn, args=(wid,), daemon=True)
            t.start()

        first_reg = True
        while True:
            if not self.master_url:
                self.master_url = self.discover_master_url()
                if not self.master_url:
                    time.sleep(4)
                    continue

            try:
                r = requests.post(
                    f"{self.master_url}/cluster/register",
                    json={
                        "node_id": self.node_id,
                        "pc_name": self.pc_name,
                        "ram_gb": self.ram_gb,
                        "default_workers": self.target_workers,
                        "force_prompt": first_reg,
                    },
                    timeout=10,
                )
                first_reg = False
                resp = r.json()
                self.approved = bool(resp.get("approved", False))
                self.target_workers = int(resp.get("workers", self.target_workers))
            except Exception:
                self.master_url = ""
            time.sleep(5)


if __name__ == "__main__":
    node = ClusterWorkerNode()
    _single_lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _single_lock_sock.bind(("127.0.0.1", 49881))
    except Exception:
        print("[!] Cluster Worker allaqachon orqa fonda ishlab turibdi! Telegramga oqim tanlash so'rovi qayta yuborilmoqda...")
        try:
            m_url = node.discover_master_url()
            if m_url:
                requests.post(
                    f"{m_url}/cluster/register",
                    json={
                        "node_id": node.node_id,
                        "pc_name": node.pc_name,
                        "ram_gb": node.ram_gb,
                        "default_workers": node.target_workers,
                        "force_prompt": True,
                    },
                    timeout=10,
                )
        except Exception:
            pass
        sys.exit(0)
    node.run_forever()
