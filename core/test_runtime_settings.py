"""Operatsion sozlamalar testlari (T0).

Owner qarori (2026-09-11): operatsion qiymat kodda qotirib qo'yilmaydi. Shu
suite uch qatlamni qoplaydi va uchinchisi eng muhimi:

1. **Qiymat o'qish** — default, chegaraga qisish, buzuq qiymat, jadval yo'qligi.
2. **Model validatsiyasi** — forma orqali noto'g'ri qiymat o'tmasligi.
3. **Iste'molchi haqiqatan sozlamadan o'qiydimi** — sozlama to'g'ri bo'lib,
   kod uni chaqirmay qo'yishi mumkin, va o'shanda birinchi ikki qatlam yashil
   turgan holda owner admin panelida raqamni o'zgartiradi, hech narsa esa
   o'zgarmaydi.
"""

import datetime
import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from bot.models import BotRuntimeSettings, TelegramOutbox
from bot.runtime_settings import DeliveryPolicy, clamp, current_policy
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _backup_probe, _telegram_probe
from core.models import OperationalSettings
from core.operational_settings import Thresholds, current_thresholds
from users.models import Notification

User = get_user_model()


# ===================================================== 1) qiymat o'qish
class DeliveryPolicyResolutionTests(TestCase):
    def test_no_row_falls_back_to_code_defaults(self):
        """Yangi o'rnatishda sozlama qatori yo'q — worker to'xtamasligi kerak."""
        BotRuntimeSettings.objects.all().delete()
        policy = current_policy()
        self.assertEqual(policy, DeliveryPolicy.defaults())

    def test_saved_values_are_used(self):
        BotRuntimeSettings.objects.update_or_create(
            pk=1, defaults={"dm_batch_size": 7, "send_interval_ms": 250}
        )
        policy = current_policy()
        self.assertEqual(policy.dm_batch_size, 7)
        self.assertEqual(policy.send_interval_ms, 250)

    def test_out_of_range_value_is_clamped_on_read(self):
        """Validator faqat formani qo'riqlaydi; `update()` uni chetlab o'tadi.

        Owner sozlamani jonli dars kunida o'zgartiradi — bitta noto'g'ri raqam
        butun navbatni to'xtatib qo'ymasligi kerak.
        """
        BotRuntimeSettings.objects.update_or_create(pk=1, defaults={"dm_batch_size": 1})
        BotRuntimeSettings.objects.filter(pk=1).update(dm_batch_size=10_000)
        self.assertEqual(current_policy().dm_batch_size, 200)

    def test_max_backoff_below_base_is_corrected(self):
        BotRuntimeSettings.objects.update_or_create(pk=1, defaults={})
        BotRuntimeSettings.objects.filter(pk=1).update(
            base_backoff_seconds=600, max_backoff_seconds=60
        )
        policy = current_policy()
        self.assertGreaterEqual(policy.max_backoff_seconds, policy.base_backoff_seconds)

    def test_send_interval_is_exposed_in_seconds(self):
        policy = DeliveryPolicy.defaults()
        self.assertAlmostEqual(policy.send_interval_seconds, policy.send_interval_ms / 1000.0)


class ClampTests(SimpleTestCase):
    def test_unreadable_value_becomes_the_default(self):
        self.assertEqual(clamp("dm_batch_size", None), 25)
        self.assertEqual(clamp("dm_batch_size", "salom"), 25)

    def test_zero_is_allowed_only_where_it_is_meaningful(self):
        """`send_interval_ms=0` — oraliqsiz; `dm_batch_size=0` — ma'nosiz."""
        self.assertEqual(clamp("send_interval_ms", 0), 0)
        self.assertEqual(clamp("dm_batch_size", 0), 1)


class ThresholdResolutionTests(TestCase):
    def test_no_row_falls_back_to_defaults(self):
        OperationalSettings.objects.all().delete()
        self.assertEqual(current_thresholds(), Thresholds.defaults())

    def test_red_below_amber_is_corrected(self):
        """Teskari bo'lsa navbat AMBER bosqichini butunlay o'tkazib yuborardi."""
        OperationalSettings.objects.update_or_create(pk=1, defaults={})
        OperationalSettings.objects.filter(pk=1).update(
            queue_age_amber_minutes=120, queue_age_red_minutes=30
        )
        resolved = current_thresholds()
        self.assertGreater(resolved.queue_age_red_minutes, resolved.queue_age_amber_minutes)


