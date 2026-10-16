"""PUB1.0b — barcha kanalda bitta registration gate.

Asosiy da'vo: `public_registration` OFF bo'lsa hech bir adapter (web, Telegram
deep-link, telefon-kontakt, Mini App) yangi `CustomUser` yaratmaydi; mavjud faol
foydalanuvchi esa kirishda va Telegramni ulashda davom etadi. Faolsizlantirilgan
hisob hech bir kanalda kira olmaydi. Kanal ro'yxatini yashirin kengaytirib
bo'lmasligi uchun production'dagi barcha yaratish joylari inventar qilinadi.
"""

import ast
import json
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from aicontrol.models import FeatureFlag
from bot.services import handle_telegram_auth_token, register_guest_via_phone
from bot.test_miniapp_parity import TEST_TOKEN, make_init_data
from core.secret_scan import tracked_files
from users.models import Notification, TelegramAuthSession
from users.registration_policy import (
    CHANNEL_MINIAPP,
    CHANNEL_RULES,
    CHANNEL_TELEGRAM_DEEPLINK,
    CHANNEL_TELEGRAM_PHONE,
    CHANNEL_WEB,
    can_create_account,
    existing_identity_may_continue,
)

User = get_user_model()
NEW_TG = 777000111
NEW_PHONE = "+998901112233"


def blind_first_telegram_lookup():
    """Birinchi `filter(telegram_id=...)` raqibni ko'rmaydi (poyga oynasi)."""
    real_filter = User.objects.filter
    seen = {"blinded": False}

    def fake_filter(*args, **kwargs):
        if "telegram_id" in kwargs and not seen["blinded"]:
            seen["blinded"] = True
            return User.objects.none()
        return real_filter(*args, **kwargs)

    return mock.patch.object(type(User.objects), "filter", side_effect=fake_filter)


def set_registration(enabled):
    FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": enabled})


class PolicyDecisionTests(TestCase):
    def test_creating_channels_follow_the_flag(self):
        for enabled in (True, False):
            set_registration(enabled)
            for channel in (CHANNEL_WEB, CHANNEL_TELEGRAM_DEEPLINK, CHANNEL_TELEGRAM_PHONE):
                with self.subTest(channel=channel, enabled=enabled):
                    decision = can_create_account(channel)
                    self.assertEqual(decision.allowed, enabled)
                    self.assertEqual(decision.code, "allowed" if enabled else "registration_closed")

    def test_miniapp_and_unknown_channels_never_create(self):
        set_registration(True)
        for channel in (CHANNEL_MINIAPP, "email_magic_link", "", None):
            with self.subTest(channel=channel):
                decision = can_create_account(channel)
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.code, "channel_not_admitted")

    def test_synthetic_email_is_admitted_only_for_telegram_channels(self):
        set_registration(True)
        self.assertFalse(can_create_account(CHANNEL_WEB).synthetic_email)
        self.assertTrue(can_create_account(CHANNEL_TELEGRAM_DEEPLINK).synthetic_email)
        self.assertTrue(can_create_account(CHANNEL_TELEGRAM_PHONE).synthetic_email)

    def test_denial_message_does_not_name_the_flag_or_channel(self):
        set_registration(False)
        message = can_create_account(CHANNEL_TELEGRAM_PHONE).message
        for leak in ("public_registration", "flag", "telegram_phone", "Telegram"):
            self.assertNotIn(leak, message)

    def test_existing_identity_rule(self):
        active = User.objects.create_user("active-one", email="a1@example.test")
        inactive = User.objects.create_user("inactive-one", email="i1@example.test", is_active=False)
        self.assertTrue(existing_identity_may_continue(active))
        self.assertFalse(existing_identity_may_continue(inactive))
        self.assertFalse(existing_identity_may_continue(None))


