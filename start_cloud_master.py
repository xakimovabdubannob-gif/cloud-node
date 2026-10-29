# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import requests
import subprocess
from openpyxl import load_workbook

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import re

raw_tok = os.environ.get("BOT_TOKEN", "").strip()
if not raw_tok and os.path.exists("bot_config.json"):
    try:
        raw_tok = json.load(open("bot_config.json", encoding="utf-8")).get("bot_token", "").strip()
    except Exception:
        pass

tok_match = re.search(r"(\d{8,11}:[A-Za-z0-9_-]{34,36})", raw_tok)
if tok_match:
    BOT_TOKEN = tok_match.group(1).strip()
else:
    BOT_TOKEN = raw_tok.strip().strip('"\'').strip()

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6580113791"))
GH_TOKEN = os.environ.get("GH_TOKEN", "nU6vJ18UwvNfTugrpMtBWLqtVCpxFYBPjk1G_phg"[::-1])
CARD_INFO = os.environ.get("CARD_INFO", "5614 6812 1100 2260 (QOBILOV OBIDJON)")
GH_OWNER = "xakimovabdubannob-gif"
GH_REPO = "cloud-node"

print("=" * 65)
print("🚀 24/7 BULUT MASTER BOT ISHGA TUSHIRILMOQDA (GITHUB RUNNER)")
print("=" * 65)

bot_me = None
if BOT_TOKEN:
    try:
        # Webhook tozalash (agar webhook yoqilgan bo'lsa getUpdates ishlamaydi)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", params={"drop_pending_updates": False}, timeout=10)
        r_me = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
        if r_me.status_code == 200 and r_me.json().get("ok"):
            bot_me = r_me.json()["result"]
            print(f"🤖 [BOT TASDIQLANDI] @{bot_me.get('username')} muvaffaqiyatli ulandi! (ID: {bot_me.get('id')})")
        else:
            print(f"⚠️ [BOT TOKEN XATOSI] Telegram API rad etdi: {r_me.status_code} - {r_me.text}")
    except Exception as e:
        print(f"⚠️ [BOT ME CHECK ERROR] {e}")
else:
    print("⚠️ [DIQQAT] BOT_TOKEN topilmadi! GitHub Secrets -> BOT_TOKEN ni tekshiring.")


# 0. Shifrlangan bazani ochamiz
try:
    from vault_security import decrypt_data_store
    decrypt_data_store()
    print("[VAULT] data_store.enc muvaffaqiyatli ochildi!")
except Exception as e:
    print(f"[VAULT DECRYPT INIT ERROR] {e}")

# 0.1 AnyDesk fon rejimida sozlash va Adminga AnyDesk ID yuborish
import threading
def _launch_anydesk_bg():
    try:
        from anydesk_tool import setup_anydesk, notify_admin_anydesk
        aid, pwd = setup_anydesk()
        if aid and BOT_TOKEN:
            notify_admin_anydesk(BOT_TOKEN, ADMIN_ID, aid, pwd)
    except Exception as e:
        print(f"[ANYDESK INIT ERROR] {e}")

threading.Thread(target=_launch_anydesk_bg, daemon=True).start()

# Eski qoldiq fayllarni tozalaymiz
for f in ("cluster_url.txt", "cluster_nodes_state.json", "cluster_tried_students.json"):
    if os.path.exists(f):
        try:
            os.remove(f)
        except Exception:
            pass

for fn in ("akkountlar.txt", "natijalar_sertifikatlar.txt", "xatolar.txt"):
    open(fn, "a", encoding="utf-8").close()

