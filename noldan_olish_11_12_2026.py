# -*- coding: utf-8 -*-
"""
noldan_yakka_tartibda.py (RABOCHIY STOLDA)
=========================================
Foydalanuvchi talabi bo'yicha maxsus algoritm:
1. Coursera'ga Aileaders'dan taklifnoma jo'natib kiradi.
2. Pochtani tekshiradi: yangi Join now xati bo'lsa ochib, 'Join Program' bosadi.
   - Agar mavjud akkount bo'lib 'Log In' / 'invalidWebToken' chiqsa: 'Log In' bosib,
     login va parolni teradi va DEDC ga ulaydi!
3. Agar xat kelmasa yoki ulanmasa, Aileaders'ga qaytib 'Qayta yuborish'/'TEKSHIRISH' bosadi.
4. Agar shunda ham Coursera 'Start your 7-day free trial' / 'Enroll for free' deb qotib tursa:
   AYLANIB TURMAYDI! Darhol Aileaders'dan profilni o'chiradi va NOLDAN yangi unikal pochta bilan
   ro'yxatdan o'tkazib, testlarni 100% yechib sertifikat oladi!
"""

import os
import sys
import re
import time
from datetime import datetime

BOT_DIR = r"d:\uzbekcodersbot"
if os.path.exists(BOT_DIR):
    sys.path.insert(0, BOT_DIR)
    os.chdir(BOT_DIR)

from master_certified_pipeline import (
    process_student,
    pick_date_aileaders,
    safe_goto_commit,
    safe_navigate,
    dismiss_all_popups,
    select_coursera_course_and_tekshir,
    complete_coursera_join_and_enroll,
    ensure_enrolled_on_coursera,
    solve_single_quiz_with_3_checks as _orig_solve_single_quiz,
    extract_certificate_with_3_checks,
    verify_student_name_with_3_checks,
    wipe_browser_session_completely,
    register_new_student_and_enroll,
    generate_student_password,
    get_certificate_map,
    get_existing_accounts,
    QUIZZES_INFO,
    check_module1_overview,
    ensure_videos_and_reading_100
)
import master_certified_pipeline

def smart_solve_quiz(page, q_name, q_url, q_num, student_name):
    print(f"\n[SMART QUIZ] {q_name} tekshirilmoqda...", flush=True)
    for _ in range(5):
        prog = page.locator("div[role='dialog']:has-text('Choose a program')").first
        if prog.count() > 0 and prog.is_visible():
            print("   👉 [SMART] 'Choose a program' oynasi topildi! 'Next' bosilmoqda...", flush=True)
            nxt = prog.locator("button:has-text('Next'), button:has-text('Далее')").first
            if nxt.count() > 0 and nxt.is_visible():
                nxt.click(force=True)
                time.sleep(2.5)
                break
        time.sleep(0.5)

    res = _orig_solve_single_quiz(page, q_name, q_url, q_num, student_name)
    if not res:
        prog = page.locator("div[role='dialog']:has-text('Choose a program')").first
        if prog.count() > 0 and prog.is_visible():
            print("   👉 [SMART] Enroll dan keyin 'Choose a program' chiqdi! 'Next' bosilmoqda...", flush=True)
            nxt = prog.locator("button:has-text('Next'), button:has-text('Далее')").first
            if nxt.count() > 0 and nxt.is_visible():
                nxt.click(force=True)
                time.sleep(3.0)
                res = _orig_solve_single_quiz(page, q_name, q_url, q_num, student_name)
    return res

master_certified_pipeline.solve_single_quiz_with_3_checks = smart_solve_quiz
solve_single_quiz_with_3_checks = smart_solve_quiz
from telegram_bot import cyrillic_to_latin_uz
from gmail_automation import GmailMailboxService
from playwright.sync_api import sync_playwright

