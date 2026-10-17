"""Blog o'qish va olqish kimga bog'lanadi (PUB1.0g).

PUB1.0g'gacha har anonim tashrifchiga bir yillik `blog_visitor` cookie qo'yilar,
maqola o'qilishi IP xeshi (soxtalashtiriladigan chap XFF'dan) va brauzer
user-agent'i bilan yozilardi. Owner qarori (PUB-D6) bo'lmaguncha:

- anonim o'qish va olqish hech narsa yozmaydi va cookie qo'ymaydi;
- kirgan foydalanuvchi uchun faqat (maqola, foydalanuvchi) - IP va UA yo'q;
- eski cookie ko'rilsa brauzerdan o'chiriladi.
"""

# PUB1.0g'gacha qo'yilgan bir yillik anonim identifikator. Endi o'qilmaydi,
# faqat brauzerdan o'chirish uchun nomi saqlanadi.
LEGACY_VISITOR_COOKIE = "blog_visitor"
# Eski yozuvlardagi anonim kalit prefiksi (tozalash buyrug'i uchun).
LEGACY_ANONYMOUS_KEY_PREFIX = "anon:"


def reader_key(request):
    """Kirgan foydalanuvchining kaliti yoki ``None`` (anonim kuzatilmaydi)."""
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return None


def forget_legacy_visitor_cookie(request, response):
    """Brauzerda qolgan eski bir yillik cookie'ni o'chiradi."""
    if LEGACY_VISITOR_COOKIE in request.COOKIES:
        response.delete_cookie(LEGACY_VISITOR_COOKIE, samesite="Lax")
    return response


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
