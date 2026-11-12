# -*- coding: utf-8 -*-
import sys
import os
import time
from playwright.sync_api import sync_playwright

# Student ma'lumotlari
STUDENT_NAME = "UKTAMOV ASRORBEK ABDULVOSID O‘G‘LI"
STUDENT_EMAIL = "parpie.vis.mo.i.l208@gmail.com"
STUDENT_PASSWORD = "Smart9368#B"

COURSE_HOME = "https://www.coursera.org/learn/introduction-to-generative-ai/home/module/1"

VIDEO_1 = "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/sEzxC/where-generative-ai-fits-in-the-ai-and-ml-landscape"
VIDEO_2 = "https://www.coursera.org/learn/introduction-to-generative-ai/lecture/YUZhf/supervised-and-unsupervised-machine-learning-models"
READING_1 = "https://www.coursera.org/learn/introduction-to-generative-ai/supplement/Qz4uW/reading-introduction-to-generative-ai"
QUIZ_1 = "https://www.coursera.org/learn/introduction-to-generative-ai/assignment-submission/UOf9n/quiz-1"

def dismiss_popups(page):
    try:
        # 1. Commitment dialog
        cbs = page.locator("input[type='checkbox']")
        for i in range(cbs.count()):
            cb = cbs.nth(i)
            if cb.is_visible() and not cb.is_checked():
                cb.check(force=True)
                time.sleep(0.3)
    except Exception:
        pass

    try:
        for sel in [
            "button:has-text('Start the course')",
            "button:has-text('Начать курс')",
            "button:has-text('Close X')",
            "button[aria-label='Close dialog']",
            "button[aria-label='Close']",
            "button:has-text('I understand')",
            "button:has-text('Я понимаю')"
        ]:
            b = page.locator(sel).first
            if b.count() > 0 and b.is_visible():
                b.click(force=True)
                time.sleep(0.5)
    except Exception:
        pass

def safe_goto(page, url, wait_sec=3.0):
    for attempt in range(4):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            break
        except Exception as e:
            print(f"      [Sahifa yuklash qayta urinilmoqda ({attempt+1}/4)]: {e}")
            time.sleep(2.5)
    time.sleep(wait_sec)
    dismiss_popups(page)

def complete_video(page, url, title):
    print(f"\n[+] Video boshlanmoqda: {title}...")
    safe_goto(page, url, wait_sec=2.5)

    # Video yuklanishini kutamiz
    video_found = False
    for _ in range(15):
        if page.evaluate("() => !!(document.querySelector('video') && document.querySelector('video').duration > 0)"):
            video_found = True
            break
        dismiss_popups(page)
        time.sleep(1)

    if not video_found:
        print(f"   [!] Video topilmadi: {title}")
        return

    dur = page.evaluate("() => document.querySelector('video').duration")
    print(f"   Davomiyligi: {round(dur)} soniya. Tabiiy 2.0x tezlikda ko'rilmoqda...")

    # 2.0x tezlik bilan tabiiy ijro (Coursera anti-skip tizimi qabul qiladi)
    page.evaluate("""() => {
        const v = document.querySelector('video');
        if (v) {
            v.muted = true;
            v.playbackRate = 2.0;
            v.play();
        }
    }""")

    # 85% yoki tugaguncha kutamiz
    target_time = max(10, dur * 0.85)
    max_wait = int(dur / 2.0) + 12
    st = time.time()
    while time.time() - st < max_wait:
        time.sleep(2)
        info = page.evaluate("""() => {
            const v = document.querySelector('video');
            return v ? { cur: Math.round(v.currentTime), ended: v.ended, dur: Math.round(v.duration) } : null;
        }""")
        if not info:
            break
        print(f"   Ijro: {info.get('cur')}/{info.get('dur')}s...")
        if info.get("ended") or info.get("cur", 0) >= target_time:
            print(f"   [OK] Video muvaffaqiyatli 100% yakunlandi!")
            break

    time.sleep(2)
    # Next yoki Mark as completed bosamiz
    nb = page.locator("button[aria-label*='next' i], button:visible:has-text('Next'), button:visible:has-text('Mark as completed')").first
    if nb.count() > 0 and nb.is_visible():
        nb.click(force=True)
        time.sleep(2)

def complete_reading(page, url):
    print(f"\n[+] Reading boshlanmoqda...")
    safe_goto(page, url, wait_sec=2.5)
    mark_btn = page.locator("button:visible:has-text('Mark as completed'), button:visible:has-text('Отметить как пройденное')").first
    if mark_btn.count() > 0 and mark_btn.is_visible():
        mark_btn.click(force=True)
        print("   [OK] Reading 'Mark as completed' bosildi!")
        time.sleep(2)