ACCOUNTS_FILE = os.path.join(BOT_DIR, "akkountlar.txt") if os.path.exists(BOT_DIR) else "akkountlar.txt"
CHROME_EXEC_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def parse_student_input(text: str):
    """Foydalanuvchi kiritgan matndan o'quvchi/pedagog ma'lumotlarini ajratib oladi."""
    line = text.strip()
    # 14 xonali JSHSHIR larni olib tashlaymiz
    line = re.sub(r"\b\d{14}\b", "", line)
    # Boshidagi tartib raqamlar
    line = re.sub(r"^\d{1,3}[\s.)\-]+", "", line).strip()

    # Tug'ilgan sana
    birth_date = ""
    m_date = re.search(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b", line)
    if m_date:
        raw_d = m_date.group(1)
        sep = "/" if "/" in raw_d else ("-" if "-" in raw_d else ".")
        p = raw_d.split(sep)
        if len(p) == 3:
            p0 = p[0].zfill(2)
            p1 = p[1].zfill(2)
            p2 = p[2]
            birth_date = f"{p0}.{p1}.{p2}"
        else:
            birth_date = raw_d.replace("/", ".").replace("-", ".")
        line = line[:m_date.start()] + " " + line[m_date.end():]

    # Sinf
    cls = ""
    m_cls = re.search(r"\b(\d{1,2}\s*[-_]?\s*[A-Za-zА-Яа-яЎўҚқҒғҲҳ]+|\d{1,2}\s*sinf)\b", line, re.IGNORECASE)
    if m_cls:
        cls = cyrillic_to_latin_uz(m_cls.group(1).strip()).replace(" ", "")
        line = line[:m_cls.start()] + " " + line[m_cls.end():]

    # Hujjat seriya va raqam (Pasport yoki Guvohnoma)
    doc_series = ""
    doc_number = ""
    m_doc = re.search(r"\b([IVXLCDM]{1,4}(?:-[A-Za-z]{1,3})?|[A-Za-z]{1,4}(?:-[A-Za-z]{1,3})?)\s*(\d{5,8})\b", line, re.IGNORECASE)
    if m_doc:
        doc_series = cyrillic_to_latin_uz(m_doc.group(1).upper().strip())
        doc_number = m_doc.group(2).strip()
        line = line[:m_doc.start()] + " " + line[m_doc.end():]
    else:
        m_num = re.search(r"\b(\d{5,8})\b", line)
        if m_num:
            doc_number = m_num.group(1).strip()
            line = line[:m_num.start()] + " " + line[m_num.end():]

    # Ism (barcha nuqta, vergul va belgilarni QAT'IY tozalaymiz)
    name = re.sub(r"[\t|;]+", " ", line)
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"[\s.,;:\-_/\\*+='\"`]+$", "", name).strip()
    name_lat = cyrillic_to_latin_uz(name).upper().strip()
    name_lat = re.sub(r"[\s.,;:\-_/\\*+='\"`]+$", "", name_lat).strip()

    return {
        "name": name_lat,
        "birth_date": birth_date,
        "doc_series": doc_series,
        "doc_number": doc_number,
        "class": cls or "8-A",
        "doc_key": f"{doc_series}{doc_number}".replace(" ", "").replace("-", "").upper() if (doc_series and doc_number) else ""
    }

def delete_old_aileaders_account(page, student):
    """Aileaders.uz dan eski qotib qolgan profilni o'chiradi."""
    s_val = student.get("doc_series", "").strip().upper()
    n_val = student.get("doc_number", "").strip()
    b_cand = student.get("birth_date", "").strip()

    print(f"\n[AILEADERS] Eski profilni o'chirish tekshirilmoqda ({s_val} {n_val})...")
    safe_goto_commit(page, "https://aileaders.uz/auth/delete_account", wait_sec=2.5)

    is_pas = (s_val in ("AE", "AA", "AB", "AC", "AD", "AF", "AG", "AH", "FA", "FB", "FC") or (len(s_val) == 2 and s_val.isalpha()))

    if is_pas:
        pas_b = page.locator("button:has-text('Passport')").first
        if pas_b.is_visible():
            pas_b.click(force=True)
            page.wait_for_timeout(300)
        n_in = page.locator("input[name='passport_number'], input[placeholder*='Seriya']").first
        if n_in.is_visible():
            n_in.fill(f"{s_val}{n_val}")
    else:
        guv = page.locator("button:has-text('Guvohnoma')").first
        if guv.is_visible():
            guv.click(force=True)
            page.wait_for_timeout(300)
        s_in = page.locator("input[name='metrika_series'], input[placeholder*='Seriya']").first
        n_in = page.locator("input[name='metrika_number'], input[placeholder*='Raqam']").first
        if s_in.is_visible() and n_in.is_visible():
            s_in.fill(s_val)
            n_in.fill(n_val)

    if b_cand:
        pick_date_aileaders(page, b_cand)
    page.wait_for_timeout(400)

    del_btn = page.locator("button:has-text(\"O'chirish\")").first
    if del_btn.is_visible():
        del_btn.click(force=True)
        page.wait_for_timeout(3000)
        body = page.locator("body").inner_text()
        if "ochirildi" in body.lower() or "o'chirildi" in body.lower() or "muvaffaqiyat" in body.lower():
            print("   ✅ Profil muvaffaqiyatli o'chirildi!")
            return True
        elif "topilmadi" in body.lower():
            print("   ℹ️ Aileaders'da o'chirish uchun eski profil topilmadi.")
            return False
    return False