# ===================================================== 2) model validatsiyasi
class ModelValidationTests(TestCase):
    def test_delivery_rejects_max_backoff_below_base(self):
        row = BotRuntimeSettings(base_backoff_seconds=600, max_backoff_seconds=60)
        with self.assertRaises(ValidationError) as ctx:
            row.full_clean()
        self.assertIn("max_backoff_seconds", ctx.exception.error_dict)

    def test_delivery_rejects_values_outside_the_safe_range(self):
        row = BotRuntimeSettings(dm_batch_size=0)
        with self.assertRaises(ValidationError) as ctx:
            row.full_clean()
        self.assertIn("dm_batch_size", ctx.exception.error_dict)

    def test_thresholds_reject_red_at_or_below_amber(self):
        row = OperationalSettings(queue_age_amber_minutes=30, queue_age_red_minutes=30)
        with self.assertRaises(ValidationError) as ctx:
            row.full_clean()
        self.assertIn("queue_age_red_minutes", ctx.exception.error_dict)


# ===================================================== 3) iste'molchilar
def _make_outbox(telegram_id):
    user = User.objects.create_user(
        username=f"rs_{telegram_id}",
        email=f"rs{telegram_id}@azurelms.test",
        password="pass-12345",
    )
    note = Notification.objects.create(recipient=user, title="X", message="y")
    return TelegramOutbox.objects.create(notification=note, telegram_id=telegram_id)


class ConsumersReadTheSettingsTests(TestCase):
    """Sozlama haqiqatan ishlatilayotganini tekshiradi."""

    def test_retry_limit_comes_from_the_policy(self):
        from bot.retry_policy import plan_retry

        policy = replace(DeliveryPolicy.defaults(), max_attempts=2)
        _, attempts, give_up, _ = plan_retry(
            error=OSError("tarmoq"), attempts=1, policy=policy
        )
        self.assertEqual(attempts, 2)
        self.assertTrue(give_up, "policy.max_attempts=2 hisobga olinmadi")

    def test_backoff_cap_comes_from_the_policy(self):
        from bot.retry_policy import plan_retry

        policy = replace(
            DeliveryPolicy.defaults(), base_backoff_seconds=5, max_backoff_seconds=6
        )
        now = timezone.now()
        _, _, _, next_at = plan_retry(
            error=OSError("tarmoq"), attempts=3, now=now, policy=policy
        )
        # Kap 6 soniya; jitter bilan ham 10 soniyadan oshmasligi kerak.
        self.assertLess((next_at - now).total_seconds(), 10)

    def test_backup_probe_uses_the_configured_staleness(self):
        """Default 7 kun bo'lsa 2 kunlik zaxira yashil; sozlama 1 bo'lsa AMBER."""
        definition = capability_by_slug("backup")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backups").mkdir()
            path = root / "backups" / "db-eski.dump"
            path.write_bytes(b"x" * 1024)
            stamp = (timezone.now() - datetime.timedelta(days=2)).timestamp()
            os.utime(path, (stamp, stamp))

            with override_settings(BASE_DIR=root):
                OperationalSettings.objects.update_or_create(
                    pk=1, defaults={"backup_stale_after_days": 7}
                )
                self.assertEqual(_backup_probe(definition).status, "green")

                OperationalSettings.objects.update_or_create(
                    pk=1, defaults={"backup_stale_after_days": 1}
                )
                self.assertEqual(_backup_probe(definition).status, "amber")

    def test_telegram_probe_uses_the_configured_queue_age(self):
        definition = capability_by_slug("telegram_outbox")
        row = _make_outbox(950)
        old = timezone.now() - datetime.timedelta(minutes=30)
        TelegramOutbox.objects.filter(pk=row.pk).update(created_at=old)

        with override_settings(TELEGRAM_BOT_TOKEN="123:real-looking-token"):
            OperationalSettings.objects.update_or_create(
                pk=1, defaults={"queue_age_amber_minutes": 15, "queue_age_red_minutes": 60}
            )
            self.assertEqual(_telegram_probe(definition).status, "amber")

            OperationalSettings.objects.update_or_create(
                pk=1, defaults={"queue_age_amber_minutes": 5, "queue_age_red_minutes": 10}
            )
            self.assertEqual(_telegram_probe(definition).status, "red")


class CycleReadsTheBatchSizeTests(TransactionTestCase):
    """`dm_batch_size` sozlamasi bir sikldagi xabar sonini cheklaydimi.

    `TransactionTestCase` ataylab: `process_outbox_once` `sync_to_async` orqali
    boshqa ulanishdan o'qiydi, oddiy `TestCase` da esa fixture tranzaksiya
    ichida qolib, o'sha ulanish uni ko'rmaydi (`database table is locked`).
    """

    def test_dm_batch_size_limits_one_cycle(self):
        import asyncio
        from unittest import mock

        from bot.outbox import process_outbox_once

        BotRuntimeSettings.objects.update_or_create(
            pk=1, defaults={"dm_batch_size": 1, "send_interval_ms": 0}
        )
        for index in range(3):
            _make_outbox(900 + index)

        class _Bot:
            async def send_message(self, *args, **kwargs):
                return mock.Mock(message_id=1)

        sent = asyncio.run(process_outbox_once(_Bot()))
        self.assertEqual(sent, 1, "dm_batch_size sozlamasi hisobga olinmadi")


