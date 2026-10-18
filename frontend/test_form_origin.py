"""Brauzer formani qanday `Origin` bilan yuboradi — va CSRF uni qabul qiladimi.

Django test client `Origin` sarlavhasini yubormaydi, shuning uchun 2026-10-19 da
topilgan xato testlarda ko'rinmagan edi: login, ro'yxat va parol sahifalari
`Referrer-Policy: no-referrer` olgan, brauzer esa bunday sahifadagi formani
`Origin: null` bilan yuboradi (Fetch standarti, “append a request `Origin`
header”) va Django CSRF 403 qaytaradi — haqiqiy brauzerda hech kim kira olmasdi.

Bu test brauzer qoidasini takrorlaydi: sahifaning o'z referrer siyosatidan
(sarlavha yoki `<meta name="referrer">`) brauzer yuboradigan `Origin`ni
hisoblaydi va formani CSRF tekshiruvi yoqilgan holda yuboradi.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from aicontrol.models import FeatureFlag

ORIGIN = "http://testserver"
META_REFERRER = re.compile(r'<meta\s+name="referrer"\s+content="([^"]+)"', re.I)
CSRF_FIELD = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
PASSWORD = "Forma-origin-2026!"


def browser_origin(response):
    """Bir xil saytdagi (http→http) forma POST'i uchun brauzer yuboradigan `Origin`.

    Hujjat siyosati: `<meta>` sarlavhadan keyin qo'llanadi; ro'yxatda oxirgi
    tanilgan qiymat amal qiladi. Bir xil sxema va host'da faqat `no-referrer`
    `null` beradi.
    """
    candidates = [response.get("Referrer-Policy", "")] + META_REFERRER.findall(response.content.decode())
    policies = [value.split(",")[-1].strip().lower() for value in candidates if value.strip()]
    policy = policies[-1] if policies else "strict-origin-when-cross-origin"
    return "null" if policy == "no-referrer" else ORIGIN


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_auth", defaults={"enabled": enabled})
        yield name


class BrowserFormOriginTests(TestCase):
    def setUp(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": True})
        self.user = get_user_model().objects.create_user("forma-origin", email="forma@example.test", password=PASSWORD)

    def submit(self, client, page_url, data, *, post_url=None):
        page = client.get(page_url)
        self.assertEqual(page.status_code, 200, page_url)
        token = CSRF_FIELD.search(page.content.decode())
        self.assertIsNotNone(token, f"{page_url}: CSRF maydoni yo'q")
        response = client.post(post_url or page_url, {**data, "csrfmiddlewaretoken": token.group(1)},
                               HTTP_ORIGIN=browser_origin(page))
        self.assertNotEqual(response.status_code, 403, f"{page_url}: brauzer formasi CSRF'da rad etildi")
        return response

    def test_login_form_is_accepted_from_a_real_browser(self):
        for name in renderers():
            client = Client(enforce_csrf_checks=True)
            with self.subTest(renderer=name):
                response = self.submit(client, reverse("login"), {"username": "forma-origin", "password": PASSWORD})
                self.assertEqual(response.status_code, 302)

    def test_registration_form_is_accepted_from_a_real_browser(self):
        for index, name in enumerate(renderers()):
            client = Client(enforce_csrf_checks=True)
            with self.subTest(renderer=name):
                response = self.submit(client, reverse("register"), {
                    "first_name": "Forma", "last_name": "Origin", "email": f"yangi{index}@example.test",
                    "password1": PASSWORD, "password2": PASSWORD,
                })
                self.assertEqual(response.status_code, 302)

    def test_password_reset_request_and_new_password_forms_are_accepted(self):
        for name in renderers():
            client = Client(enforce_csrf_checks=True)
            with self.subTest(renderer=name, step="request"):
                response = self.submit(client, reverse("password_reset"), {"email": "forma@example.test"})
                self.assertEqual(response.status_code, 302)
            uid = urlsafe_base64_encode(force_bytes(self.user.pk))
            link = reverse("password_reset_confirm", args=[uid, default_token_generator.make_token(self.user)])
            opened = client.get(link)
            self.assertEqual(opened.status_code, 302)
            with self.subTest(renderer=name, step="new password"):
                response = self.submit(client, opened["Location"],
                                       {"new_password1": "Yangi-Qatiy-Kalit-77", "new_password2": "Yangi-Qatiy-Kalit-77"})
                self.assertEqual(response.status_code, 302)
            self.user.set_password(PASSWORD)
            self.user.save()

    def test_browser_origin_rule_matches_the_fetch_standard(self):
        class Page:
            def __init__(self, header, body=""):
                self.headers, self.content = {"Referrer-Policy": header} if header else {}, body.encode()

            def get(self, key, default=""):
                return self.headers.get(key, default)

        self.assertEqual(browser_origin(Page("no-referrer")), "null")
        self.assertEqual(browser_origin(Page("same-origin")), ORIGIN)
        self.assertEqual(browser_origin(Page("", '<meta name="referrer" content="no-referrer">')), "null")
        self.assertEqual(browser_origin(Page("no-referrer", '<meta name="referrer" content="same-origin">')), ORIGIN)