def clean_old_account_from_file(student_name: str, doc_key: str = ""):
    """akkountlar.txt faylidan shu o'quvchining eski qotib qolgan yozuvini butunlay tozalaydi."""
    if not os.path.exists(ACCOUNTS_FILE):
        return
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        clean_lines = []
        name_clean = student_name.upper().strip()
        first_two = " ".join(name_clean.split()[:2]) if len(name_clean.split()) >= 2 else name_clean
        removed = False
        for line in lines:
            line_up = line.upper()
            if (name_clean and name_clean in line_up) or (first_two and first_two in line_up) or (doc_key and doc_key in line_up):
                removed = True
                continue
            clean_lines.append(line)
        if removed:
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                f.writelines(clean_lines)
            print(f"   🧹 'akkountlar.txt' dan eski qotgan yozuv tozalandi.")
    except Exception as e:
        print(f"   [!] akkountlar.txt tozalashda: {e}")

def select_generativ_ai_course_clean(page):
    """
    Aileaders'da Telegram reklamasining 'X' tugmasini bosib yopadi,
    'Coursera' tabini tanlaydi va aniq 1-kartochka: 'Generativ Sun'iy Intellektga Kirish'
    kursini bosib, 'TEKSHIRISH' tugmasini bosadi.
    """
    print("   [AILEADERS] Kurslar sahifasi ochilmoqda...")
    safe_goto_commit(page, "https://aileaders.uz/courses?platform=coursera", wait_sec=2.5)
    time.sleep(1.2)

    # 1. Telegram modal reklamasining 'X' tugmasini bosib yopish (pastga tushib ketmasligi uchun)
    print("   👉 [AILEADERS] Telegram reklamasining 'X' tugmasi tekshirilmoqda...")
    for _ in range(4):
        # Escape bosish
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        time.sleep(0.2)

        # X yoki Yopish tugmalarini bosish
        x_clicked = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button, a, span, div'));
            const x = btns.find(b => {
                const t = (b.innerText || b.textContent || '').trim();
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                const cl = (b.className || '').toString().toLowerCase();
                return (t === '✕' || t === '×' || t === 'X' || t === 'x' || aria.includes('close') || aria.includes('yopish') || cl.includes('close'));
            });
            if (x) {
                x.click();
                return true;
            }
            return false;
        }""")
        if x_clicked:
            print("   ✅ Telegram reklamasining 'X' tugmasi bosildi!")
            time.sleep(0.8)
            break

        # Agar modal bo'lsa, uni tozalash
        page.evaluate("""() => {
            document.querySelectorAll('[role="dialog"], .modal, div[class*="popup"], div[class*="banner"]').forEach(m => {
                const t = (m.innerText || '').toLowerCase();
                if (t.includes('telegram') || t.includes('kanal') || t.includes('obuna')) {
                    const btn = m.querySelector('button');
                    if (btn) btn.click(); else m.remove();
                }
            });
            document.querySelectorAll('[class*="backdrop"], [class*="overlay"]').forEach(el => el.remove());
        }""")
        time.sleep(0.4)

    dismiss_all_popups(page)

    # 2. 'Coursera' tabini bosish
    try:
        c_tab = page.locator("button:has-text('Coursera 5'), button:has-text('Coursera'), [role='tab']:has-text('Coursera')").first
        if c_tab.count() > 0 and c_tab.is_visible():
            c_tab.click(force=True)
            time.sleep(1.2)
    except Exception:
        pass

    # 3. Aynan 1-kartochka: "Generativ Sun'iy Intellektga Kirish" ni bosish
    print("   👉 [AILEADERS] 1-kartochka: 'Generativ Sun\\'iy Intellektga Kirish' bosilmoqda...")
    card_done = False

    # Usul A: Matn orqali to'g'ridan-to'g'ri bosish
    try:
        gen_txt = page.locator("text=\"Generativ Sun'iy Intellektga Kirish\"").first
        if gen_txt.count() > 0 and gen_txt.is_visible():
            gen_txt.scroll_into_view_if_needed()
            gen_txt.click(force=True)
            card_done = True
            print("   ✅ 'Generativ Sun\\'iy Intellektga Kirish' kartochkasi bosildi!")
            time.sleep(1.5)
    except Exception:
        pass

    # Usul B: JS orqali kartochka yoki ko'k aylana tugmani (↗) bosish
    if not card_done:
        res = page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('*'));
            const target = els.find(el => (el.innerText || '').trim() === "Generativ Sun'iy Intellektga Kirish");
            if (target) {
                const card = target.closest('div[class*="cursor-pointer"], article, div[class*="rounded"], div') || target;
                card.scrollIntoView({block: 'center', behavior: 'instant'});
                const btn = card.querySelector('button, a, div[class*="rounded-full"], svg');
                if (btn) btn.click(); else card.click();
                return true;
            }
            return false;
        }""")
        if res:
            card_done = True
            print("   ✅ JS orqali kartochka bosildi!")
            time.sleep(1.5)

    # 4. Ochilgan modalda 'TEKSHIRISH' tugmasini bosish
    print("   👉 [AILEADERS] 'TEKSHIRISH' tugmasi bosilmoqda...")
    for _ in range(6):
        tek_clicked = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('div[role="dialog"] button, .modal button, button, a'));
            const tBtn = btns.find(b => {
                const t = (b.innerText || b.textContent || '').trim().toLowerCase();
                return t === 'tekshirish' || t.includes('tekshirish') || t.includes('kursga yozilish') || t.includes('qayta yuborish');
            });
            if (tBtn) {
                tBtn.click();
                return true;
            }
            return false;
        }""")
        if tek_clicked:
            print("   ✅ 'TEKSHIRISH' tugmasi muvaffaqiyatli bosildi!")
            time.sleep(3.0)
            break
        time.sleep(0.8)

def is_coursera_blocked_by_paywall(page):
    """Coursera pullik 7-day trial, joy tugaganligi yoki 'Enroll for free' deb qotganini aniqlaydi."""
    try:
        body = page.locator("body").inner_text()
        body_low = body.lower()
        if "all spots are currently filled" in body_low or "no available seats" in body_low:
            return True
        if "start your 7-day free trial" in body_low or "7-day free trial" in body_low:
            return True
        if "choose a program" in body_low:
            return True
        if "reach out to your organization admin" in body_low:
            return True
        if "enroll for free" in body_low and "dedc" not in page.url.lower():
            return True
        if page.locator("button:has-text('Start your 7-day free trial')").count() > 0:
            return True
        if page.locator("text='All spots are currently filled'").count() > 0:
            return True
    except Exception:
        pass
    return False

def complete_coursera_join_and_enroll_custom(page, mail_svc, email, student_password, full_name="", wait_timeout=35):
    """
    Coursera Enterprise 'Join now' taklifnomasini ochadi:
    1. Agar sahifada 'Log In' / 'invalidWebToken' chiqsa - avtomatik 'Log In' bosib,
       email va parolni teradi va tizimga kiradi!
    2. Agar 'All spots are currently filled' (joy qolmagan) bo'lsa - darhol False qaytaradi.
    3. Yangi profil bo'lsa - 'Create password' orqali parolni o'rnatadi.
    4. 'Join Program' / 'Присоединиться к программе' bosib DEDC ga ulaydi.
    5. DEDC Generativ AI kurs sahifasiga kirib tekshiradi.
    """
    print(f"   [Pochta tekshiruvi] {email} pochtasidan 'Join now' kutilmoqda...")
    coursera_link = mail_svc.wait_for_coursera_invite(timeout=wait_timeout)
    if not coursera_link:
        print("   ⚠️ Pochtaga Coursera taklifnomasi kelmadi.")
        return False, "NO_LINK"

    all_invite_links = mail_svc.get_all_coursera_invites() if hasattr(mail_svc, "get_all_coursera_invites") else [coursera_link]
    if not all_invite_links:
        all_invite_links = [coursera_link]

    for idx_link, inv_link in enumerate(all_invite_links, 1):
        print(f"   [Coursera Join #{idx_link}/{len(all_invite_links)}] Taklifnoma ochilmoqda...")
        safe_goto_commit(page, inv_link, wait_sec=4.0)
        time.sleep(2.0)

        # 1. Login holatini tekshirish
        for _ in range(3):
            cookies = [c.get("name", "") for c in page.context.cookies()]
            has_cauth = any("CAUTH" in c for c in cookies)

            login_btn = page.locator("a[href*='authMode=login'], button[data-e2e='header-login-button'], button:has-text('Log In'), a:has-text('Log In'), button:has-text('Войти'), a:has-text('Войти')").first

            if (not has_cauth) and ("invalidWebToken" in page.url or "authMode=login" in page.url or (login_btn.count() > 0 and login_btn.is_visible())):
                print(f"   🔑 [COURSERA] Mavjud akkaunt aniqlandi ({email}). 'Log In' bosilib kirilmoqda...")
                try:
                    if login_btn.count() > 0 and login_btn.is_visible():
                        login_btn.click(force=True)
                        time.sleep(2.0)
                    elif "invalidWebToken" in page.url or "authMode=login" in page.url:
                        safe_goto_commit(page, "https://www.coursera.org/?authMode=login", wait_sec=3.0)

                    em_inp = page.locator("input[type='email'], input[name='email']").first
                    if em_inp.count() > 0 and em_inp.is_visible():
                        em_inp.fill(email)
                        time.sleep(0.5)
                        cont_btn = page.locator("div[role='dialog'] button:has-text('Continue'), form button:has-text('Continue'), button:has-text('Continue'), button:has-text('Продолжить')").first
                        if cont_btn.count() > 0 and cont_btn.is_visible():
                            cont_btn.click(force=True)
                            time.sleep(1.0)
                        else:
                            page.keyboard.press("Enter")
                            time.sleep(1.0)

                    pw_inp = page.locator("input[type='password'], input[name='password']").first
                    for _ in range(15):
                        if pw_inp.count() > 0 and pw_inp.is_visible():
                            break
                        time.sleep(0.4)

                    if pw_inp.count() > 0 and pw_inp.is_visible():
                        print(f"   🔑 [COURSERA] Parol kiritilmoqda...")
                        pw_inp.fill(student_password)
                        time.sleep(0.5)
                        sub_btn = page.locator("div[role='dialog'] button.cds-button-primary, form button.cds-button-primary, button[type='submit'], button:has-text('Log In'), button:has-text('Войти')").first
                        if sub_btn.count() > 0 and sub_btn.is_visible():
                            sub_btn.click(force=True)
                        else:
                            page.keyboard.press("Enter")
                        time.sleep(4.0)

                    dismiss_all_popups(page)

                    # Tizimga kirgach, taklifnoma havolasini qayta ochamiz (DEDC ga ulanish uchun)
                    print("   🔄 [COURSERA] Tizimga kirildi! DEDC taklifnomasiga qayta yo'naltirilmoqda...")
                    safe_goto_commit(page, inv_link, wait_sec=4.0)
                    time.sleep(3.0)
                except Exception as e_l:
                    print(f"   [!] Coursera loginida xato: {e_l}")
                break
            time.sleep(0.5)

        # 2. "Add a recovery email" -> 'Skip for now' tekshiruvi (SSO dan qaytishda)
        for _ in range(6):
            if "recovery" in page.url.lower() or page.locator("text='Add a recovery email'").count() > 0 or page.locator("button:has-text('Skip for now'), a:has-text('Skip for now')").count() > 0:
                print("   👉 [COURSERA] 'Add a recovery email' sahifasi! 'Skip for now' bosilmoqda...")
                skip_b = page.locator("button:has-text('Skip for now'), a:has-text('Skip for now')").first
                if skip_b.count() > 0 and skip_b.is_visible():
                    skip_b.click(force=True)
                    time.sleep(3.0)
                    break
            time.sleep(0.5)

        # 3. DEDC sahifasida "Generative AI Introduction" kartochkasi bo'lsa, darhol bosamiz!
        clicked_course_card = False
        for _ in range(6):
            gen_card = page.locator("a:has-text('Generative AI'), div:has-text('Generative AI Introduction'), a[href*='introduction-to-generative-ai']").first
            if gen_card.count() > 0 and gen_card.is_visible():
                print("   👉 [COURSERA] DEDC sahifasida 'Generative AI Introduction' kartochkasi bosilmoqda...")
                try:
                    gen_card.scroll_into_view_if_needed()
                    gen_card.click(force=True)
                    clicked_course_card = True
                    time.sleep(3.5)
                    break
                except Exception:
                    pass
            time.sleep(0.5)

        if not clicked_course_card:
            res_c = page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('a, div, article, h3, p'));
                const target = els.find(el => {
                    const t = (el.innerText || '').toLowerCase();
                    return t.includes('generative ai') && (t.includes('introduction') || t.includes('google cloud'));
                });
                if (target) {
                    const clickEl = target.closest('a') || target;
                    clickEl.click();
                    return true;
                }
                return false;
            }""")
            if res_c:
                clicked_course_card = True
                print("   👉 [COURSERA] JS orqali 'Generative AI' kartochkasi bosildi!")
                time.sleep(3.5)

        # 4. Yangi profil uchun "Create password"
        c_pwd = page.locator("input[placeholder='Create password'], input[placeholder*='password' i]").first
        if c_pwd.count() > 0 and c_pwd.is_visible():
            print("   🔒 [COURSERA] Yangi profil paroli o'rnatilmoqda...")
            c_pwd.click(force=True)
            page.keyboard.type(student_password, delay=30)
            time.sleep(0.5)
            set_b = page.locator("button:has-text('Set Password'), button:has-text('Continue'), button[type='submit']").first
            if set_b.count() > 0 and set_b.is_visible():
                set_b.click(force=True)
                time.sleep(4.0)

        # 5. "Join Program" / "Присоединиться к программе"
        for _ in range(8):
            try:
                join_b = page.locator("button:has-text('Join Program'), button:has-text('Присоединиться к программе'), button:has-text('Join'), button:has-text('Accept Invitation'), div[role='dialog'] button:has-text('Continue'), div[role='dialog'] button:has-text('Продолжить')").first
                if join_b.count() > 0 and join_b.is_visible():
                    print("   👉 [COURSERA] 'Join Program' tugmasi bosilmoqda...")
                    join_b.click(force=True)
                    time.sleep(3.0)
                    break
            except Exception:
                pass
            time.sleep(0.5)

        dismiss_all_popups(page)

        # 6. Kurs sahifasida "Enroll" / "Go to Course" tugmasini bosish
        enr_b = page.locator("button:has-text('Enroll'), button:has-text('Go to Course'), button:has-text('Перейти к курсу'), button:has-text('Записаться')").first
        if enr_b.count() > 0 and enr_b.is_visible():
            print("   👉 [COURSERA] 'Enroll' / 'Go to Course' tugmasi bosilmoqda...")
            enr_b.click(force=True)
            time.sleep(2.5)
            dismiss_all_popups(page)

        # 7. Agar "Choose a program" oynasi chiqsa, 'Next' tugmasini bosamiz!
        for _ in range(8):
            prog_dialog = page.locator("div[role='dialog']:has-text('Choose a program')").first
            if prog_dialog.count() > 0 and prog_dialog.is_visible():
                print("   👉 [COURSERA] 'Choose a program' oynasi chiqdi! 'Next' tugmasi bosilmoqda...")
                next_btn = prog_dialog.locator("button:has-text('Next'), button:has-text('Далее')").first
                if next_btn.count() > 0 and next_btn.is_visible():
                    next_btn.click(force=True)
                    time.sleep(3.5)
                    dismiss_all_popups(page)
                    break
            time.sleep(0.5)

        # 8. DEDC Generativ AI kurs sahifasiga kirib tekshirish
        safe_navigate(page, "https://www.coursera.org/learn/introduction-to-generative-ai/home/module/1", wait_sec=3.5)
        dismiss_all_popups(page)

        # Agar yana "Choose a program" yoki "Enroll" chiqsa
        enr_b2 = page.locator("button:has-text('Enroll'), button:has-text('Go to Course')").first
        if enr_b2.count() > 0 and enr_b2.is_visible():
            enr_b2.click(force=True)
            time.sleep(2.0)
            next_btn2 = page.locator("div[role='dialog'] button:has-text('Next'), button:has-text('Next')").first
            if next_btn2.count() > 0 and next_btn2.is_visible():
                next_btn2.click(force=True)
                time.sleep(3.0)
                dismiss_all_popups(page)

        if not is_coursera_blocked_by_paywall(page):
            cookies = [c.get("name", "") for c in page.context.cookies()]
            if any("CAUTH" in c for c in cookies):
                return True, "SUCCESS"

    return False, "FAILED"

