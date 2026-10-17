# -*- coding: utf-8 -*-
"""
UZBEK CODERS BOT - MASTER CERTIFIED PIPELINE (v7.0)
---------------------------------------------------
Qoidalar:
1. Bitta o'quvchi uchun brauzer 1 marta ochiladi (qayta-qayta yopib ochilmaydi!).
2. Module 1 (/learn/introduction-to-generative-ai/home/module/1) tekshiriladi:
   - Videolar va Reading 100% ko'rilganmi? Agar qolib ketgani bo'lsa, faqat o'shani bajaradi.
   - Quiz 1, 2, 3, 4 tekshiriladi:
     * Agar 100% (You passed!) bo'lsa -> vaqt ketkazmay darhol o'tkazib yuboradi!
     * Agar 0% / Failed / Started / -- bo'lsa -> kirib, aniq 100% javobni belgilab,
       ism-familiyani yozib, 1-Submit va "Ready to submit?" oynasidagi 2-Submitni bosadi!
     * Har bir qadam 3 martagacha tekshiriladi (bajarildimi yoki yo'qmi).
3. Kurs 100% bo'lgach, "Verify My Name" (First, Middle, Last name + Galichka + Submit) bajariladi.
4. Sertifikat havolasi olinib natijalar_sertifikatlar.txt ga yoziladi va keyingi o'quvchiga o'tiladi.
"""

import sys
import os
import re
import time
import json
import ssl
import random
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FILE_LOCK = threading.Lock()

RESULTS_FILE = "natijalar_sertifikatlar.txt"
ACCOUNTS_FILE = "akkountlar.txt"
ROSTER_FILE = "oquvchi.txt"
ERRORS_FILE = "xatolar.txt"

COMMON_PASSWORD = "@Ak101095"
PHONE_FORMATTED = "+998 (88) 667 10 60"
PHONE_RAW = "886671060"
MAILTM_PASS = "Password123!"

VIDEO_LINKS = [
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/sEzxC/where-generative-ai-fits-in-the-ai-and-ml-landscape",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/YUZhf/supervised-and-unsupervised-machine-learning-models",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/HGiXV/generative-ai-as-a-subset-of-deep-learning",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/jno82/is-it-generative-ai-or-not",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/Nfz2y/defining-generative-ai-a-formal-approach",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/6npRm/transformers-hallucinations-and-prompts",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/oG55M/an-overview-of-generative-ai-model-types",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/zMq98/generative-ai-for-code-generation",
    "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/XulSM/leveraging-google-cloud-for-enhanced-generative-ai"
]

READING_LINK = "https://www.coursera.org/learn/introduction-to-generative-ai/supplement/vARuq/reading"

QUIZZES_INFO = [
    ("Quiz 1", "https://www.coursera.org/learn/introduction-to-generative-ai/assignment-submission/UOf9n/quiz-1", 1),
    ("Quiz 2", "https://www.coursera.org/learn/introduction-to-generative-ai/assignment-submission/PbAYx/quiz-2", 2),
    ("Quiz 3", "https://www.coursera.org/learn/introduction-to-generative-ai/assignment-submission/68izF/quiz-3", 3),
    ("Quiz 4", "https://www.coursera.org/learn/introduction-to-generative-ai/assignment-submission/QR1K5/quiz-4", 4)
]

def get_completed_students():
    with FILE_LOCK:
        completed = set()
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "http" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 1:
                            completed.add(parts[0].upper())
        return completed

