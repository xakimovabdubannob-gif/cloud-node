import os
import sys
import time
import re
from telethon.sync import TelegramClient

API_ID = 26521369
API_HASH = "fa2e0d37e50c4aa3d54c1537b0d88470"
SESSION_PATH = os.path.join(os.path.dirname(__file__), "tg_session")

def fetch_code():
    try:
        with TelegramClient(SESSION_PATH, API_ID, API_HASH) as client:
            bot = client.get_entity("@aistudy_uz_bot")
            
            # Kod olish tugmasini bosish
            messages = client.get_messages(bot, limit=5)
            clicked = False
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for b in row:
                            if "Tasdiqlash kodini olish" in b.text:
                                b.click()
                                clicked = True
                                break
                        if clicked:
                            break
                if clicked:
                    break
                    
            if not clicked:
                client.send_message(bot, "/start")
                time.sleep(2)
                msgs = client.get_messages(bot, limit=3)
                for m in msgs:
                    if m.buttons:
                        for row in m.buttons:
                            for b in row:
                                if "Tasdiqlash kodini olish" in b.text:
                                    b.click()
                                    clicked = True
                                    break
                                    
            for _ in range(45):
                time.sleep(1)
                latest = client.get_messages(bot, limit=3)
                for msg in latest:
                    txt = msg.text or ""
                    match = re.search(r'\b(\d{6})\b', txt)
                    if match:
                        print(match.group(1))
                        return
    except Exception as e:
        sys.stderr.write(str(e))

if __name__ == "__main__":
    fetch_code()
