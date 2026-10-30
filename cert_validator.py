# -*- coding: utf-8 -*-
"""
Coursera sertifikatlarini qat'iy tekshirish moduli:
1. Sertifikat kodi avval boshqa o'quvchiga berilmaganligini (dublikat emasligini) tekshiradi.
2. Coursera rasmiy sahifasidagi 'Completed by' ismi o'quvchi ismi bilan mos kelishini tekshiradi.
Begona yoki eski sertifikatlar 100% filtrlanadi.
"""
import os
import re
import urllib.request

def clean_uz_name(s: str) -> str:
    if not s:
        return ""
    s = s.upper().strip()
    s = s.replace("`", "'").replace("ʻ", "'").replace("ʼ", "'").replace("‘", "'").replace("’", "'")
    s = re.sub(r"[^A-Z\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def get_cert_code(url_or_code: str) -> str:
    if not url_or_code:
        return ""
    s = str(url_or_code).strip().rstrip("/")
    return s.split("/")[-1].upper()

def get_cert_owner(cert_url_or_code: str, timeout: int = 10):
    code = get_cert_code(cert_url_or_code)
    if not code or len(code) < 8:
        return None
    url = f"https://www.coursera.org/account/accomplishments/verify/{code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
        # Pattern 1: Completed by <strong>NAME</strong>
        m1 = re.search(r"Completed by\s*(?:<[^>]+>)*\s*([A-Z`'ʻʼ\s]{3,60}?)(?:<|/span|/h3|/strong)", html, re.I)
        if m1:
            name = m1.group(1).strip()
            if len(name) >= 3 and not any(k in name.upper() for k in ["UNKNOWN", "GOOGLE", "COURSERA"]):
                return name

        # Pattern 2: NAME's account is verified
        m2 = re.search(r"([A-Z`'ʻʼ\s]{4,60})'s account is verified", html, re.I)
        if m2:
            name = m2.group(1).strip()
            if len(name) >= 3 and not any(k in name.upper() for k in ["UNKNOWN", "GOOGLE", "COURSERA"]):
                return name
    except Exception as e:
        print(f"[CERT_VALIDATOR FETCH ERR] {code}: {e}")
    return None

def verify_cert_matches_student(cert_url_or_code: str, student_name: str, timeout: int = 10):
    """
    Sertifikat Courseradagi egasi berilgan o'quvchi ismi bilan mosligini tekshiradi.
    Mos kelsa: (True, owner_name)
    Mos kelmasa: (False, error_reason)
    """
    owner = get_cert_owner(cert_url_or_code, timeout=timeout)
    if not owner:
        return False, "Sertifikat sahifasidan egasining ismini yuklab bo'lmadi"

    clean_owner = clean_uz_name(owner)
    clean_target = clean_uz_name(student_name)

    # 1. To'liq toza moslik
    if clean_owner == clean_target or clean_owner.replace(" ", "") == clean_target.replace(" ", ""):
        return True, owner

    # 2. Ism va Familiya so'zlari bo'yicha moslik
    stop_words = {"OGLI", "QIZI", "O", "G", "LI"}
    owner_words = set(w for w in clean_owner.split() if len(w) > 2 and w not in stop_words)
    target_words = set(w for w in clean_target.split() if len(w) > 2 and w not in stop_words)

    intersection = owner_words.intersection(target_words)
    # Kamida 2 ta asosiy so'z (masalan Ism va Familiya) bir xil bo'lishi kerak
    if len(intersection) >= 2:
        return True, owner

    return False, f"Sertifikat egasi ({owner}) o'quvchi ({student_name}) ga to'g'ri kelmadi!"

def is_cert_already_used_by_other(cert_url_or_code: str, current_student_name: str, results_file: str = "natijalar_sertifikatlar.txt"):
    """
    Ushbu sertifikat kodi avval boshqa o'quvchiga berilganligini tekshiradi.
    Boshqaga berilgan bo'lsa: (True, existing_student_name)
    Yangi/shu o'quvchiniki bo'lsa: (False, "")
    """
    code = get_cert_code(cert_url_or_code)
    if not code:
        return False, ""

    if not os.path.exists(results_file):
        return False, ""

    cur_clean = clean_uz_name(current_student_name)

    try:
        with open(results_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_s = line.strip()
                if not line_s or "http" not in line_s or code not in line_s:
                    continue
                parts = [p.strip() for p in line_s.split("|")]
                if len(parts) >= 2:
                    st_in_file = parts[0]
                    st_clean = clean_uz_name(st_in_file)
                    # Agar bu sertifikat boshqa o'quvchiga tegishli bo'lsa
                    if st_clean != cur_clean and st_clean.replace(" ", "") != cur_clean.replace(" ", ""):
                        # Kamida 2 ta so'z farq qilsa -> bu aniq boshqa odam
                        words_f = set(w for w in st_clean.split() if len(w) > 2)
                        words_c = set(w for w in cur_clean.split() if len(w) > 2)
                        if len(words_f.intersection(words_c)) < 2:
                            return True, st_in_file
    except Exception:
        pass

    return False, ""
