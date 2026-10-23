"""
Encrypted credential management using the keyring library with Windows DPAPI fallback.
Never stores passwords or tokens in plain text.
"""

import base64
import ctypes
from ctypes import wintypes
from typing import Optional
from app.logger import logger

SERVICE_NAME = "CVModifierApp"
DEFAULT_USER = "smtp_credentials"


# Windows DPAPI Fallback structures if keyring fails or is disabled
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _win_dpapi_encrypt(plaintext: str) -> Optional[str]:
    """Encrypts plaintext string using Windows DPAPI (CryptProtectData)."""
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        b_data = plaintext.encode("utf-8")
        blob_in = DATA_BLOB(len(b_data), ctypes.create_string_buffer(b_data, len(b_data)))
        blob_out = DATA_BLOB()

        # CryptProtectData(pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
        if crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            "CVModifierSecret",
            None,
            None,
            None,
            0x01,  # CRYPTPROTECT_UI_FORBIDDEN
            ctypes.byref(blob_out),
        ):
            encrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            kernel32.LocalFree(blob_out.pbData)
            return base64.b64encode(encrypted_bytes).decode("ascii")
    except Exception as e:
        logger.warning(f"DPAPI encryption failed: {e}")
    return None


def _win_dpapi_decrypt(cipher_b64: str) -> Optional[str]:
    """Decrypts base64-encoded ciphertext using Windows DPAPI (CryptUnprotectData)."""
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        encrypted_bytes = base64.b64decode(cipher_b64.encode("ascii"))
        blob_in = DATA_BLOB(
            len(encrypted_bytes),
            ctypes.create_string_buffer(encrypted_bytes, len(encrypted_bytes)),
        )
        blob_out = DATA_BLOB()

        if crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0x01,  # CRYPTPROTECT_UI_FORBIDDEN
            ctypes.byref(blob_out),
        ):
            decrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            kernel32.LocalFree(blob_out.pbData)
            return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.warning(f"DPAPI decryption failed: {e}")
    return None


def store_password(username: str = DEFAULT_USER, password: str = "") -> bool:
    """
    Securely stores a password using keyring.
    Falls back to Windows DPAPI if keyring backend is unavailable.
    """
    key = username.strip() if username else DEFAULT_USER
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, key, password)
        logger.info(f"Stored credentials in keyring for user '{key}'.")
        return True
    except Exception as e:
        logger.warning(f"Keyring storage failed for '{key}', attempting DPAPI fallback: {e}")
        encrypted = _win_dpapi_encrypt(password)
        if encrypted:
            # Store DPAPI cipher in database settings under encrypted key
            from app.database import set_setting
            set_setting(f"_dpapi_sec_{key}", encrypted)
            logger.info(f"Stored credentials using Windows DPAPI fallback for '{key}'.")
            return True
        else:
            logger.error(f"Both keyring and DPAPI storage failed for '{key}'.")
            return False


def get_password(username: str = DEFAULT_USER) -> Optional[str]:
    """
    Retrieves the stored password from keyring or DPAPI fallback.
    """
    key = username.strip() if username else DEFAULT_USER
    try:
        import keyring
        pwd = keyring.get_password(SERVICE_NAME, key)
        if pwd is not None:
            return pwd
    except Exception as e:
        logger.warning(f"Keyring retrieval failed for '{key}': {e}")

    # Try DPAPI fallback
    try:
        from app.database import get_setting
        encrypted = get_setting(f"_dpapi_sec_{key}", None)
        if encrypted:
            return _win_dpapi_decrypt(encrypted)
    except Exception as e:
        logger.warning(f"DPAPI fallback retrieval failed: {e}")

    return None


def delete_password(username: str):
    """Deletes stored password from keyring and DPAPI storage."""
    key = username.strip() or DEFAULT_USER
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, key)
    except Exception:
        pass
    try:
        from app.database import set_setting
        set_setting(f"_dpapi_sec_{key}", "")
    except Exception:
        pass


import os
import hmac
import hashlib


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hashes a password with a cryptographically secure random salt using PBKDF2-HMAC-SHA256.
    Uses 200,000 iterations for robust offline security.
    Returns (hex_hash, hex_salt).
    """
    if not salt:
        salt = os.urandom(16).hex()
    salt_bytes = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        200_000,
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a plain password against stored hash and salt using constant-time comparison."""
    try:
        salt_bytes = bytes.fromhex(salt)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            200_000,
        )
        return hmac.compare_digest(key.hex(), password_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

