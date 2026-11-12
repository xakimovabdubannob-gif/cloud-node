@echo off
chcp 65001 >nul
title UZBEK CODERS - BARCHA KOMPYUTERLAR VA SERTIFIKATLAR HOLATI
cd /d "%~dp0"

python -c "import json, time, os; from cluster_master_bridge import parse_excel_students, get_completed_students, get_unrecoverable_students; done=get_completed_students(); unrec=get_unrecoverable_students(); print('='*75); print(f'JAMI SERTIFIKATLAR BAZADA: {len(done)} ta | JSHSHIR/XATO: {len(unrec)} ta'); cands=sorted([(os.path.getmtime(os.path.join('bot_orders',f)),os.path.join('bot_orders',f)) for f in os.listdir('bot_orders') if f.startswith('in_') and f.endswith('.xlsx')],reverse=True); st=parse_excel_students(cands[0][1]) if cands else []; d_cur=sum(1 for s in st if s['name'] in done); u_cur=sum(1 for s in st if s['name'] in unrec); print(f'JORIY BUYURTMA ({len(st)} ta): Olindi={d_cur} ta | Xato={u_cur} ta | Qoldi={len(st)-d_cur-u_cur} ta'); print('='*75); nodes=json.load(open('cluster_nodes_state.json',encoding='utf-8')) if os.path.exists('cluster_nodes_state.json') else {}; now=time.time(); [print(f'[{i+2}-Kompyuter] {v.get(\"pc_name\")} ({v.get(\"ram_gb\")}GB, {v.get(\"workers\")} Agent) | Holat: {\"ONLAYN\" if now-v.get(\"last_seen\",0)<120 else \"UZILGAN\"}\n   Oxirgi ish: {v.get(\"status\",\"-\")}') for i,(k,v) in enumerate(nodes.items())]; print('='*75)"

echo.
pause
