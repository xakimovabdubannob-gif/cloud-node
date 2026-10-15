# -*- coding: utf-8 -*-
import os, sys, time, json, subprocess, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
bot_tok = '8552767203:AAFvypK6KpVVSZgJAusBtRbTZYyck2armkc'
adm_id = 6580113791
for f_state in ('cluster_nodes_state.json', 'cluster_tried_students.json'):
    if os.path.exists(f_state): os.remove(f_state)
open('cluster_nodes_state.json', 'w', encoding='utf-8').write('{}')
print('Bulutli dispetcher va ko`prik ishga tushmoqda...')
sys.stdout.flush()
p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])
p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
requests.post(f'https://api.telegram.org/bot{bot_tok}/sendMessage', data={'chat_id': adm_id, 'text': '☁️ <b>BARCHA ESKI KOMPYUTERLAR TOZALANDI!</b>\nFaqat 100% Virtual Bulut Server ishlayapti!', 'parse_mode': 'HTML'}, timeout=10)
while True:
    time.sleep(30)
    if p_bot.poll() is not None: p_bot = subprocess.Popen([sys.executable, '-u', 'telegram_bot.py'])
    if p_bridge.poll() is not None: p_bridge = subprocess.Popen([sys.executable, '-u', 'cluster_master_bridge.py'])