class WebRegistrationTests(TestCase):
    form = {
        "username": "yangi-oquvchi", "email": "yangi@example.test",
        "first_name": "Yangi", "last_name": "O'quvchi",
        "password1": "Kuchli-parol-2026", "password2": "Kuchli-parol-2026",
    }

    def test_closed_registration_creates_no_account_on_get_or_direct_post(self):
        set_registration(False)
        before = User.objects.count()
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
        response = self.client.post(reverse("register"), self.form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_open_registration_still_creates_one_account(self):
        set_registration(True)
        before = User.objects.count()
        response = self.client.post(reverse("register"), self.form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), before + 1)

    def test_existing_user_can_still_log_in_when_registration_is_closed(self):
        set_registration(False)
        User.objects.create_user("mavjud", email="mavjud@example.test", password="Kuchli-parol-2026")
        response = self.client.post(reverse("login"), {"username": "mavjud", "password": "Kuchli-parol-2026"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)


class TelegramDeepLinkTests(TestCase):
    def start_session(self):
        response = self.client.post(reverse("telegram_auth_init"))
        self.assertEqual(response.status_code, 200)
        return response.json()["token"]

    def counts(self):
        return User.objects.count(), Notification.objects.count()

    def test_closed_registration_rejects_unknown_identity_and_keeps_intent(self):
        set_registration(False)
        token = self.start_session()
        before = self.counts()
        result = handle_telegram_auth_token(f"auth_{token}", NEW_TG, "Ali", "", "ali_tg")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "registration_closed")
        self.assertEqual(self.counts(), before)
        session = TelegramAuthSession.objects.get(token=token)
        self.assertEqual(session.status, TelegramAuthSession.STATUS_PENDING)
        self.assertIsNone(session.user)

    def test_open_registration_creates_exactly_one_account(self):
        set_registration(True)
        token = self.start_session()
        users_before, notifications_before = self.counts()
        result = handle_telegram_auth_token(f"auth_{token}", NEW_TG, "Ali", "", "ali_tg")
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "register_success")
        self.assertEqual(User.objects.count(), users_before + 1)
        self.assertEqual(Notification.objects.count(), notifications_before + 1)
        self.assertEqual(User.objects.get(telegram_id=NEW_TG).email, f"tg_{NEW_TG}@telegram.local")

    def test_existing_active_user_logs_in_even_when_closed(self):
        set_registration(False)
        user = User.objects.create_user("tg-mavjud", email="tgm@example.test", telegram_id=NEW_TG)
        token = self.start_session()
        result = handle_telegram_auth_token(f"auth_{token}", NEW_TG)
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "login_success")
        response = self.client.post(reverse("telegram_auth_consume", args=[token]))
        self.assertEqual(response.json()["status"], "authenticated")
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_deactivated_identity_cannot_log_in_through_the_bot(self):
        set_registration(True)
        User.objects.create_user("tg-blok", email="tgb@example.test", telegram_id=NEW_TG, is_active=False)
        token = self.start_session()
        before = self.counts()
        result = handle_telegram_auth_token(f"auth_{token}", NEW_TG)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "identity_inactive")
        self.assertEqual(self.counts(), before)
        response = self.client.post(reverse("telegram_auth_consume", args=[token]))
        self.assertNotEqual(response.json().get("status"), "authenticated")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_identity_deactivated_after_confirmation_is_not_logged_in(self):
        set_registration(True)
        user = User.objects.create_user("tg-keyin", email="tgk@example.test", telegram_id=NEW_TG)
        token = self.start_session()
        self.assertTrue(handle_telegram_auth_token(f"auth_{token}", NEW_TG).ok)
        User.objects.filter(pk=user.pk).update(is_active=False)
        response = self.client.post(reverse("telegram_auth_consume", args=[token]))
        self.assertEqual(response.json()["status"], "not_found")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_parallel_claim_for_the_same_telegram_id_yields_one_account(self):
        set_registration(True)
        token = self.start_session()
        # Raqib so'rov akkauntni o'z transactionida commit qilgan, lekin bizning
        # birinchi tekshiruvimiz uni hali ko'rmagan — keyin real UNIQUE xatosi.
        User.objects.create_user(username="raqib", email="raqib@example.test", telegram_id=NEW_TG)
        with blind_first_telegram_lookup():
            result = handle_telegram_auth_token(f"auth_{token}", NEW_TG, "Ali", "", "ali_tg")
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.code, "login_success")
        self.assertEqual(User.objects.filter(telegram_id=NEW_TG).count(), 1)
        self.assertEqual(TelegramAuthSession.objects.get(token=token).user.username, "raqib")


