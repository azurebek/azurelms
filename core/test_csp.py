"""A0b/5 — CSP header haqiqatan chiqadimi va Mini App uni buzmaydimi.

Fon: paket `django-csp 4.0`, sozlamalar esa eski `CSP_*` nomlarida edi. v4
faqat `CONTENT_SECURITY_POLICY` dictini o'qiydi, ya'ni `SECURITY_STRICT=True`
bo'lganda ham header umuman chiqmasdi.

Ikkinchi muammo: `TelegramMiniAppFrameMiddleware` headerni o'zi yozardi.
django-csp v4 esa header allaqachon mavjud bo'lsa butun siyosatni o'tkazib
yuboradi, ya'ni Mini App sahifalari `frame-ancestors` dan boshqa hech narsasiz
qolardi. Shuning uchun bu yerda ikkala holat ham — oddiy sahifa va Mini App
sessiyasi — real javob sarlavhasi darajasida tekshiriladi.
"""

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.csp_policy import TELEGRAM_SCRIPT_SRC, build_csp_policy

CSP_MIDDLEWARE = "csp.middleware.CSPMiddleware"


def parse_csp(header):
    """`"a 'self'; b 'none'"` -> `{"a": ["'self'"], "b": ["'none'"]}`."""
    directives = {}
    for part in header.split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def _middleware_with_csp():
    """Joriy zanjir + CSP middleware (u faqat SECURITY_STRICT'da ulanadi)."""
    chain = list(settings.MIDDLEWARE)
    if CSP_MIDDLEWARE not in chain:
        chain.insert(0, CSP_MIDDLEWARE)
    return chain


class CspPolicyShapeTests(SimpleTestCase):
    """Siyosatning o'zi — django-csp v4 kutgan shaklda."""

    def test_policy_uses_the_v4_directives_key(self):
        policy = build_csp_policy("example.test")
        self.assertIn("DIRECTIVES", policy)

    def test_settings_expose_content_security_policy(self):
        """Eski `CSP_*` nomlari v4 tomonidan o'qilmaydi — header chiqmasdi."""
        self.assertTrue(getattr(settings, "CONTENT_SECURITY_POLICY", None))

    def test_dangerous_directives_are_locked_down(self):
        directives = build_csp_policy("example.test")["DIRECTIVES"]
        self.assertEqual(directives["object-src"], ["'none'"])
        self.assertEqual(directives["base-uri"], ["'self'"])
        self.assertEqual(directives["form-action"], ["'self'"])

    def test_default_policy_does_not_allow_framing_by_telegram(self):
        """Oddiy sahifa iframe'ga tushmasin; Mini App istisnosi per-response."""
        directives = build_csp_policy("example.test")["DIRECTIVES"]
        self.assertEqual(directives["frame-ancestors"], ["'self'"])

    def test_mini_app_script_source_is_allowed(self):
        directives = build_csp_policy("example.test")["DIRECTIVES"]
        self.assertIn(TELEGRAM_SCRIPT_SRC, directives["script-src"])

    def test_websocket_origin_follows_the_app_domain(self):
        self.assertIn(
            "wss://example.test",
            build_csp_policy("example.test")["DIRECTIVES"]["connect-src"],
        )
        self.assertIn(
            "ws://localhost:8000",
            build_csp_policy("")["DIRECTIVES"]["connect-src"],
        )


class CspResponseHeaderTests(TestCase):
    """Header real javobda chiqadimi."""

    def test_normal_page_gets_a_full_policy(self):
        with override_settings(MIDDLEWARE=_middleware_with_csp()):
            response = self.client.get(reverse("home"))
        header = response.headers.get("Content-Security-Policy", "")
        self.assertTrue(header, "CSP header umuman chiqmadi")
        directives = parse_csp(header)
        for name in ("default-src", "script-src", "object-src", "frame-ancestors"):
            with self.subTest(directive=name):
                self.assertIn(name, directives)
        # Oddiy sahifa Telegram iframe'iga tushmasligi kerak. `script-src` da
        # telegram.org bo'lishi esa to'g'ri — Mini App skriptini yuklaydi.
        self.assertEqual(directives["frame-ancestors"], ["'self'"])

    def test_mini_app_session_keeps_the_full_policy_and_widens_frame_ancestors(self):
        """Eng muhim regressiya: Mini App sahifasi siyosatsiz qolmasligi kerak."""
        session = self.client.session
        session["telegram_miniapp"] = True
        session.save()

        with override_settings(MIDDLEWARE=_middleware_with_csp()):
            response = self.client.get(reverse("home"))

        directives = parse_csp(response.headers.get("Content-Security-Policy", ""))
        self.assertIn("script-src", directives, "Mini App sahifasi to'liq siyosatni yo'qotdi")
        self.assertEqual(directives["object-src"], ["'none'"])
        self.assertIn("https://web.telegram.org", directives["frame-ancestors"])
        self.assertNotIn("X-Frame-Options", response.headers)

    def test_normal_session_still_gets_x_frame_options(self):
        with override_settings(MIDDLEWARE=_middleware_with_csp()):
            response = self.client.get(reverse("home"))
        # Mini App bo'lmagan sessiyada middleware headerni olib tashlamaydi.
        self.assertNotEqual(response.headers.get("X-Frame-Options", ""), "")

    def test_mini_app_keeps_a_frame_control_when_csp_middleware_is_off(self):
        """Local profil: `X-Frame-Options` olib tashlangach frame nazoratsiz qolmasin.

        CSP middleware faqat `SECURITY_STRICT` da ulanadi. Mini App middleware
        esa har ikkala profilda `X-Frame-Options` ni olib tashlaydi — demak
        ulanmagan holatda minimal `frame-ancestors` o'zi yozilishi kerak, aks
        holda sahifani istalgan sayt iframe'ga oladi.
        """
        chain = [m for m in settings.MIDDLEWARE if m != CSP_MIDDLEWARE]
        session = self.client.session
        session["telegram_miniapp"] = True
        session.save()

        with override_settings(MIDDLEWARE=chain):
            response = self.client.get(reverse("home"))

        directives = parse_csp(response.headers.get("Content-Security-Policy", ""))
        self.assertIn("frame-ancestors", directives)
        self.assertIn("https://web.telegram.org", directives["frame-ancestors"])
        self.assertNotIn("X-Frame-Options", response.headers)