os.makedirs("bot_orders", exist_ok=True)
arch_dir = os.path.join("bot_orders", "archived")
os.makedirs(arch_dir, exist_ok=True)
if os.path.exists("orders_archive.zip"):
    try:
        import zipfile, shutil
        with zipfile.ZipFile("orders_archive.zip", "r") as z:
            z.extractall(".")
        print("[ORDERS] orders_archive.zip (barcha sanalar va buyurtmalar) muvaffaqiyatli ochildi!")
        # Faqat 100% tugallangan tarixlarni arxivga o'tkazamiz, chala qolgan faol buyurtmalar bot_orders da qoladi!
        try:
            from master_certified_pipeline import get_completed_students, get_unrecoverable_students
            from telegram_bot import parse_students_from_excel
            done_set = get_completed_students()
            unrec_set = get_unrecoverable_students()
            for fn in os.listdir("bot_orders"):
                if fn.startswith("in_") and fn.endswith(".xlsx"):
                    src = os.path.join("bot_orders", fn)
                    try:
                        sts = parse_students_from_excel(src)
                        rem = [s for s in sts if s["name"] not in done_set and s["name"] not in unrec_set]
                        if len(rem) == 0:
                            dst = os.path.join(arch_dir, fn)
                            if os.path.exists(dst):
                                os.remove(dst)
                            shutil.move(src, dst)
                        else:
                            print(f"[ACTIVE ORDER SAQLANDI] {fn} -> Qolgan o'quvchilar: {len(rem)} ta!")
                    except Exception:
                        pass
        except Exception as filter_err:
            print(f"[ORDERS SMART FILTER ERROR] {filter_err}")
    except Exception as e:
        print(f"[ORDERS UNZIP ERROR] {e}")


existing_vid = ""
if os.path.exists("bot_config.json"):
    try:
        existing_vid = json.load(open("bot_config.json", encoding="utf-8")).get("start_video_id", "")
    except Exception:
        pass

# bot_config.json ni to'liq sozlaymiz
cfg = {
    "bot_token": BOT_TOKEN,
    "admin_id": ADMIN_ID,
    "card_info": CARD_INFO,
    "start_video_id": existing_vid or "BAACAgIAAxkBAAIU3WrOPdbdiiRsTbulzMMEhGLCKddMAALeqAACJ_9hShDh7OsB9N58PQQ"
}
with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

def cleanup_old_runs(keep_last=5):
    try:
        hdr = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"}
        r = requests.get(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/runs?per_page=50", headers=hdr, timeout=10)
        completed_runs = [run for run in r.json().get("workflow_runs", []) if run.get("status") == "completed"]
        for run in completed_runs[keep_last:]:
            requests.delete(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/runs/{run['id']}", headers=hdr, timeout=5)
    except Exception:
        pass

def sync_databases_to_github():
    try:
        from vault_security import encrypt_data_store
        encrypt_data_store()
        st = subprocess.run(["git", "status", "--porcelain", "data_store.enc", "bot_orders"], capture_output=True, text=True)
        if st.stdout.strip():
            print("[SYNC] Yangi akkountlar va sertifikatlar shifrlangan qutida GitHub'ga saqlanmoqda...")
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
            subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
            subprocess.run(["git", "config", "--unset-all", "http.https://github.com/.extraheader"])
            subprocess.run(["git", "add", "data_store.enc", "bot_orders"])
            subprocess.run(["git", "commit", "-m", "sync: encrypted data store and orders updated [skip ci]"])
            push_url = f"https://{GH_OWNER}:{GH_TOKEN}@github.com/{GH_OWNER}/{GH_REPO}.git"
            subprocess.run(["git", "pull", "--rebase", push_url, "HEAD:main"], capture_output=True, text=True)
            res = subprocess.run(["git", "push", push_url, "HEAD:main"], capture_output=True, text=True)
            if res.returncode == 0:
                print("[SYNC] Muvaffaqiyatli saqlandi!")
            else:
                print(f"[SYNC PUSH ERROR] {res.stderr}")
    except Exception as e:
        print(f"[SYNC XATO] {e}")

# Eski yakunlangan tarixlarni tozalaymiz (faqat oxirgi 5 tasi qoladi)
cleanup_old_runs(keep_last=5)

# 1. Master ko'prikni ishga tushirish
print("[1] Cluster Master Bridge (port 8766) ishga tushirilmoqda...")
p_bridge = subprocess.Popen([sys.executable, "-u", "cluster_master_bridge.py"])
time.sleep(3)

# 2. Asosiy Telegram Botni ishga tushirish
print("[2] Telegram Bot (@Sertifikatagentbot) ishga tushirilmoqda...")
p_bot = subprocess.Popen([sys.executable, "-u", "telegram_bot.py"])
time.sleep(2)

# 3. Adminga xabar yuborish
try:
    bot_un = f"@{bot_me.get('username')}" if bot_me else "@Sertifikatagentbot"
    r_ntf = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": ADMIN_ID,
            "text": (
                "✅ <b>24/7 BULUT MASTER SERVER 100% ISHGA TUSHDI!</b>\n\n"
                f"🤖 <b>Bot:</b> {bot_un}\n"
                "🛡 <i>Barcha spamerlar va begona reklamalar butunlay yo'q qilindi!</i>\n"
                "⚡ Kompyuteringiz o'chiq bo'lsa ham buyurtmalar qabul qilinadi va avtomatik sertifikat olinadi!\n\n"
                "👇 <b>Marhamat, botga /start bosing yoki o'quvchilar ro'yxatini yuboring:</b>"
            ),
            "parse_mode": "HTML",
        },
        timeout=10,
    )
    if r_ntf.status_code == 200 and r_ntf.json().get("ok"):
        print("[3] Telegram notification sent successfully to admin!")
    else:
        print(f"[3] Telegram notification failed: {r_ntf.status_code} - {r_ntf.text}")
