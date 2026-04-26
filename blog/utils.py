import hashlib
import uuid

from django.conf import settings


BLOG_VISITOR_COOKIE = "blog_visitor"
BLOG_VISITOR_COOKIE_AGE = 60 * 60 * 24 * 365


def ensure_visitor_token(request):
    existing = request.COOKIES.get(BLOG_VISITOR_COOKIE)
    if existing:
        return existing, False
    return uuid.uuid4().hex, True


def set_visitor_cookie(response, visitor_token):
    response.set_cookie(
        BLOG_VISITOR_COOKIE,
        visitor_token,
        max_age=BLOG_VISITOR_COOKIE_AGE,
        httponly=True,
        secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
        samesite="Lax",
    )


def viewer_key_for_request(request, visitor_token):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"anon:{visitor_token}"


def build_ip_hash(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "").strip()
    if not ip:
        return ""
    salted = f"{settings.SECRET_KEY}:{ip}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def is_probable_bot(user_agent):
    marker = (user_agent or "").lower()
    bot_markers = [
        "bot",
        "spider",
        "crawler",
        "preview",
        "facebookexternalhit",
        "slackbot",
        "discordbot",
        "whatsapp",
        "curl",
        "python-requests",
    ]
    return any(item in marker for item in bot_markers)
