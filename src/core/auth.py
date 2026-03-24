import base64
import hmac
import json
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from src.config import settings


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC with a random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return hmac.compare_digest(dk.hex(), hashed)


def _sign(data: str) -> str:
    return hmac.new(settings.AUTH_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def create_token(payload: Dict[str, Any]) -> str:
    data = payload.copy()
    exp_minutes = settings.AUTH_TOKEN_EXP_MIN or 60 * 24
    exp = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)
    data["exp"] = int(exp.timestamp())
    body = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    sig = _sign(body)
    return f"{body}.{sig}"


def decode_token(token: str) -> Dict[str, Any] | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode()).decode())
    except Exception:
        return None
    exp = payload.get("exp")
    if exp and datetime.now(timezone.utc).timestamp() > exp:
        return None
    return payload
