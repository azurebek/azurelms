"""PUB1.4e — Telegram orqali kirish: odam nima bo'layotganini biladi va o'zi qaror qiladi.

Asosiy xavfsizlik da'vosi: havolani ochishning o'zi hech kimni kiritmaydi. Bot
avval nima so'ralayotganini va saytdagi kodni ko'rsatadi; kirish faqat
«Kirishni tasdiqlash» tugmasidan keyin. Aks holda begona odam o'z brauzerida
boshlagan havolani yuborib, uni bosganning hisobiga kirib olardi. Rad etilgan
oqim `declined` bo'ladi va brauzer buni muddat tugashini kutmasdan ko'radi.

UX da'vosi: panel JS'siz yashirin (o'lik tugma yo'q), ikkala renderer bitta
belgilash va bitta skriptni ishlatadi, kirish matni ro'yxat holatiga mos va
rost (telefon raqami so'ralmaydi).
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from bot.routers.onboarding import (
    TG_AUTH_CONFIRM,
    TG_AUTH_DECLINE,
    cb_telegram_auth_confirm,
    cb_telegram_auth_decline,
    cmd_start_handler,
)
from bot.services import decline_telegram_auth_token, describe_telegram_auth_request, handle_telegram_auth_token
from users import telegram_auth_service as telegram_auth
from users.models import TelegramAuthSession

User = get_user_model()
TG_ID = 777_000_111


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        set_flag("frontend_v1_auth", enabled)
        yield name


class FlowMixin:
    def start(self):
        response = self.client.post(reverse("telegram_auth_init"))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def row(self, token):
        return TelegramAuthSession.objects.get(token=token)

    def browser_status(self, token):
        return self.client.get(reverse("telegram_auth_status", args=[token])).json()["status"]


class ConfirmationStepTests(FlowMixin, TestCase):
    def setUp(self):
        set_flag("public_registration", True)

    def test_init_returns_a_three_digit_code_the_bot_repeats(self):
        User.objects.create_user("tg-ali", email="ali@example.test", telegram_id=TG_ID)
        flow = self.start()
        self.assertRegex(flow["code"], r"^\d{3}$")
        self.assertEqual(flow["code"], telegram_auth.confirmation_code(flow["token"]))
        prompt = describe_telegram_auth_request(f"auth_{flow['token']}", TG_ID)
        self.assertTrue(prompt.ok)
        self.assertEqual(prompt.code, "confirm")
        self.assertIn(f"Saytdagi tasdiqlash kodi: {flow['code']}", prompt.message)
        self.assertIn("Bu men emas", prompt.message)

    def test_reading_the_request_authenticates_nobody(self):
        User.objects.create_user("tg-ali", email="ali@example.test", telegram_id=TG_ID)
        flow = self.start()
        describe_telegram_auth_request(f"auth_{flow['token']}", TG_ID)
        row = self.row(flow["token"])
        self.assertEqual(row.status, TelegramAuthSession.STATUS_PENDING)
        self.assertIsNone(row.user)
        self.assertEqual(self.browser_status(flow["token"]), "pending")

    def test_unknown_identity_is_told_what_a_new_profile_stores(self):
        flow = self.start()
        prompt = describe_telegram_auth_request(f"auth_{flow['token']}", TG_ID)
        self.assertTrue(prompt.ok)
        self.assertIn("yangi profil ochiladi", prompt.message)
        self.assertIn("Telefon raqamingiz so'ralmaydi", prompt.message)

    def test_hopeless_requests_are_declined_before_any_button(self):
        cases = {
            "identity_inactive": lambda: User.objects.create_user(
                "tg-blok", email="blok@example.test", telegram_id=TG_ID, is_active=False),
            "registration_closed": lambda: set_flag("public_registration", False),
        }
        for code, arrange in cases.items():
            User.objects.filter(telegram_id=TG_ID).delete()
            set_flag("public_registration", True)
            arrange()
            flow = self.start()
            prompt = describe_telegram_auth_request(f"auth_{flow['token']}", TG_ID)
            with self.subTest(code=code):
                self.assertFalse(prompt.ok)
                self.assertEqual(prompt.code, code)
                self.assertEqual(self.browser_status(flow["token"]), "declined")

    def test_a_stale_link_explains_itself(self):
        flow = self.start()
        TelegramAuthSession.objects.filter(token=flow["token"]).update(status=TelegramAuthSession.STATUS_EXPIRED)
        for token in (flow["token"], "mavjud-emas"):
            prompt = describe_telegram_auth_request(f"auth_{token}", TG_ID)
            with self.subTest(token=token[:6]):
                self.assertFalse(prompt.ok)
                self.assertIn("eskirgan yoki yopilgan", prompt.message)


class DeclineTests(FlowMixin, TestCase):
    def setUp(self):
        set_flag("public_registration", True)
        self.user = User.objects.create_user("tg-ali", email="ali@example.test", telegram_id=TG_ID)

    def test_not_me_closes_the_flow_for_good(self):
        flow = self.start()
        result = decline_telegram_auth_token(f"auth_{flow['token']}", TG_ID)
        self.assertTrue(result.ok)
        self.assertEqual(self.browser_status(flow["token"]), "declined")
        later = handle_telegram_auth_token(f"auth_{flow['token']}", TG_ID)
        self.assertFalse(later.ok)
        consume = self.client.post(reverse("telegram_auth_consume", args=[flow["token"]])).json()
        self.assertEqual(consume["status"], "declined")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_the_confirming_person_can_still_take_it_back_before_the_browser_does(self):
        flow = self.start()
        self.assertTrue(handle_telegram_auth_token(f"auth_{flow['token']}", TG_ID).ok)
        stranger = decline_telegram_auth_token(f"auth_{flow['token']}", TG_ID + 1)
        self.assertFalse(stranger.ok)
        self.assertEqual(self.row(flow["token"]).status, TelegramAuthSession.STATUS_AUTHENTICATED)
        self.assertTrue(decline_telegram_auth_token(f"auth_{flow['token']}", TG_ID).ok)
        consume = self.client.post(reverse("telegram_auth_consume", args=[flow["token"]])).json()
        self.assertEqual(consume["status"], "declined")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_used_flow_cannot_be_declined(self):
        flow = self.start()
        handle_telegram_auth_token(f"auth_{flow['token']}", TG_ID)
        self.client.post(reverse("telegram_auth_consume", args=[flow["token"]]))
        self.assertFalse(decline_telegram_auth_token(f"auth_{flow['token']}", TG_ID).ok)
        self.assertEqual(self.row(flow["token"]).status, TelegramAuthSession.STATUS_USED)


class BotRouterTests(FlowMixin, TransactionTestCase):
    """Haqiqiy handlerlar (dispatcher'siz): havola ochilishi kirish emas, tugma kirish."""

    def setUp(self):
        set_flag("public_registration", True)
        self.user = User.objects.create_user("tg-ali", email="ali@example.test", telegram_id=TG_ID)
        self.person = SimpleNamespace(id=TG_ID, first_name="Ali", last_name="", username="ali_tg")

    def open_link(self, token):
        message = SimpleNamespace(from_user=self.person, answer=AsyncMock())
        asyncio.run(cmd_start_handler(message, SimpleNamespace(args=f"auth_{token}"), None, "guest"))
        return message

    def press(self, handler, prefix, token):
        callback = SimpleNamespace(
            data=prefix + token, from_user=self.person, answer=AsyncMock(),
            message=SimpleNamespace(edit_text=AsyncMock(), answer=AsyncMock()),
        )
        asyncio.run(handler(callback))
        return callback

    def test_opening_the_link_only_asks(self):
        flow = self.start()
        message = self.open_link(flow["token"])
        text = message.answer.await_args.args[0]
        markup = message.answer.await_args.kwargs["reply_markup"]
        self.assertIn(flow["code"], text)
        datas = [button.callback_data for row in markup.inline_keyboard for button in row]
        self.assertEqual(datas, [TG_AUTH_CONFIRM + flow["token"], TG_AUTH_DECLINE + flow["token"]])
        self.assertTrue(all(len(data.encode()) <= 64 for data in datas))
        self.assertEqual(self.row(flow["token"]).status, TelegramAuthSession.STATUS_PENDING)

    def test_the_confirm_button_signs_the_browser_in(self):
        flow = self.start()
        callback = self.press(cb_telegram_auth_confirm, TG_AUTH_CONFIRM, flow["token"])
        self.assertIn("tasdiqlandi", callback.message.edit_text.await_args.args[0])
        callback.message.answer.assert_awaited()  # rolga mos klaviatura
        consume = self.client.post(reverse("telegram_auth_consume", args=[flow["token"]])).json()
        self.assertEqual(consume["status"], "authenticated")
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))

    def test_the_not_me_button_closes_the_flow(self):
        flow = self.start()
        callback = self.press(cb_telegram_auth_decline, TG_AUTH_DECLINE, flow["token"])
        self.assertIn("Rad etildi", callback.message.edit_text.await_args.args[0])
        self.assertEqual(self.browser_status(flow["token"]), "declined")


