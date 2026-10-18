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
        
        if "akkountlar" in pack and pack["akkountlar"]:
            with open("akkountlar.txt", "w", encoding="utf-8") as f:
                f.write(pack["akkountlar"])
        if "natijalar" in pack and pack["natijalar"]:
            with open("natijalar_sertifikatlar.txt", "w", encoding="utf-8") as f:
                f.write(pack["natijalar"])
        return True
    except Exception as e:
        print(f"[VAULT DECRYPT ERROR] {e}")
        return False
