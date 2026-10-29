# -*- coding: utf-8 -*-
"""
GMAIL AUTOMATION FOR AILEADERS & COURSERA
Avtomatik pochta boshqaruvi:
- parpievismoil208@gmail.com uchun cheksiz nuqtali (dot) aliaslar yaratish (32,000+ ta o'quvchi uchun yetarli).
- IMAP orqali Aileaders.uz tasdiqlash havolalarini avtomatik ushlab olish.
- IMAP orqali Coursera taklifnoma / magic link havolalarini avtomatik ushlab olish.
"""

import sys, os, time, imaplib, email, re
from email.header import decode_header

GMAIL_USER = "parpievismoil208@gmail.com"
GMAIL_APP_PWD = "urctpdhupszdjpct"
BASE_USERNAME = "parpievismoil208"
DOMAIN = "gmail.com"
ACCOUNTS_FILE = "akkountlar.txt"
RESULTS_FILE = "natijalar_sertifikatlar.txt"

def generate_dot_alias(index: int) -> str:
    """
    parpievismoil208 dan 32,768 ta noyob nuqtali pochta manzilini generatsiya qiladi.
    """
    s = BASE_USERNAME
    n = len(s) - 1
    res = []
    for i in range(len(s)):
        res.append(s[i])
        if i < n and (index & (1 << i)):
            res.append(".")
    return "".join(res) + f"@{DOMAIN}"


USED_ALIASES_FILE = "used_aliases.txt"

def get_next_available_alias() -> str:
    used_text = ""
    for fn in [USED_ALIASES_FILE, ACCOUNTS_FILE, RESULTS_FILE]:
        if os.path.exists(fn):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    used_text += f.read() + " "
            except Exception:
                pass

    for i in range(1, 32000):
        alias = generate_dot_alias(i)
        if alias not in used_text:
            try:
                with open(USED_ALIASES_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{alias}\n")
            except Exception:
                pass
            return alias
    return f"{BASE_USERNAME}@{DOMAIN}"


def connect_gmail(timeout=12):
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=timeout)
    mail.login(GMAIL_USER, GMAIL_APP_PWD)
    mail.select("INBOX")
    return mail