def get_unrecoverable_students():
    """Umuman kirib bo'lmaydigan (oldin boshqa joyda ro'yxatdan o'tgan va bazada paroli yo'q) o'quvchilar ro'yxati.
    Bularga oxirida qayta urinilmaydi!"""
    with FILE_LOCK:
        unrec = set()
        if os.path.exists(ERRORS_FILE):
            with open(ERRORS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "ILOJI_YOQ" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 1:
                            unrec.add(parts[0].upper())
        return unrec

def save_unrecoverable_student(full_name, class_name, reason):
    with FILE_LOCK:
        print("\n" + "!" * 75)
        print(f"[ILOJI YO'Q - O'TKAZILDI] {full_name} ({class_name})")
        print(f"Sababi: {reason}")
        print("Bu o'quvchiga oxirida qayta urinilmaydi (bazada login-paroli yo'q / kirib bo'lmaydi)!")
        print("!" * 75)
        with open(ERRORS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{full_name} | {class_name} | ILOJI_YOQ: {reason}\n")

def get_existing_accounts():
    with FILE_LOCK:
        accounts = {}
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        full_name = parts[0].upper()
                        email = parts[2]
                        password = parts[3]
                        accounts[full_name] = {"email": email, "password": password}
                    elif len(parts) >= 3:
                        full_name = parts[0].upper()
                        email = parts[1]
                        password = parts[2]
                        accounts[full_name] = {"email": email, "password": password}
        return accounts

def save_certificate_result(full_name, class_name, cert_url):
    with FILE_LOCK:
        print("\n" + "=" * 75)
        print(f"MUVAFFAQIYAT! {full_name} SERTIFIKATI OLINDI:")
        print(cert_url)
        print("=" * 75)
        with open(RESULTS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{full_name} | {class_name} | {cert_url}\n")

def dismiss_all_popups(page):
    try:
        page.evaluate("""() => {
            const labels = Array.from(document.querySelectorAll('label, span'));
            labels.forEach(l => {
                const lt = (l.innerText || '').trim();
                if (lt.includes('I commit to completing this course') || lt.includes('Я обязуюсь пройти этот курс')) {
                    try { l.click(); } catch(e) {}
                }
            });
            const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
            if (document.body && document.body.innerText.includes('My commitment') && cbs.length > 0 && !cbs[0].checked) {
                try { cbs[0].click(); } catch(e) {}
            }

            const btns = Array.from(document.querySelectorAll('button, a'));
            btns.forEach(b => {
                const t = (b.innerText || '').trim();
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                if (t === 'Start the course' || t === 'Close' || t.startsWith('Close') ||
                    t === 'Continue learning' || t === 'Next' || t === 'Got it' || t === 'Done' || t === 'Dismiss' ||
                    t === 'Начать курс' || t === 'Закрыть' || t === 'Далее' || t === 'Понятно' || t === 'Готово' ||
                    aria.includes('close') || aria.includes('закрыть')) {
                    try { b.click(); } catch(e) {}
                }
            });
        }""")
    except Exception:
        pass

def safe_navigate(page, url, max_retries=3, wait_sec=1.5):
    for _ in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=22000)
            time.sleep(wait_sec)
            dismiss_all_popups(page)
            return True
        except Exception:
            time.sleep(1.0)
    return False

def login_coursera(page, email, password, full_name=""):
    print(f"[LOGIN] Kirish boshlanmoqda: {email}...")
    clean_name = (full_name or "").replace("`", "'").strip()
    was_signup = False
    for try_idx in range(1, 4):
        try:
            page.goto("https://www.coursera.org/?authMode=login", wait_until="domcontentloaded", timeout=22000)
            for _ in range(12):
                if page.locator("input[type='email']").first.is_visible():
                    break
                login_btn = page.locator("a[href*='authMode=login'], button[data-e2e='header-login-button'], a:has-text('Войти'), button:has-text('Войти'), a:has-text('Log In')").first
                if login_btn.is_visible():
                    login_btn.click(force=True)
                time.sleep(0.4)

            email_inp = page.locator("input[type='email']").first
            if email_inp.is_visible():
                email_inp.fill(email)
                page.keyboard.press("Enter")
                for _ in range(12):
                    if page.locator("input[type='password']").first.is_visible():
                        break
                    time.sleep(0.3)

            # Agar Sign up oynasi chiqib qolsa (Full Name so'rasa), demak hali 1-HAVOLA (Set Password) bajarilmagan -> darhol tiklashga o'tamiz!
            fn_inp = page.locator("input[name='fullName'], input[placeholder*='full name' i], input[placeholder*='имя' i]").first
            if fn_inp.count() > 0 and fn_inp.is_visible():
                print(f"   [ANIQLANDI] {email} hali Coursera taklifnomasini (Set Password) faollashtirmagan. Pochtadan 1-havola ochiladi...")
                return False, True

            pwd_inp = page.locator("input[type='password']").first
            if pwd_inp.is_visible():
                pwd_inp.fill(password)
                sub_btn = page.locator("div[role='dialog'] button.cds-button-primary, form button.cds-button-primary").first
                if sub_btn.is_visible():
                    sub_btn.click(force=True)
                else:
                    page.keyboard.press("Enter")
                for _ in range(22):
                    time.sleep(0.4)
                    cookies = [c.get("name", "") for c in page.context.cookies()]
                    if any("CAUTH" in c for c in cookies) or ("authMode=login" not in page.url and page.locator("input[type='password']").count() == 0):
                        break
                time.sleep(1.2)
                dismiss_all_popups(page)
                cookies = [c.get("name", "") for c in page.context.cookies()]
                if any("CAUTH" in c for c in cookies):
                    print(f"[LOGIN] Tizimga muvaffaqiyatli kirildi! ({email})")
                    return True, was_signup
        except Exception:
            time.sleep(1.5)
    return False, was_signup

def ensure_enrolled_on_coursera(page):
    """Agar o'quvchi kursga hali Enroll ('Enroll Starts Oct 11' / 'Зарегистрироваться') bo'lmagan bo'lsa,
    Enroll tugmasini bosib, kursning ichiga (/home/module/1) kirganini 100% tekshiradi!"""
    for _ in range(3):
        try:
            for _ in range(3):
                dismiss_all_popups(page)
                time.sleep(0.25)

            # Agar /home/ ichida bo'lsa va Quiz 1 ko'rinib turgan bo'lsa — haqiqatan Enroll bo'lgan!
            if "/home/" in page.url and page.locator("a:has-text('Quiz 1')").count() > 0:
                return True

            # Agar DEDC dasturi sahifasida 'Join Program' / 'Continue' chiqib turgan bo'lsa, darhol bosamiz
            try:
                prog_btn = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), div[role='dialog'] button:has-text('Continue'), div[role='dialog'] button:has-text('Продолжить')").first
                if prog_btn.count() > 0 and prog_btn.is_visible():
                    prog_btn.click(force=True)
                    time.sleep(2.5)
            except Exception:
                pass

            # MUHIM: Enroll tugmasi faqat kursning asosiy sahifasida (/learn/introduction-to-generative-ai) chiqadi, /home/module/1 da chiqmaydi!
            safe_navigate(page, "https://www.coursera.org/learn/introduction-to-generative-ai", wait_sec=2.5)

            for _ in range(12):
                dismiss_all_popups(page)
                if "/home/" in page.url and page.locator("a:has-text('Quiz 1')").count() > 0:
                    return True
                enr_btn = page.locator(
                    "button[data-e2e='enroll-button'], "
                    "button:has-text('Enroll'), "
                    "button:has-text('Зарегистрироваться'), "
                    "button:has-text('Начать обучение')"
                ).first
                if enr_btn.count() > 0 and enr_btn.is_visible():
                    b_txt = (enr_btn.inner_text() or "").strip().lower()
                    if "trial" in b_txt or "пробный" in b_txt or "free trial" in b_txt:
                        print(f"   [!] Kurs pullik rejimda ('{b_txt}') — DEDC dasturiga ulanmagan!")
                        return False
                    print("   [ENROLL] 'Enroll' (Kursga yozilish) tugmasi topildi va bosilmoqda...")
                    box = enr_btn.bounding_box()
                    if box:
                        page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    else:
                        enr_btn.click(force=True)
                    time.sleep(2.5)
                    dismiss_all_popups(page)
                    page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('div[role="dialog"] button, button, a'));
                        const cont = btns.find(b => {
                            const t = (b.innerText || '').toLowerCase();
                            return t.includes('go to course') || t.includes('continue') || t.includes('start learning') ||
                                   t.includes('продолжить') || t.includes('начать обучение') || t.includes('перейти к курсу');
                        });
                        if (cont) cont.click();
                    }""")
                    time.sleep(3.0)
                    break
                time.sleep(0.5)

            safe_navigate(page, "https://www.coursera.org/learn/introduction-to-generative-ai/home/module/1", wait_sec=2.5)
            for _ in range(6):
                if page.locator("a:has-text('Quiz 1')").count() > 0:
                    return True
                time.sleep(0.5)
        except Exception:
            time.sleep(1.0)
    return False

def check_module1_overview(page):
    """
    SUPER-TEZ Module 1 va darslar ro'yxatini tekshirish:
    - Qaysi Video yoki Reading bajarilmagan (yashil ptichkasi yo'q)?
    - Qaysi Quizlar 100% PASSED, qaysilari NEEDS_TAKE?
    """
    safe_navigate(page, "https://www.coursera.org/learn/introduction-to-generative-ai/home/module/1", wait_sec=2.2)
    if "/home/" not in page.url or page.locator("a:has-text('Quiz 1')").count() == 0 or page.locator("button[data-e2e='enroll-button'], button:has-text('Enroll'), button:has-text('Зарегистрироваться')").count() > 0:
        ensure_enrolled_on_coursera(page)

    quiz_overview = page.evaluate("""() => {
        function getItemRow(el) {
            let curr = el;
            for (let d = 0; d < 5; d++) {
                if (!curr.parentElement) break;
                if (curr.parentElement.querySelectorAll('a').length > 1) break;
                curr = curr.parentElement;
            }
            return curr;
        }

        function isRowGreenCompleted(el) {
            const row = getItemRow(el);
            if (!row) return false;
            const txt = (row.innerText || '');
            if (txt.includes('100%') && !txt.includes('0%')) return true;

            const nodes = Array.from(row.querySelectorAll('svg, path, circle, span, div, [data-testid], [aria-label]'));
            for (const n of nodes) {
                const tid = (n.getAttribute('data-testid') || '').toLowerCase();
                const aria = (n.getAttribute('aria-label') || '').toLowerCase();
                if (tid.includes('completed') || tid.includes('success') || aria.includes('completed') || aria.includes('пройдено')) {
                    return true;
                }
                const style = window.getComputedStyle(n);
                for (const prop of [style.color, style.fill, style.backgroundColor, n.getAttribute('fill') || '']) {
                    const m = prop.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                    if (m) {
                        const r = parseInt(m[1]), g = parseInt(m[2]), b = parseInt(m[3]);
                        if (g > r + 20 && g > b + 10 && g > 70) {
                            return true;
                        }
                    }
                }
            }
            return false;
        }

        const res = {
            quizzes: { 'Quiz 1': 'NEEDS_TAKE', 'Quiz 2': 'NEEDS_TAKE', 'Quiz 3': 'NEEDS_TAKE', 'Quiz 4': 'NEEDS_TAKE' },
            quiz_urls: {}
        };

        const links = Array.from(document.querySelectorAll('a'));
        links.forEach(a => {
            const h = a.href || '';
            const t = (a.innerText || '').trim();
            if (!h.includes('introduction-to-generative-ai')) return;
            for (let i = 1; i <= 4; i++) {
                if (t.includes('Quiz ' + i) && h.includes('/assignment-submission/')) {
                    res.quiz_urls['Quiz ' + i] = h;
                }
                if (t.includes('Quiz ' + i)) {
                    const row = getItemRow(a);
                    const rTxt = (row ? row.innerText : '') || '';
                    if ((rTxt.includes('100%') && !rTxt.includes('0%')) || isRowGreenCompleted(a)) {
                        res.quizzes['Quiz ' + i] = 'PASSED';
                    }
                }
            }
        });

        return res;
    }""")

    # Chap menyudan Video va Readinglarning yashil ptichkasini tekshiramiz
    safe_navigate(page, VIDEO_LINKS[0], wait_sec=2.0)
    vid_overview = page.evaluate("""(defaultVideos) => {
        function getItemRow(a) {
            let curr = a;
            for (let d = 0; d < 4; d++) {
                if (!curr.parentElement) break;
                if (curr.parentElement.querySelectorAll('a').length > 1) break;
                curr = curr.parentElement;
            }
            return curr;
        }

        function isGreen(a) {
            const row = getItemRow(a);
            if (!row) return false;
            const nodes = Array.from(row.querySelectorAll('svg, path, circle, span, div, [data-testid], [aria-label]'));
            for (const n of nodes) {
                const tid = (n.getAttribute('data-testid') || '').toLowerCase();
                const aria = (n.getAttribute('aria-label') || '').toLowerCase();
                if (tid.includes('completed') || tid.includes('success') || aria.includes('completed') || aria.includes('пройдено')) {
                    return true;
                }
                const style = window.getComputedStyle(n);
                for (const prop of [style.color, style.fill, style.backgroundColor, n.getAttribute('fill') || '']) {
                    const m = prop.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                    if (m) {
                        const r = parseInt(m[1]), g = parseInt(m[2]), b = parseInt(m[3]);
                        if (g > r + 20 && g > b + 10 && g > 70) return true;
                    }
                }
            }
            return false;
        }

        const uncompleted_videos = [];
        let reading_done = false;
        const completedSlugs = new Set();

        const links = Array.from(document.querySelectorAll('a'));
        links.forEach(a => {
            const h = (a.href || '').split('?')[0];
            if (!h.includes('introduction-to-generative-ai')) return;
            if (h.includes('/lecture/')) {
                const slug = h.replace(/\\/+$/, '').split('/').pop();
                if (isGreen(a)) {
                    completedSlugs.add(slug);
                } else {
                    if (!uncompleted_videos.includes(h)) uncompleted_videos.push(h);
                }
            } else if (h.includes('/supplement/')) {
                if (isGreen(a)) reading_done = true;
            }
        });

        defaultVideos.forEach(vUrl => {
            const cleanV = vUrl.split('?')[0];
            const slug = cleanV.replace(/\\/+$/, '').split('/').pop();
            if (!completedSlugs.has(slug) && !uncompleted_videos.some(u => u.includes(slug))) {
                uncompleted_videos.push(cleanV);
            }
        });

        return { uncompleted_videos, reading_done };
    }""", VIDEO_LINKS)

    return {
        "uncompleted_videos": vid_overview["uncompleted_videos"],
        "reading_done": vid_overview["reading_done"],
        "quizzes": quiz_overview["quizzes"],
        "quiz_urls": quiz_overview["quiz_urls"]
    }

def ensure_videos_and_reading_100(page, overview):
    """SUPER-TEZ Video va Reading bajarish: faqat bajarilmaganlarini 3 ta parallel tabda ~15 soniyada 100% qiladi!"""
    uncompleted_videos = overview.get("uncompleted_videos", [])
    reading_done = overview.get("reading_done", True)

    if reading_done and len(uncompleted_videos) == 0:
        print("[+] Barcha Videolar va Reading allaqachon 100% bajarilgan! O'tkazib yuboriladi.")
        return

    if not reading_done:
        for r_try in range(1, 4):
            print(f"[-] Reading bajarilmagan, 100% qilinmoqda (urinish #{r_try}/3)...")
            safe_navigate(page, READING_LINK, wait_sec=1.5)
            mark_btn = page.locator("button:has-text('Mark as completed'), button:has-text('Отметить как пройденное')").first
            if mark_btn.is_visible():
                mark_btn.click(force=True)
                time.sleep(1.5)
            if not mark_btn.is_visible():
                print("[+] Reading 100% bajarildi!")
                break

    if len(uncompleted_videos) > 0:
        print(f"[-] {len(uncompleted_videos)} ta video ko'rilmagan. SUPER-TEZ rejimda yakunlanmoqda...")
        try:
            page.set_default_timeout(12000)
            page.set_default_navigation_timeout(18000)
        except Exception:
            pass

        for idx_v, vl in enumerate(uncompleted_videos, 1):
            slug = vl.split("?")[0].rstrip("/").split("/")[-1]
            print(f"   [Video {idx_v}/{len(uncompleted_videos)}] Yakunlanmoqda: {slug}...")
            safe_goto_commit(page, vl, wait_sec=1.5)
            dismiss_all_popups(page)

            for _ in range(10):
                try:
                    has_dur = page.evaluate("() => { const v = document.querySelector('video'); return !!(v && v.duration > 1); }")
                    if has_dur:
                        break
                except Exception:
                    pass
                time.sleep(0.4)

            try:
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = true;
                        try { v.playbackRate = 2.0; } catch(e) {}
                        const p1 = v.play();
                        if (p1 && p1.catch) p1.catch(() => {});
                        if (v.duration && v.duration > 1) {
                            v.currentTime = Math.max(0, v.duration - 1.5);
                        }
                        v.dispatchEvent(new Event('playing'));
                        v.dispatchEvent(new Event('timeupdate'));
                        const p2 = v.play();
                        if (p2 && p2.catch) p2.catch(() => {});
                        setTimeout(() => {
                            try {
                                if (v.duration && v.duration > 1) v.currentTime = Math.max(0, v.duration - 0.2);
                                v.dispatchEvent(new Event('timeupdate'));
                                v.dispatchEvent(new Event('ended'));
                            } catch(e) {}
                        }, 900);
                    }
                    const btns = Array.from(document.querySelectorAll('button'));
                    const mark = btns.find(b => /mark as completed|отметить как/i.test(b.innerText || ''));
                    if (mark) mark.click();
                }""")
            except Exception:
                pass
            time.sleep(2.4)

        # Yakuniy tekshiruv: agar birorta video yashil bo'lmay qolgan bo'lsa, qayta yopamiz
        safe_goto_commit(page, VIDEO_LINKS[0], wait_sec=1.5)
        try:
            still_missing = page.evaluate("""(vUrls) => {
                function getItemRow(a) {
                    let curr = a;
                    for (let d = 0; d < 4; d++) {
                        if (!curr.parentElement || curr.parentElement.querySelectorAll('a').length > 1) break;
                        curr = curr.parentElement;
                    }
                    return curr;
                }
                function isGreen(a) {
                    const row = getItemRow(a);
                    if (!row) return false;
                    const nodes = Array.from(row.querySelectorAll('svg, path, circle, span, div, [data-testid], [aria-label]'));
                    for (const n of nodes) {
                        const tid = (n.getAttribute('data-testid') || '').toLowerCase();
                        const aria = (n.getAttribute('aria-label') || '').toLowerCase();
                        if (tid.includes('completed') || tid.includes('success') || aria.includes('completed') || aria.includes('пройдено')) return true;
                        const style = window.getComputedStyle(n);
                        for (const prop of [style.color, style.fill, style.backgroundColor, n.getAttribute('fill') || '']) {
                            const m = prop.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                            if (m) {
                                const r = parseInt(m[1]), g = parseInt(m[2]), b = parseInt(m[3]);
                                if (g > r + 20 && g > b + 10 && g > 70) return true;
                            }
                        }
                    }
                    return false;
                }
                const missing = [];
                vUrls.forEach(u => {
                    const slug = u.split('?')[0].replace(/\\/+$/, '').split('/').pop();
                    const a = Array.from(document.querySelectorAll('a')).find(x => (x.href || '').includes(slug));
                    if (a && !isGreen(a)) missing.push(u);
                });
                return missing;
            }""", uncompleted_videos)
        except Exception:
            still_missing = []

        for vl in still_missing:
            slug = vl.split("?")[0].rstrip("/").split("/")[-1]
            print(f"   [Qayta tekshiruv] Video yakunlanmoqda: {slug}...")
            safe_goto_commit(page, vl, wait_sec=1.5)
            for _ in range(8):
                try:
                    if page.evaluate("() => { const v = document.querySelector('video'); return !!(v && v.duration > 1); }"):
                        break
                except Exception:
                    pass
                time.sleep(0.4)
            try:
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = true;
                        if (v.duration && v.duration > 1) v.currentTime = Math.max(0, v.duration - 1.5);
                        const p = v.play();
                        if (p && p.catch) p.catch(() => {});
                        v.dispatchEvent(new Event('timeupdate'));
                        setTimeout(() => {
                            try {
                                if (v.duration && v.duration > 1) v.currentTime = v.duration;
                                v.dispatchEvent(new Event('timeupdate'));
                                v.dispatchEvent(new Event('ended'));
                            } catch(e) {}
                        }, 900);
                    }
                }""")
            except Exception:
                pass
            time.sleep(2.8)

def solve_single_quiz_with_3_checks(page, q_name, q_url, q_num, student_name):
    """
    Bitta Quizni BIRINCHI URINISHDA 100% yechadi va "You passed!" bo'lganini 3 martagacha tekshiradi!
    """
    clean_honor_name = student_name.replace("`", "").replace("'", "").replace("ʻ", "").replace("ʼ", "").strip()

    for check_try in range(1, 4):
        try:
            mult = check_try  # 1-urinish: 1x (tez), 2-urinish: 2x uzoqroq, 3-urinish: 3x uzoqroq kutadi!
            print(f"\n>>> [{q_name}] Tekshiruv va topshirish (Qadam #{check_try}/3 | Kutish koeffitsiyenti: {mult}x) <<<")
            if q_url.split("?")[0].rstrip("/") not in page.url or "/attempt" in page.url:
                safe_navigate(page, q_url, wait_sec=2.5 * mult)

            # Faqat haqiqatdan landing sahifaga qaytib qolib, Enroll tugmasi ko'rinib tursa Enroll qilamiz
            enr_check = page.locator("button[data-e2e='enroll-button'], button:has-text('Enroll'), button:has-text('Зарегистрироваться')").first
            if enr_check.count() > 0 and enr_check.is_visible() and "/assignment-submission/" not in page.url and "/attempt" not in page.url:
                ensure_enrolled_on_coursera(page)
                safe_navigate(page, q_url, wait_sec=2.5 * mult)

            # Tugma ('Start assignment' / 'Resume' / 'Try again') yoki 'You passed!' chiqishini sabr bilan kutamiz!
            act_selector = (
                "button:has-text('Resume assignment'), a:has-text('Resume assignment'), "
                "button:has-text('Start assignment'), a:has-text('Start assignment'), "
                "button:has-text('Try again'), a:has-text('Try again'), "
                "button:has-text('Retake'), a:has-text('Retake'), "
                "button:has-text('Resume'), button:has-text('Start'), "
                "button:has-text('Возобновить'), button:has-text('Начать'), "
                "button:has-text('Пройти тест'), button:has-text('Повторить')"
            )
            for _ in range(20 * mult):
                dismiss_all_popups(page)
                page_text = page.evaluate("() => (document.body ? document.body.innerText : '')")
                if "You passed!" in page_text or "Your grade: 100%" in page_text or "Вы прошли!" in page_text:
                    print(f"[+] {q_name} 100% PASSED tasdiqlandi!")
                    return True
                hm = page.locator("div[data-testid='HonorCodeModal'] button, button:has-text('Continue'), button:has-text('Продолжить')").first
                if hm.count() > 0 and hm.is_visible():
                    hm.click(force=True)
                has_start_btn = page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('button, a'));
                    return els.some(el => {
                        if (el.offsetWidth < 20 || el.offsetHeight < 15) return false;
                        const t = (el.innerText || '').trim().toLowerCase();
                        return t === 'start assignment' || t === 'resume assignment' || t === 'try again' ||
                               t === 'retake' || t === 'resume' || t === 'start' ||
                               t === 'начать' || t === 'возобновить' || t === 'пройти тест' || t === 'повторить';
                    });
                }""")
                if has_start_btn or ("/attempt" in page.url and page.locator("input[type='radio']").count() >= 4):
                    break
                time.sleep(0.5)

            # 3. Asosiy sahifadagi KO'RINIB TURGAN Start assignment / Resume / Try again tugmasini bosib /attempt ga kiramiz!
            for click_try in range(3):
                if "/attempt" in page.url and page.locator("input[type='radio']").count() >= 4:
                    break

                clicked_txt = page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('button, a'));
                    const target = els.find(el => {
                        if (el.offsetWidth < 20 || el.offsetHeight < 15) return false;
                        const t = (el.innerText || '').trim().toLowerCase();
                        return t === 'start assignment' || t === 'resume assignment' || t === 'try again' ||
                               t === 'retake' || t === 'resume' || t === 'start' ||
                               t === 'начать' || t === 'возобновить' || t === 'пройти тест' || t === 'повторить';
                    });
                    if (target) {
                        target.scrollIntoView({block: 'center'});
                        target.click();
                        return (target.innerText || '').trim();
                    }
                    return '';
                }""")
                if clicked_txt:
                    print(f"[{q_name}] '{clicked_txt}' tugmasi bosildi! Savollar ochilishi kutilmoqda ({mult}x)...")
                    time.sleep(3.0 * mult)
                else:
                    act_btn = page.locator(act_selector).first
                    if act_btn.count() > 0 and act_btn.is_visible():
                        b_label = act_btn.inner_text().strip()
                        if "пробный" in b_label.lower() or "trial" in b_label.lower():
                            print(f"[!] [{q_name}] Akkountda DEDC dasturi ulanmagan ('{b_label}' chiqdi)!")
                            return False
                        print(f"[{q_name}] '{b_label}' tugmasi bosilmoqda ({mult}x)...")
                        act_btn.click(force=True)
                        time.sleep(3.0 * mult)

                if "courseraplus" in page.url.lower():
                    print(f"[!] [{q_name}] Coursera Plus (pullik sahifa) ochildi — bu akkount DEDC ga ulanmagan!")
                    return False

                # Confirmation dialog yoki Honor Code chiqsa Continue bosamiz
                conf_btn = page.locator("div[role='dialog'] button:has-text('Continue'), div[role='dialog'] button:has-text('Продолжить'), div[role='dialog'] button:has-text('Start'), div[data-testid='HonorCodeModal'] button").first
                if conf_btn.count() > 0 and conf_btn.is_visible():
                    conf_btn.click(force=True)
                    time.sleep(2.0 * mult)

                if "/attempt" in page.url and page.locator("input[type='radio']").count() >= 4:
                    break
                time.sleep(1.0 * mult)

            print(f"[{q_name}] Formaga kirildi: {page.url}")
            if "courseraplus" in page.url.lower():
                return False

            # Savollar (kamida 4 ta radio tugma!) to'liq yuklanishini kutamiz (agar Start assignment endi chiqsa, uni bosamiz!)
            for _ in range(25 * mult):
                if page.locator("input[type='radio']").count() >= 4:
                    break
                page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('button, a'));
                    const target = els.find(el => {
                        if (el.offsetWidth < 20 || el.offsetHeight < 15) return false;
                        const t = (el.innerText || '').trim().toLowerCase();
                        return t === 'start assignment' || t === 'resume assignment' || t === 'try again' ||
                               t === 'continue' || t === 'продолжить' || t === 'начать' || t === 'возобновить';
                    });
                    if (target) target.click();
                }""")
                time.sleep(0.5)

            if page.locator("input[type='radio']").count() == 0 and "/attempt" not in page.url:
                print(f"[!] [{q_name}] Savollar ochilmadi ({page.url}) — kursga Enroll holati tekshirilmoqda...")
                if not ensure_enrolled_on_coursera(page):
                    return False

            # Agar ekranda avvalgi urinishdan "Ready to submit?" modal oynasi ochiq qolgan bo'lsa, Cancel bosib yopamiz
            try:
                cancel_modal = page.locator("div[role='dialog'] button:has-text('Cancel'), div[role='dialog'] button:has-text('Отмена')").first
                if cancel_modal.is_visible():
                    cancel_modal.click(force=True)
                    time.sleep(0.5)
            except Exception:
                pass

            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.3)

            def select_radio_by_keywords_guaranteed(must_contain_list, must_not_contain_list=None):
                """Aniq kalit so'zlar qatnashgan radio javobni topib bosadi va React .checked === true bo'lganini 100% tekshiradi!"""
                must_not_contain_list = must_not_contain_list or []
                # 1. Playwright locator orqali haqiqiy click va check()
                for group in must_contain_list:
                    loc = page.locator("label")
                    for kw in group:
                        loc = loc.filter(has_text=re.compile(re.escape(kw), re.I))
                    for bad_kw in must_not_contain_list:
                        loc = loc.filter(has_not_text=re.compile(re.escape(bad_kw), re.I))
                    if loc.count() > 0 and loc.first.is_visible():
                        target_lbl = loc.first
                        target_lbl.scroll_into_view_if_needed()
                        target_lbl.click(force=True)
                        time.sleep(0.3)
                        r_inp = target_lbl.locator("input[type='radio']").first
                        if r_inp.count() > 0 and not r_inp.is_checked():
                            try:
                                r_inp.check(force=True)
                            except Exception:
                                pass
                            time.sleep(0.25)
                        if r_inp.count() > 0 and not r_inp.is_checked():
                            box = r_inp.bounding_box()
                            if box:
                                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                time.sleep(0.25)
                        if r_inp.count() > 0 and r_inp.is_checked():
                            return True

                # 2. JS fallback (r.checked = true qilmasdan, haqiqiy click bilan!)
                for _ in range(3):
                    matched_ok = page.evaluate("""({mustList, notList}) => {
                        const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                        for (const r of radios) {
                            let container = r.closest('label') || r.parentElement;
                            for (let d = 0; d < 4; d++) {
                                if (container && (container.innerText || '').trim().length > 15) break;
                                if (container && container.parentElement) container = container.parentElement;
                            }
                            const txt = ((container ? container.innerText : '') || '').toLowerCase();
                            const okMust = mustList.some(group => group.every(w => txt.includes(w.toLowerCase())));
                            const badNot = notList.some(w => txt.includes(w.toLowerCase()));
                            if (okMust && !badNot) {
                                container.scrollIntoView({block: 'center'});
                                if (!r.checked) container.click();
                                if (!r.checked) r.click();
                                return r.checked === true;
                            }
                        }
                        return false;
                    }""", {"mustList": must_contain_list, "notList": must_not_contain_list})
                    if matched_ok:
                        return True
                    time.sleep(0.3)
                return False

            # 4. ANIQ 100% TO'G'RI JAVOBNI BELGILASH (1-urinishdayoq 100% bexato!)
            if q_num == 1:
                # Quiz 1: "...create new content, such as text, images, audio, and video."
                select_radio_by_keywords_guaranteed([
                    ["text, images, audio, and video"],
                    ["такой как текст, изображения, аудио и видео"],
                    ["create new content", "video"]
                ], must_not_contain_list=["only text"])

            elif q_num == 2:
                # Quiz 2: "A generative AI model could be trained on a dataset of images of cats and then used to generate new images of cats. A discriminative AI model could be trained on a dataset of images of cats and dogs and then used to classify new images as either cats or dogs."
                select_radio_by_keywords_guaranteed([
                    ["used to generate new images of cats. a discriminative", "classify new images as either cats or dogs"],
                    ["generate new images of cats. a discriminative"],
                    ["создания новых изображений кошек. дискримина", "классификации новых изображений"]
                ], must_not_contain_list=[
                    "cluster images",
                    "used to classify new images of cats",
                    "discriminative ai model could be trained on a dataset of images of cats and then used to generate",
                    "discriminative model could be trained on a dataset of images of cats and then used to generate"
                ])

            elif q_num == 3:
                # Quiz 3: "...pre-trained on a vast quantity of data..."
                select_radio_by_keywords_guaranteed([
                    ["vast quantity of data"],
                    ["огромном количестве данных"]
                ])

            elif q_num == 4:
                # Quiz 4, 1-savol: 3 ta to'g'ri checkboxni belgilash va 1 ta noto'g'risini o'chirish (Ingliz va Rus tillarida!)
                for kw_group in [
                    ["not trained on enough", "не обучена на достаточном", "недостаточном количестве данных"],
                    ["not given enough context", "не предоставлено достаточно контекста", "недостаточно контекста"],
                    ["noisy or dirty data", "зашумленных или грязных", "шумных или грязных"],
                ]:
                    for correct_txt in kw_group:
                        lbl = page.locator(f"label:has-text('{correct_txt}')").first
                        if lbl.count() > 0 and lbl.is_visible():
                            lbl.scroll_into_view_if_needed()
                            cb_in = lbl.locator("input[type='checkbox']").first
                            if cb_in.count() > 0:
                                if not cb_in.is_checked():
                                    lbl.click(force=True)
                                    time.sleep(0.2)
                                    if not cb_in.is_checked():
                                        box_cb = cb_in.bounding_box()
                                        if box_cb:
                                            page.mouse.click(box_cb['x'] + box_cb['width']/2, box_cb['y'] + box_cb['height']/2)
                            else:
                                lbl.click(force=True)
                            break

                for wrong_txt in ["trained on too much data", "слишком большом объеме данных", "слишком большом количестве"]:
                    wrong_lbl = page.locator(f"label:has-text('{wrong_txt}')").first
                    if wrong_lbl.count() > 0 and wrong_lbl.is_visible():
                        cb_w = wrong_lbl.locator("input[type='checkbox']").first
                        if cb_w.count() > 0 and cb_w.is_checked():
                            wrong_lbl.click(force=True)

                # Quiz 4, 2-savol: "...given to the large language model as input..."
                select_radio_by_keywords_guaranteed([
                    ["given to the large language model as input"],
                    ["передается большой языковой модели"]
                ])

            time.sleep(0.4)

            # 5. PASTGA TUSHIB ISM-FAMILIYANI VA HONOR CODE GALICHKASINI KIRITISH
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.4)

            und_btn = page.locator("button:visible:has-text('I understand'), button:visible:has-text('Я понимаю')").first
            if und_btn.is_visible():
                und_btn.click(force=True)
                time.sleep(0.3)

            name_inp = page.locator("input[placeholder*='legal name'], input[placeholder*='удостоверении'], input[placeholder*='Ф. И. О.'], [data-testid='honor-code-legal-name-input'], input[type='text']").last
            if name_inp.is_visible():
                curr_val = (name_inp.input_value() or "").strip()
                if len(curr_val) < 3 or "`" in curr_val or "'" in curr_val:
                    name_inp.click(force=True)
                    name_inp.fill("")
                    page.keyboard.type(clean_honor_name, delay=10)
                    time.sleep(0.4)

            # Honor Code galichkasini (checkbox) barcha Quizlarda (1, 2, 3 va 4) belgilash!
            honor_cb = page.locator("label:has-text('understand and agree') input[type='checkbox'], label:has-text('понимаю и соглашаюсь') input[type='checkbox'], input[type='checkbox']").last
            try:
                if honor_cb.count() > 0 and not honor_cb.is_checked():
                    box = honor_cb.bounding_box()
                    if box:
                        page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    else:
                        honor_cb.check(force=True)
                    time.sleep(0.4)
            except Exception:
                pass

            # 6. IKKALA SUBMIT TUGMASINI BOSISH
            sub_btn_1 = page.locator("button:has-text('Submit'), button:has-text('Отправить')").first
            if not sub_btn_1.is_visible():
                print(f"[!] [{q_name}] Submit tugmasi ko'rinmadi (forma ochilmagan), qayta harakat qilinadi...")
                continue

            is_en = sub_btn_1.is_enabled()
            print(f"[{q_name}] 1-Submit holati: is_enabled = {is_en}")

            if is_en:
                sub_btn_1.click(force=True)
                time.sleep(1.0)
                if page.locator("button:has-text('Submit'), button:has-text('Отправить')").count() < 2:
                    box1 = sub_btn_1.bounding_box()
                    if box1:
                        page.mouse.click(box1['x'] + box1['width']/2, box1['y'] + box1['height']/2)
                print(f"[{q_name}] 1-Submit bosildi! 'Ready to submit?' oynasi kutilmoqda...")
                for _ in range(10):
                    if page.locator("button:has-text('Submit'), button:has-text('Отправить')").count() >= 2:
                        break
                    time.sleep(0.25)

                # 2-Submit ("Ready to submit?" oynasi ichidagi Submit, Cancel tugmasi yonidagi!)
                for modal_try in range(1, 4):
                    if "/attempt" not in page.url:
                        break
                    all_submits = page.locator("button:has-text('Submit'), button:has-text('Отправить')").all()
                    if len(all_submits) >= 2:
                        sub_btn_2 = all_submits[-1]
                        print(f"[{q_name}] 2-Submit (Modal ichidagi Submit, urinish #{modal_try}) sichqoncha bilan bosilmoqda...")
                        try:
                            box2 = sub_btn_2.bounding_box(timeout=2500)
                            if box2:
                                page.mouse.click(box2['x'] + box2['width']/2, box2['y'] + box2['height']/2)
                            else:
                                sub_btn_2.click(force=True, timeout=2500)
                        except Exception:
                            pass
                        for _ in range(12):
                            time.sleep(0.45)
                            if "/attempt" not in page.url:
                                break
                    else:
                        break

                # Natija (100% / You passed!) chiqishini kutamiz
                for _ in range(10):
                    after_text = page.evaluate("() => (document.body ? document.body.innerText : '')")
                    if "You passed!" in after_text or "Your grade: 100%" in after_text or "Вы прошли!" in after_text or "You didn't pass" in after_text:
                        break
                    time.sleep(0.4)

                dismiss_all_popups(page)
                after_text = page.evaluate("() => (document.body ? document.body.innerText : '')")
                if "You passed!" in after_text or "Your grade: 100%" in after_text or "Вы прошли!" in after_text:
                    print(f"[+] {q_name} BIRINCHI URINISHDA MUVAFFAQIYATLI 100% TOPSHIRILDI ('Your grade: 100%')!")
                    return True
                else:
                    print(f"[!] {q_name} natijasi hali 100% ko'rinmadi, qayta tekshiriladi...")
        except Exception as e:
            print(f"[!] [{q_name}] {check_try}-urinishda xatolik ushlandi (qayta harakat qilinadi): {e}")
            time.sleep(1.5)

    return False

