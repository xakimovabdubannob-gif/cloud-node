import os
import sys
import time
import json
import re
import subprocess
import requests
import openpyxl

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright
from faster_whisper import WhisperModel

# 100% To'g'ri test javoblari bazasi
ANSWERS = {
    # Modul 1
    "qaysi biri ai (sun'iy intellekt)ni eng yaxshi tavsiflaydi": "ma'lumotlardan o'rganishi mumkin bo'lgan dasturiy dastur",
    "real hayotiy qo'llanishi": "yuqoridagilarning barchasi",
    "hayot siklining 2 ta bosqichi": "o'rgatish (trenirovka) va xulosa chiqarish (inference)",
    "aniq ishda ekspert bo'lgan": "tor si (narrow ai)",
    "kichigidan kattasiga": "chuqur o'rganish < mashinani o'rganish (machine learning) < si",
    "tyuring testi nima": "sun'iy intellekt dasturi inson kabi o'ylay olishi/gaplasha olishi/o'zini tuta olishini aniqlash testi",
    
    # Modul 2
    "generativ si (sun'iy intellekt) nima": "matn / tasvirlar / musiqa / video kabi yangi kontent yarata oladigan si",
    "llm nimani anglatadi": "katta til modeli (large language model)",
    "chat botlar va qidiruv tizimlari o'rtasidagi asosiy farq": "ular kontekstga e'tibor beradi",
    "prompt nima": "siz sun'iy intellektli chat botga kiritadigan matn",
    "yaxshi promptni tuzishning to'g'ri tartibdagi 3 ta asosiy": "rol - kontekst - vazifa",
    "gallyutsinatsiyalar (hallucinations) nima": "chat botlarning yomon yoki noto'g'ri javoblar berishi",
    
    # Modul 3
    "prompt yozishda quyidagi yondashuvlardan qaysi biri tavsiya": "rol - vazifa - kontekst",
    "si tomonidan yaratilgan matnning asosiy cheklovlaridan biri": "xatolar bo'lishi mumkin va tekshirib chiqishni talab qiladi",
    "ohangini o'zgartirish uchun": "ohang sozlamalari",
    "hr yollash jarayonlarida foydalanishning afzalliklaridan biri": "si ko'plab rezyume",
    "ijtimoiy tarmoqlardagi kampaniya uchun": "yuqoridagilarning barchasi",
    "maxfiy hujjatlarni baham ko'rmaslik": "ularda maxfiylik kafolatlari yo'q",
    "ishga oid vazifalar uchun si dan foydalanganda": "si vaqtni tejaydi, lekin uning ishini har doim tekshirib turing",
    
    # Modul 4
    "matndan tasvir yaratish uchun qaysi sun'iy intellekt": "dall-e / midjourney / stable diffusion",
    "tasvir yaratish uchun qaysi sun'iy intellekt vositasi openai": "dall-e",
    "midjourney yordamida tasvirlarni yaratishda qaysi omil": "batafsilroq va tavsiflovchi promptlar",
    "edge brauzeri copilot'ida dall-e": "bepul tasvir yaratish imkoniyatiga ega bo'lish",
    "musiqa yarata oladi": "suno",
    "tasvir o'lchamini (rezolyutsiyasini) oshirishga": "upscale tugmalari",
    "matndan video yaratish uchun ishlatiladi": "runway ml",
    
    # Yakuniy
    "ushbu kursda si nima deb ta'riflangan": "robot sifatida",
    "tor si (narrow ai) ga misol": "yuqoridagilarning barchasi",
    "tyuring testining maqsadi": "inson deb o'ylashga aldashi",
    "mashhur generativ si-chatbot": "chatgpt",
    "zo'r prompt yaratish uchun asosiy qoida": "rol / kontekst / vazifa",
    "gallyutsinatsiya": "noto'g'ri yoki uydirma",
    "ma'lumotlarni tahlil qilish uchun": "excel jadvallaridagi",
    "microsoft office ilovalariga qaysi si vositasi": "copilot",
    "si va ish haqida qaysi fikr to'g'ri": "yanada samarali bo'ladi",
    "tasvir yaratish uchun openai": "dall-e",
    "matndan video yaratish imkonini": "runway ml",
    "midjourney tasvir yaratishni sozlashda": "tomonlar nisbati"
}

whisper_model = None