# ===================================================== 4) auditlangan yuza
class RuntimeSettingsSurfaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="t0owner", email="t0owner@azurelms.test", password="pass-12345"
        )
        self.url = reverse("backoffice_runtime_settings")

    def _payload(self, form_name="delivery", **overrides):
        if form_name == "delivery":
            data = {
                "form_name": "delivery",
                "dm_batch_size": 25,
                "group_batch_size": 10,
                "poll_interval_seconds": 15,
                "lease_seconds": 120,
                "send_interval_ms": 50,
                "max_attempts": 5,
                "base_backoff_seconds": 30,
                "max_backoff_seconds": 900,
                "change_reason": "sinov",
                "confirm_change": "on",
            }
        else:
            data = {
                "form_name": "thresholds",
                "backup_stale_after_days": 7,
                "queue_age_amber_minutes": 15,
                "queue_age_red_minutes": 60,
                "change_reason": "sinov",
                "confirm_change": "on",
            }
        data.update(overrides)
        return data

    def test_owner_can_open_the_page_and_every_field_renders(self):
        """Shablon faqat mavjud bo'lishi emas, **chizilishi** kerak.

        2026-09-05 UX auditining saboqi: shablon matnini grep qiladigan test
        endi parse qilinmaydigan shablonga qarshi ham yashil qoladi. Shuning
        uchun sahifa render qilinadi va har bir maydon nomi javobda
        tekshiriladi.
        """
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operatsion sozlamalar")

        expected = [
            "dm_batch_size", "group_batch_size", "poll_interval_seconds",
            "lease_seconds", "send_interval_ms", "max_attempts",
            "base_backoff_seconds", "max_backoff_seconds",
            "backup_stale_after_days", "queue_age_amber_minutes",
            "queue_age_red_minutes",
        ]
        for name in expected:
            self.assertContains(
                response, f'name="{name}"', msg_prefix=f"{name} maydoni chizilmadi"
            )
        # Ikki forma, ikkita sabab/tasdiq juftligi va ikki `form_name`.
        self.assertContains(response, 'name="form_name"', count=2)
        self.assertContains(response, 'name="change_reason"', count=2)
        self.assertContains(response, 'name="confirm_change"', count=2)

    def test_non_owner_cannot_open_the_page(self):
        student = User.objects.create_user(
            username="t0student", email="t0student@azurelms.test", password="pass-12345"
        )
        self.client.force_login(student)
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_change_is_saved_and_audited(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, self._payload(send_interval_ms=200))

        self.assertEqual(BotRuntimeSettings.load().send_interval_ms, 200)
        event = SystemAuditEvent.objects.filter(
            action="settings.bot_delivery.update"
        ).first()
        self.assertIsNotNone(event, "audit yozuvi yozilmadi")
        self.assertEqual(event.reason, "sinov")
        self.assertIn("send_interval_ms", event.after)

    def test_reason_is_mandatory(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, self._payload(send_interval_ms=300, change_reason="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(BotRuntimeSettings.load().send_interval_ms, 300)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_confirmation_is_mandatory(self):
        self.client.force_login(self.owner)
        payload = self._payload(send_interval_ms=300)
        payload.pop("confirm_change")
        self.client.post(self.url, payload)
        self.assertNotEqual(BotRuntimeSettings.load().send_interval_ms, 300)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_no_op_save_writes_nothing(self):
        """O'zgarish bo'lmasa audit tarixiga shovqin qo'shilmaydi."""
        BotRuntimeSettings.load()
        self.client.force_login(self.owner)
        self.client.post(self.url, self._payload())
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_thresholds_form_is_independent(self):
        """Bir formani saqlash ikkinchisini yiqitmasligi kerak."""
        self.client.force_login(self.owner)
        self.client.post(self.url, self._payload("thresholds", backup_stale_after_days=3))
        self.assertEqual(OperationalSettings.load().backup_stale_after_days, 3)
        self.assertTrue(
            SystemAuditEvent.objects.filter(
                action="settings.operational_thresholds.update"
            ).exists()
        )


class AdminIsReadOnlyTests(TestCase):
    """Admin auditlanmagan yozish yo'li bo'lib qolmasligi kerak.

    `AISettingsAdmin` aynan shu xatoga ega (faqat `updated_by`), va PR #103
    review uni ko'rsatdi. Shu test o'sha xatoni bu yerda qaytarishga yo'l
    qo'ymaydi.
    """

    def test_settings_admins_do_not_allow_writes(self):
        from django.contrib import admin as dj_admin

        for model in (BotRuntimeSettings, OperationalSettings):
            site_admin = dj_admin.site._registry[model]
            editable = [
                f.name
                for f in model._meta.fields
                if f.name not in site_admin.readonly_fields
            ]
            self.assertEqual(
                editable, [], f"{model.__name__} admin'da tahrirlanadigan maydon qoldi"
            )
            self.assertFalse(site_admin.has_add_permission(None))
            self.assertFalse(site_admin.has_delete_permission(None))
