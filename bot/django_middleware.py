from django.conf import settings

CSP_MIDDLEWARE = "csp.middleware.CSPMiddleware"


class TelegramMiniAppFrameMiddleware:
    """Telegram orqali tasdiqlangan sessionlarni Web Telegram iframe'ida ochadi.

    Bu middleware `X-Frame-Options` ni olib tashlaydi — aks holda Telegram
    WebView sahifani ko'rsata olmaydi. Demak uning o'rniga **doim** biror
    frame nazorati qolishi shart, aks holda sahifani istalgan sayt iframe'ga
    olib qo'yadi.

    Ilgari bu yerda `Content-Security-Policy` headeri qo'lda yozilardi. Bu
    django-csp v4 bilan xavfli: uning middleware'i header allaqachon mavjud
    bo'lsa **butun siyosatni o'tkazib yuboradi** (`no_header = HEADER not in
    response`), ya'ni Mini App sahifalari `frame-ancestors` dan boshqa hech
    qanday himoyasiz qolardi — `script-src`, `object-src`, `base-uri`siz.

    Endi ikki yo'l bor (A0b):

    * CSP middleware ulangan bo'lsa (strict profil) — bu yerda faqat shu javob
      uchun `frame-ancestors` almashtiriladi va to'liq siyosatni django-csp
      quradi;
    * ulanmagan bo'lsa (local profil) — minimal `frame-ancestors` headeri
      yoziladi, chunki `X-Frame-Options` allaqachon olib tashlangan.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.session.get("telegram_miniapp"):
            return response

        from core.csp_policy import TELEGRAM_FRAME_ANCESTORS

        response.headers.pop("X-Frame-Options", None)
        # django-csp v4 per-response override'i.
        response._csp_replace = {"frame-ancestors": list(TELEGRAM_FRAME_ANCESTORS)}

        if CSP_MIDDLEWARE not in settings.MIDDLEWARE:
            response.headers.setdefault(
                "Content-Security-Policy",
                "frame-ancestors " + " ".join(TELEGRAM_FRAME_ANCESTORS),
            )
        return response