class TelegramPhoneTests(TestCase):
    def register(self, telegram_id=NEW_TG, phone=NEW_PHONE):
        return register_guest_via_phone(
            telegram_id=telegram_id, telegram_username="ali_tg", phone=phone, first_name="Ali",
        )

    def test_closed_registration_rejects_new_phone(self):
        set_registration(False)
        before = (User.objects.count(), Notification.objects.count())
        result = self.register()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "registration_closed")
        self.assertEqual((User.objects.count(), Notification.objects.count()), before)

    def test_closed_registration_still_links_existing_phone_account(self):
        set_registration(False)
        user = User.objects.create_user("tel-mavjud", email="tel@example.test", phone_number=NEW_PHONE)
        result = self.register()
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "linked")
        user.refresh_from_db()
        self.assertEqual(user.telegram_id, NEW_TG)

    def test_open_registration_creates_one_account(self):
        set_registration(True)
        before = User.objects.count()
        result = self.register()
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "registered")
        self.assertEqual(User.objects.count(), before + 1)

    def test_deactivated_identities_are_not_linked_or_recreated(self):
        set_registration(True)
        blocked_tg = User.objects.create_user("tel-blok", email="tb@example.test", telegram_id=NEW_TG, is_active=False)
        self.assertEqual(self.register().code, "identity_inactive")
        blocked_phone = User.objects.create_user("tel-blok2", email="tb2@example.test",
                                                 phone_number="+998907776655", is_active=False)
        result = self.register(telegram_id=NEW_TG + 1, phone="+998907776655")
        self.assertEqual(result.code, "identity_inactive")
        blocked_phone.refresh_from_db()
        self.assertIsNone(blocked_phone.telegram_id)
        self.assertEqual(User.objects.filter(pk__in=[blocked_tg.pk, blocked_phone.pk]).count(), 2)
        self.assertEqual(User.objects.count(), 2)

    def test_parallel_claim_for_the_same_telegram_id_yields_one_account(self):
        set_registration(True)
        User.objects.create_user(username="raqib-tel", email="rt@example.test", telegram_id=NEW_TG)
        with blind_first_telegram_lookup():
            result = self.register()
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.code, "already_linked")
        self.assertEqual(User.objects.filter(telegram_id=NEW_TG).count(), 1)


class ProfileLinkTokenTests(TestCase):
    """Profil sahifasidagi Telegram ulash tokeni ham ayni identity qoidasida."""

    def test_token_issued_before_deactivation_cannot_link_telegram(self):
        from bot.services import link_user_from_start_token
        from users.test_telegram_link_claim import token_from_context

        user = User.objects.create_user("profil-blok", email="pb@example.test")
        token = token_from_context(user)
        User.objects.filter(pk=user.pk).update(is_active=False)
        result = link_user_from_start_token(token, NEW_TG, "olinmasin")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "identity_inactive")
        user.refresh_from_db()
        self.assertIsNone(user.telegram_id)

    def test_active_owner_still_links(self):
        from bot.services import link_user_from_start_token
        from users.test_telegram_link_claim import token_from_context

        user = User.objects.create_user("profil-faol", email="pf@example.test")
        result = link_user_from_start_token(token_from_context(user), NEW_TG, "faol")
        self.assertTrue(result.ok, result.message)
        user.refresh_from_db()
        self.assertEqual(user.telegram_id, NEW_TG)


