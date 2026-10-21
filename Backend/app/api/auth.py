import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from app.config import settings

MAX_AGE_SECONDS = 24 * 3600


def validate_init_data(init_data: str) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise ValueError("bad signature")
    if time.time() - int(pairs.get("auth_date", "0")) > MAX_AGE_SECONDS:
        raise ValueError("expired")

    return json.loads(pairs["user"])


async def current_user(authorization: str = Header(default="")) -> dict:
    # Режим разработчика: только если DEV_USER_ID задан в .env
    # и запрос пришёл без подписи Telegram (обычный браузер).
    if settings.dev_user_id is not None and authorization.strip() in ("", "tma"):
        return {"id": settings.dev_user_id, "first_name": "Dev"}

    if not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return validate_init_data(authorization[4:])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Unauthorized")