# -*- coding: utf-8 -*-
import os, sys, time, json, subprocess, shutil, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None

bot_tok = "8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc"
adm_id = 6580113791

# 1. bot_config.json ni avtomatik yaratish
cfg_data = {
    "bot_token": bot_tok,
    "admin_id": adm_id,
    "card_info": "9860 **** **** **** (Admin @OBIDBEK1988 orqali)",
    "start_video_id": ""
}
with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg_data, f, indent=2)

# 2. cloudflared.exe ni joriy papkaga nusxalash
cf_which = shutil.which("cloudflared")
if cf_which and not os.path.exists("cloudflared.exe"):
    try:
        shutil.copy2(cf_which, "cloudflared.exe")
        print(f"[OK] cloudflared.exe nusxalandi: {cf_which}")
    except Exception as e:
        print(f"[WARN] cloudflared nusxalash: {e}")

# 3. Eski holatlarni tozalash
for f_state in ('cluster_nodes_state.json', 'cluster_tried_students.json'):
    if os.path.exists(f_state):
        try: os.remove(f_state)
        except Exception: pass
with open('cluster_nodes_state.json', 'w', encoding='utf-8') as f:
    f.write('{}')

for f_txt in ('natijalar_sertifikatlar.txt', 'xatolar.txt', 'akkountlar.txt'):
    if not os.path.exists(f_txt):
        open(f_txt, 'w', encoding='utf-8').close()

os.makedirs("bot_orders", exist_ok=True)

print("=" * 60)
print("🚀 BULUT MASTER DISPETCHER ISHGA TUSHMOQDA...")
print("=" * 60)
sys.stdout.flush()

# Ko'prik va Telegram botni ishga tushirish
p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])
print(f"[OK] cluster_master_bridge.py ishga tushdi (PID: {p_bridge.pid})")
sys.stdout.flush()

time.sleep(2)
p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
print(f"[OK] telegram_bot.py ishga tushdi (PID: {p_bot.pid})")
sys.stdout.flush()

time.sleep(4)
requests.post(
    f"https://api.telegram.org/bot{bot_tok}/sendMessage",
    data={
        "chat_id": adm_id,
        "text": "☁️ <b>100% VIRTUAL BULUT SERVER ISHGA TUSHDI!</b>\n\n• Eski kompyuterlar tozalandi\n• Bot va Ko'prik to'liq faol\n• Barcha tugmalar ishlayapti!",
        "parse_mode": "HTML"
    },
    timeout=10
)

while True:
    time.sleep(15)
    if p_bot.poll() is not None:
        print(f"[RESTART] telegram_bot.py to'xtab qoldi, qayta yoqilmoqda...")
        sys.stdout.flush()
        p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
    if p_bridge.poll() is not None:
        print(f"[RESTART] cluster_master_bridge.py to'xtab qoldi, qayta yoqilmoqda...")
        sys.stdout.flush()
        p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])
