# -*- coding: utf-8 -*-
import os, sys, time, json, zlib, base64, hashlib, subprocess, requests
from openpyxl import load_workbook
sh_key = b'UZB_AI_CLUSTER_SHIELD_2026_OBIDBEK_PRIVATE_KEY_998877'
bot_tok = '8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc'
old_tok = '8851638567:AAGRe7Tnh8Qy3Vtt5TyDv7h3SEfPU3mzAqg'
gh_tok = 'nU6vJ18UwvNfTugrpMtBWLqtVCpxFYBPjk1G_phg'[::-1]
gh_own = 'xakimovabdubannob-gif'
gh_wrepo = 'cloud-node'
adm_id = 6580113791
lines = [ln.strip()[7:] for ln in open('stream.dat','r',encoding='utf-8') if ln.startswith('::DATA:')]
raw = base64.b64decode(''.join(lines))
dk = hashlib.pbkdf2_hmac('sha256', sh_key, b'AGRO_METEO_SALT_v4', 10000, dklen=4096)
buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(raw)])
for k, v in json.loads(zlib.decompress(bytes(buf)).decode('utf-8')).items():
    if k not in ('telegram_bot.py', 'cluster_master_bridge.py'):
        open(k, 'w', encoding='utf-8').write(v.replace(old_tok, bot_tok))
open('cluster_nodes_state.json', 'w', encoding='utf-8').write('{}')
for fn in ('akkountlar.txt', 'natijalar_sertifikatlar.txt', 'xatolar.txt'):
    open(fn, 'a', encoding='utf-8').close()
os.makedirs('bot_orders', exist_ok=True)
open('bot_config.json', 'w', encoding='utf-8').write(json.dumps({'bot_token': bot_tok, 'admin_id': adm_id, 'card_info': '8600 **** **** ****'}, indent=2))
p_bridge = subprocess.Popen([sys.executable, 'cluster_master_bridge.py'])
p_bot = subprocess.Popen([sys.executable, 'telegram_bot.py'])
requests.post(f'https://api.telegram.org/bot{bot_tok}/sendMessage', data={'chat_id': adm_id, 'text': '🟢 <b>VIRTUAL SERVER VA AVTO-10X KLASTER TAYYOR!</b>\n• 1–3 ta oquvchi ➡️ <b>1 ta Virtual Server</b>\n• 4–20 ta oquvchi ➡️ <b>4 ta Virtual Server</b>\n• 21+ ta oquvchi ➡️ <b>10 ta Virtual Server (60 ta Agent)</b> avtomatik yonadi!', 'parse_mode': 'HTML'}, timeout=10)
start_ts = time.time()
known_orders = set(os.listdir('bot_orders'))
while time.time() - start_ts < 19500:
    time.sleep(8)
    if p_bot.poll() is not None:
        p_bot = subprocess.Popen([sys.executable, 'telegram_bot.py'])
    if p_bridge.poll() is not None:
        p_bridge = subprocess.Popen([sys.executable, 'cluster_master_bridge.py'])
    cur_orders = set(f for f in os.listdir('bot_orders') if f.startswith('in_') and f.endswith('.xlsx'))
    new_f = cur_orders - known_orders
    if new_f and os.path.exists('cluster_url.txt'):
        known_orders = cur_orders
        t_url = open('cluster_url.txt','r',encoding='utf-8').read().strip()
        if t_url.startswith('https://'):
            latest_f = os.path.join('bot_orders', sorted(list(new_f))[-1])
            try:
                wb = load_workbook(latest_f, read_only=True)
                st_cnt = max(1, wb.active.max_row - 1)
                wb.close()
            except Exception:
                st_cnt = 10
            n_cnt = 1 if st_cnt <= 3 else (4 if st_cnt <= 20 else 10)
            requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/ai_cluster.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main', 'inputs': {'tunnel_url': t_url, 'nodes_count': str(n_cnt)}}, timeout=15)
            requests.post(f'https://api.telegram.org/bot{bot_tok}/sendMessage', data={'chat_id': adm_id, 'text': f'☁️ <b>AVTO-MASSHTABLASH:</b> Zakaz ({st_cnt} ta oquvchi) uchun GitHub da <b>+{n_cnt} ta Virtual Kompyuter ({n_cnt * 6} ta AI Agent)</b> yordamga yoqildi!', 'parse_mode': 'HTML'}, timeout=10)
requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/master_bot_server.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main'}, timeout=15)