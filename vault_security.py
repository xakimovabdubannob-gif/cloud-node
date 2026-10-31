# -*- coding: utf-8 -*-
import os
import sys
import json
import base64
import hashlib
from cryptography.fernet import Fernet

DEFAULT_SHIELD = "UZB_AI_CLUSTER_SHIELD_2026_OBIDBEK_PRIVATE_KEY_998877"

def get_fernet_key(shield_key: str = None) -> bytes:
    key_str = shield_key or os.environ.get("SHIELD_KEY", DEFAULT_SHIELD)
    return base64.urlsafe_b64encode(hashlib.sha256(key_str.encode("utf-8")).digest())

def encrypt_data_store(shield_key: str = None) -> bool:
    try:
        f_key = get_fernet_key(shield_key)
        fernet = Fernet(f_key)
        
        acc_text = ""
        if os.path.exists("akkountlar.txt"):
            with open("akkountlar.txt", "r", encoding="utf-8", errors="replace") as f:
                acc_text = f.read()
                
        cert_text = ""
        if os.path.exists("natijalar_sertifikatlar.txt"):
            with open("natijalar_sertifikatlar.txt", "r", encoding="utf-8", errors="replace") as f:
                cert_text = f.read()
                
        pack = {
            "akkountlar": acc_text,
            "natijalar": cert_text,
        }
        raw_json = json.dumps(pack, ensure_ascii=False).encode("utf-8")
        enc_bytes = fernet.encrypt(raw_json)
        with open("data_store.enc", "wb") as f:
            f.write(enc_bytes)
        return True
    except Exception as e:
        print(f"[VAULT ENCRYPT ERROR] {e}")
        return False

def decrypt_data_store(shield_key: str = None) -> bool:
    try:
        if not os.path.exists("data_store.enc"):
            return False
        f_key = get_fernet_key(shield_key)
        fernet = Fernet(f_key)
        with open("data_store.enc", "rb") as f:
            enc_bytes = f.read()
        raw_json = fernet.decrypt(enc_bytes)
        pack = json.loads(raw_json.decode("utf-8"))
        
        # Birlashtirish (Merge) - hech qachon mavjud yangi sertifikatlarni o'chirib yubormaymiz!
        if "akkountlar" in pack and pack["akkountlar"]:
            existing_acc = set()
            if os.path.exists("akkountlar.txt"):
                with open("akkountlar.txt", "r", encoding="utf-8", errors="replace") as f:
                    existing_acc = {line.strip() for line in f if line.strip()}
            vault_accs = [l.strip() for l in pack["akkountlar"].splitlines() if l.strip()]
            new_accs = [l for l in vault_accs if l not in existing_acc]
            if new_accs:
                with open("akkountlar.txt", "a", encoding="utf-8") as f:
                    f.write("\n".join(new_accs) + "\n")

        if "natijalar" in pack and pack["natijalar"]:
            existing_certs = set()
            if os.path.exists("natijalar_sertifikatlar.txt"):
                with open("natijalar_sertifikatlar.txt", "r", encoding="utf-8", errors="replace") as f:
                    existing_certs = {line.strip() for line in f if line.strip()}
            vault_certs = [l.strip() for l in pack["natijalar"].splitlines() if l.strip()]
            new_certs = [l for l in vault_certs if l not in existing_certs]
            if new_certs:
                with open("natijalar_sertifikatlar.txt", "a", encoding="utf-8") as f:
                    f.write("\n".join(new_certs) + "\n")
        return True
    except Exception as e:
        print(f"[VAULT DECRYPT ERROR] {e}")
        return False