def get_clean_body_and_links(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ["text/plain", "text/html"]:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    links = re.findall(r'https?://[^\s<>"\'`]+', body)
    return body, links



def is_cluster_node():
    return bool(os.environ.get("TUNNEL_URL") or os.environ.get("CLUSTER_MASTER_URL") or os.path.exists("cluster_url.txt"))


def _query_master_mail_hub(mail_type: str, target_email: str) -> str:
    """Master Server (port 8766 yoki Cloudflare tunnel) orqali keshdagi havolani 0ms da oladi (Gmailga ulanishsiz!)."""
    master_url = os.environ.get("CLUSTER_MASTER_URL", "").strip()
    if not master_url and os.path.exists("cluster_url.txt"):
        try:
            master_url = open("cluster_url.txt", "r", encoding="utf-8").read().strip().splitlines()[0].strip()
        except Exception:
            pass
    if not master_url or not master_url.startswith("http"):
        master_url = "http://127.0.0.1:8766"

    try:
        import requests
        r = requests.get(f"{master_url}/cluster/mail_invite", params={"type": mail_type, "email": target_email}, timeout=3)
        if r.status_code == 200:
            d = r.json()
            if d.get("ok") and d.get("link"):
                return d["link"]
    except Exception:
        pass
    return None


def wait_for_aileaders_activation(target_email: str, timeout_sec=90) -> str:
    """
    Master Hub yoki IMAP orqali target_email ga kelgan Aileaders faollashtirish havolasini avtomatik ushlaydi.
    """
    clean_target = target_email.lower().strip()
    t_start = time.time()
    print(f"[GMAIL] Aileaders faollashtirish xabari kutilmoqda: {clean_target} (maksimum {timeout_sec}s)...")

    while time.time() - t_start < timeout_sec:
        hub_link = _query_master_mail_hub("activation", clean_target)
        if hub_link:
            print(f"[GMAIL HUB] Aileaders havolasi Master Hubdan olindi: {hub_link}")
            return hub_link
        if is_cluster_node() and (time.time() - t_start < 45):
            time.sleep(2.5)
            continue
        time.sleep(2.5)
        try:
            mail = connect_gmail()
            status, messages = mail.search(None, "ALL")
            mail_ids = messages[0].split()
            # Eng yangi 15 ta xatni tekshiramiz
            for m_id in reversed(mail_ids[-15:]):
                status, msg_data = mail.fetch(m_id, "(RFC822)")
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        to_addr = (msg.get("To") or "").lower()
                        sender = (msg.get("From") or "").lower()
                        subj = (msg.get("Subject") or "")
                        body, links = get_clean_body_and_links(msg)

                        for l in links:
                            if "aileaders.uz/auth/activate" in l:
                                # Havola aynan shu target_email uchun bo'lsa
                                if clean_target in l.lower() or clean_target in to_addr:
                                    clean_link = l.replace("&amp;", "&")
                                    print(f"[GMAIL IMAP] Aileaders faollashtirish havolasi topildi ({clean_target}): {clean_link}")
                                    mail.logout()
                                    return clean_link
            mail.logout()
        except Exception as e:
            print(f"[GMAIL IMAP] Ogohlantirish: {e}")

        time.sleep(3.0)

    print(f"[GMAIL IMAP] Aileaders faollashtirish xabari {timeout_sec}s ichida kelmadi.")
    return None


def extract_coursera_magic_link_from_msg(msg):
    """
    Coursera Magic Link xabaridan aynan 'Log in' tugmasining havolasini oladi (tepadagi logoni EMAS!).
    """
    body, links = get_clean_body_and_links(msg)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body, "html.parser")
        for a in soup.find_all("a", href=True):
            txt = a.get_text().strip().lower()
            href = a["href"]
            if any(k in txt for k in ["log in", "sign in", "войти", "kirish", "click the link", "sign in using this link"]):
                return href.replace("&amp;", "&")
    except Exception:
        pass

    coursera_links = [l.replace("&amp;", "&") for l in links if "link.coursera.org" in l or "coursera.org/magicLinks" in l]
    if len(coursera_links) > 1:
        return coursera_links[1]
    elif coursera_links:
        return coursera_links[0]
    return None


def extract_coursera_invite_link_from_msg(msg):
    """
    Coursera xabaridan aynan taklifnoma / kursga kirish tugmasining havolasini oladi (logoni emas!).
    """
    body, links = get_clean_body_and_links(msg)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body, "html.parser")
        for a in soup.find_all("a", href=True):
            txt = a.get_text().strip().lower()
            href = a["href"]
            if any(k in txt for k in ["explore courses", "join now", "join program", "accept invitation", "start learning", "boshlash"]):
                return href.replace("&amp;", "&")
    except Exception:
        pass

    # Agar bs4 topa olmasa, logo bo'lmagan linklarni filtrlaymiz
    coursera_links = [l.replace("&amp;", "&") for l in links if "link.coursera.org" in l or "coursera.org/programs" in l]
    if len(coursera_links) > 1:
        return coursera_links[1]
    elif coursera_links:
        return coursera_links[0]
    return None


