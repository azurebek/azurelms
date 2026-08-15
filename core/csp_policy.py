"""Content-Security-Policy siyosati — django-csp v4 formatida (A0b).

Nima buzilgan edi: paket `django-csp 4.0`, sozlamalar esa hali eski `CSP_*`
nomlarida turardi. v4 faqat `CONTENT_SECURITY_POLICY` dictini o'qiydi, ya'ni
`SECURITY_STRICT=True` bo'lganda ham **hech qanday CSP header chiqmasdi** —
himoya bor deb o'ylanardi, aslida yo'q edi.

Siyosat shu yerda, alohida funksiyada quriladi: sozlamalar import vaqtida
hisoblanadi va uni test qilib bo'lmaydi, funksiya esa `APP_DOMAIN` bilan
chaqirilib natijasi to'g'ridan-to'g'ri tekshiriladi.

Telegram Mini App uchun alohida eslatma: u `telegram.org` dan skript yuklaydi
va Telegram iframe'i ichida ochiladi. Skript manbasi shu yerda, umumiy
siyosatda; `frame-ancestors` esa faqat Mini App sessiyasida
`bot.django_middleware.TelegramMiniAppFrameMiddleware` orqali kengaytiriladi.
"""

TELEGRAM_SCRIPT_SRC = "https://telegram.org"
TELEGRAM_FRAME_ANCESTORS = ("'self'", "https://web.telegram.org", "https://*.telegram.org")


def build_csp_policy(app_domain=""):
    """django-csp v4 uchun `CONTENT_SECURITY_POLICY` dictini quradi."""
    websocket_origin = f"wss://{app_domain}" if app_domain else "ws://localhost:8000"
    return {
        "DIRECTIVES": {
            "default-src": ["'self'"],
            # `unsafe-inline` hali kerak: shablonlarda inline `<script>` bloklari
            # bor. Ularni nonce'ga ko'chirish alohida ish.
            "script-src": [
                "'self'",
                "https://cdn.jsdelivr.net",
                "https://www.googletagmanager.com",
                "https://www.google-analytics.com",
                # Mini App `telegram-web-app.js` ni shu domendan yuklaydi.
                TELEGRAM_SCRIPT_SRC,
                "'unsafe-inline'",
            ],
            "style-src": [
                "'self'",
                "https://cdn.jsdelivr.net",
                "https://fonts.googleapis.com",
                "'unsafe-inline'",
            ],
            "font-src": ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
            "img-src": [
                "'self'",
                "data:",
                "https://*.digitaloceanspaces.com",
                "https://www.google-analytics.com",
            ],
            "media-src": ["'self'"],
            "frame-src": ["'self'", "https://www.youtube.com", "https://player.vimeo.com"],
            # Default: sahifa hech qayerga embed qilinmaydi. Mini App sessiyasi
            # buni per-response `_csp_replace` bilan kengaytiradi.
            "frame-ancestors": ["'self'"],
            "connect-src": ["'self'", "https://www.google-analytics.com", websocket_origin],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "object-src": ["'none'"],
        }
    }