def run_single_student_smart_flow(student):
    """Foydalanuvchi talabiga to'liq mos keladigan aqlli oqim."""
    full_name = student["name"]
    doc_key = student.get("doc_key", "")
    print(f"\n=======================================================")
    print(f"🚀 JARAYON BOSHLANDI: {full_name}")
    print(f"=======================================================")

    with sync_playwright() as p:
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--start-maximized",
            "--lang=en-US",
        ]
        launch_opts = {"headless": False, "args": browser_args}
        if os.path.exists(CHROME_EXEC_PATH):
            launch_opts["executable_path"] = CHROME_EXEC_PATH

        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(no_viewport=True, locale="en-US")
        page = context.new_page()

        try:
            # 1. Eski akkountni tekshiramiz
            accs = get_existing_accounts()
            ac = accs.get(full_name) or (accs.get(doc_key) if doc_key else None)
            
            dedc_joined = False

            if ac and ac.get("email") and ac.get("password"):
                email = ac["email"]
                pwd = ac["password"]
                print(f"\n[1/4] Mavjud profil topildi: {email}")
                print("   Aileaders'ga kirib Coursera 'TEKSHIRISH' tugmasi bosilmoqda...")

                # 1-urinish: Aileaders'ga kirib TEKSHIRISH bosish
                for try_ail in (1, 2):
                    print(f"\n   --- [URINISH #{try_ail}/2] Coursera taklifnomasini yuborish va ulanish ---")
                    safe_goto_commit(page, "https://aileaders.uz/auth/login", wait_sec=2.0)
                    em_in = page.locator("input[type='email'], input[name='email']").first
                    pw_in = page.locator("input[type='password'], input[name='password']").first
                    if em_in.is_visible() and pw_in.is_visible():
                        em_in.fill(email)
                        pw_in.fill(pwd)
                        btn_sub = page.locator("button[type='submit'], button:has-text('Kirish')").first
                        if btn_sub.is_visible():
                            btn_sub.click(force=True)
                            page.wait_for_timeout(3000)

                    select_generativ_ai_course_clean(page)

                    # Pochtani tekshirish va Log In / Join
                    try:
                        m_svc = GmailMailboxService(existing_email=email)
                        joined_res = complete_coursera_join_and_enroll_custom(page, m_svc, email, pwd, full_name=full_name, wait_timeout=25)
                        joined_ok = joined_res[0] if isinstance(joined_res, tuple) else joined_res
                        reason = joined_res[1] if isinstance(joined_res, tuple) else ""

                        if joined_ok:
                            safe_navigate(page, "https://www.coursera.org/organizations/dedc/learn/introduction-to-generative-ai/home/module/1", wait_sec=3.0)
                            dismiss_all_popups(page)
                            if not is_coursera_blocked_by_paywall(page):
                                dedc_joined = True
                                print("   ✅ Coursera DEDC ga muvaffaqiyatli ulandi (bepul homiylik faol)!")
                                break

                        if reason == "SPOTS_FILLED":
                            print("\n   ⚡ [ANIQ BLOK] 'All spots are currently filled' - bepul o'rin qolmagan! Aylanmasdan akkaunt o'chiriladi!")
                            break
                    except Exception as e_m:
                        print(f"   [!] Pochta tekshiruvida: {e_m}")

                    if not dedc_joined:
                        print(f"   ⚠️ Urinish #{try_ail} da ulanmadi yoki pullik ko'rsatmoqda. Qayta yuboriladi...")

            # Agar ulanmagan bo'lsa yoki pullik 7-day trial / All spots filled deb qotib tursa:
            # AYLANIB TURMAYDI! Akkauntni o'chiradi va NOLDAN boshlaydi!
            if not dedc_joined:
                print("\n" + "!" * 65)
                print("⚠️ COURSERA DEDC GA ULANMADI (ALL SPOTS FILLED / 7-DAY TRIAL)!")
                print("❗️ AYLANMASDAN, AILEADERS'DAN AKKAUNT O'CHIRILMOQDA...")
                print("!" * 65)

                delete_old_aileaders_account(page, student)
                clean_old_account_from_file(full_name, doc_key)

                print("\n[NOLDAN BOSHLASH] Yangi toza pochta bilan Aileaders va Coursera'ga noldan ro'yxatdan o'tilmoqda...")
                wipe_browser_session_completely(context, page)

                reg_status, new_acc = register_new_student_and_enroll(context, page, student)
                if reg_status == "UNRECOVERABLE" or not new_acc:
                    print(f"[XATO] Noldan ro'yxatdan o'tishda xatolik: {reg_status}")
                    return False

                print(f"✅ Yangi profil muvaffaqiyatli ochildi: {new_acc['email']}")
                safe_navigate(page, "https://www.coursera.org/organizations/dedc/learn/introduction-to-generative-ai/home/module/1", wait_sec=3.0)
                dismiss_all_popups(page)

            # 2. Testlarni yechish (Quiz 1, 2, 3, 4)
            print("\n[TESTLAR] Coursera testlari (1-4) 100% tekshirilmoqda va yechilmoqda...")
            try:
                overview = check_module1_overview(page)
                quiz_statuses = overview.get("quizzes", {})
                dynamic_urls = overview.get("quiz_urls", {})
                for q_name, default_url, q_num in QUIZZES_INFO:
                    actual_url = dynamic_urls.get(q_name, default_url)
                    if quiz_statuses.get(q_name) == "PASSED":
                        print(f"   [+] {q_name} allaqachon topshirilgan (PASSED)")
                    else:
                        print(f"   [-] {q_name} yechilmoqda...")
                        solve_single_quiz_with_3_checks(page, q_name, actual_url, q_num, full_name)

                # Videolar va Reading
                ensure_videos_and_reading_100(page, overview)
            except Exception as e_quiz:
                print(f"   [!] Testlar yechishda: {e_quiz}")
                # Fallback: to'g'ridan-to'g'ri QUIZZES_INFO orqali
                for q_name, default_url, q_num in QUIZZES_INFO:
                    solve_single_quiz_with_3_checks(page, q_name, default_url, q_num, full_name)

            # 3. Ismni toza tasdiqlash
            print("\n[VERIFY] Ism Coursera'da xatosiz tasdiqlanmoqda (Verify My Name)...")
            verify_student_name_with_3_checks(page, full_name)

            # 4. Sertifikatni olish
            print("\n[SERTIFIKAT] Havola tekshirilmoqda...")
            cert_url = extract_certificate_with_3_checks(page, full_name)

            if cert_url:
                print("\n" + "=" * 70)
                print(f"🎉 MUVAFFAQIYATLI YAKUNLANDI! SERTIFIKAT TAYYOR!")
                print(f"👤 O'quvchi:   {full_name}")
                print(f"🏅 Sertifikat: {cert_url}")
                print("=" * 70)

                desktop_p = os.path.join(os.path.expanduser("~"), "Desktop", "YANGI_SERTIFIKAT_NATIJA.txt")
                with open(desktop_p, "a", encoding="utf-8") as df:
                    df.write(f"\n{full_name} | {student.get('class', '')} | {cert_url}\n")
                print(f"\n📄 Natija ish stolingizdagi 'YANGI_SERTIFIKAT_NATIJA.txt' fayliga saqlandi!")
                return True
            else:
                print("\n⚠️ Testlar yechildi, Coursera sahifasida sertifikat generatsiya qilinishi kutilmoqda.")
                return False

        except Exception as ex:
            print(f"\n[XATOLIK]: {ex}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            try:
                browser.close()
            except Exception:
                pass

def main():
    print("=" * 70)
    print("   UZBEK CODERS - YAKKA TARTIBDA NOLDAN SERTIFIKAT OLISH TIZIMI")
    print("======================================================================")
    print("Foydalanuvchi talabi bo'yicha maxsus algoritm:")
    print(" 1. Coursera'ga Aileaders'dan TEKSHIRISH orqali kiradi.")
    print(" 2. Pochtani tekshiradi, yangi Join taklifnomasi bilan ulanadi.")
    print(" 3. Bo'lmasa qayta yuboradi.")
    print(" 4. Yana bo'lmasa (pullik trial chiqsa): AYLANMASDAN akkauntni o'chiradi")
    print("    va NOLDAN yangi profil ochib, 100% sertifikat oladi!")
    print("======================================================================")

    user_inp = input("\nMa'lumotlarni tashlang (Enter bossangiz avtomatik Nishonova Munojatxon olinadi):\n(Namuna: Nishonova Munojatxon Ergashevna 15.06.1984 AE 7786512)\n> ").strip()
    if not user_inp:
        user_inp = "Nishonova Munojatxon Ergashevna 15.06.1984 AE 7786512"
        print(f"👉 Standart tanlandi: {user_inp}")

    st = parse_student_input(user_inp)
    if not st["name"]:
        st["name"] = input("F.I.SH: ").strip().upper()
    st["name"] = re.sub(r"[\s.,;:\-_/\\*+='\"`]+$", "", st["name"]).strip()

    if not st["birth_date"]:
        st["birth_date"] = input("Tug'ilgan sana (masalan: 15.06.1984): ").strip()
    if not st["doc_series"]:
        st["doc_series"] = input("Seriya (masalan: AE): ").strip().upper()
    if not st["doc_number"]:
        st["doc_number"] = input("Raqam (masalan: 7786512): ").strip()

    print("\n" + "-" * 50)
    print(f"👤 Ism:     {st['name']}")
    print(f"📅 Sana:    {st['birth_date']}")
    print(f"📑 Hujjat:  {st['doc_series']} {st['doc_number']}")
    print("-" * 50)

    run_single_student_smart_flow(st)
    input("\nTugadi. Chiqish uchun Enter bosing...")

if __name__ == "__main__":
    main()