def wait_for_coursera_invite(target_email: str, timeout_sec=90) -> str:
    """
    Master Hub yoki IMAP orqali Coursera Enterprise (DEDC) taklifnoma havolasini avtomatik ushlaydi.
    """
    clean_target = target_email.lower().strip()
    t_start = time.time()
    print(f"[GMAIL] Coursera taklifnoma xabari kutilmoqda: {clean_target} (maksimum {timeout_sec}s)...")

    while time.time() - t_start < timeout_sec:
        hub_link = _query_master_mail_hub("coursera", clean_target)
        if hub_link:
            print(f"[GMAIL HUB] Coursera havolasi Master Hubdan olindi: {hub_link}")
            return hub_link
        if is_cluster_node() and (time.time() - t_start < 45):
            time.sleep(2.5)
            continue
        time.sleep(2.5)
        try:
            mail = connect_gmail()
            status, messages = mail.search(None, "ALL")
            mail_ids = messages[0].split()
            for m_id in reversed(mail_ids[-20:]):
                status, msg_data = mail.fetch(m_id, "(RFC822)")
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        to_addr = (msg.get("To") or "").lower()
                        sender = (msg.get("From") or "").lower()
                        subj = (msg.get("Subject") or "")
                        body, links = get_clean_body_and_links(msg)

                        # Faqat aynan shu o'quvchining pochtasiga kelgan Coursera taklifnoma xatlarini tekshiramiz:
                        if clean_target in to_addr or clean_target in body.lower():
                            if "click the link to log in" in subj.lower() or "magic" in subj.lower():
                                continue  # Magic login xatlarini taklifnoma deb adashtirmaymiz!
                            clean_l = extract_coursera_invite_link_from_msg(msg)
                            if clean_l:
                                print(f"[GMAIL IMAP] Coursera havolasi topildi ({clean_target}): {clean_l}")
                                mail.logout()
                                return clean_l
            mail.logout()
        except Exception as e:
            print(f"[GMAIL IMAP] Ogohlantirish: {e}")

        time.sleep(3.0)

    print(f"[GMAIL IMAP] Coursera taklifnoma xabari {timeout_sec}s ichida kelmadi.")
    return None


class GmailMailboxService:
    def __init__(self, existing_email=None):
        if existing_email:
            self.email = existing_email
        else:
            self.email = get_next_available_alias()
        self.token = "gmail_imap_active"
        print(f"[GmailMailboxService] Faol pochta: {self.email}")

    def wait_for_activation(self, timeout=60):
        return wait_for_aileaders_activation(self.email, timeout_sec=timeout)

    def wait_for_coursera(self, timeout=60):
        return wait_for_coursera_invite(self.email, timeout_sec=timeout)

    def wait_for_coursera_invite(self, timeout=60):
        return wait_for_coursera_invite(self.email, timeout_sec=timeout)

    def get_all_coursera_invites(self):
        c_link = wait_for_coursera_invite(self.email, timeout_sec=30)
        return [c_link] if c_link else []


def fetch_coursera_magic_link(target_email: str, timeout_sec=40) -> str:
    """Master Hub yoki Gmail orqali Coursera Magic Link (login link) ni avtomatik ushlaydi."""
    clean_target = target_email.lower().strip()
    t_start = time.time()
    while time.time() - t_start < timeout_sec:
        hub_link = _query_master_mail_hub("magic", clean_target)
        if hub_link and "5tTM5sERtHreZReD_lDVWA" not in hub_link:
            print(f"[GMAIL HUB] Magic Link Master Hubdan olindi: {hub_link}")
            return hub_link
        if is_cluster_node() and (time.time() - t_start < 45):
            time.sleep(2.5)
            continue
        time.sleep(2.5)
        try:
            mail = connect_gmail()
            status, messages = mail.search(None, "ALL")
            mail_ids = messages[0].split()
            for m_id in reversed(mail_ids[-10:]):
                status, msg_data = mail.fetch(m_id, "(RFC822)")
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        to_addr = (msg.get("To") or "").lower()
                        subj = (msg.get("Subject") or "").lower()
                        if clean_target in to_addr and ("log in" in subj or "click the link" in subj or "magic" in subj or "link" in subj):
                            clean_l = extract_coursera_magic_link_from_msg(msg)
                            if clean_l:
                                print(f"[GMAIL IMAP] Magic Link topildi ({clean_target}): {clean_l}")
                                mail.logout()
                                return clean_l
            mail.logout()
        except Exception:
            pass
    return None
