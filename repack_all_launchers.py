# -*- coding: utf-8 -*-
import os
import zlib
import base64
import hashlib
import json
import requests

SHIELD_KEY = b"UZB_AI_CLUSTER_SHIELD_2026_OBIDBEK_PRIVATE_KEY_998877"
SALT = b"AGRO_METEO_SALT_v4"
TUNNEL_URL = "https://indicator-cod-motherboard-tribal.trycloudflare.com"

with open("master_certified_pipeline.py", "r", encoding="utf-8") as f:
    fresh_pipeline = f.read()

with open("cluster_worker.py", "r", encoding="utf-8") as f:
    fresh_worker = f.read()

boot_node_code = """import os, sys, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["HEADLESS"] = "0"
os.environ["WORKER_COUNT"] = "4"
sys.exit(subprocess.run([sys.executable, "-u", "cluster_worker.py"]).returncode)
"""

def repack_bat(bat_path):
    if not os.path.exists(bat_path):
        print(f"[!] {bat_path} topilmadi!")
        return False
    with open(bat_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_bat = f.read()
    
    lines = [ln.strip()[7:] for ln in raw_bat.splitlines() if ln.strip().startswith("::DATA:")]
    if not lines:
        print(f"[!] {bat_path} ichida ::DATA: topilmadi!")
        return False
        
    raw = base64.b64decode("".join(lines))
    dk = hashlib.pbkdf2_hmac("sha256", SHIELD_KEY, SALT, 10000, dklen=4096)
    buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(raw)])
    payload = json.loads(zlib.decompress(bytes(buf)).decode("utf-8"))
    
    # Update pipeline, worker, boot_node and tunnel
    payload["master_certified_pipeline.py"] = fresh_pipeline
    payload["cluster_worker.py"] = fresh_worker
    payload["boot_node.py"] = boot_node_code
    payload["cluster_url.txt"] = TUNNEL_URL + "\n"
    
    # Recompress
    comp = zlib.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), 9)
    enc_buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(comp)])
    b64_str = base64.b64encode(bytes(enc_buf)).decode("ascii")
    
    new_data_lines = ["::DATA:" + b64_str[i:i+120] for i in range(0, len(b64_str), 120)]
    non_data_lines = [ln for ln in raw_bat.splitlines() if not ln.strip().startswith("::DATA:")]
    
    # Make sure cluster_url in bat text is also updated
    updated_non_data = []
    for l in non_data_lines:
        if "trycloudflare.com" in l and "echo " in l:
            updated_non_data.append(f'echo {TUNNEL_URL}> "%WORK_DIR%\\cluster_url.txt"')
        else:
            updated_non_data.append(l)
            
    new_bat_content = "\n".join(updated_non_data + new_data_lines) + "\n"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(new_bat_content)
    print(f"[OK] {bat_path} yangilandi va repacking muvaffaqiyatli bo'ldi (4 ta Agent + Ruscha testlar)!")
    return True

repack_bat("UNIVERSAL_OQIM_QOSHISH.bat")

# Send updated bat file to Admin Telegram
BOT_TOKEN = "8552767203:AAEVjdw0jviuxMuJipycWSTesz7vB-sTmn8"
ADMIN_ID = 6580113791

caption = (
    "⚡ <b>YANGILANDI: 4 TA PARALLEL AGENT + RUSCHA TO'LIQ MOSLASHUV</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚙️ <b>O'zgarishlar:</b>\n"
    "• 🤖 <b>4 ta Agent (16GB RAM uchun eng yengil va stabil rejim)</b>;\n"
    "• 🇷🇺 <b>Ruscha testlar va savollar javoblari 100% to'liq ulandi</b> (Quiz 1, 2, 3, 4 barcha sinonim variantlari bilan);\n"
    "• 🎬 <b>Videolar va Reading ruscha knopkalari</b> ('Отметить как пройденное', 'Отметить как выполненное', 'Далее', 'Следующий материал');\n"
    "• 📝 <b>Test topshirish va Honor Code</b> ('Сдать', 'Отправить', 'Я понимаю', 'Кодекс чести');\n"
    "• 🚀 <b>'Запустить курс'</b> tugmasi bir zumda bosiladi!\n\n"
    "👇 <i>Eskisini yopib, ushbu yangi faylni ishga tushiring!</i>"
)

try:
    with open("UNIVERSAL_OQIM_QOSHISH.bat", "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            data={"chat_id": ADMIN_ID, "caption": caption, "parse_mode": "HTML"},
            files={"document": ("UNIVERSAL_OQIM_QOSHISH.bat", f, "application/octet-stream")},
            timeout=30
        )
        print("Telegram sendDocument status:", r.status_code, r.json().get("ok"))
except Exception as e:
    print("Telegram error:", e)