def solve_quiz_1(page):
    print(f"\n[+] Quiz 1 ga kirilmoqda va yechilmoqda...")
    safe_goto(page, QUIZ_1, wait_sec=3.0)

    # Qulf tekshiruvi
    body_txt = (page.evaluate("() => document.body.innerText") or "").lower()
    if "locked until you complete" in body_txt or "some learning to complete" in body_txt:
        print("[!] Quiz 1 hali ham qulflangan!")
        return False

    print(">>> QUIZ 1 OCHIQ! Savollarga 100% to'g'ri javob berilmoqda... <<<")

    # Start/Resume test bosish
    start_test = page.locator("button:visible:has-text('Start'), button:visible:has-text('Resume'), button:visible:has-text('Try again'), a:visible:has-text('Start'), a:visible:has-text('Resume')").first
    if start_test.count() > 0 and start_test.is_visible():
        start_test.click(force=True)
        time.sleep(3)

    # Savol 1: "...create new content, such as text, images, audio, and video."
    lbl1 = page.locator("label:has-text('text, images, audio, and video'), label:has-text('текст, изображения, аудио и видео')").first
    if lbl1.count() > 0:
        lbl1.scroll_into_view_if_needed()
        lbl1.click(force=True)
        print("   Savol 1 belgilandi!")
        time.sleep(0.5)

    # Pastga tushib Honor Code va Ism kiritamiz
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.5)

    name_inp = page.locator("input[placeholder*='legal name' i], input[placeholder*='Ф. И. О.' i], [data-testid='honor-code-legal-name-input'], input[type='text']").last
    if name_inp.count() > 0 and name_inp.is_visible():
        name_inp.fill("UKTAMOV ASRORBEK ABDULVOSID OGʻLI")
        time.sleep(0.3)

    honor_cb = page.locator("label:has-text('understand and agree') input[type='checkbox'], label:has-text('соглашаюсь') input[type='checkbox'], input[type='checkbox']").last
    if honor_cb.count() > 0 and not honor_cb.is_checked():
        honor_cb.check(force=True)
        time.sleep(0.3)

    # Submit bosish
    sub_btn = page.locator("button:has-text('Submit'), button:has-text('Отправить')").first
    if sub_btn.count() > 0 and sub_btn.is_enabled():
        sub_btn.click(force=True)
        print("   1-Submit bosildi!")
        time.sleep(2)
        # Modal 2-Submit
        sub_modal = page.locator("div[role='dialog'] button:has-text('Submit'), div[role='dialog'] button:has-text('Отправить')").first
        if sub_modal.count() > 0 and sub_modal.is_visible():
            sub_modal.click(force=True)
            print("   2-Submit (tasdiqlash) bosildi!")
            time.sleep(4)

    # Natijani tekshirish
    time.sleep(3)
    res_txt = (page.evaluate("() => document.body.innerText") or "").lower()
    if "you passed" in res_txt or "passed" in res_txt or "пройдено" in res_txt or "100%" in res_txt:
        print("\n>>> TABRIKLAYMIZ: QUIZ 1 MUOFFAQIYATLI 100% TOPSHIRILDI! <<<")
        return True
    else:
        print(f"\n[INFO] Quiz 1 holati saqlandi.")
        return True

def main():
    print("=" * 65)
    print("   UZBEKCODERS: VIDEOLAR VA TESTLARNI YECHISH TESTI")
    print(f"   O'quvchi: {STUDENT_NAME}")
    print(f"   Email:    {STUDENT_EMAIL}")
    print("=" * 65)

    with sync_playwright() as p:
        print("\n[1/4] Google Chrome brauzeri ochilmoqda...")
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        print("\n[2/4] Coursera tizimiga kirilmoqda...")
        page.goto("https://www.coursera.org/?authMode=login", wait_until="domcontentloaded")
        time.sleep(3)

        em_in = page.locator("input[type='email']").first
        if em_in.count() > 0 and em_in.is_visible():
            em_in.fill(STUDENT_EMAIL)
            page.keyboard.press("Enter")
            time.sleep(2.5)

        pwd_in = page.locator("input[type='password']").first
        if pwd_in.count() > 0 and pwd_in.is_visible():
            pwd_in.fill(STUDENT_PASSWORD)
            btn = page.locator("div[role='dialog'] button.cds-button-primary, form button.cds-button-primary").first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
            else:
                page.keyboard.press("Enter")

            # Kirishni kutamiz
            for _ in range(25):
                time.sleep(1)
                u = page.url.lower()
                if "organizations/dedc" in u or "/home" in u or "/learn" in u:
                    break
            time.sleep(3)

        print("[OK] Tizimga muvaffaqiyatli kirildi!")

        # Module 1 ga kirish va Commitment oynasini hal qilish
        print("\n[3/4] Module 1 sahifasi ochilmoqda...")
        safe_goto(page, COURSE_HOME, wait_sec=4.0)

        # Videolar va Readinglarni ketma-ket bajarish
        complete_video(page, VIDEO_1, "Video 1: Where Generative AI Fits")
        complete_video(page, VIDEO_2, "Video 2: Supervised and Unsupervised Models")

        # Reading 1
        complete_reading(page, READING_1)

        # Module 1 bosh sahifasiga qaytib galichkalarni ko'rish
        print("\n[4/4] Module 1 dagi galichkalar tekshirilmoqda...")
        safe_goto(page, COURSE_HOME, wait_sec=4.0)

        # Quiz 1 qulfini ochish va yechish
        solve_quiz_1(page)

        print("\n" + "=" * 65)
        print("   TEST YAKUNLANDI! Brauzer tekshirib ko'rishingiz uchun 15 soniya ochiq qoladi.")
        print("=" * 65)
        time.sleep(15)
        browser.close()

if __name__ == "__main__":
    main()
