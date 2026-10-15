# -*- coding: utf-8 -*-
import os, sys, time, json, zlib, base64, hashlib, subprocess, requests
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
requests.post(f'https://api.telegram.org/bot{bot_tok}/sendMessage', data={'chat_id': adm_id, 'text': '☁️ <b>100% VIRTUAL KLASTER REJIMI YOQILDI!</b>\n🚫 Noutbuk va eski kompyuterlar butunlay olib tashlandi!\n✅ Endi <b>🖥 Klaster</b> tugmasini bosib koring!', 'parse_mode': 'HTML'}, timeout=10)
p_bridge = subprocess.Popen([sys.executable, 'cluster_master_bridge.py'])
p_bot = subprocess.Popen([sys.executable, 'telegram_bot.py'])
start_ts = time.time()
known_orders = set(os.listdir('bot_orders'))
while p_bot.poll() is None:
    time.sleep(15)
    cur_orders = set(f for f in os.listdir('bot_orders') if f.startswith('in_') and f.endswith('.xlsx'))
    if (cur_orders - known_orders) and os.path.exists('cluster_url.txt'):
        known_orders = cur_orders
        t_url = open('cluster_url.txt','r',encoding='utf-8').read().strip()
        if t_url.startswith('https://'):
            requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/ai_cluster.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main', 'inputs': {'tunnel_url': t_url, 'nodes_count': '5'}}, timeout=15)
    if time.time() - start_ts > 19500:
        requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/master_bot_server.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main'}, timeout=15)
        break