"""Password hashing, JWT tokens and device API keys."""
import hashlib
import hmac
import secrets
import time

import jwt

from .config import settings

_PBKDF2_ROUNDS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id: int, org_id: int, role: str) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "org": org_id, "role": role, "iat": now,
               "exp": now + settings.jwt_ttl_minutes * 60}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def new_device_key() -> tuple[str, str, str]:
    """Return (plaintext key, sha256 hash, display prefix)."""
    key = "fod_" + secrets.token_urlsafe(32)
    return key, hash_device_key(key), key[:10]


def hash_device_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