@override_settings(TELEGRAM_BOT_TOKEN=TEST_TOKEN)
class MiniAppParityTests(TestCase):
    def auth(self, telegram_id):
        return self.client.post(
            reverse("bot:miniapp_auth"),
            data=json.dumps({"init_data": make_init_data(telegram_id), "next": "/"}),
            content_type="application/json",
        )

    def test_unknown_identity_never_gets_an_account(self):
        for enabled in (True, False):
            set_registration(enabled)
            with self.subTest(enabled=enabled):
                before = User.objects.count()
                self.assertEqual(self.auth(NEW_TG).status_code, 404)
                self.assertEqual(User.objects.count(), before)

    def test_existing_active_and_deactivated_identities(self):
        set_registration(False)
        User.objects.create_user("mini-faol", email="mf@example.test", telegram_id=NEW_TG)
        User.objects.create_user("mini-blok", email="mb@example.test", telegram_id=NEW_TG + 1, is_active=False)
        self.assertEqual(self.auth(NEW_TG).status_code, 200)
        self.client.logout()
        self.assertEqual(self.auth(NEW_TG + 1).status_code, 404)


class CreationCallSiteInventoryTests(TestCase):
    """Production kodida yangi foydalanuvchi yaratadigan har joy ma'lum va gated.

    Yangi `create_user(...)` qo'shilsa shu test qizil bo'ladi: kim qo'shgan
    bo'lsa, uni `registration_policy` orqali o'tkazishi va ro'yxatga yozishi kerak.
    """

    # (fayl, funksiya) → qanday himoyalangan
    KNOWN = {
        ("bot/services.py", "handle_telegram_auth_token"): "policy",
        ("bot/services.py", "register_guest_via_phone"): "policy",
        ("core/demo_seed.py", "seed_demo_data"): "local_only",
    }
    CREATE_ATTRS = {"create_user", "create_superuser"}
    MODEL_CREATE_ATTRS = {"create", "get_or_create", "update_or_create", "bulk_create"}
    USER_NAMES = {"User", "CustomUser", "UserModel"}

    def _receiver_is_user_manager(self, node):
        # `User.objects.create(...)`, `get_user_model().objects.get_or_create(...)`
        target = node.func.value
        if isinstance(target, ast.Attribute) and target.attr == "objects":
            owner = target.value
            if isinstance(owner, ast.Name) and owner.id in self.USER_NAMES:
                return True
            if isinstance(owner, ast.Call) and getattr(owner.func, "id", "") == "get_user_model":
                return True
        return False

    def creation_sites(self):
        root = Path(settings.BASE_DIR)
        sites = set()
        for name in tracked_files(root):
            if not name.endswith(".py") or "/migrations/" in name or "/management/" in name:
                continue
            base = name.rsplit("/", 1)[-1]
            if base.startswith("test") or base == "tests.py" or name.startswith(("playground/", "tests/")):
                continue
            tree = ast.parse((root / name).read_text(encoding="utf-8"))
            for func in ast.walk(tree):
                if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(func):
                    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                        continue
                    attr = node.func.attr
                    if attr in self.CREATE_ATTRS or (attr in self.MODEL_CREATE_ATTRS and self._receiver_is_user_manager(node)):
                        sites.add((name, func.name))
        return sites

    def test_every_creation_site_is_known(self):
        self.assertEqual(self.creation_sites(), set(self.KNOWN))

    def test_policy_sites_call_the_shared_decision(self):
        root = Path(settings.BASE_DIR)
        for (name, function), guard in self.KNOWN.items():
            source = (root / name).read_text(encoding="utf-8")
            tree = ast.parse(source)
            func = next(n for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function)
            body = ast.get_source_segment(source, func)
            with self.subTest(site=(name, function)):
                if guard == "policy":
                    self.assertIn("can_create_account(", body)
                else:
                    self.assertIn("seed_demo", (root / "core/management/commands/seed_demo.py").read_text(encoding="utf-8"))

    def test_web_register_view_uses_the_shared_decision(self):
        source = (Path(settings.BASE_DIR) / "users/views.py").read_text(encoding="utf-8")
        self.assertIn("can_create_account(CHANNEL_WEB", source)
        self.assertNotIn('flag_enabled("public_registration")', source)

    def test_every_channel_rule_is_explicit(self):
        self.assertEqual(set(CHANNEL_RULES), {CHANNEL_WEB, CHANNEL_TELEGRAM_DEEPLINK, CHANNEL_TELEGRAM_PHONE, CHANNEL_MINIAPP})