def verify_student_name_with_3_checks(page, student_name):
    """Verify My Name sahifasida ismni kiritib, galichka qo'yib, Submit bosadi (1x, 2x, 3x kutish bilan)."""
    print(f"\n[ISMNI TASDIQLASH] {student_name}...")
    for v_try in range(1, 4):
        try:
            mult = v_try
            safe_navigate(page, "https://www.coursera.org/organizations/dedc/my-learning?myLearningTab=CERTIFICATES")
            time.sleep(3.5 * mult)
            dismiss_all_popups(page)
            time.sleep(1.0)

            v_btn = page.locator("button:has-text('Verify My Name'), a:has-text('Verify My Name'), button:has-text('Проверить мое имя'), a:has-text('Проверить мое имя')").first
            if not v_btn.is_visible():
                safe_navigate(page, "https://www.coursera.org/organizations/dedc")
                time.sleep(3.5 * mult)
                dismiss_all_popups(page)
                time.sleep(1.0)
                v_btn = page.locator("button:has-text('Verify My Name'), a:has-text('Verify My Name'), button:has-text('Проверить мое имя'), a:has-text('Проверить мое имя')").first

            if not v_btn.is_visible():
                print("[ISMNI TASDIQLASH] 'Verify My Name' tugmasi yo'q (ism allaqachon tasdiqlangan!).")
                return True

            print(f"[ISMNI TASDIQLASH] 'Verify My Name' bosilmoqda (urinish #{v_try}/3 | {mult}x)...")
            box_v = v_btn.bounding_box()
            if box_v:
                page.mouse.click(box_v['x'] + box_v['width']/2, box_v['y'] + box_v['height']/2)
            else:
                v_btn.click(force=True)
            time.sleep(3.5 * mult)
            dismiss_all_popups(page)

            # Ism yozish maydonlari (First/Middle/Last name) ochilganini tekshiramiz
            inp_count = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).filter(i => i.type === 'text' && !i.className.includes('autosuggest') && !(i.placeholder || '').toLowerCase().includes('search')).length;
            }""")
            if inp_count < 2 and v_btn.is_visible():
                v_btn.click(force=True)
                time.sleep(3.0 * mult)

            parts = student_name.split()
            first_name = parts[0] if len(parts) > 0 else student_name
            middle_name = parts[1] if len(parts) > 2 else ""
            last_name = " ".join(parts[2:]) if len(parts) > 2 else (parts[1] if len(parts) == 2 else "")

            # 1. FIRST NAME
            page.evaluate("""() => {
                const inps = Array.from(document.querySelectorAll('input')).filter(i => i.type === 'text' && !i.className.includes('autosuggest') && !(i.placeholder || '').toLowerCase().includes('search'));
                if (inps.length >= 1) { inps[0].value = ''; inps[0].focus(); }
            }""")
            time.sleep(0.3)
            page.keyboard.type(first_name, delay=30)
            time.sleep(0.4)

            # 2. MIDDLE NAME
            if middle_name:
                page.evaluate("""() => {
                    const inps = Array.from(document.querySelectorAll('input')).filter(i => i.type === 'text' && !i.className.includes('autosuggest') && !(i.placeholder || '').toLowerCase().includes('search'));
                    if (inps.length >= 2) { inps[1].value = ''; inps[1].focus(); }
                }""")
                time.sleep(0.3)
                page.keyboard.type(middle_name, delay=30)
                time.sleep(0.4)

            # 3. LAST NAME
            if last_name:
                page.evaluate("""() => {
                    const inps = Array.from(document.querySelectorAll('input')).filter(i => i.type === 'text' && !i.className.includes('autosuggest') && !(i.placeholder || '').toLowerCase().includes('search'));
                    if (inps.length >= 3) { inps[2].value = ''; inps[2].focus(); }
                }""")
                time.sleep(0.3)
                page.keyboard.type(last_name, delay=30)
                time.sleep(0.4)

            # 4. Galichka (Checkbox)
            cb = page.locator("input[type='checkbox']").first
            if cb.count() > 0 and cb.is_visible():
                box = cb.bounding_box()
                if box:
                    page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    time.sleep(1)
                if not cb.is_checked():
                    lbl = page.locator("label:has-text('By checking this box'), label:has-text('Устанавливая этот флажок')").first
                    if lbl.is_visible():
                        lbl.click(force=True)
                        time.sleep(1)

            # 5. Submit ('Save' yozilmaydi, chunki 'Saved' tabiga bosilib ketmasligi kerak!)
            sub_v = page.locator("button:has-text('Submit'), button:has-text('Отправить')").first
            if sub_v.is_visible() and sub_v.is_enabled():
                box_s = sub_v.bounding_box()
                if box_s:
                    page.mouse.click(box_s['x'] + box_s['width']/2, box_s['y'] + box_s['height']/2)
                else:
                    sub_v.click(force=True)
                print("[ISMNI TASDIQLASH] Tasdiqlash muvaffaqiyatli yuborildi!")
                time.sleep(5.0 * mult)
                return True
            else:
                print(f"[!] Verify My Name Submit tugmasi faol emas, qayta tekshirilmoqda ({v_try}/3)...")
        except Exception as e:
            print(f"[!] Verify My Name {v_try}-urinishda xatolik ushlandi: {e}")
            time.sleep(2)

    return False

def extract_certificate_with_3_checks(page, student_name=""):
    """Sertifikat havolasini 3 martagacha (1x, 2x, 3x kutish bilan) tekshirib oladi. Agar kurs hali IN_PROGRESS bo'lsa, o'sha yerdagi kamchilikni (Quiz yoki Video) darhol topib bajaradi!"""
    for c_try in range(1, 4):
        try:
            mult = c_try
            print(f"[SERTIFIKAT QIDIRUV #{c_try}/3 | Kutish: {mult}x] Tekshirilmoqda...")
            # 1. Certificates tab
            safe_navigate(page, "https://www.coursera.org/organizations/dedc/my-learning?myLearningTab=CERTIFICATES")
            time.sleep(4.5 * mult)
            dismiss_all_popups(page)
            links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && h.includes('/account/accomplishments/verify/'))""")
            if links:
                return links[0]

            vc = page.locator("a:has-text('View certificate'), button:has-text('View certificate'), a:has-text('Посмотреть сертификат'), button:has-text('Посмотреть сертификат')").first
            if vc.is_visible():
                vc.click(force=True)
                time.sleep(4.5 * mult)
                if "/account/accomplishments/verify/" in page.url:
                    return page.url

            # Agar CERTIFICATES bo'sh bo'lsa, IN_PROGRESS tabini tekshiramiz: qaysi Quiz yoki Video qolib ketganini ko'ramiz!
            safe_navigate(page, "https://www.coursera.org/organizations/dedc/my-learning?myLearningTab=IN_PROGRESS")
            time.sleep(4)
            dismiss_all_popups(page)
            in_prog_text = page.evaluate("() => (document.body ? document.body.innerText : '')")
            if "Introduction to Generative AI" in in_prog_text and "% complete" in in_prog_text:
                print("[!] DIQQAT: Kurs hali 'In Progress' da turibdi! IN_PROGRESS ichida qolib ketgan Quiz/Video tekshirilmoqda...")
                handled_in_prog = False
                # Birinchi o'rinda IN_PROGRESS kartochkasida qaysi Quiz yozilganini tekshiramiz
                for q_name, default_url, q_num in QUIZZES_INFO:
                    if q_name in in_prog_text and student_name:
                        print(f"[IN_PROGRESS] '{q_name}' qolib ketgani aniqlandi! Darhol yechilmoqda...")
                        solve_single_quiz_with_3_checks(page, q_name, default_url, q_num, student_name)
                        handled_in_prog = True
                        break

                # Agar aniq Quiz nomi ko'rinmasa yoki Video/Reading qolib ketgan bo'lsa, 'Resume' tugmasini bosib kiramiz
                if not handled_in_prog:
                    resume_btn = page.locator("a:has-text('Resume'), button:has-text('Resume'), a:has-text('Продолжить'), button:has-text('Продолжить')").first
                    if resume_btn.is_visible():
                        print("[IN_PROGRESS] 'Resume' tugmasi bosilib qolib ketgan dars/testga kirilmoqda...")
                        resume_btn.click(force=True)
                        time.sleep(5)
                        dismiss_all_popups(page)
                        curr_u = page.url
                        if "/assignment-submission/" in curr_u or "quiz-" in curr_u:
                            for q_name, default_url, q_num in QUIZZES_INFO:
                                if f"quiz-{q_num}" in curr_u.lower() or q_name.lower() in (page.evaluate("() => (document.body ? document.body.innerText : '')")).lower():
                                    if student_name:
                                        solve_single_quiz_with_3_checks(page, q_name, curr_u.split("/attempt")[0], q_num, student_name)
                                    break
                        elif "/lecture/" in curr_u:
                            print(f"[IN_PROGRESS] Qolib ketgan video ko'rilmoqda: {curr_u}")
                            for _ in range(8):
                                dismiss_all_popups(page)
                                if page.evaluate("() => { const v = document.querySelector('video'); return !!(v && v.duration > 1); }"):
                                    break
                                time.sleep(1)
                            page.evaluate("""() => {
                                const v = document.querySelector('video');
                                if (v) { v.muted = true; if (v.duration > 1) v.currentTime = Math.max(0, v.duration - 2.0); const p = v.play(); if (p && p.catch) p.catch(() => {}); }
                            }""")
                            time.sleep(5)
                        elif "/supplement/" in curr_u:
                            mark_btn = page.locator("button:has-text('Mark as completed'), button:has-text('Отметить как пройденное')").first
                            if mark_btn.is_visible():
                                mark_btn.click(force=True)
                                time.sleep(2.5)
                        handled_in_prog = True

                if handled_in_prog and student_name:
                    verify_student_name_with_3_checks(page, student_name)
                    continue
                return None

            # 2. Accomplishments sahifasi
            safe_navigate(page, "https://www.coursera.org/account/accomplishments")
            time.sleep(5)
            dismiss_all_popups(page)
            links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && h.includes('/account/accomplishments/verify/'))""")
            if links:
                return links[0]

            vc2 = page.locator("a:has-text('View certificate'), button:has-text('View certificate'), a:has-text('Посмотреть сертификат')").first
            if vc2.is_visible():
                vc2.click(force=True)
                time.sleep(5)
                if "/account/accomplishments/verify/" in page.url:
                    return page.url
        except Exception as e:
            print(f"[!] Sertifikat qidiruv {c_try}-urinishda xatolik: {e}")
            time.sleep(2)

    return None

class TempMailAPI:
    def __init__(self, existing_email=None):
        self.ctx = ssl._create_unverified_context()
        self.password = MAILTM_PASS
        self.token = ""
        if existing_email:
            self.email = existing_email
            for pwd_try in [MAILTM_PASS, COMMON_PASSWORD]:
                try:
                    body = json.dumps({'address': self.email, 'password': pwd_try}).encode()
                    req = urllib.request.Request('https://api.mail.tm/token', data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=self.ctx, timeout=10) as r:
                        self.token = json.loads(r.read().decode()).get('token', '')
                    if self.token:
                        self.password = pwd_try
                        break
                except Exception:
                    pass
            return

        for attempt in range(5):
            try:
                req = urllib.request.Request('https://api.mail.tm/domains', headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=self.ctx, timeout=10) as r:
                    dom = json.loads(r.read().decode())['hydra:member'][0]['domain']
                rnd = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
                self.email = f"{rnd}@{dom}"
                body = json.dumps({'address': self.email, 'password': self.password}).encode()
                req = urllib.request.Request('https://api.mail.tm/accounts', data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=self.ctx, timeout=10) as r:
                    pass
                req = urllib.request.Request('https://api.mail.tm/token', data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=self.ctx, timeout=10) as r:
                    self.token = json.loads(r.read().decode())['token']
                break
            except Exception as e:
                time.sleep(2.5)
                if attempt == 4:
                    raise e

    def wait_for_activation(self, timeout=35):
        if not self.token:
            return ""
        end_time = time.time() + timeout
        while time.time() < end_time:
            time.sleep(1.2)
            try:
                headers = {'Authorization': f'Bearer {self.token}', 'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request('https://api.mail.tm/messages', headers=headers)
                with urllib.request.urlopen(req, context=self.ctx, timeout=8) as r:
                    msgs = json.loads(r.read().decode()).get('hydra:member', [])
                for msg in msgs:
                    mid = msg['id']
                    req_m = urllib.request.Request(f'https://api.mail.tm/messages/{mid}', headers=headers)
                    with urllib.request.urlopen(req_m, context=self.ctx, timeout=8) as rm:
                        data = json.loads(rm.read().decode())
                        html = data.get('html', [''])[0] if isinstance(data.get('html'), list) else (data.get('html') or '')
                        text = data.get('text') or ''
                        links = re.findall(r'https?://[^\s"\'<>)]+', html + ' ' + text)
                        for l in links:
                            if 'activate' in l.lower() or 'uzbcoders' in l.lower() or 'aileaders' in l.lower():
                                return l.replace('&amp;', '&')
            except Exception:
                pass
        return ""

    def get_all_coursera_invites(self):
        """Pochtadagi barcha Coursera taklifnoma havolalarini (1: Join Coursera, 2: DEDC invites you to learn) qaytaradi."""
        if not self.token:
            return []
        account_links = []
        program_links = []
        try:
            headers = {'Authorization': f'Bearer {self.token}', 'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request('https://api.mail.tm/messages', headers=headers)
            with urllib.request.urlopen(req, context=self.ctx, timeout=8) as r:
                msgs = json.loads(r.read().decode()).get('hydra:member', [])
            for msg in msgs:
                subj = msg.get('subject', '').lower()
                if any(k in subj for k in ['invited', 'invitation', 'coursera', 'приглаш', 'обучен', 'learn', 'digital education']):
                    mid = msg['id']
                    req_m = urllib.request.Request(f'https://api.mail.tm/messages/{mid}', headers=headers)
                    with urllib.request.urlopen(req_m, context=self.ctx, timeout=8) as rm:
                        data = json.loads(rm.read().decode())
                        html = data.get('html', [''])[0] if isinstance(data.get('html'), list) else (data.get('html') or '')
                        found_url = ""
                        a_tags = re.findall(r'<a\s+[^>]*href=["\'](https?://link\.coursera\.org/f/a/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.I)
                        for href, txt in a_tags:
                            clean_t = re.sub(r'<[^>]+>', '', txt).strip().lower()
                            if any(w in clean_t for w in ['join now', 'присоединиться', 'join coursera', 'accept', 'start learning', 'начать', 'explore courses', 'log in', 'sign in']):
                                found_url = href.replace('&amp;', '&')
                                break
                        if not found_url:
                            links = re.findall(r'https?://link\.coursera\.org/f/a/[^\s"\'<>)]+', html)
                            if links:
                                found_url = links[0].replace('&amp;', '&')
                        if found_url:
                            # Avval 'Join now' va 'DEDC invites you to learn' ni to'g'ri tartibda yig'amiz
                            if 'you\'re invited to join coursera' in subj:
                                account_links.insert(0, found_url)
                            elif 'digital education' in subj or 'invites you to learn' in subj or 'обучен' in subj:
                                program_links.append(found_url)
                            else:
                                account_links.append(found_url)
        except Exception:
            pass
        return account_links + program_links

    def wait_for_coursera_invite(self, timeout=50):
        """Pochtadagi 2-XABAR: Coursera 'Join now' taklifnoma havolasini oladi."""
        if not self.token:
            return ""
        end_time = time.time() + timeout
        while time.time() < end_time:
            time.sleep(2.0)
            all_links = self.get_all_coursera_invites()
            if all_links:
                return all_links[-1]  # Agar DEDC program xati kelgan bo'lsa o'shani, aks holda 1-xatni qaytaradi
        return ""

def fill_react_input(locator, text: str):
    try:
        locator.scroll_into_view_if_needed()
        locator.click(force=True)
        locator.press("Control+a")
        locator.press("Backspace")
        locator.press_sequentially(text, delay=15)
    except Exception:
        pass

def pick_date_aileaders(page, birth_date: str):
    birth_date = str(birth_date).strip().split()[0]  # '2014-09-24 00:00:00' -> '2014-09-24'
    if "-" in birth_date:
        parts = birth_date.split("-")
        if len(parts[0]) == 4:  # YYYY-MM-DD
            year_str, month_idx, day_int = parts[0], int(parts[1]) - 1, int(parts[2])
        else:  # DD-MM-YYYY
            day_int, month_idx, year_str = int(parts[0]), int(parts[1]) - 1, parts[2]
    elif "/" in birth_date:
        parts = birth_date.split("/")
        if len(parts[0]) == 4:
            year_str, month_idx, day_int = parts[0], int(parts[1]) - 1, int(parts[2])
        elif int(parts[1]) > 12:
            month_idx, day_int, year_str = int(parts[0]) - 1, int(parts[1]), str(parts[2])
        else:
            day_int, month_idx, year_str = int(parts[0]), int(parts[1]) - 1, str(parts[2])
    else:
        day_str, month_str, year_str = birth_date.split(".")
        day_int, month_idx = int(day_str), int(month_str) - 1

    cal_btn = page.locator("button#date, button[data-slot='popover-trigger']").first
    cal_btn.click(force=True)
    page.wait_for_timeout(500)

    for s in page.locator("select").all():
        opts = [o.inner_text().strip() for o in s.locator("option").all()]
        if len(opts) == 12:
            s.select_option(index=month_idx)
            s.dispatch_event("change")
            page.wait_for_timeout(300)
        elif year_str in opts:
            s.select_option(label=year_str)
            s.dispatch_event("change")
            page.wait_for_timeout(300)

    page.wait_for_timeout(400)
    page.evaluate("""(day) => {
        const btns = Array.from(document.querySelectorAll('td:not(.rdp-outside) button'));
        const b = btns.find(x => x.innerText.trim() === String(day));
        if (b) b.click();
    }""", day_int)
    page.wait_for_timeout(400)

def safe_goto_commit(page, url, wait_sec=3.0):
    """Hech qachon TimeoutError berib to'xtab qolmaydigan xavfsiz o'tish funksiyasi!"""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(wait_sec)
        return True
    except Exception:
        try:
            page.goto(url, wait_until="commit", timeout=20000)
            time.sleep(wait_sec + 2.0)
            return True
        except Exception as e:
            print(f"   [Ogohlantirish] Sahifa yuklanishida kechikish: {str(e)[:80]}")
            time.sleep(2.0)
    return False

def ensure_aileaders_activated_and_tekshirish(page, mail_svc, student_email, student_password):
    """1-XABAR: Aileaders.uz pochtadan 1-faollashtirish havolasini ochadi (kelmasa 'Qayta yuborish' bosadi),
    so'ng Aileaders-ga kirib 'Generativ AI' kursida 'TEKSHIRISH' tugmasini bosadi."""
    try:
        print("   [1-XABAR: Aileaders Tasdiqlash] Pochtaga aktivatsiya havolasi kutilmoqda...")
        act_link = mail_svc.wait_for_activation(timeout=20)
        if not act_link:
            print("   [1-XABAR: Aileaders Tasdiqlash] Xat kechikdi, Aileaders.uz orqali 'Qayta yuborish' bosilmoqda...")
            safe_goto_commit(page, "https://aileaders.uz/auth/login", wait_sec=2.0)
            l_em = page.locator("input[type='email'], input[name='email']").first
            if l_em.count() > 0 and l_em.is_visible():
                l_em.fill(student_email)
            l_pwd = page.locator("input[type='password'], input[name='password']").first
            if l_pwd.count() > 0 and l_pwd.is_visible():
                l_pwd.fill(student_password)
            l_sub = page.locator("button[type='submit'], button:has-text('Kirish')").first
            if l_sub.count() > 0 and l_sub.is_visible():
                l_sub.click(force=True)

            for _ in range(8):
                page.wait_for_timeout(500)
                try:
                    clicked_resend = page.evaluate("""(em) => {
                        const el = Array.from(document.querySelectorAll('button, span, a, div')).find(e => (e.innerText || '').trim() === 'Qayta yuborish');
                        if (el) { el.click(); return true; }
                        return false;
                    }""", student_email)
                    if clicked_resend:
                        print("   [+] 'Qayta yuborish' tugmasi bosildi!")
                        break
                except Exception:
                    pass

            try:
                page.evaluate("""(em) => {
                    fetch('/api/profile/verify-email?email=' + encodeURIComponent(em)).catch(() => {});
                }""", student_email)
            except Exception:
                pass
            act_link = mail_svc.wait_for_activation(timeout=40)

        if act_link:
            print(f"   [1-XABAR: Aileaders Tasdiqlash] Aktivatsiya havolasi ochilmoqda...")
            safe_goto_commit(page, act_link, wait_sec=3.0)

        # Aileaders ga kirish (Login)
        safe_goto_commit(page, "https://aileaders.uz/auth/login", wait_sec=2.0)
        l_em = page.locator("input[type='email'], input[name='email']").first
        if l_em.count() > 0 and l_em.is_visible():
            fill_react_input(l_em, student_email)
        l_pwd = page.locator("input[type='password'], input[name='password']").first
        if l_pwd.count() > 0 and l_pwd.is_visible():
            fill_react_input(l_pwd, student_password)
        page.wait_for_timeout(400)
        l_sub = page.locator("button[type='submit'], button:has-text('Kirish')").first
        if l_sub.count() > 0 and l_sub.is_visible():
            l_sub.click(force=True)
            page.wait_for_timeout(3200)

        # Coursera kursini tanlash va "TEKSHIRISH" bosish
        print("   Coursera 'Generativ AI' kursi biriktirilmoqda...")
        safe_goto_commit(page, "https://aileaders.uz/courses", wait_sec=2.8)
        time.sleep(1.0)
        # 1. Telegram yoki boshqa modalni yopish
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(x => x.getAttribute('aria-label') === 'Yopish' || (x.innerText || '').trim().toLowerCase() === 'close');
            if (b) b.click();
        }""")
        page.keyboard.press("Escape")
        time.sleep(0.5)

        # 2. 'Kurslar' va 'Coursera' filterini tanlash
        kurslar_tab = page.locator("button:has-text('Kurslar')").first
        if kurslar_tab.count() > 0 and kurslar_tab.is_visible():
            kurslar_tab.click(force=True)
            time.sleep(0.5)

        c_tab = page.locator("button").filter(has_text=re.compile(r"Coursera", re.I)).first
        if c_tab.count() > 0 and c_tab.is_visible():
            c_tab.click(force=True)
            time.sleep(1.5)

        # 3. 'Generativ Sun’iy Intellektga Kirish' kartochkasini tanlash / ochish
        h3 = page.locator("h3").filter(has_text=re.compile(r"Generativ", re.I)).first
        if h3.count() > 0 and h3.is_visible():
            card_box = h3.locator("xpath=ancestor::div[contains(@class, 'flex-col')]").first
            open_btn = card_box.locator("button[aria-label='Kursni ochish']").first if card_box.count() > 0 else None
            if open_btn and open_btn.count() > 0 and open_btn.is_visible():
                open_btn.click(force=True)
            else:
                h3.click(force=True)
            time.sleep(2.5)

        tekshir_b = page.locator("button:has-text('TEKSHIRISH'), button:has-text('Tekshirish'), button:has-text('Boshlash'), button:has-text('Kursga')").first
        if tekshir_b.count() > 0 and tekshir_b.is_visible():
            print("   'TEKSHIRISH' bosildi!")
            tekshir_b.click(force=True)
            time.sleep(4.0)
    except Exception as e:
        print(f"   [!] Aileaders faollashtirishda ogohlantirish: {e}")


def complete_coursera_join_and_enroll(page, mail_svc, student_password, full_name="", wait_timeout=45):
    """2-XABAR: Pochtadagi Coursera Enterprise 'Join now' taklifnomasini ochadi.
    TARTIB:
    1. Avval 'Create password' / Ism maydoni (yangi profil bo'lsa) orqali parolni o'rnatadi.
    2. Shu bo'lmasa KEYIN mavjud profil parolini (Log in / Welcome back) kiritib tizimga kiradi.
    3. DEDC dasturiga ('Join Program') ulanadi va kursga Enroll qiladi."""
    print("   [2-XABAR: Coursera Join now] Taklifnoma kutilmoqda...")
    coursera_link = mail_svc.wait_for_coursera_invite(timeout=wait_timeout)
    if not coursera_link:
        if getattr(mail_svc, "email", ""):
            ensure_aileaders_activated_and_tekshirish(page, mail_svc, mail_svc.email, student_password)
        coursera_link = mail_svc.wait_for_coursera_invite(timeout=40)

    if not coursera_link:
        return False

    all_invite_links = mail_svc.get_all_coursera_invites() if hasattr(mail_svc, "get_all_coursera_invites") else [coursera_link]
    if not all_invite_links:
        all_invite_links = [coursera_link]

    if "authMode=" in page.url:
        try:
            page.goto("about:blank", timeout=5000)
        except Exception:
            pass

    for idx_link, inv_link in enumerate(all_invite_links, 1):
        print(f"   [2-XABAR: Coursera Join #{idx_link}/{len(all_invite_links)}] Taklifnoma ochilmoqda...")
        safe_goto_commit(page, inv_link, wait_sec=4.0)
        return_to_url = ""
        for step_i in range(35):
            try:
                if "returnTo=" in page.url and not return_to_url:
                    q_params = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
                    if q_params.get("returnTo"):
                        return_to_url = q_params["returnTo"][0]

                # Agar sahifada 'Join Program' / 'Continue' / 'Присоединиться к программе' chiqsa, bosamiz!
                join_prog_btn = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), button:has-text('Accept invitation'), div[role='dialog'] button:has-text('Continue'), div[role='dialog'] button:has-text('Продолжить')").first
                if join_prog_btn.count() > 0 and join_prog_btn.is_visible():
                    print("   [JOIN] 'Join Program' tugmasi bosilmoqda...")
                    join_prog_btn.click(force=True)
                    time.sleep(2.5)

                # Agar email kiritish maydoni bo'lsa (Log in / Welcome back):
                em_in_join = page.locator("input[type='email'], input[name='email']").first
                if em_in_join.count() > 0 and em_in_join.is_visible():
                    em_val = getattr(mail_svc, "email", "")
                    if em_val:
                        try:
                            cur_em = em_in_join.input_value().strip()
                        except Exception:
                            cur_em = ""
                        if not cur_em:
                            em_in_join.fill(em_val)
                            time.sleep(0.3)
                    cont_b = page.locator("button:has-text('Continue'), button:has-text('Продолжить'), button:has-text('Next'), button:has-text('Далее'), button[type='submit']").first
                    if cont_b.count() > 0 and cont_b.is_visible():
                        cont_b.click(force=True)
                        time.sleep(1.2)

                # TARTIB:
                # 1) BIRINCHI NAVBATDA: 'Create password' / Ism kiritish bormi? (Yangi profil uchun)
                create_pwd = page.locator("input[placeholder*='Create password' i], input[aria-label*='Create password' i], input[id*='create-password' i]").first
                fn_in = page.locator("input[name='fullName'], input[placeholder*='full name' i], input[placeholder*='имя' i]").first
                
                is_create_password = False
                if create_pwd.count() > 0 and create_pwd.is_visible():
                    is_create_password = True
                    pwd_box = create_pwd
                elif fn_in.count() > 0 and fn_in.is_visible() and page.locator("input[type='password']").count() > 0:
                    is_create_password = True
                    pwd_box = page.locator("input[type='password']").first

                if is_create_password:
                    print("   [PAROL O'RNATISH] 'Create password' maydoni topildi...")
                    if fn_in.count() > 0 and fn_in.is_visible():
                        try:
                            cur_fn = fn_in.input_value().strip()
                        except Exception:
                            cur_fn = ""
                        if not cur_fn and full_name:
                            fn_in.click(force=True)
                            time.sleep(0.15)
                            fn_in.fill(full_name.replace("`", "'"))
                            time.sleep(0.25)
                    pwd_box.click(force=True)
                    time.sleep(0.2)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    time.sleep(0.15)
                    page.keyboard.type(student_password, delay=35)
                    time.sleep(0.5)

                    set_b = page.locator("button:has-text('Set Password'), button:has-text('Установить пароль'), button:has-text('Create Account'), button:has-text('Создать'), button:has-text('Continue'), button:has-text('Продолжить'), button[type='submit']").first
                    if set_b.count() > 0 and set_b.is_visible():
                        print("   [+] 'Set Password' bosilmoqda...")
                        set_b.click(force=True)
                        time.sleep(3.0)

                # 2) SHU BO'LMASA KEYIN: Mavjud parol kiritish maydoni (Log in / Welcome back)
                else:
                    existing_pwd = page.locator("input[type='password'], input[name='password']").first
                    if existing_pwd.count() > 0 and existing_pwd.is_visible():
                        print("   [LOGIN] 'Create password' yo'q (profil oldin ochilgan). Mavjud parol kiritilmoqda...")
                        existing_pwd.click(force=True)
                        time.sleep(0.2)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        time.sleep(0.15)
                        page.keyboard.type(student_password, delay=35)
                        time.sleep(0.5)

                        login_btn = page.locator("button:has-text('Log in'), button:has-text('Войти'), button:has-text('Next'), button:has-text('Далее'), button:has-text('Continue'), button:has-text('Продолжить'), button[type='submit']").first
                        if login_btn.count() > 0 and login_btn.is_visible():
                            print("   [+] 'Log in' bosilmoqda...")
                            login_btn.click(force=True)
                            time.sleep(3.0)

                cookies = [c.get("name", "") for c in page.context.cookies()]
                if any("CAUTH" in c for c in cookies) or "/programs/" in page.url or "/learn/" in page.url:
                    j_b = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе')").first
                    if j_b.count() > 0 and j_b.is_visible():
                        j_b.click(force=True)
                        time.sleep(2.0)
                    time.sleep(2.0)
                    break
            except Exception:
                pass
            time.sleep(0.6)

        for _ in range(8):
            try:
                terms_b = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), button:has-text('Продолжить'), button:has-text('Continue')").first
                if terms_b.count() > 0 and terms_b.is_visible():
                    terms_b.click(force=True)
                    time.sleep(3.0)
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if return_to_url and "learning-program" not in page.url:
            safe_goto_commit(page, return_to_url, wait_sec=3.5)
            try:
                terms_b = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), button:has-text('Продолжить'), button:has-text('Continue')").first
                if terms_b.count() > 0 and terms_b.is_visible():
                    terms_b.click(force=True)
                    time.sleep(3.0)
            except Exception:
                pass

    # Agar 2-xat ('invites you to learn on Coursera') hozirgina kelgan bo'lsa, uni ham tekshirib ochamiz
    try:
        latest_links = mail_svc.get_all_coursera_invites() if hasattr(mail_svc, "get_all_coursera_invites") else []
        for extra_l in latest_links:
            if extra_l not in all_invite_links:
                safe_goto_commit(page, extra_l, wait_sec=4.0)
                for _ in range(8):
                    terms_b = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), button:has-text('Продолжить'), button:has-text('Continue')").first
                    if terms_b.count() > 0 and terms_b.is_visible():
                        terms_b.click(force=True)
                        time.sleep(3.0)
                        break
                    time.sleep(0.5)
    except Exception:
        pass

    ensure_enrolled_on_coursera(page)
    return True

def register_new_student_and_enroll(context, page, student, status_callback=None):
    """Bazada (akkountlar.txt) yo'q o'quvchini Aileaders.uz + Coursera da ro'yxatdan o'tkazadi."""
    full_name = student["name"]
    class_name = student.get("class", "")
    birth_date = student.get("birth_date", "").strip()
    doc_series = student.get("doc_series", "").strip()
    doc_number = student.get("doc_number", "").strip()

    if not birth_date or not doc_series or not doc_number:
        save_unrecoverable_student(full_name, class_name, "akkountlar.txt da yo'q va ro'yxatdan o'tish uchun tug'ilgan sana/hujjat ma'lumotlari berilmagan")
        return "UNRECOVERABLE", None

    print(f"[REGISTRATSIYA] {full_name} bazada yo'q. Aileaders.uz orqali yangi profil ochilmoqda...")
    try:
        mail_svc = TempMailAPI()
        student_email = mail_svc.email
        student_password = COMMON_PASSWORD
        print(f"   Yangi pochta: {student_email}")
    except Exception as e:
        print(f"[!] TempMail xatosi: {e}")
        return "RETRY", None

    # Hujjat seriyasini har xil variantlarda (Guvohnoma: T, I-TV, TV, I-FR va Passport) tekshirib ko'rish ro'yxati
    ds_up = doc_series.upper().strip()
    num_pad7 = doc_number.zfill(7) if len(doc_number) < 7 else doc_number
    doc_candidates = []
    if "-" in ds_up:
        doc_candidates.append(("guvohnoma", ds_up, num_pad7))
        if ds_up != "I-TV":
            doc_candidates.append(("guvohnoma", "I-TV", num_pad7))
        if ds_up != "I-FR":
            doc_candidates.append(("guvohnoma", "I-FR", num_pad7))
        doc_candidates.append(("guvohnoma", "T", doc_number))
    elif ds_up in ("T", "TV", "FR", "TN", "AN", "SM", "QA", "SU", "NA", "BU", "XO", "JZ", "SI", "QR", "TS"):
        doc_candidates.append(("guvohnoma", ds_up, doc_number if ds_up == "T" else num_pad7))
        if ds_up == "T":
            doc_candidates.append(("guvohnoma", "I-TV", num_pad7))
            doc_candidates.append(("guvohnoma", "TV", num_pad7))
            doc_candidates.append(("guvohnoma", "I-FR", num_pad7))
            if len(doc_number) == 8:
                doc_candidates.append(("guvohnoma", "I-TV", doc_number[1:]))
                doc_candidates.append(("guvohnoma", "I-FR", doc_number[1:]))
        else:
            doc_candidates.append(("guvohnoma", f"I-{ds_up}", num_pad7))
            doc_candidates.append(("guvohnoma", "T", doc_number))
            doc_candidates.append(("guvohnoma", "I-FR", num_pad7))
        doc_candidates.append(("passport", ds_up, doc_number))
    else:
        doc_candidates.append(("passport", ds_up, doc_number))
        doc_candidates.append(("guvohnoma", ds_up, num_pad7))
        doc_candidates.append(("guvohnoma", f"I-{ds_up}", num_pad7))
        doc_candidates.append(("guvohnoma", "T", doc_number))

    try:
        reg_step2_ok = False
        for cand_idx, (doc_mode, s_val, n_val) in enumerate(doc_candidates):
            if cand_idx > 0:
                print(f"   [HUJJAT VARIANTI #{cand_idx + 1}] {doc_mode.upper()} sifatida '{s_val} {n_val}' tekshirilmoqda...")
            safe_goto_commit(page, "https://aileaders.uz/auth/register", wait_sec=2.5)

            if doc_mode == "guvohnoma":
                guv_b = page.locator("button:has-text('Guvohnoma')").first
                try:
                    guv_b.wait_for(state="visible", timeout=12000)
                except Exception:
                    pass
                if guv_b.is_visible():
                    guv_b.click(force=True)
                    page.wait_for_timeout(600)
                page.locator("input[placeholder*='Seriya'], input[name='metrika_series']").first.fill(s_val)
                page.locator("input[placeholder*='Raqam'], input[name='metrika_number']").first.fill(n_val)
            else:
                pass_b = page.locator("button").filter(has_text="Passport").first
                if pass_b.is_visible():
                    pass_b.click(force=True)
                    page.wait_for_timeout(400)
                page.locator("input[name='passport_number'], input[placeholder*='Seriya']").first.fill(f"{s_val}{n_val}")

            pick_date_aileaders(page, birth_date)

            cb = page.locator("button[role='combobox'], button[data-slot='select-trigger']").first
            if cb.is_visible():
                cb.click(force=True)
                page.wait_for_timeout(400)
                opt = page.locator("[role='option']").first
                if opt.is_visible():
                    opt.click(force=True)
                page.wait_for_timeout(400)

            sub1 = page.locator("button[type='submit']").filter(has_text=re.compile(r"Ro.yxatdan o.tish", re.I)).first
            if sub1.is_visible():
                sub1.click(force=True)
                page.wait_for_timeout(3500)

            keyingi = page.locator("button:has-text('Keyingi')").first
            if not keyingi.is_visible():
                b_txt1 = page.evaluate("() => (document.body ? document.body.innerText : '')")
                if "registratsiya qilingan" in b_txt1.lower():
                    print(f"   [!] Aileaders.uz javobi: '{s_val} {n_val}' ushbu ma'lumotlar bilan oldin registratsiya qilingan!")
                    save_unrecoverable_student(full_name, class_name, f"Aileaders.uz: Ushbu ma'lumotlar bilan oldin registratsiya qilingan ({s_val} {n_val})")
                    return "UNRECOVERABLE", None
                continue

            print(f"   1-bosqich muvaffaqiyatli ({s_val} {n_val})! 'Keyingi' bosilmoqda...")
            em_in = page.locator("input[type='email'], input[name='email']").first
            for _ in range(3):
                if em_in.count() > 0 and em_in.is_visible():
                    break
                keyingi.click(force=True)
                page.wait_for_timeout(1500)

            try:
                em_in.wait_for(state="visible", timeout=7000)
            except Exception:
                pass

            if not em_in.is_visible():
                continue
            fill_react_input(em_in, student_email)

            ph_in = page.locator("input[name='number'], input[type='tel']").first
            if ph_in.is_visible():
                ph_in.click(force=True)
                ph_in.evaluate("""(el, val) => {
                    el.focus();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(el, val);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""", PHONE_FORMATTED)

            p1 = page.locator("input[name='password1'], input[type='password']").first
            p2 = page.locator("input[name='password2']").first
            if p1.is_visible():
                fill_react_input(p1, student_password)
            if p2.is_visible():
                fill_react_input(p2, student_password)

            page.wait_for_timeout(800)
            sub2 = page.locator("div[role='dialog'] button, form button").filter(has_text=re.compile(r"Keyingi|Ro.yxatdan|Yuborish", re.I)).last
            sub2.click(force=True)
            page.wait_for_timeout(3500)

            body_txt = page.evaluate("() => (document.body ? document.body.innerText : '')")
            if "Serverda ichki xatolik" in body_txt or ("/auth/register" in page.url and em_in.is_visible() and "xatolik" in body_txt.lower()):
                print(f"   [!] '{s_val} {n_val}' da Aileaders server xatosi berdi, keyingi variant sinab ko'riladi...")
                continue

            reg_step2_ok = True
            break

        if not reg_step2_ok:
            save_unrecoverable_student(full_name, class_name, f"Barcha hujjat variantlari ({doc_series} {doc_number}: T/TV/I-TV/I-FR) tekshirildi, Aileaders ma'lumotni topmadi!")
            return "UNRECOVERABLE", None

        with FILE_LOCK:
            with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{full_name} | {class_name} | {student_email} | {student_password} | {PHONE_RAW}\n")
        print(f"   [OK] Yangi akkount bazaga (akkountlar.txt) saqlandi: {student_email}")
        if status_callback:
            status_callback(f"📧 Aileaders.uz profil ochildi ({student_email})! 1-xabar aktivatsiya qilinmoqda...")

        # 1-XABAR: Aileaders Tasdiqlash + TEKSHIRISH
        ensure_aileaders_activated_and_tekshirish(page, mail_svc, student_email, student_password)
        if status_callback:
            status_callback(f"🔗 1-xabar tasdiqlandi! Coursera 2-xabar (Join now) ulanmoqda...")

        # 2-XABAR: Coursera Join now + Set Password
        joined_ok = complete_coursera_join_and_enroll(page, mail_svc, student_password, full_name=full_name, wait_timeout=45)
        if joined_ok:
            if status_callback:
                status_callback(f"✅ Coursera DEDC dasturiga ulandi va kursga yozildi!")
            return "OK", {"email": student_email, "password": student_password}
        return "RETRY", {"email": student_email, "password": student_password}
    except Exception as e:
        print(f"   [!] Ro'yxatdan o'tishda xatolik ushlandi (to'xtab qolmaydi!): {e}")
        return "RETRY", ({"email": student_email, "password": student_password} if reg_step2_ok else None)

def process_student(student, status_callback=None, headless=False, worker_id=0):
    t_start = time.time()
    full_name = student["name"]
    class_name = student.get("class", "")
    tag = f"[OQIM #{worker_id}] " if worker_id else ""

    if full_name in get_completed_students():
        print(f"{tag}[CHECK] {full_name} allaqachon sertifikat olgan. Keyingi o'quvchiga o'tiladi.")
        return "COMPLETED"

    if full_name in get_unrecoverable_students():
        print(f"{tag}[SKIP - ILOJI YO'Q] {full_name} oldin ro'yxatdan o'tgan va bazada paroli yo'q (yoki kirib bo'lmaydi). Qayta urinilmaydi!")
        return "UNRECOVERABLE"

    accounts = get_existing_accounts()
    acc = accounts.get(full_name)

    common_media_args = [
        "--disable-blink-features=AutomationControlled",
        "--autoplay-policy=no-user-gesture-required",
        "--mute-audio",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ]
    if headless:
        launch_args = common_media_args + ["--window-size=1920,1080"]
        ctx_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
    else:
        if worker_id == 1:
            launch_args = common_media_args + ["--window-position=0,0", "--window-size=960,1030"]
        elif worker_id == 2:
            launch_args = common_media_args + ["--window-position=960,0", "--window-size=960,1030"]
        else:
            launch_args = common_media_args + ["--start-maximized"]
        ctx_kwargs = {
            "no_viewport": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }

    try:
        with sync_playwright() as p:
            win_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            linux_chrome = "/usr/bin/google-chrome"
            if sys.platform != "win32":
                launch_args = launch_args + ["--no-sandbox", "--disable-dev-shm-usage"]
            exe_path = win_chrome if os.path.exists(win_chrome) else (linux_chrome if os.path.exists(linux_chrome) else None)
            browser = p.chromium.launch(
                executable_path=exe_path,
                headless=headless,
                args=launch_args
            )
            context = browser.new_context(**ctx_kwargs)
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            if not acc:
                if status_callback:
                    status_callback(f"📝 Yangi profil ro'yxatdan o'tkazilmoqda...")
                reg_status, new_acc = register_new_student_and_enroll(context, page, student, status_callback=status_callback)
                if reg_status == "UNRECOVERABLE":
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return "UNRECOVERABLE"
                elif not new_acc:
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return "FAILED"
                acc = new_acc
                # Yangi ochilgan profil Courseraga kirganini tekshiramiz, kirmagan bo'lsa kiramiz!
                cookies = [c.get("name", "") for c in context.cookies()]
                if not any("CAUTH" in c for c in cookies):
                    try:
                        existing_mail = TempMailAPI(existing_email=acc["email"])
                        if existing_mail.token:
                            complete_coursera_join_and_enroll(page, existing_mail, acc["password"], full_name=full_name, wait_timeout=25)
                    except Exception:
                        pass
                cookies = [c.get("name", "") for c in context.cookies()]
                if not any("CAUTH" in c for c in cookies):
                    print(f"{tag}[!] {acc['email']} ga bu safar kirib bo'lmadi, keyingi bosqichda qayta tekshiriladi!")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return "FAILED"
                if not ensure_enrolled_on_coursera(page):
                    try:
                        existing_mail = TempMailAPI(existing_email=acc["email"])
                        if existing_mail.token:
                            complete_coursera_join_and_enroll(page, existing_mail, acc["password"], full_name=full_name, wait_timeout=18)
                    except Exception:
                        pass
            else:
                email = acc["email"]
                password = acc["password"]
                print(f"\n=======================================================")
                print(f"{tag}>>> O'QUVCHI: {full_name} ({email}) <<<")
                print(f"=======================================================")
                if status_callback:
                    status_callback(f"🔐 {full_name}: Pochtadan DEDC Join ulanmoqda ({email})...")

                # Coursera to'g'ridan-to'g'ri (authMode=login) da captcha / to'lov so'raydi.
                # Shuning uchun doimo POCHTA (mail.tm) dagi 'Join now' yoki Aileaders 'TEKSHIRISH' orqali kiriladi!
                print(f"{tag}[POCHTA-JOIN] {email} uchun mail.tm pochtasidan Join/DEDC havolasi ochilmoqda...")
                existing_mail = TempMailAPI(existing_email=email)
                joined_ok = False
                if existing_mail.token:
                    joined_ok = complete_coursera_join_and_enroll(page, existing_mail, password, full_name=full_name, wait_timeout=20)

                if not joined_ok or not ensure_enrolled_on_coursera(page):
                    print(f"{tag}[AILEADERS-TEKSHIRISH] {email} uchun Aileaders TEKSHIRISH orqali yangi Join havolasi yuborilmoqda...")
                    if status_callback:
                        status_callback(f"🔄 {full_name}: Aileaders TEKSHIRISH orqali yangi Join yuborilmoqda...")
                    try:
                        ensure_aileaders_activated_and_tekshirish(page, existing_mail, email, password)
                        complete_coursera_join_and_enroll(page, existing_mail, password, full_name=full_name, wait_timeout=25)
                    except Exception as rec_e:
                        print(f"{tag}[!] Aileaders TEKSHIRISH xatosi: {rec_e}")

                if not ensure_enrolled_on_coursera(page):
                    print(f"{tag}[!] {email} kursga yozilmadi, keyingi bosqichda qayta tekshiriladi!")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return "FAILED"

            cert_url = None
            # Sertifikat chiqmasa, xatoni topib to'g'rilash uchun 3 marta to'liq tekshirib harakat qiladi!
            for full_try in range(1, 4):
                try:
                    if full_try > 1:
                        print(f"\n{tag}[QAYTA TEKSHIRUV #{full_try}/3] {full_name}: Sertifikat chiqmagani sababli xatoni (test/video/verify) topib to'g'rilanmoqda...")

                    # 2. Module 1 dagi barcha Quiz va dars holatini tekshirish
                    overview = check_module1_overview(page)

                    # 3. BIRINCHI O'RINDA 4 TA QUIZNI TEKSHIRISH VA YECHISH!
                    quiz_statuses = overview.get("quizzes", {})
                    dynamic_urls = overview.get("quiz_urls", {})
                    print(f"{tag}[MODULE 1 QUIZ HOLATI]: {quiz_statuses}")
                    if status_callback:
                        status_callback(f"✍️ {full_name}: Quiz testlari (1-4) yechilmoqda...")

                    for q_name, default_url, q_num in QUIZZES_INFO:
                        actual_url = dynamic_urls.get(q_name, default_url)
                        if "/assignment-submission/" not in str(actual_url):
                            actual_url = default_url
                        if quiz_statuses.get(q_name) == "PASSED":
                            print(f"{tag}[+] {q_name} allaqachon 100% (PASSED) - vaqt sarflamay o'tkazib yuborildi!")
                        else:
                            print(f"{tag}[-] {q_name} bajarilmagan ({quiz_statuses.get(q_name)}) - birinchi o'rinda yechilmoqda...")
                            solve_single_quiz_with_3_checks(page, q_name, actual_url, q_num, full_name)

                    # 4. KEYIN Videolar va Reading 100% ekanligini tekshirish (agar yashil ptichka bo'lsa, kirmaydi!)
                    if status_callback:
                        status_callback(f"🎬 {full_name}: Videolar va Reading 100% tekshirilmoqda...")
                    ensure_videos_and_reading_100(page, overview)

                    # 5. Ismni tasdiqlash (Verify My Name)
                    if status_callback:
                        status_callback(f"✅ {full_name}: Ism tasdiqlanmoqda (Verify My Name) va Sertifikat olinmoqda...")
                    verify_student_name_with_3_checks(page, full_name)

                    # 6. Rasmiy sertifikat havolasini olish (chiqmasa IN_PROGRESS ichidan qolib ketgan Quiz/Videoni topib bajaradi!)
                    cert_url = extract_certificate_with_3_checks(page, full_name)
                    if cert_url:
                        break
                except Exception as e:
                    print(f"{tag}[!] {full_name} {full_try}-urinishda xatolik ushlandi (qayta tekshiriladi): {e}")
                    time.sleep(1.5)

            try:
                browser.close()
            except Exception:
                pass

            elapsed = int(time.time() - t_start)
            if cert_url:
                save_certificate_result(full_name, class_name, cert_url)
                print(f"{tag}[TEZLIK] {full_name} sertifikati {elapsed} soniyada ({elapsed // 60} daqiqa {elapsed % 60} soniyada) olindi!")
                return "COMPLETED"
            else:
                print(f"{tag}[!] {full_name} uchun 3 marta urinishda ham sertifikat havolasi chiqmadi! ({elapsed}s)")
                return "FAILED"
    except Exception as outer_err:
        print(f"{tag}[!] {full_name} jarayonida kutilmagan xato ushlandi (dastur to'xtab qolmaydi!): {outer_err}")
        return "FAILED"

ROSTER_EXCEL = "oquvchi.xlsx"
RESULTS_EXCEL = "natijalar_sertifikatlar.xlsx"

def get_certificate_map():
    with FILE_LOCK:
        cert_map = {}
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "http" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 3:
                            cert_map[parts[0].upper()] = parts[2]
                        elif len(parts) == 2:
                            cert_map[parts[0].upper()] = parts[1]
        return cert_map

def get_error_reason_map():
    with FILE_LOCK:
        err_map = {}
        if os.path.exists(ERRORS_FILE):
            with open(ERRORS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "|" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 2:
                            err_map[parts[0].upper()] = parts[-1]
        return err_map

def create_or_load_roster_excel():
    """oquvchi.xlsx shablonini yaratadi (agar yo'q bo'lsa oquvchi.txt dan ko'chiradi) va ichidagi o'quvchilarni o'qiydi."""
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    txt_students = []
    if os.path.exists(ROSTER_FILE):
        with open(ROSTER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = [p.strip() for p in re.split(r'\t|\|', line) if p.strip()]
                    if len(parts) >= 5:
                        txt_students.append({
                            "name": parts[0].upper(),
                            "birth_date": parts[1],
                            "doc_series": parts[2],
                            "doc_number": parts[3],
                            "class": parts[4],
                            "school": parts[5] if len(parts) >= 6 else ""
                        })

    if txt_students:
        wb = Workbook()
        ws = wb.active
        ws.title = "Oquvchilar Shabloni"

        default_class = txt_students[0].get("class", "5-V") if txt_students else ""
        ws.append([
            "COURSERA SERTIFIKAT (SHABLON)",
            f"MAKTAB / SINF: {default_class}",
            f"JAMI O'QUVCHILAR: {len(txt_students)} ta",
            "", "", ""
        ])
        top_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        top_font = Font(color="FFFFFF", bold=True, size=11)
        for c_i in range(1, 7):
            c = ws.cell(row=1, column=c_i)
            c.fill = top_fill
            c.font = top_font

        headers = ["№", "F.I.SH", "Tug'ilgan sana", "I-FR (Seriya)", "Guvohnoma / Pasport raqami", "Sinf"]
        ws.append(headers)
        hdr_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        hdr_font = Font(color="FFFFFF", bold=True, size=11)
        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )
        for c_i in range(1, len(headers) + 1):
            c = ws.cell(row=2, column=c_i)
            c.fill = hdr_fill
            c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center")

        for idx, st in enumerate(txt_students, 1):
            ws.append([
                idx,
                st["name"],
                st["birth_date"],
                st["doc_series"],
                st["doc_number"],
                st["class"],
            ])
            for c_i in range(1, len(headers) + 1):
                ws.cell(row=idx + 2, column=c_i).border = thin_border

        col_widths = [6, 40, 16, 15, 25, 12]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=2, column=i).column_letter].width = w

        try:
            wb.save(ROSTER_EXCEL)
        except Exception:
            pass
        return txt_students

    if os.path.exists(ROSTER_EXCEL):
        students = []
        wb = load_workbook(ROSTER_EXCEL, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            vals = [str(v).strip() if v is not None else "" for v in row]
            if not any(vals):
                continue
            first_non_empty = next((v for v in vals if v), "")
            if first_non_empty.upper().startswith("COURSERA") or first_non_empty in ["№", "#", "T/R"] or "F.I.SH" in " ".join(vals).upper():
                continue
            if vals[0].isdigit() and len(vals) >= 6:
                name_val = vals[1].upper()
                b_date = vals[2]
                d_ser = vals[3]
                d_num = vals[4]
                s_cls = vals[5]
            else:
                non_empty = [v for v in vals if v]
                if non_empty and non_empty[0].isdigit():
                    non_empty = non_empty[1:]
                if len(non_empty) < 1:
                    continue
                name_val = non_empty[0].upper()
                b_date = non_empty[1] if len(non_empty) > 1 else ""
                d_ser = non_empty[2] if len(non_empty) > 2 else ""
                d_num = non_empty[3] if len(non_empty) > 3 else ""
                s_cls = non_empty[4] if len(non_empty) > 4 else ""
            if len(name_val.split()) >= 2:
                students.append({
                    "name": name_val,
                    "birth_date": b_date,
                    "doc_series": d_ser,
                    "doc_number": d_num,
                    "class": s_cls,
                })
        if students:
            return students

    return txt_students

def export_results_to_excel(students, output_file=RESULTS_EXCEL, school_info=""):
    """Barcha o'quvchilar ma'lumotlari, Login, Parol, Sertifikat havolasi va Sertifikat raqami bilan Excelga saqlaydi."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    accounts = get_existing_accounts()
    certs = get_certificate_map()
    errors = get_error_reason_map()
    unrec_set = get_unrecoverable_students()

    with FILE_LOCK:
        wb = Workbook()
        ws = wb.active
        ws.title = "Coursera Natijalar"

        total_cnt = len(students)
        done_cnt = sum(1 for s in students if s["name"] in certs)
        classes_set = sorted({s.get("class", "") for s in students if s.get("class", "")})
        class_label = ", ".join(classes_set) if classes_set else "—"
        if school_info:
            school_label = f"MAKTAB: {school_info} ({class_label})"
        else:
            school_label = f"MAKTAB / SINF: {class_label}"

        top_row = [
            "COURSERA SERTIFIKAT",
            school_label,
            f"JAMI: {total_cnt} ta",
            f"OLINDI: {done_cnt} ta",
            "", "", "", "", "", ""
        ]
        ws.append(top_row)
        top_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        top_font = Font(color="FFFFFF", bold=True, size=11)
        for col_i in range(1, 11):
            c = ws.cell(row=1, column=col_i)
            c.fill = top_fill
            c.font = top_font
            c.alignment = Alignment(horizontal="center" if col_i != 2 else "left", vertical="center")

        headers = [
            "№",
            "F.I.SH",
            "Tug'ilgan sana",
            "I-FR (Seriya)",
            "Raqami",
            "Sinf",
            "Pochta (Login)",
            "Parol",
            "Sertifikat Havolasi",
            "Sertifikat Raqami / Holati"
        ]
        ws.append(headers)
        hdr_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        hdr_font = Font(color="FFFFFF", bold=True, size=11)
        ok_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        skip_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        wait_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        for col_i in range(1, len(headers) + 1):
            c = ws.cell(row=2, column=col_i)
            c.fill = hdr_fill
            c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center")

        for idx, st in enumerate(students, 1):
            name = st["name"]
            acc = accounts.get(name, {})
            email = acc.get("email", "—")
            password = acc.get("password", "—")
            cert_url = certs.get(name, "")

            if cert_url:
                cert_id = cert_url.rstrip("/").split("/")[-1]
                cert_status = cert_id
                r_fill = ok_fill
            elif name in unrec_set:
                reason = errors.get(name, "Oldin ro'yxatdan o'tgan (bazada login-paroli yo'q)")
                cert_status = f"ILOJI YO'Q: {reason}"
                r_fill = skip_fill
            else:
                cert_status = "Jarayonda (Navbatda)"
                r_fill = wait_fill

            row_data = [
                idx,
                name,
                st.get("birth_date", ""),
                st.get("doc_series", ""),
                st.get("doc_number", ""),
                st.get("class", ""),
                email,
                password,
                cert_url if cert_url else "—",
                cert_status
            ]
            ws.append(row_data)
            row_num = idx + 2
            for col_i in range(1, len(headers) + 1):
                c = ws.cell(row=row_num, column=col_i)
                c.fill = r_fill
                c.border = thin_border
                if col_i in [1, 3, 4, 5, 6]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                if col_i == 9 and cert_url:
                    c.hyperlink = cert_url
                    c.font = Font(color="0563C1", underline="single")

        col_widths = [6, 38, 15, 14, 15, 10, 30, 15, 56, 35]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=2, column=i).column_letter].width = w

        try:
            wb.save(output_file)
        except Exception as e:
            print(f"[!] Excel faylni saqlashda ogohlantirish (fayl ochiq bo'lishi mumkin): {e}")
        return output_file

def run_pipeline(headless=False, max_workers=1, mode_title=""):
    title = mode_title or f"UZBEK CODERS BOT - SUPER-TEZ 100% PIPELINE (v9.0 | Oqimlar: {max_workers}x | Virtual={headless})"
    print("=" * 80)
    print(title)
    print("=" * 80)

    students = create_or_load_roster_excel()
    export_results_to_excel(students, RESULTS_EXCEL)
    print(f"[+] Shablon fayl: {ROSTER_EXCEL} | Natijalar Excel: {RESULTS_EXCEL}")

    for pass_num in range(1, 4):
        done_set = get_completed_students()
        unrec_set = get_unrecoverable_students()
        remaining_indexed = [
            (idx, s) for idx, s in enumerate(students, 1)
            if s["name"] not in done_set and s["name"] not in unrec_set
        ]
        if not remaining_indexed:
            export_results_to_excel(students, RESULTS_EXCEL)
            print("\n[YAKUNLANDI] Barcha imkoni bor o'quvchilarning sertifikatlari 100% olindi va Excelga saqlandi!")
            break

        if pass_num > 1:
            print("\n" + "=" * 80)
            print(f"QOLIB KETGAN {len(remaining_indexed)} TA O'QUVCHINI QAYTA TEKSHIRIB OLISH (BOSQICH #{pass_num}/3)")
            print("(Kirib bo'lmaydigan / bazada paroli yo'q o'quvchilarga qayta urinilmaydi!)")
            print("=" * 80)

        if max_workers <= 1:
            for idx, student in remaining_indexed:
                s_name = student["name"]
                if s_name in get_completed_students() or s_name in get_unrecoverable_students():
                    continue
                print(f"\n[{idx}/{len(students)}] ISHLOV BERILMOQDA: {s_name}")
                try:
                    status = process_student(student, headless=headless, worker_id=0)
                except Exception as e:
                    print(f"[!] {s_name} da kutilmagan xato ushlandi (kod to'xtamaydi, davom etadi): {e}")
                    status = "FAILED"
                try:
                    export_results_to_excel(students, RESULTS_EXCEL)
                except Exception:
                    pass
                if status == "UNRECOVERABLE":
                    print(f"[O'TKAZILDI - QAYTA URINILMAYDI] {s_name}: Profilga kirish yoki ro'yxatdan o'tkazishning iloji yo'q!")
                elif status != "COMPLETED":
                    print(f"[E'LON] {s_name} 3 marta urinishda ham sertifikat olmadi. Keyingi o'quvchiga o'tilmoqda (oxirida qayta uriniladi)!")
        else:
            # 2x Parallel Super-Tez Rejim (Virtual yoki Ekranda 2 oyna)
            worker_slot_lock = threading.Lock()
            available_slots = list(range(1, max_workers + 1))

            def _run_one(item):
                idx, student = item
                s_name = student["name"]
                if s_name in get_completed_students() or s_name in get_unrecoverable_students():
                    return
                with worker_slot_lock:
                    w_id = available_slots.pop(0) if available_slots else 1
                try:
                    print(f"\n[OQIM #{w_id}] [{idx}/{len(students)}] ISHLOV BERILMOQDA: {s_name}")
                    try:
                        status = process_student(student, headless=headless, worker_id=w_id)
                    except Exception as e:
                        print(f"[OQIM #{w_id}] [!] {s_name} da kutilmagan xato ushlandi (davom etadi): {e}")
                        status = "FAILED"
                    try:
                        export_results_to_excel(students, RESULTS_EXCEL)
                    except Exception:
                        pass
                    if status == "UNRECOVERABLE":
                        print(f"[OQIM #{w_id}] [O'TKAZILDI - QAYTA URINILMAYDI] {s_name}")
                    elif status != "COMPLETED":
                        print(f"[OQIM #{w_id}] [E'LON] {s_name} oxirida qayta tekshiriladi!")
                finally:
                    with worker_slot_lock:
                        available_slots.append(w_id)
                        available_slots.sort()

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(_run_one, item) for item in remaining_indexed]
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        print(f"[!] Parallel oqim xatosi: {e}")

    export_results_to_excel(students, RESULTS_EXCEL)

def main():
    headless_flag = "--headless" in sys.argv or "--virtual" in sys.argv or (sys.platform != "win32" and "--gui" not in sys.argv)
    workers_cnt = 2 if "--2x" in sys.argv else 1
    for arg in sys.argv[1:]:
        if arg.startswith("--workers="):
            try:
                workers_cnt = max(1, int(arg.split("=", 1)[1]))
            except Exception:
                pass
    run_pipeline(headless=headless_flag, max_workers=workers_cnt)

if __name__ == "__main__":
    main()
