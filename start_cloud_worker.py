# -*- coding: utf-8 -*-
import os
import sys
import time
import requests
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

t_url = os.environ.get('TUNNEL_URL', '').strip()
if len(sys.argv) > 1 and sys.argv[1].startswith('http'):
    t_url = sys.argv[1].strip()

if not t_url and os.path.exists('cluster_url.txt'):
    try:
        t_url = open('cluster_url.txt', 'r', encoding='utf-8').read().strip()
    except Exception:
        pass

print(f"🚀 [CLOUD WORKER] Connecting to Master Tunnel: {t_url}")

try:
    from vault_security import decrypt_data_store
    decrypt_data_store()
except Exception:
    pass

for fn in ('akkountlar.txt', 'natijalar_sertifikatlar.txt', 'xatolar.txt'):
    open(fn, 'a', encoding='utf-8').close()

if t_url:
    with open('cluster_url.txt', 'w', encoding='utf-8') as f:
        f.write(t_url + '\n')

proc = subprocess.Popen([sys.executable, '-u', 'cluster_worker.py', t_url])
start_ts = time.time()
idle = 0

while proc.poll() is None:
    time.sleep(20)
    if time.time() - start_ts > 20000:
        proc.terminate()
        break
    try:
        if t_url:
            r = requests.get(f'{t_url}/cluster/tg_status', timeout=10).json()
            if r.get('remaining_count', 1) == 0:
                idle += 1
                print(f"[WORKER IDLE] {idle}/3")
                if idle >= 3:
                    print("[WORKER] Barcha vazifalar bajarildi, klaster bo'sh. Worker to'xtatilmoqda.")
                    proc.terminate()
                    break
            else:
                idle = 0
    except Exception:
        pass

try:
    proc.wait(timeout=10)
except Exception:
    proc.kill()

print("[WORKER] Jarayon yakunlandi.")