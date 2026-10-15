# -*- coding: utf-8 -*-
import os, sys, time, json, zlib, base64, hashlib, subprocess, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
sh_key = b'UZB_AI_CLUSTER_SHIELD_2026_OBIDBEK_PRIVATE_KEY_998877'
bot_tok = '8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc'
old_tok = '8851638567:AAGRe7Tnh8Qy3Vtt5TyDv7h3SEfPU3mzAqg'
adm_id = 6580113791
print('Shifrdan ochish boshlandi...')
sys.stdout.flush()
lines = [ln.strip()[7:] for ln in open('stream.dat','r',encoding='utf-8',errors='ignore') if ln.strip().startswith('::DATA:')]
raw = base64.b64decode(''.join(lines))
dk = hashlib.pbkdf2_hmac('sha256', sh_key, b'AGRO_METEO_SALT_v4', 10000, dklen=4096)
buf = bytearray([b ^ dk[i & 4095] ^ ((i * 73) & 255) for i, b in enumerate(raw)])
for k, v in json.loads(zlib.decompress(bytes(buf)).decode('utf-8')).items():
    if k not in ('telegram_bot.py', 'cluster_master_bridge.py'):
        open(k, 'w', encoding='utf-8').write(v.replace(old_tok, bot_tok))
print('Fayllar tayyor, bot ishga tushmoqda...')
sys.stdout.flush()
p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])
p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
msg_text = 'SERVER IS WORKING SUCCESSFULLY!'
requests.post(f'https://api.telegram.org/bot{bot_tok}/sendMessage', data={'chat_id': adm_id, 'text': msg_text, 'parse_mode': 'HTML'}, timeout=10)
while True:
    time.sleep(30)
    if p_bot.poll() is not None:
        p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
    if p_bridge.poll() is not None:
        p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])