class PanelMarkupTests(TestCase):
    def setUp(self):
        set_flag("public_registration", True)

    def test_both_renderers_share_one_panel_and_one_script(self):
        for name in renderers():
            for page in ("login", "register"):
                html = self.client.get(reverse(page), {"next": "/courses/"}).content.decode()
                with self.subTest(renderer=name, page=page):
                    self.assertRegex(html, r"<div[^>]*data-telegram-auth hidden")
                    self.assertIn("frontend_v1/js/login.js", html)
                    self.assertNotIn("js/telegram-login.js", html)
                    self.assertNotIn('href="#"', html)
                    self.assertIn("data-telegram-code", html)
                    self.assertIn("Telegram orqali kirish uchun JavaScript kerak", html)
                    self.assertIn("Telefon raqamingiz so‘ralmaydi", html)
                    self.assertIn("?next=%2Fcourses%2F", html)

    def test_intro_copy_follows_the_registration_state(self):
        set_flag("public_registration", False)
        for name in renderers():
            html = self.client.get(reverse("login")).content.decode()
            with self.subTest(renderer=name):
                self.assertIn("hozircha yangi profil ochilmaydi", html)
                self.assertNotIn("yangi profil ochiladi va", html)

    def test_the_popup_script_is_gone(self):
        self.assertFalse((Path(settings.BASE_DIR) / "static/js/telegram-login.js").exists())
