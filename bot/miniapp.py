"""Telegram Mini App (WebApp) initData validatsiyasi (F5).

Telegram webview sahifaga imzolangan `initData` qatorini beradi:
key=value juftliklar + `hash` (HMAC-SHA256, kalit = HMAC("WebAppData", bot_token)).
Rasmiy spets: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Bu modul sof funksiya — tarmoqsiz, to'liq testlanadi.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60


def build_data_check_string(pairs):
    return "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))


def compute_init_data_hash(pairs, bot_token):
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(
        secret_key, build_data_check_string(pairs).encode(), hashlib.sha256
    ).hexdigest()


def validate_init_data(init_data, bot_token, *, max_age_seconds=DEFAULT_MAX_AGE_SECONDS, now=None):
    """initData imzosi va muddatini tekshiradi.

    Muvaffaqiyatda {"user": {...}|None, "auth_date": int} qaytaradi, aks holda None.
    """
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", "")
    if not received_hash:
        return None

    expected_hash = compute_init_data_hash(pairs, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    try:
        auth_date = int(pairs.get("auth_date", "0") or 0)
    except ValueError:
        return None
    now = now if now is not None else time.time()
    if max_age_seconds and (now - auth_date) > max_age_seconds:
        return None

    user = None
    if pairs.get("user"):
        try:
            user = json.loads(pairs["user"])
        except (TypeError, ValueError):
            user = None

    return {"user": user, "auth_date": auth_date}


def safe_next_path(raw_next):
    """Open-redirect himoyasi: faqat sayt ichidagi absolute-path'ga ruxsat."""
    path = (raw_next or "").strip()
    if not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/users/dashboard/"
    return path
