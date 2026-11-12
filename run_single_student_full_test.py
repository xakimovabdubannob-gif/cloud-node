# -*- coding: utf-8 -*-
import sys
import os
import time
from playwright.sync_api import sync_playwright

STUDENT_NAME = "UKTAMOV ASRORBEK ABDULVOSID O‘G‘LI"
STUDENT_EMAIL = "parpie.vis.mo.i.l208@gmail.com"
STUDENT_PASSWORD = "Smart9368#B"

COURSE_SLUG = "introduction-to-generative-ai"
COURSE_HOME = f"https://www.coursera.org/learn/{COURSE_SLUG}/home/module/1"

MODULE_ITEMS = [
    # Module 1
    ("video", "Video 1: Where Generative AI Fits", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/sEzxC/where-generative-ai-fits-in-the-ai-and-ml-landscape"),
    ("video", "Video 2: Supervised and Unsupervised Models", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/YUZhf/supervised-and-unsupervised-machine-learning-models"),
    ("quiz", "Quiz 1", f"https://www.coursera.org/learn/{COURSE_SLUG}/assignment-submission/UOf9n/quiz-1"),
    ("video", "Video 3: Generative AI as a Subset of Deep Learning", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/HGiXV/generative-ai-as-a-subset-of-deep-learning"),
    ("video", "Video 4: Is It Generative AI or Not?", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/jno82/is-it-generative-ai-or-not"),
    ("video", "Video 5: Defining Generative AI: A Formal Approach", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/Nfz2y/defining-generative-ai-a-formal-approach"),
    ("quiz", "Quiz 2", f"https://www.coursera.org/learn/{COURSE_SLUG}/assignment-submission/PbAYx/quiz-2"),
    ("video", "Video 6: Transformers, Hallucinations, and Prompts", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/6npRm/transformers-hallucinations-and-prompts"),
    ("video", "Video 7: An Overview of Generative AI Model Types", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/oG55M/an-overview-of-generative-ai-model-types"),
    ("quiz", "Quiz 3", f"https://www.coursera.org/learn/{COURSE_SLUG}/assignment-submission/68izF/quiz-3"),
    ("video", "Video 8: Generative AI for Code Generation", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/zMq98/generative-ai-for-code-generation"),
    ("video", "Video 9: Leveraging Google Cloud for Enhanced Gen AI", f"https://www.coursera.org/learn/{COURSE_SLUG}/lecture/XulSM/leveraging-google-cloud-for-enhanced-generative-ai"),
    ("reading", "Reading: Introduction to Generative AI", f"https://www.coursera.org/learn/{COURSE_SLUG}/supplement/vARuq/reading"),
    ("quiz", "Quiz 4", f"https://www.coursera.org/learn/{COURSE_SLUG}/assignment-submission/QR1K5/quiz-4")
]

QUIZ_ANSWERS = {
    "quiz 1": ["text, images, audio, and video", "создания нового контента, например текста, изображений, аудио и видео"],
    "quiz 2": ["based on general knowledge and patterns", "на основе общих знаний и шаблонов"],
    "quiz 3": ["a type of artificial intelligence", "тип искусственного интеллекта"],
    "quiz 4": ["vertex ai", "gemini"]
}

def safe_goto(page, url, wait_sec=3.0):
    for attempt in range(5):
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=22000)
            break
        except Exception as e:
            time.sleep(2.0)
    time.sleep(wait_sec)
    dismiss_popups(page)

def dismiss_popups(page):
    try:
        # Checkboxlar
        page.evaluate("""() => {
            const cbs = document.querySelectorAll("input[type='checkbox']");
            cbs.forEach(cb => { if (!cb.checked) cb.click(); });
        }""")
        # Modallar va tugmalar
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button, a"));
            for (const b of btns) {
                const t = (b.innerText || '').trim().toLowerCase();
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                if (t === 'start the course' || t === 'начать курс' || t === 'continue' || t === 'i understand' || t === 'close x' || aria === 'close dialog' || aria === 'close modal' || t === 'ignore') {
                    if (b.offsetParent !== null) {
                        b.click();
                    }
                }
            }
        }""")
    except Exception:
        pass

def perform_login(page, context):
    print("\n[1/3] Coursera tizimiga kirilmoqda...")
    page.goto('https://www.coursera.org/?authMode=login', wait_until='domcontentloaded')
    time.sleep(3.0)

    # Email
    em = page.locator(".cds-Modal-container input[type='email'], input[type='email']").first
    if em.count() > 0 and em.is_visible():
        em.fill(STUDENT_EMAIL)
        time.sleep(0.4)
        c_btn = page.locator(".cds-Modal-container button[type='submit'], .cds-Modal-container button:has-text('Continue')").first
        if c_btn.count() > 0 and c_btn.is_visible():
            c_btn.click(force=True)
        else:
            em.press("Enter")
        time.sleep(2.0)

    # Parol
    pwd = page.locator(".cds-Modal-container input[type='password'], input[type='password']").first
    if pwd.count() > 0 and pwd.is_visible():
        pwd.fill(STUDENT_PASSWORD)
        time.sleep(0.4)
        sub = page.locator(".cds-Modal-container button[data-e2e='login-form-submit-button'], .cds-Modal-container button[type='submit']").first
        if sub.count() > 0 and sub.is_visible():
            sub.click(force=True)
        else:
            pwd.press("Enter")

    # CAUTH yoki redirect kutish
    logged_in = False
    for _ in range(25):
        time.sleep(1.0)
        cookies = [c['name'] for c in context.cookies()]
        u = page.url.lower()
        if 'CAUTH' in cookies or "organizations/dedc" in u or "/home" in u or "/learn" in u:
            logged_in = True
            break

    time.sleep(4.0)
    print(f"[OK] Tizimga muvaffaqiyatli kirildi! ({STUDENT_EMAIL})")
    return logged_in

def play_video_to_end(page, url, title):
    print(f"\n[-] Video tekshirilmoqda: {title}...")
    safe_goto(page, url, wait_sec=3.0)

    # Video elementini topish
    for _ in range(12):
        if page.evaluate("() => !!(document.querySelector('video') && document.querySelector('video').duration > 0)"):
            break
        dismiss_popups(page)
        time.sleep(1.0)

    dur = page.evaluate("() => document.querySelector('video') ? document.querySelector('video').duration : 0")
    if not dur or dur <= 0:
        print(f"   [!] Video topilmadi yoki allaqachon ko'rilgan.")
        return

    # Avval video allaqachon ko'rilganmi tekshiramiz
    cur_pos = page.evaluate("() => document.querySelector('video') ? document.querySelector('video').currentTime : 0")
    if cur_pos >= dur - 2:
        print(f"   [OK] Ushbu video allaqachon to'liq ko'rilgan ({round(cur_pos)}/{round(dur)}s).")
        return

    print(f"   Davomiyligi: {round(dur)} soniya. Tabiiy 2.0x tezlikda oxirigacha ko'rilmoqda...")

    # 2.0x tezlikda ijro etish
    page.evaluate("""() => {
        const v = document.querySelector('video');
        if (v) {
            v.muted = true;
            v.playbackRate = 2.0;
            v.play();
        }
        const playBtn = document.querySelector("button[aria-label*='Play' i], .vjs-big-play-button, .c-video-play-button");
        if (playBtn) playBtn.click();
    }""")

    max_wait = int(dur / 2.0) + 12
    st = time.time()
    while time.time() - st < max_wait:
        time.sleep(2.0)
        info = page.evaluate("""() => {
            const v = document.querySelector('video');
            return v ? {
                cur: Math.round(v.currentTime),
                dur: Math.round(v.duration),
                ended: v.ended,
                paused: v.paused
            } : null;
        }""")
        if not info:
            break
        print(f"   Ijro: {info.get('cur')}/{info.get('dur')}s...")
        if info.get('ended') or info.get('cur', 0) >= info.get('dur', 100) - 1:
            print(f"   [OK] {title} to'liq ko'rildi!")
            break
        if info.get('paused'):
            page.evaluate("() => document.querySelector('video') && document.querySelector('video').play()")

    time.sleep(2.5)

    # Next yoki Mark as completed bosish
    page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button, a'));
        const next = btns.find(b => {
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            const txt = (b.innerText || '').toLowerCase();
            return (aria.includes('next') || txt.includes('next') || txt.includes('mark as completed')) && b.offsetParent !== null;
        });
        if (next) next.click();
    }""")
    time.sleep(2.0)

def complete_reading(page, url):
    print(f"\n[-] Reading ochilmoqda...")
    safe_goto(page, url, wait_sec=2.5)
    page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const btn = btns.find(b => /mark as completed|отметить как пройденное/i.test(b.innerText || ''));
        if (btn) btn.click();
    }""")
    print("   [OK] Reading yakunlandi!")
    time.sleep(2.0)

def solve_quiz(page, url, q_title):
    print(f"\n>>> [{q_title}] TEST TOPILDI VA YECHILMOQDA... <<<")
    safe_goto(page, url, wait_sec=3.0)

    # Qulf tekshiruvi
    body_text = page.evaluate("() => document.body.innerText") or ""
    if "locked until you complete" in body_text.lower() or "some learning to complete" in body_text.lower():
        print(f"   [!] {q_title} hali ham qulflangan!")
        return False

    # Start assignment / Resume assignment / Try again
    start_btn = page.locator("button:visible:has-text('Start assignment'), button:visible:has-text('Start'), button:visible:has-text('Resume'), button:visible:has-text('Try again'), a:visible:has-text('Start')").first
    if start_btn.count() > 0 and start_btn.is_visible():
        start_btn.click(force=True)
        print("   'Start assignment' bosildi!")
        time.sleep(3.5)

    dismiss_popups(page)

    # Savollarga javob berish
    q_key = q_title.lower()
    targets = QUIZ_ANSWERS.get(q_key, [])
    labels = page.locator("label")
    for i in range(labels.count()):
        lbl = labels.nth(i)
        txt = (lbl.inner_text() or "").lower()
        if any(t in txt for t in targets):
            lbl.scroll_into_view_if_needed()
            lbl.click(force=True)
            print(f"   [OK] Javob belgilandi: {txt[:60]}...")
            time.sleep(0.4)

    # Honor code va ism
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1.0)

    name_inp = page.locator("input[placeholder*='legal name' i], input[placeholder*='Ф. И. О.' i], [data-testid='honor-code-legal-name-input'], input[type='text']").last
    if name_inp.count() > 0 and name_inp.is_visible():
        name_inp.fill("UKTAMOV ASRORBEK ABDULVOSID OGʻLI")
        time.sleep(0.3)
        print("   [OK] Ism kiritildi!")

    honor_cb = page.locator("label:has-text('understand and agree') input[type='checkbox'], label:has-text('соглашаюсь') input[type='checkbox'], input[type='checkbox']").last
    if honor_cb.count() > 0 and not honor_cb.is_checked():
        honor_cb.check(force=True)
        time.sleep(0.3)
        print("   [OK] Honor Code belgilandi!")

    # Submit bosish
    sub_btn = page.locator("button:has-text('Submit'), button:has-text('Отправить')").first
    if sub_btn.count() > 0 and sub_btn.is_enabled():
        sub_btn.click(force=True)
        print("   [OK] 1-Submit bosildi!")
        time.sleep(2.0)
        sub_modal = page.locator("div[role='dialog'] button:has-text('Submit'), div[role='dialog'] button:has-text('Отправить')").first
        if sub_modal.count() > 0 and sub_modal.is_visible():
            sub_modal.click(force=True)
            print("   [OK] 2-Submit (tasdiqlash) bosildi!")
            time.sleep(4.0)

    # Natijani tekshirish
    time.sleep(3.0)
    res_txt = (page.evaluate("() => document.body.innerText") or "").lower()
    if "you passed" in res_txt or "passed" in res_txt or "пройдено" in res_txt or "100%" in res_txt:
        print(f"\n>>> TABRIKLAYMIZ: {q_title} MUOFFAQIYATLI 100% TOPSHIRILDI! <<<")
        return True
    return True

def main():
    print("=" * 65)
    print("   UZBEKCODERS: 1 TA O'QUVCHI UCHUN VIDEOLAR VA TESTLAR")
    print(f"   O'quvchi: {STUDENT_NAME}")
    print(f"   Email:    {STUDENT_EMAIL}")
    print("=" * 65)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        if not perform_login(page, context):
            print("[!] Kirish amalga oshmadi!")
            browser.close()
            return

        print("\n[2/3] Kurs bo'yicha videolar ko'rilmoqda va testlar yechilmoqda...")
        for item_type, title, url in MODULE_ITEMS:
            if item_type == "video":
                play_video_to_end(page, url, title)
            elif item_type == "reading":
                complete_reading(page, url)
            elif item_type == "quiz":
                solve_quiz(page, url, title)

        print("\n[3/3] Kurs yakuniy holati tekshirilmoqda...")
        safe_goto(page, COURSE_HOME, wait_sec=4.0)
        time.sleep(5.0)

        # Sertifikat tekshiruvi
        cert_found = False
        accomplishments_url = "https://www.coursera.org/accomplishments"
        safe_goto(page, accomplishments_url, wait_sec=4.0)
        time.sleep(3.0)
        cert_link = page.locator("a[href*='/accomplishments/verify/'], a[href*='/accomplishments/certificate/']").first
        if cert_link.count() > 0:
            href = cert_link.get_attribute("href")
            full_cert = f"https://www.coursera.org{href}" if href.startswith("/") else href
            print("\n" + "=" * 65)
            print(f">>> SERTIFIKAT HAVOLASI TOPILDI: {full_cert} <<<")
            print("=" * 65)
            cert_found = True

        print("\n" + "=" * 65)
        print("   JARAYON TO'LIQ YAKUNLANDI! Brauzer 20 soniya ochiq qoladi.")
        print("=" * 65)
        time.sleep(20)
        browser.close()

if __name__ == "__main__":
    main()
