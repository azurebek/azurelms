"""Bildirishnoma havolasi Mini App avto-loginidan o'tadi (A3).

Worker matnga oddiy `https://.../courses/...` havolasini qo'shardi.
Telegram-only o'quvchi uni bosganda brauzerda **autentifikatsiyasiz**
sahifa ochilardi — ya'ni "yangi dars ochildi" yoki "vazifangiz tekshirildi"
xabari kerakli joyga olib bormasdi va o'quvchi login ekraniga tushardi.

Mini App tugmasi (`web_app`) esa `initData` bilan ochiladi va sessiya
avtomatik tiklanadi. Mexanizm loyihada allaqachon bor edi
(`bot/keyboards.py::miniapp_button`), faqat outbox undan foydalanmasdi.

Lokal profil uchun muhim shart: Telegram `web_app` tugmasini faqat public
HTTPS domenda qabul qiladi. Shuning uchun `localhost` da tugma yasalmaydi
va eski (oddiy havolali) xulq saqlanadi — bu degradatsiya, nosozlik emas.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from bot.models import TelegramOutbox
from bot.outbox import render_outbox_markup, render_outbox_text
from users.models import Notification

User = get_user_model()


class OutboxMiniAppLinkTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="link-student", email="link-student@example.test",
            password="x", telegram_id=990001,
        )

    def _queue(self, url):
        notification = Notification.objects.create(
            recipient=self.student,
            title="Yangi dars ochildi",
            message="Dars 2 endi ochiq.",
            url=url,
        )
        return TelegramOutbox.objects.get(notification=notification)

    @override_settings(APP_DOMAIN="azurelms.example")
    def test_a_relative_url_becomes_a_miniapp_button(self):
        item = self._queue("/courses/4/lesson/7/")

        markup = render_outbox_markup(item)

        self.assertIsNotNone(markup)
        button = markup.inline_keyboard[0][0]
        self.assertIsNotNone(button.web_app)
        self.assertIn("/bot/miniapp/?next=", button.web_app.url)
        self.assertIn("%2Fcourses%2F4%2Flesson%2F7%2F", button.web_app.url)

    @override_settings(APP_DOMAIN="azurelms.example")
    def test_the_bare_url_is_not_repeated_in_the_text(self):
        """Ikki nusxa bo'lsa, o'quvchi avto-login bermaydiganini bosishi mumkin."""
        item = self._queue("/courses/4/lesson/7/")

        text = render_outbox_text(item)

        self.assertIn("Yangi dars ochildi", text)
        self.assertNotIn("https://azurelms.example/courses/4/lesson/7/", text)

    @override_settings(APP_DOMAIN="localhost:8000")
    def test_local_profile_falls_back_to_the_plain_link(self):
        """Lokalda Telegram web_app tugmasini rad etadi — eski yo'l qoladi."""
        item = self._queue("/courses/4/lesson/7/")

        self.assertIsNone(render_outbox_markup(item))
        # Lokalda matnda ham havola chiqmaydi (mavjud xulq saqlanadi).
        self.assertNotIn("/courses/4/lesson/7/", render_outbox_text(item))

    @override_settings(APP_DOMAIN="azurelms.example")
    def test_an_external_url_is_left_alone(self):
        """Tashqi sayt Mini App ichida ochilmaydi — `?next=` faqat o'zimizniki."""
        item = self._queue("https://example.com/boshqa/")

        self.assertIsNone(render_outbox_markup(item))
        self.assertIn("https://example.com/boshqa/", render_outbox_text(item))

    @override_settings(APP_DOMAIN="azurelms.example")
    def test_a_notification_without_a_url_gets_no_button(self):
        notification = Notification.objects.create(
            recipient=self.student, title="Xabar", message="Havolasiz",
        )
        item = TelegramOutbox.objects.get(notification=notification)

        self.assertIsNone(render_outbox_markup(item))
