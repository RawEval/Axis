"""AES-256-GCM token encryption for OAuth tokens.

The key comes from TOKEN_ENCRYPTION_KEY env var (32 bytes, base64). Never log
plaintext tokens. Decryption happens in-memory only at call time.
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _key() -> bytes:
    raw = settings.token_encryption_key
    try:
        key = base64.b64decode(raw)
    except Exception:  # noqa: BLE001
        # fallback: allow raw hex or plain string for local dev
        key = raw.encode()
    if len(key) < 32:
        # pad for dev, fail loud in prod via AxisBaseSettings validator
        key = (key + b"\x00" * 32)[:32]
    return key[:32]


def encrypt_token(plaintext: str) -> bytes:
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return nonce + ct  # prepend nonce


def decrypt_token(blob: bytes) -> str:
    nonce, ct = blob[:12], blob[12:]
    aes = AESGCM(_key())
    return aes.decrypt(nonce, ct, associated_data=None).decode("utf-8")
