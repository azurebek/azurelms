"""Umumiy feature flag registri (A2).

Ilgari yagona flag `AISettings.ai_remote_calls_enabled` edi — qattiq yozilgan
bitta maydon. Reja esa har capability uchun flag/kill switch talab qiladi
(`05-launch-ops.md` §2).

Registr **kodda** e'lon qilinadi, DB esa faqat o'zgartirilgan qiymatni saqlaydi.
Sabab: kodda e'lon qilingan flag topiladigan bo'ladi, har biriga hujjatlangan
default va izoh biriktiriladi, va registrdan olib tashlangan flagning eski
DB qatori jim ta'sir qilib qolmaydi.
"""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.flags import (
    FLAG_REGISTRY,
    UnknownFlag,
    flag_by_slug,
    flag_enabled,
    set_flag,
)


class FlagRegistryTests(TestCase):
    def test_registry_is_not_empty_and_slugs_are_unique(self):
        slugs = [flag.slug for flag in FLAG_REGISTRY]
        self.assertTrue(slugs, "bo'sh registr hech narsani boshqarmaydi")
        self.assertEqual(len(slugs), len(set(slugs)), "slug takrorlangan")

    def test_unknown_slug_raises_instead_of_silently_returning_false(self):
        """Xato yozilgan slug jim `False` qaytarsa, capability jim o'chib qoladi."""
        with self.assertRaises(UnknownFlag):
            flag_enabled("mavjud-emas-flag")

    def test_every_flag_documents_itself(self):
        for flag in FLAG_REGISTRY:
            self.assertTrue(flag.label, f"{flag.slug}: yorliq yo'q")
            self.assertTrue(flag.description, f"{flag.slug}: izoh yo'q")
            self.assertIn(flag.default, (True, False), f"{flag.slug}: default bool emas")


class FlagReadTests(TestCase):
    def setUp(self):
        self.flag = FLAG_REGISTRY[0]

    def test_declared_default_is_used_when_no_override_exists(self):
        self.assertFalse(FeatureFlag.objects.filter(slug=self.flag.slug).exists())
        self.assertEqual(flag_enabled(self.flag.slug), self.flag.default)

    def test_stored_override_wins_over_the_default(self):
        FeatureFlag.objects.create(slug=self.flag.slug, enabled=not self.flag.default)
        self.assertEqual(flag_enabled(self.flag.slug), not self.flag.default)

    def test_database_failure_falls_back_to_the_declared_default(self):
        """Flag o'qish yiqilsa capability e'lon qilingan holatida qolsin."""
        with patch("aicontrol.models.FeatureFlag.objects") as manager:
            manager.filter.side_effect = DatabaseError("baza yo'q")
            self.assertEqual(flag_enabled(self.flag.slug), self.flag.default)

    def test_a_row_for_a_removed_flag_is_inert(self):
        FeatureFlag.objects.create(slug="olib-tashlangan-flag", enabled=True)
        with self.assertRaises(UnknownFlag):
            flag_enabled("olib-tashlangan-flag")


class SetFlagTests(TestCase):
    def setUp(self):
        self.flag = FLAG_REGISTRY[0]

    def test_change_is_persisted_and_audited(self):
        set_flag(self.flag.slug, enabled=not self.flag.default, reason="demo oldidan yopamiz")

        self.assertEqual(flag_enabled(self.flag.slug), not self.flag.default)
        event = SystemAuditEvent.objects.filter(action="feature_flag.update").first()
        self.assertIsNotNone(event, "flag o'zgarishi auditlanmagan")
        self.assertEqual(event.before, {"enabled": self.flag.default})
        self.assertEqual(event.after, {"enabled": not self.flag.default})
        self.assertIn("demo oldidan", event.reason)

    def test_setting_the_same_value_writes_nothing(self):
        """Ledger bosilmagan tugmalar bilan to'lmasin."""
        changed = set_flag(self.flag.slug, enabled=self.flag.default, reason="o'zgarishsiz")

        self.assertFalse(changed)
        self.assertEqual(SystemAuditEvent.objects.filter(action="feature_flag.update").count(), 0)

    def test_unknown_slug_cannot_be_written(self):
        with self.assertRaises(UnknownFlag):
            set_flag("mavjud-emas-flag", enabled=True, reason="x")
        self.assertFalse(FeatureFlag.objects.filter(slug="mavjud-emas-flag").exists())

    def test_flag_definition_is_reachable_by_slug(self):
        self.assertEqual(flag_by_slug(self.flag.slug), self.flag)
        with self.assertRaises(UnknownFlag):
            flag_by_slug("mavjud-emas-flag")
