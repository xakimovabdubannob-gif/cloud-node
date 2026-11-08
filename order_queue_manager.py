# -*- coding: utf-8 -*-
"""
order_queue_manager.py
======================
Ko'p sonli buyurtmalar (Excel fayllar) navbatini to'liq boshqarish moduli:
- Har bir buyurtma uchun unikal qisqa ID (hash)
- Bittada xatosiz o'chirish / arxivlash (dst mavjud bo'lsa ham)
- Istalgan buyurtmani darhol 1-o'ringa chiqarish
- O'rin almashtirish (oldinga / orqaga)
- Muzlatish (Pause) va faollashtirish
- Telegram callback_data uzunligi chegarasiga (64 bayt) 100% mos
"""

import os
import sys
import json
import time
import shutil
import hashlib
from typing import List, Dict, Optional, Tuple

ORDERS_DIR = "bot_orders"
ARCHIVE_DIR = os.path.join(ORDERS_DIR, "archived")
QUEUE_STATE_FILE = os.path.join(ORDERS_DIR, "queue_state.json")
CERTS_FILE = "natijalar_sertifikatlar.txt"
ERRORS_FILE = "xatolar_keshi.txt"

def _ensure_dirs():
    os.makedirs(ORDERS_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

def get_order_id(filename: str) -> str:
    """Fayl nomi uchun unikal 8 belgili qisqa ID qaytaradi"""
    return hashlib.md5(filename.encode("utf-8")).hexdigest()[:8]

def _get_completed_and_unrec_keys() -> Tuple[set, set]:
    done_set = set()
    if os.path.exists(CERTS_FILE):
        try:
            with open(CERTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    p = line.strip().split("|")
                    if p and p[0].strip():
                        done_set.add(p[0].strip().upper())
        except Exception:
            pass

    unrec_set = set()
    if os.path.exists(ERRORS_FILE):
        try:
            with open(ERRORS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    p = line.strip().split("|")
                    if p and p[0].strip():
                        unrec_set.add(p[0].strip().upper())
        except Exception:
            pass
    return done_set, unrec_set

def count_excel_progress(file_path: str, done_set: set, unrec_set: set) -> Tuple[int, int, int]:
    """Qaytaradi: (total, completed_count, remaining_count)"""
    if not os.path.exists(file_path):
        return 0, 0, 0
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=True, read_only=True)
        ws = wb.active
        total = 0
        done_cnt = 0
        for row in ws.iter_rows(values_only=True):
            if not row or not any(row):
                continue
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if not cells:
                continue
            first_c = cells[0].upper()
            if any(h in first_c for h in ["F.I.SH", "F.I.O", "ISM", "FAMILIYA", "№", "T/R", "FISH"]):
                continue
            name_cand = ""
            for val in cells:
                parts = val.split()
                if len(parts) >= 2 and all(p.isalpha() or "'" in p or "`" in p or "ʻ" in p for p in parts[:2]):
                    name_cand = val.upper()
                    break
            if not name_cand and len(cells) >= 1 and len(cells[0].split()) >= 2:
                name_cand = cells[0].upper()

            if name_cand:
                total += 1
                if name_cand in done_set or name_cand in unrec_set:
                    done_cnt += 1
        rem = max(0, total - done_cnt)
        return total, done_cnt, rem
    except Exception:
        return 0, 0, 0

def load_queue_state() -> Dict:
    _ensure_dirs()
    if os.path.exists(QUEUE_STATE_FILE):
        try:
            with open(QUEUE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"queue": [], "parallel_mode": False}

def save_queue_state(state: Dict):
    _ensure_dirs()
    try:
        tmp = QUEUE_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        if os.path.exists(QUEUE_STATE_FILE):
            os.remove(QUEUE_STATE_FILE)
        os.rename(tmp, QUEUE_STATE_FILE)
    except Exception as e:
        print(f"[QUEUE SAVE ERROR] {e}")

def sync_and_get_queue() -> List[Dict]:
    _ensure_dirs()
    state = load_queue_state()
    existing_items: List[Dict] = state.get("queue", [])

    disk_files = [f for f in os.listdir(ORDERS_DIR) if f.startswith("in_") and f.endswith(".xlsx")]
    done_set, unrec_set = _get_completed_and_unrec_keys()

    updated_queue = []
    # 1. Avval mavjud navbatdagi fayllarni tekshiramiz
    for item in existing_items:
        fn = item.get("filename")
        if fn in disk_files:
            fp = os.path.join(ORDERS_DIR, fn)
            tot, done, rem = count_excel_progress(fp, done_set, unrec_set)
            item["id"] = get_order_id(fn)
            item["total"] = tot
            item["done"] = done
            item["remaining"] = rem
            item["mtime"] = os.path.getmtime(fp)
            if "status" not in item:
                item["status"] = "active"
            updated_queue.append(item)
            disk_files.remove(fn)

    # 2. Yangi diskka tushgan, lekin hali queue_state da bo'lmagan fayllarni oxiriga qo'shamiz
    disk_files_sorted = sorted(disk_files, key=lambda x: os.path.getmtime(os.path.join(ORDERS_DIR, x)))
    for fn in disk_files_sorted:
        fp = os.path.join(ORDERS_DIR, fn)
        parts = fn.split("_")
        chat_id = int(parts[1]) if len(parts) >= 3 and parts[1].isdigit() else 6580113791
        clean_name = fn
        if len(parts) >= 4:
            clean_name = "_".join(parts[3:]).rsplit(".", 1)[0]
        elif len(parts) >= 3:
            clean_name = parts[2].rsplit(".", 1)[0]

        tot, done, rem = count_excel_progress(fp, done_set, unrec_set)
        new_item = {
            "id": get_order_id(fn),
            "filename": fn,
            "display_name": clean_name,
            "chat_id": chat_id,
            "status": "active",
            "total": tot,
            "done": done,
            "remaining": rem,
            "mtime": os.path.getmtime(fp),
            "added_ts": int(time.time()),
        }
        updated_queue.append(new_item)

    for idx, item in enumerate(updated_queue, 1):
        item["priority"] = idx

    state["queue"] = updated_queue
    save_queue_state(state)
    return updated_queue

def find_order_by_id(order_id: str) -> Optional[Dict]:
    queue = sync_and_get_queue()
    for item in queue:
        if item.get("id") == order_id or str(item.get("priority")) == str(order_id):
            return item
    return None

def move_order_to_top_by_id(order_id: str) -> bool:
    item = find_order_by_id(order_id)
    if item:
        return move_order_to_top(item["filename"])
    return False

def move_order_to_top(filename: str) -> bool:
    state = load_queue_state()
    queue = state.get("queue", [])
    target = None
    for item in queue:
        if item.get("filename") == filename:
            target = item
            break
    if not target:
        return False
    queue.remove(target)
    target["status"] = "active"
    queue.insert(0, target)
    for idx, item in enumerate(queue, 1):
        item["priority"] = idx
    state["queue"] = queue
    save_queue_state(state)
    return True

def swap_order_by_id(order_id: str, direction: str) -> bool:
    item = find_order_by_id(order_id)
    if item:
        return swap_order_position(item["filename"], direction)
    return False

def swap_order_position(filename: str, direction: str) -> bool:
    state = load_queue_state()
    queue = state.get("queue", [])
    idx = -1
    for i, item in enumerate(queue):
        if item.get("filename") == filename:
            idx = i
            break
    if idx == -1:
        return False

    if direction == "up" and idx > 0:
        queue[idx], queue[idx - 1] = queue[idx - 1], queue[idx]
    elif direction == "down" and idx < len(queue) - 1:
        queue[idx], queue[idx + 1] = queue[idx + 1], queue[idx]
    else:
        return False

    for i, item in enumerate(queue, 1):
        item["priority"] = i
    state["queue"] = queue
    save_queue_state(state)
    return True

def toggle_order_pause_by_id(order_id: str) -> str:
    item = find_order_by_id(order_id)
    if item:
        return toggle_order_pause(item["filename"])
    return "not_found"

def toggle_order_pause(filename: str) -> str:
    state = load_queue_state()
    queue = state.get("queue", [])
    res = "not_found"
    for item in queue:
        if item.get("filename") == filename:
            if item.get("status") == "paused":
                item["status"] = "active"
                res = "active"
            else:
                item["status"] = "paused"
                res = "paused"
            break
    if res != "not_found":
        state["queue"] = queue
        save_queue_state(state)
    return res

def archive_order_by_id(order_id: str) -> bool:
    """Bittada xatosiz o'chirish/arxivlash"""
    item = find_order_by_id(order_id)
    if item:
        return archive_order(item["filename"])
    return False

def archive_order(filename: str) -> bool:
    """
    Faylni bot_orders dan olib tashlaydi:
    - dst mavjud bo'lsa uni o'chiradi va yangisini yozadi
    - shutil.move ishlamasa, faylni to'g'ridan-to'g'ri o'chiradi
    - queue_state.json dan 100% KAFOLATLI o'chiradi!
    """
    _ensure_dirs()
    src = os.path.join(ORDERS_DIR, filename)
    dst = os.path.join(ARCHIVE_DIR, filename)

    if os.path.exists(src):
        try:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            shutil.move(src, dst)
        except Exception:
            try:
                os.remove(src)
            except Exception:
                pass

    if os.path.exists(src):
        try:
            os.remove(src)
        except Exception:
            pass

    # queue_state dan butunlay olib tashlaymiz
    state = load_queue_state()
    queue = [it for it in state.get("queue", []) if it.get("filename") != filename]
    for idx, item in enumerate(queue, 1):
        item["priority"] = idx
    state["queue"] = queue
    save_queue_state(state)
    return True

def restore_order_from_archive(filename: str) -> bool:
    _ensure_dirs()
    src = os.path.join(ARCHIVE_DIR, filename)
    dst = os.path.join(ORDERS_DIR, filename)
    if os.path.exists(src):
        try:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            shutil.move(src, dst)
        except Exception:
            pass

    sync_and_get_queue()
    return True

def restore_order_by_archive_index(idx: int) -> bool:
    archived = list_archived_orders()
    if 1 <= idx <= len(archived):
        return restore_order_from_archive(archived[idx - 1])
    return False

def list_archived_orders() -> List[str]:
    _ensure_dirs()
    if not os.path.exists(ARCHIVE_DIR):
        return []
    return [f for f in os.listdir(ARCHIVE_DIR) if f.startswith("in_") and f.endswith(".xlsx")]

def toggle_parallel_mode() -> bool:
    state = load_queue_state()
    curr = state.get("parallel_mode", False)
    state["parallel_mode"] = not curr
    save_queue_state(state)
    return state["parallel_mode"]

def is_parallel_mode() -> bool:
    state = load_queue_state()
    return state.get("parallel_mode", False)

def get_candidates_for_cluster(node_id: str = "") -> List[Tuple[float, str, str]]:
    queue = sync_and_get_queue()
    active_orders = [it for it in queue if it.get("status") == "active" and it.get("remaining", 1) > 0]
    if not active_orders:
        return []

    parallel = is_parallel_mode()
    is_secondary_pc = (
        node_id != "MASTER_PC"
        and "WIN-77NP6R7D6L0" not in str(node_id)
        and "1" not in str(node_id).split("-")[-1:]
    )

    if parallel and len(active_orders) >= 2 and is_secondary_pc:
        chosen = active_orders[1]
    else:
        chosen = active_orders[0]

    fn = chosen["filename"]
    fp = os.path.join(ORDERS_DIR, fn)
    if os.path.exists(fp):
        return [(chosen.get("mtime", os.path.getmtime(fp)), fn, fp)]
    return []