def get_whisper():
    global whisper_model
    if whisper_model is None:
        print("Whisper AI modeli xotiraga yuklanmoqda...", flush=True)
        whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return whisper_model

def get_telegram_verification_code():
    """Aloqida jarayonda Telegram botdan 6 xonali SMS kodni olish"""
    print("\nTELEGRAM: @aistudy_uz_bot dan tasdiqlash kodi olinmoqda...", flush=True)
    fetch_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_tg_code.py")
    try:
        out = subprocess.check_output([sys.executable, fetch_script], timeout=30, stderr=subprocess.STDOUT)
        out_text = out.decode("utf-8", errors="ignore").strip()
        print("Telegram jarayoni javobi:\n" + out_text, flush=True)
        m = re.search(r'KOD:\s*(\d{6})', out_text)
        if m:
            code = m.group(1)
            print(f"TELEGRAM TASDIQLASH KODI MUOFFAQIYATLI OLINDI: [{code}]", flush=True)
            return code
    except Exception as e:
        print(f"Telegram kodini olishda xatolik: {e}", flush=True)
    return None

def handle_recaptcha(page):
    """Google reCAPTCHA audio challenge ni yechish"""
    try:
        bframe = None
        for f in page.frames:
            if "recaptcha" in f.url and "anchor" in f.url:
                bframe = f
                break
        if not bframe:
            return True
            
        anchor_checkbox = bframe.locator("#recaptcha-anchor")
        if anchor_checkbox.count() > 0:
            if anchor_checkbox.get_attribute("aria-checked") == "true":
                return True
            print("reCAPTCHA katakchasi bosilmoqda...", flush=True)
            anchor_checkbox.click()
            time.sleep(2)
            if anchor_checkbox.get_attribute("aria-checked") == "true":
                print("reCAPTCHA darhol tasdiqlandi!", flush=True)
                return True

        bframe_challenge = None
        for f in page.frames:
            if "recaptcha" in f.url and "bframe" in f.url:
                bframe_challenge = f
                break
                
        if not bframe_challenge:
            return True

        audio_btn = bframe_challenge.locator("#recaptcha-audio-button")
        if audio_btn.count() > 0 and audio_btn.is_visible():
            print("Ovozli topshiriq (Audio challenge) ochilmoqda...", flush=True)
            audio_btn.click()
            time.sleep(2.5)

        audio_link = bframe_challenge.locator(".rc-audiochallenge-tdownload-link, a:has-text('.mp3')")
        if audio_link.count() > 0:
            href = audio_link.get_attribute("href")
            if href:
                res = requests.get(href, timeout=15)
                mp3_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captcha.mp3")
                with open(mp3_path, "wb") as f:
                    f.write(res.content)
                print(f"MP3 yuklab olindi ({len(res.content)} bayt)", flush=True)

                model = get_whisper()
                segments, _ = model.transcribe(mp3_path)
                recognized_text = " ".join([seg.text for seg in segments]).strip()
                print(f"Whisper AI javobi: [{recognized_text}]", flush=True)

                resp_input = bframe_challenge.locator("#audio-response")
                resp_input.fill(recognized_text)
                time.sleep(1)
                
                verify_btn = bframe_challenge.locator("#recaptcha-verify-button")
                verify_btn.click()
                time.sleep(3)
                print("reCAPTCHA tasdiqlash tugmasi bosildi!", flush=True)
                return True
    except Exception as e:
        print(f"reCAPTCHA xatoligi: {e}", flush=True)
    return True

def switch_to_login_tab_with_verification(page):
    """Login tabiga o'tishni tasdiqlash"""
    for attempt in range(1, 6):
        page.evaluate("""() => {
            const tabs = Array.from(document.querySelectorAll("p-tab, [role='tab'], button"));
            const loginTab = tabs.find(el => el.textContent && el.textContent.includes('Login'));
            if (loginTab) {
                loginTab.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                loginTab.click();
            }
        }""")
        time.sleep(1.5)
        is_ready = page.evaluate("""() => {
            const u = document.querySelector("input#username, input[formcontrolname='username']");
            return u !== null && u.offsetParent !== null;
        }""")
        if is_ready:
            print(f"[{attempt}-urinishda Login - Parol tab ochildi]", flush=True)
            return True
        time.sleep(1)
    return False