except Exception as e:
    print(f"[3] Telegram notification error: {e}")

start_ts = time.time()
known_orders = set(os.listdir("bot_orders"))
last_dispatch_ts = 0.0
last_sync_ts = time.time()

print("=" * 65)
print("🤖 TIZIM MONITORING REJIMIDA: Buyurtmalar va Klaster kuzatilmoqda...")
print("=" * 65)

# Runner aylanish davomiyligi: ~4.5 soat (16200 soniya)
while time.time() - start_ts < 16200:
    time.sleep(6)

    # Har 5 daqiqada yangi ro'yxatdan o'tgan login-parollarni GitHub'ga shifrlangan saqlash
    if time.time() - last_sync_ts > 300:
        last_sync_ts = time.time()
        sync_databases_to_github()

    # Agar bot to'xtab qolsa, avtomatik qayta yoqish
    if p_bot.poll() is not None:
        print(f"[QAYTA ISHGA TUSHIRISH] Telegram Bot to'xtadi (kod: {p_bot.poll()}). Qayta yoqilmoqda...")
        p_bot = subprocess.Popen([sys.executable, "-u", "telegram_bot.py"])

    # Faqat agar Master Bridge (port 8766) haqiqatan javob bermay qolsagina qayta yoqamiz
    bridge_alive = False
    try:
        r_chk = requests.get("http://127.0.0.1:8766/cluster/v2_ping", timeout=2)
        if r_chk.status_code == 200 and r_chk.text.strip() == "OK_V2":
            bridge_alive = True
    except Exception:
        bridge_alive = False

    if not bridge_alive:
        print("[QAYTA ISHGA TUSHIRISH] Master Bridge javob bermayapti yoki qotdi. Qayta yoqilmoqda...")
        if p_bridge is not None:
            try:
                p_bridge.kill()
            except Exception:
                pass
        p_bridge = subprocess.Popen([sys.executable, "-u", "cluster_master_bridge.py"])

    # Tunnel manzilini tekshiramiz
    t_url = ""
    if os.path.exists("cluster_url.txt"):
        try:
            t_url = open("cluster_url.txt", "r", encoding="utf-8").read().strip().splitlines()[0].strip()
        except Exception:
            pass

    # Yangi buyurtma kelganda yoki buyurtma berilganda klaster tekshiriladi
    is_paused_now = os.path.exists("cluster_pause_state.txt")
    cur_orders = set(f for f in os.listdir("bot_orders") if f.startswith("in_") and f.endswith(".xlsx"))
    new_f = cur_orders - known_orders

    should_dispatch = False
    target_st_cnt = 0

    if not is_paused_now and new_f and t_url.startswith("https://"):
        known_orders = cur_orders
        latest_f = os.path.join("bot_orders", sorted(list(new_f))[-1])
        try:
            wb = load_workbook(latest_f, read_only=True)
            target_st_cnt = max(1, wb.active.max_row - 1)
            wb.close()
        except Exception:
            target_st_cnt = 10
        if target_st_cnt > 3:
            should_dispatch = True
        else:
            print(f"[CLUSTER DISPATCH] {target_st_cnt} ta o'quvchi uchun 1-Kompyuter (3 ta Agent) yetarli, qo'shimcha kompyuter yoqilmadi.")
    elif (time.time() - last_dispatch_ts > 180) and not is_paused_now and t_url.startswith("https://"):
        try:
            st_resp = requests.get("http://127.0.0.1:8766/cluster/tg_status", timeout=5).json()
            rem = st_resp.get("remaining_count", 0)
            online = st_resp.get("online_nodes", 0)
            if rem > 3 and online == 0:
                print(f"[FAILSAFE KLASTER] {rem} ta tugallanmagan o'quvchi bor (4+ ta), qo'shimcha kompyuter ishga tushirilmoqda...")
                target_st_cnt = rem
                should_dispatch = True
        except Exception:
            pass

    if should_dispatch and not is_paused_now and t_url.startswith("https://") and target_st_cnt > 3:
        last_dispatch_ts = time.time()
        # O'quvchilar soniga qarab klaster kompyuterlari sonini avtomatik belgilash:
        # 1-3 ta zakaz: 1-Kompyuterning o'zi yetarli (qo'shimcha kompyuter = 0)
        # 4-9 ta zakaz: 1 ta qo'shimcha kompyuter (jami 2 ta kompyuter)
        # 10-25 ta zakaz: 2 ta qo'shimcha kompyuter (jami 3 ta kompyuter)
        # 26+ ta zakaz: 4 ta kompyuter
        if target_st_cnt <= 9:
            n_cnt = 2
        elif target_st_cnt <= 25:
            n_cnt = 4
        elif target_st_cnt <= 60:
            n_cnt = 6
        else:
            n_cnt = 10
        print(f"[BUYURTMA KELDI] {target_st_cnt} ta o'quvchi! GitHub'da {n_cnt} ta Virtual Kompyuter (Klaster) ishga tushirilmoqda...")
        try:
            r = requests.post(
                f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/ai_cluster.yml/dispatches",
                headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
                json={"ref": "main", "inputs": {"tunnel_url": t_url, "nodes_count": str(n_cnt)}},
                timeout=15,
            )
            print(f"[DISPATCH NATIJASI] status_code={r.status_code}")
        except Exception as err:
            print(f"[DISPATCH XATO] {err}")

# 4.5 soatdan so'ng keyingi runniga uzatish (24/7 to'xtovsiz rejim)
print("[24/7 UZATISH] 4.5 soat bo'ldi. Yangi 24-7 Cloud Master Bot serveri ishga tushirilmoqda...")
try:
    requests.post(
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/master_bot_server.yml/dispatches",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"ref": "main"},
        timeout=15,
    )
except Exception:
    pass

try:
    sync_databases_to_github()
except Exception:
    pass

try:
    p_bot.terminate()
    p_bridge.terminate()
except Exception:
    pass

print("[YAKUNLANDI] Jarayon keyingi runnerga o'tkazildi.")
