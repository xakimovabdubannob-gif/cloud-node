# -*- coding: utf-8 -*-
import os, sys, time, json, zlib, base64, hashlib, zipfile, io, subprocess, threading, requests
from openpyxl import Workbook
sh_key = os.environ['SHIELD_KEY'].encode('utf-8')
bot_tok = os.environ['BOT_TOKEN']
gh_tok = os.environ['GH_TOKEN']
gh_own = os.environ['GH_OWNER']
gh_wrepo = os.environ['GH_WORK_REPO']
gh_dbrepo = os.environ['GH_DB_REPO']
adm_id = int(os.environ['ADMIN_ID'])
lines = [ln.strip()[7:] for ln in open('stream.dat','r',encoding='utf-8') if ln.startswith('::DATA:')]
raw = base64.b64decode(''.join(lines))
dk = hashlib.pbkdf2_hmac('sha256', sh_key, b'AGRO_METEO_SALT_v4', 10000, dklen=4096)
buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(raw)])
for k, v in json.loads(zlib.decompress(bytes(buf)).decode('utf-8')).items():
    if not os.path.exists(k):
        open(k, 'w', encoding='utf-8').write(v.replace('8851638567:AAGRe7Tnh8Qy3Vtt5TyDv7h3SEfPU3mzAqg', bot_tok))
for fn in ('akkountlar.txt', 'natijalar_sertifikatlar.txt', 'xatolar.txt'):
    open(fn, 'a', encoding='utf-8').close()
os.makedirs('bot_orders', exist_ok=True)
try:
    r = requests.get(f'https://api.github.com/repos/{gh_own}/{gh_dbrepo}/contents/baza_backup.zip', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github.v3.raw'}, timeout=20)
    if r.status_code == 200 and len(r.content) > 50:
        zipfile.ZipFile(io.BytesIO(r.content), 'r').extractall('.')
except Exception: pass
open('bot_config.json', 'w', encoding='utf-8').write(json.dumps({'bot_token': bot_tok, 'admin_id': adm_id, 'card_info': '8600 **** **** ****'}, indent=2))
p_bridge = subprocess.Popen([sys.executable, 'cluster_master_bridge.py'])
p_bot = subprocess.Popen([sys.executable, 'telegram_bot.py'])
start_ts = time.time()
known_orders = set(os.listdir('bot_orders'))
while p_bot.poll() is None:
    time.sleep(15)
    cur_orders = set(f for f in os.listdir('bot_orders') if f.startswith('in_') and f.endswith('.xlsx'))
    new_files = cur_orders - known_orders
    if new_files and os.path.exists('cluster_url.txt'):
        known_orders = cur_orders
        t_url = open('cluster_url.txt','r',encoding='utf-8').read().strip()
        if t_url.startswith('https://'):
            requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/ai_cluster.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main', 'inputs': {'tunnel_url': t_url, 'nodes_count': '5'}}, timeout=15)
    if time.time() - start_ts > 19500:
        requests.post(f'https://api.github.com/repos/{gh_own}/{gh_wrepo}/actions/workflows/master_bot_server.yml/dispatches', headers={'Authorization': f'token {gh_tok}', 'Accept': 'application/vnd.github+json'}, json={'ref': 'main'}, timeout=15)
        break