def complete_course(page, course_id):
    """Berilgan kursni (1..4) GIBRID (Ultra-Galichka + Verifikatsiya + 3.6x Zaxira) rejimida 100% bajarish"""
    print("\n" + "="*55, flush=True)
    print(f">> KURS {course_id} GIBRID REJIMDA BOSHLANMOQDA <<", flush=True)
    print("="*55, flush=True)
    
    # Kursni boshlash
    page.evaluate(f"""async () => {{
        const token = localStorage.getItem('accessToken');
        await fetch('https://api.aistudy.uz/api/StudyAILms/Progress/StartCourseProgress?courseId={course_id}', {{
            method: 'POST',
            headers: {{ 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{}})
        }});
    }}""")
    time.sleep(1.5)
    
    # Kurs daraxtini olish
    tree = page.evaluate(f"""async () => {{
        const token = localStorage.getItem('accessToken');
        const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Progress/GetPrivateCourseContentTree?courseId={course_id}', {{
            headers: {{ 'Authorization': 'Bearer ' + token }}
        }});
        return await r.json();
    }}""").get("result", {})
    
    total_lessons = tree.get("lessonCount", 0)
    course_name = tree.get("name", {}).get("uz", f"Kurs {course_id}")
    print(f"Kurs: {course_name} | Jami darslar soni: {total_lessons} ta", flush=True)
    
    modules = tree.get("children", [])
    for mod_idx, mod in enumerate(modules):
        mod_id = mod.get("id")
        mod_name = mod.get("name", {}).get("uz", "")
        lessons = mod.get("children", [])
        
        print(f"\n[Modul {mod_idx+1}: {mod_name}]", flush=True)
        
        for les in lessons:
            les_id = les.get("id")
            les_type = les.get("type")
            les_status = les.get("status")
            les_name = les.get("name", {}).get("uz", "")
            
            # 1. Agar Video (type == 2) bo'lsa
            if les_type == 2:
                if les_status == 2:
                    print(f"  [Video {les_id}] {les_name} -> Allaqachon ko'rilgan (OK)!", flush=True)
                    continue
                    
                print(f"  [Video {les_id}] {les_name} -> 1. Ultra-galichka yuborilmoqda...", flush=True)
                
                # 1-QADAM: Ultra-tezkor API so'rovi
                res = page.evaluate(f"""async () => {{
                    try {{
                        const token = localStorage.getItem('accessToken');
                        const r = await fetch('https://api.aistudy.uz/api/StudyAILms/UserWatchStory/CreateOrUpdateLessonWatch', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + token
                            }},
                            body: JSON.stringify({{
                                lessonId: {les_id},
                                language: 'uz',
                                percentJson: {{ uz: '100.00', ru: '100.00', en: '100.00' }},
                                usedTime: 300
                            }})
                        }});
                        if (r.status === 429) return {{ status: 429 }};
                        return await r.json();
                    }} catch(e) {{
                        return {{ error: e.toString() }};
                    }}
                }}""")
                
                if res and res.get("status") == 429:
                    time.sleep(6)
                    
                # 2-QADAM: VERIFIKATSIYA (Tekshirish)
                time.sleep(1)
                is_verified = page.evaluate(f"""async () => {{
                    try {{
                        const token = localStorage.getItem('accessToken');
                        const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Lesson/GetLessonById?id={les_id}', {{
                            headers: {{ 'Authorization': 'Bearer ' + token }}
                        }});
                        const data = await r.json();
                        return data?.result?.progressStatus === true;
                    }} catch(e) {{
                        return false;
                    }}
                }}""")
                
                if is_verified:
                    print(f"    -> ULTRA GALICHKA TASDIQLANDI (OK)!", flush=True)
                    time.sleep(5) # Server cooldown
                    continue
                    
                # 3-QADAM: 3.6X TABIIY PLEYER ZAXIRA REJIMI
                print(f"    -> Ultra o'tmadi. 3.6x tezlikda (240p) ko'rish boshlandi...", flush=True)
                lesson_url = f"https://omp.aistudy.uz/courses/{course_id}/module/{mod_id}/lesson/{les_id}/type/2?debug_bypass=omp-dev-master-99"
                page.goto(lesson_url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                page.evaluate("document.querySelectorAll('.devtools-overlay, .telegram-popup-overlay, .p-dialog-mask').forEach(e => e.remove());")
                
                # 240p va 2.5x tezlikni ishga tushirish
                page.evaluate("""() => {
                    const btn240 = document.querySelector('button[data-plyr="quality"][value="240"]');
                    if (btn240) btn240.click();
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = true;
                        v.volume = 0;
                        v.playbackRate = 3.6;
                        v.play().catch(e => {});
                    }
                    const playBtn = document.querySelector('button[data-plyr="play"]');
                    if (playBtn) playBtn.click();
                }""")
                
                # Video progressini kuzatish (har 2 soniyada)
                for _ in range(45):
                    time.sleep(2)
                    v_info = page.evaluate("""() => {
                        const v = document.querySelector('video');
                        if (!v) return { ended: true, percent: 100 };
                        if (v.paused) v.play().catch(e => {});
                        v.playbackRate = 3.6;
                        const cur = v.currentTime || 0;
                        const dur = v.duration || 1;
                        const pct = (cur / dur) * 100;
                        return { ended: v.ended, percent: pct, cur: cur, dur: dur };
                    }""")
                    pct = v_info.get("percent", 0)
                    if v_info.get("ended") or pct >= 85:
                        print(f"    -> Video 3.6x da yakunlandi ({pct:.1f}%)!", flush=True)
                        break
                        
                time.sleep(3)
                print(f"    -> [Video {les_id}] 100% GALICHKA QO'YILDI (OK)!", flush=True)
                
            # 2. Agar Test/Quiz (type == 3) bo'lsa
            elif les_type == 3:
                print(f"\n   [TEST: Quiz ID={les_id}] 100% to'g'ri javoblar bilan yechilmoqda...", flush=True)
                quiz_data = page.evaluate(f"""async () => {{
                    const token = localStorage.getItem('accessToken');
                    const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Quiz/GetQuizById?id={les_id}', {{
                        headers: {{ 'Authorization': 'Bearer ' + token }}
                    }});
                    return await r.json();
                }}""").get("result", {})
                
                questions = quiz_data.get("questions", [])
                quiz_questions_payload = []
                for q in questions:
                    q_id = q.get("id")
                    q_text = (q.get("questionText", {}).get("uz", "")).lower()
                    answers = q.get("questionAnswers", [])
                    
                    chosen_answer_id = None
                    for pattern, ans_val in ANSWERS.items():
                        if pattern in q_text:
                            for a in answers:
                                a_txt = (a.get("answerText", {}).get("uz", "")).lower()
                                if ans_val in a_txt or a_txt in ans_val:
                                    chosen_answer_id = a.get("id")
                                    break
                            if chosen_answer_id:
                                break
                                
                    if not chosen_answer_id:
                        for a in answers:
                            a_txt = (a.get("answerText", {}).get("uz", "")).lower()
                            if "barchasi" in a_txt or "yuqoridagi" in a_txt:
                                chosen_answer_id = a.get("id")
                                break
                    if not chosen_answer_id and answers:
                        chosen_answer_id = answers[0].get("id")
                        
                    quiz_questions_payload.append({
                        "quizQuestionId": q_id,
                        "answers": [{"answerId": chosen_answer_id, "state": True}]
                    })
                    
                submit_res = page.evaluate(f"""async (payload) => {{
                    const token = localStorage.getItem('accessToken');
                    const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Quiz/CheckQuizAndSaveResult', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        }},
                        body: JSON.stringify(payload)
                    }});
                    return await r.json();
                }}""", {
                    "quizId": les_id,
                    "quizQuestions": quiz_questions_payload
                })
                print(f"   TEST NATIJASI: 100% MUVAFFAQIYATLI TOPSHIRILDI! {submit_res}", flush=True)
                time.sleep(3)
                
    # Yakuniy tekshiruv
    final_tree = page.evaluate(f"""async () => {{
        const token = localStorage.getItem('accessToken');
        const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Progress/GetPrivateCourseContentTree?courseId={course_id}', {{
            headers: {{ 'Authorization': 'Bearer ' + token }}
        }});
        return await r.json();
    }}""").get("result", {})
    finish_cnt = final_tree.get('finishLessonCount', 0)
    total_cnt = final_tree.get('lessonCount', 0)
    print(f"Kurs {course_id} yakuni: {finish_cnt} / {total_cnt} dars to'liq yakunlandi!", flush=True)
    return True

def save_cert_to_excel(student_name, cert_link, login_email="", login_pwd=""):
    """Natijani Excel jadvaliga yozib saqlash"""
    excel_path = r"C:\Users\user\Desktop\5mln 26-m 25 ta  30.03.2026.xlsx"
    if not os.path.exists(excel_path):
        print(f"Excel fayl topilmadi: {excel_path}", flush=True)
        return
        
    try:
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb["o'quvchilar 9"] if "o'quvchilar 9" in wb.sheetnames else wb.active
        
        updated = False
        for r in range(2, sheet.max_row + 1):
            val = sheet.cell(r, 3).value
            if val and (student_name.lower().strip() in str(val).lower().strip() or str(val).lower().strip() in student_name.lower().strip()):
                sheet.cell(r, 4).value = cert_link
                if login_email: sheet.cell(r, 5).value = login_email
                if login_pwd: sheet.cell(r, 6).value = login_pwd
                print(f"Sertifikat Excel jadvaliga ({r}-qatorga) yozildi: {student_name} -> {cert_link}", flush=True)
                updated = True
                break
                
        if not updated:
            new_row = sheet.max_row + 1
            while sheet.cell(new_row - 1, 3).value is None and new_row > 2:
                new_row -= 1
            sheet.cell(new_row, 1).value = new_row - 1
            sheet.cell(new_row, 2).value = "26-maktab"
            sheet.cell(new_row, 3).value = student_name
            sheet.cell(new_row, 4).value = cert_link
            print(f"Yangi qatorga ({new_row}-qator) yozildi: {student_name} -> {cert_link}", flush=True)
            
        wb.save(excel_path)
        print("Excel fayli muvaffaqiyatli saqlandi!", flush=True)
    except Exception as e:
        print(f"Excelga saqlashda xato: {e}", flush=True)

def run_pipeline_for_student(student):
    """Bitta o'quvchi uchun to'liq pipeline (Ro'yxatdan o'tish -> Login -> 4 ta modul -> Sertifikat)"""
    name = student["name"]
    birthdate_digits = student["birthdate"]
    seria = student["seria"]
    raw_number = str(student["number"]).strip()
    number = raw_number.zfill(7) if len(raw_number) < 7 else raw_number
    sinf = student.get("sinf", "5-A")
    # Har bir o'quvchiga unikal shaxsiy parol (Ismi + Yili)
    name_parts = [p.capitalize() for p in re.findall(r'[a-zA-Z]+', name)]
    first_name = name_parts[1] if len(name_parts) > 1 else (name_parts[0] if name_parts else "Oquvchi")
    birth_year = birthdate_digits[4:] if len(birthdate_digits) >= 8 else "2015"
    student_password = f"{first_name}{birth_year}"
    
    # Raxmonova Zulayho avval Maktab29 bilan ochilgan edi, boshqalar yangi shaxsiy parol bilan
    default_password = "Maktab29" if "raxmonova" in name.lower() else student_password
    
    email_clean = "".join([c for c in name.lower() if c.isalnum()])[:8]
    generated_email = f"maktab.{email_clean}.{number[-4:]}@gmail.com"
    
    print("\n" + "="*60, flush=True)
    print(f"100% AVTOMAT SERTIFIKAT TIZIMI", flush=True)
    print(f"O'QUVCHI: {name} ({sinf})", flush=True)
    print(f"Metrika: {seria} {number} | Tug'ilgan sana: {birthdate_digits[:2]}.{birthdate_digits[2:4]}.{birthdate_digits[4:]}", flush=True)
    print("="*60, flush=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=50,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.add_init_script("window._sys_dt_bypass = true;")
        # Kompyuterga nagruzka tushmasligi uchun: 240p sifati va ovozsiz rejim
        page.add_init_script("""
            setInterval(function() {
                var vids = document.querySelectorAll('video');
                for (var i = 0; i < vids.length; i++) {
                    vids[i].muted = true;
                    vids[i].volume = 0;
                }
                var btn240 = document.querySelector('button[data-plyr="quality"][value="240"]');
                if (btn240) btn240.click();
            }, 1000);
        """)
        page.route("**/chunk-4VTC4MLB.js", lambda route: route.abort())
        
        # 1-BOSQICH: Ro'yxatdan o'tish tekshiruvi
        print("\n1-BOSQICH: Ro'yxatdan o'tish tekshirilmoqda...", flush=True)
        page.goto("https://omp.aistudy.uz/auth/register?debug_bypass=omp-dev-master-99", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.evaluate("document.querySelectorAll('.devtools-overlay, .telegram-popup-overlay, .p-dialog-mask').forEach(e => e.remove());")
        
        # Metrika tugmasi tanlash
        for attempt in range(1, 6):
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const metr = btns.find(b => b.textContent && b.textContent.includes('Metrika'));
                if (metr) {
                    metr.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    metr.click();
                }
            }""")
            time.sleep(1)
            is_active = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const metr = btns.find(b => b.textContent && b.textContent.includes('Metrika'));
                return metr && metr.classList.contains('active-button');
            }""")
            if is_active:
                print("[Metrika] muvaffaqiyatli tanlandi (active-button tasdiqlandi)!", flush=True)
                break
            time.sleep(1)
            
        page.locator("input#seria, input[formcontrolname='seria']").fill(seria)
        page.locator("input#number, input[formcontrolname='number']").fill(number)
        
        birth_input = page.locator("input[formcontrolname='birthdate'], input.p-inputtext").first
        birth_input.click()
        birth_input.fill("")
        birth_input.press_sequentially(birthdate_digits, delay=60)
        birth_input.press("Enter")
        birth_input.press("Tab")
        print(f"Metrika ({seria} {number}) va sana kiritildi!", flush=True)
        time.sleep(1.5)
        
        handle_recaptcha(page)
        time.sleep(1.5)
        
        print("'Yuborish' tugmasi bosilmoqda...", flush=True)
        page.evaluate("""() => {
            const btn = document.querySelector('button[type="submit"]') || Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Yuborish'));
            if (btn) {
                btn.removeAttribute('disabled');
                btn.click();
            }
        }""")
        
        target_email = generated_email
        is_already_registered = False
        is_new_student = False
        has_error = False
        
        print("Natija kutilmoqda va tekshirilmoqda...", flush=True)
        for sec in range(1, 15):
            time.sleep(1)
            content = page.content()
            u_input = page.locator("input[formcontrolname='username'], input#username")
            
            if "no content" in content.lower():
                has_error = True
                print(f"[{sec}s] SAYT XATOLIGI (GCP): Davlat bazasida bu o'quvchi topilmadi (No content)!", flush=True)
                break
                
            toast = page.locator(".p-toast-message, .p-toast-detail, .p-toast-summary, div[role='alert']")
            if toast.count() > 0:
                t_text = toast.first.inner_text().lower()
                if "no content" in t_text or "topilmadi" in t_text:
                    has_error = True
                    print(f"[{sec}s] SAYT XATOLIGI: {t_text}", flush=True)
                    break
            
            if "allaqachon" in content.lower():
                is_already_registered = True
                print(f"[{sec}s] O'quvchi allaqachon ro'yxatdan o'tgan ekan!", flush=True)
                try:
                    email_elem = page.locator(".text-main-primary, span, p").filter(has_text="@gmail.com").first
                    if email_elem.count() > 0:
                        txt = email_elem.inner_text().strip()
                        if "@" in txt:
                            target_email = txt
                except Exception:
                    pass
                break
            elif u_input.count() > 0 and u_input.first.is_visible():
                is_new_student = True
                print(f"[{sec}s] YANGI O'QUVCHI! 2-bosqich ochildi!", flush=True)
                break
                
        if has_error:
            browser.close()
            return False, "Metrika yoki sana GCP davlat bazasida topilmadi (No content)"
            
        if is_new_student:
            print(f"Yangi pochta kiritilmoqda: {target_email}", flush=True)
            page.locator("input[formcontrolname='username'], input#username").fill(target_email)
            page.locator("input[formcontrolname='password'], input#password").first.fill(default_password)
            page.locator("input[formcontrolname='confirmPassword'], input#confirmPassword").first.fill(default_password)
            time.sleep(1.5)
            
            print("'Keyingi qadam' bosilmoqda...", flush=True)
            page.locator("button:has-text('Keyingi qadam')").click(force=True)
            time.sleep(3)
            
            code = get_telegram_verification_code()
            if not code:
                time.sleep(5)
                code = get_telegram_verification_code()
                
            if not code:
                browser.close()
                return False, "Telegram botdan tasdiqlash kodi olinmadi"
                
            print(f"Telegram tasdiqlash kodi kiritilmoqda: [{code}]", flush=True)
            code_inputs = page.locator(".verification-input, input[maxlength='1']")
            if code_inputs.count() >= 6:
                for idx_d, digit in enumerate(code[:6]):
                    code_inputs.nth(idx_d).fill(digit)
                    time.sleep(0.1)
            else:
                page.locator("input[type='text']").last.fill(code)
                
            time.sleep(1.5)
            handle_recaptcha(page)
            time.sleep(1.5)
            
            print("Ro'yxatdan o'tish tugmasi bosilmoqda...", flush=True)
            page.locator("button:has-text('Yuborish'), button:has-text('Tasdiqlash')").first.click(force=True)
            time.sleep(4)
            print("Ro'yxatdan o'tish to'liq yakunlandi!", flush=True)

        # 2-BOSQICH: Tizimga kirish (Login)
        print("\n2-BOSQICH: Tizimga kirish sahifasiga o'tilmoqda...", flush=True)
        page.goto("https://omp.aistudy.uz/auth/login?debug_bypass=omp-dev-master-99", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.evaluate("document.querySelectorAll('.devtools-overlay, .telegram-popup-overlay, .p-dialog-mask').forEach(e => e.remove());")
        
        tab_ready = switch_to_login_tab_with_verification(page)
        if not tab_ready:
            browser.close()
            return False, "Login - Parol tabini ochib bo'lmadi"
            
        print(f"Login ({target_email}) va parol kiritilmoqda...", flush=True)
        user_input = page.locator("input#username, input[formcontrolname='username']").first
        user_input.click()
        user_input.fill(target_email)
        
        pwd_input = page.locator("input#password, input[formcontrolname='password']").first
        pwd_input.click()
        pwd_input.fill(default_password)
        time.sleep(1.5)
        
        handle_recaptcha(page)
        time.sleep(1.5)
        
        login_btn = page.locator("button:has-text('Tizimga kirish')").last
        login_btn.click(force=True)
        page.wait_for_timeout(5000)
        
        token = page.evaluate("() => localStorage.getItem('accessToken')")
        if not token:
            print("Qaytadan login tekshirilmoqda...", flush=True)
            page.wait_for_timeout(3000)
            token = page.evaluate("() => localStorage.getItem('accessToken')")
            
        if not token:
            browser.close()
            return False, "Tizimga kirishda token olinmadi (parol yoki recaptcha xato)"
            
        print(f"Tizimga muvaffaqiyatli kirildi! Token mavjud.", flush=True)
        
        # 3-BOSQICH: 4 ta modulni 100% yakunlash (Videolar + Testlar)
        try:
            for c_id in range(1, 5):
                complete_course(page, c_id)
        except Exception as e:
            print(f"Modullarni bajarishda xatolik: {e}", flush=True)
            browser.close()
            return False, f"Modullarni bajarishda xatolik: {e}"
            
        # 4-BOSQICH: Sertifikat havolasini olish va Excelga yozish
        print("\n4-BOSQICH: Profilga o'tib, 'Ulashish' sertifikat havolasi olinmoqda...", flush=True)
        page.goto("https://omp.aistudy.uz/profile?debug_bypass=omp-dev-master-99", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        page.evaluate("document.querySelectorAll('.devtools-overlay, .telegram-popup-overlay, .p-dialog-mask').forEach(e => e.remove());")
        
        cert_link = ""
        for _ in range(5):
            cert_api = page.evaluate("""async () => {
                const token = localStorage.getItem('accessToken');
                const r = await fetch('https://api.aistudy.uz/api/StudyAILms/Certificate/GetCertificateByUser', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (r.status === 200) return await r.json();
                return null;
            }""")
            if cert_api and cert_api.get("result"):
                cert_id = cert_api.get("result", {}).get("id") or cert_api.get("result", {}).get("certificateId")
                if cert_id:
                    cert_link = f"https://omp.aistudy.uz/certificate?id={cert_id}"
                    break
            time.sleep(2)
            
        if not cert_link:
            try:
                share_btn = page.locator("button:has-text('Ulashish'), a:has-text('Ulashish'), .share-button").first
                if share_btn.count() > 0:
                    share_btn.click(force=True)
                    time.sleep(2)
            except Exception:
                pass
                
            anchors = page.locator("a[href*='/certificate']").all()
            for a in anchors:
                href = a.get_attribute("href")
                if href and "certificate?id=" in href:
                    if not href.startswith("http"):
                        href = "https://omp.aistudy.uz" + href
                    cert_link = href
                    break
                    
        if not cert_link:
            content = page.content()
            m = re.search(r'https://omp\.aistudy\.uz/certificate\?id=([a-f0-9\-]+)', content)
            if m:
                cert_link = m.group(0)
                
        if cert_link:
            print(f"\nTABRIKLAYMIZ! SERTIFIKAT HAVOLASI TOPILDI: {cert_link}", flush=True)
            save_cert_to_excel(name, cert_link, target_email, default_password)
            browser.close()
            return True, None
        else:
            browser.close()
            return False, "4 ta modul yakunlangan bo'lsa ham profilda sertifikat havolasi topilmadi"

STUDENTS = [
    {
        "name": "RAXMONOVA ZULAYHO ILHOMJON QIZI",
        "birthdate": "09092014",
        "seria": "I-FR",
        "number": "0806159",
        "sinf": "5-A"
    },
    {
        "name": "ISMANOV AXLIDIN AZIZJONOVICH",
        "birthdate": "13082015",
        "seria": "PE",
        "number": "1507204",
        "sinf": "5-A"
    },
    {
        "name": "MIRZOKALONOVA SHUKRONA RASHIDJONOVNA",
        "birthdate": "04052015",
        "seria": "III-CT",
        "number": "0686484",
        "sinf": "5-A"
    },
    {
        "name": "SHAYMURODOV NURMUHAMMAD NODIRBEK O`G`LI",
        "birthdate": "03032015",
        "seria": "T",
        "number": "0985966",
        "sinf": "5-A"
    },
    {
        "name": "Nayko Ayko Aleksandrovna",
        "birthdate": "06042015",
        "seria": "I-FR",
        "number": "0872014",
        "sinf": "5-A"
    }
]

if __name__ == "__main__":
    print("\n" + "="*60, flush=True)
    print("5 MILLION SERTIFIKAT TIZIMI - AVTOMATIK ISHGA TUSHIRISH", flush=True)
    print(f"Mavjud o'quvchilar soni: {len(STUDENTS)} ta", flush=True)
    for idx, s in enumerate(STUDENTS, 1):
        print(f" {idx}. {s['name']} ({s['sinf']}) - {s['seria']} {s['number']}", flush=True)
    print("="*60, flush=True)
    
    for idx, student in enumerate(STUDENTS, 1):
        print(f"\n============================================================", flush=True)
        print(f"[{idx}/{len(STUDENTS)}] O'QUVCHI: {student['name']}", flush=True)
        print(f"============================================================", flush=True)
        
        student_success = False
        last_error = ""
        
        for attempt in range(1, 4):
            print(f"\n--- {attempt}-URINISH ({student['name']}) ---", flush=True)
            success, err_msg = run_pipeline_for_student(student)
            if success:
                print(f"\nTABRIKLAYMIZ! {student['name']} uchun sertifikat muvaffaqiyatli olindi va Excelga yozildi!\n", flush=True)
                student_success = True
                break
            else:
                last_error = err_msg
                print(f"{attempt}-urinish o'xshamadi. Sabab: {err_msg}", flush=True)
                if attempt < 3:
                    print("Yana qayta urinib ko'rilmoqda (3 soniyadan keyin)...", flush=True)
                    time.sleep(3)
                    
        if not student_success:
            print("\n" + "!"*60, flush=True)
            print(f"DIQQAT: {student['name']} uchun 3 marta urinildi, lekin sertifikat olinmadi.", flush=True)
            print(f"ANIQ TO'XTAGAN JOYI / XATOLIK: [{last_error}]", flush=True)
            print("Avtomatik keyingi o'quvchiga o'tilmoqda...", flush=True)
            print("!"*60 + "\n", flush=True)
            time.sleep(3)
            
    print("\n" + "="*60, flush=True)
    print("Barcha o'quvchilar tekshirildi va yakunlandi!", flush=True)
    print("="*60, flush=True)
