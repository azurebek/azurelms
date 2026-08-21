"""Backup, email va memory probe'lari (A2).

Reja capability registrida bu uchtasini ham talab qiladi, ammo ular umuman
ro'yxatda yo'q edi — ya'ni Control Center ularni na yashil, na qizil
ko'rsatardi, shunchaki jim o'tkazib yuborardi.

Har probe **read-only**: zaxira olmaydi, xat yubormaydi, xotira yozmaydi.
Sog'liq sahifasi tekshirayotgan narsasini o'zgartirmasligi kerak.
"""

import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.utils import timezone

from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _backup_probe, _email_probe, _memory_probe


class BackupProbeTests(TestCase):
    def setUp(self):
        self.definition = capability_by_slug("backup")

    def _probe_with_backups(self, ages_in_days):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backups").mkdir()
            for age in ages_in_days:
                path = root / "backups" / f"db-{age}.sqlite3"
                path.write_bytes(b"x" * 1024)
                stamp = (timezone.now() - datetime.timedelta(days=age)).timestamp()
                import os

                os.utime(path, (stamp, stamp))
            with override_settings(BASE_DIR=root):
                return _backup_probe(self.definition)

    def test_no_backup_at_all_is_not_reported_as_healthy(self):
        with TemporaryDirectory() as tmp:
            with override_settings(BASE_DIR=Path(tmp)):
                result = _backup_probe(self.definition)
        self.assertNotEqual(result.status, "green", "zaxirasizlik yashil bo'lmasligi kerak")

    def test_a_fresh_backup_is_green(self):
        self.assertEqual(self._probe_with_backups([0]).status, "green")

    def test_a_stale_backup_is_amber_not_green(self):
        """Eski zaxira bor — ammo u tiklash uchun yetarli emas."""
        result = self._probe_with_backups([30])
        self.assertEqual(result.status, "amber")

    def test_the_newest_backup_decides(self):
        self.assertEqual(self._probe_with_backups([30, 0]).status, "green")


class EmailProbeTests(TestCase):
    def setUp(self):
        self.definition = capability_by_slug("email")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", IS_LOCAL=True
    )
    def test_console_backend_is_fine_locally(self):
        result = _email_probe(self.definition)
        self.assertEqual(result.status, "green")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", IS_LOCAL=False
    )
    def test_console_backend_in_production_is_red(self):
        """Xat jim yo'qoladi: parol tiklash va bildirishnoma yetib bormaydi."""
        result = _email_probe(self.definition)
        self.assertEqual(result.status, "red")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        IS_LOCAL=False,
    )
    def test_configured_smtp_is_green(self):
        self.assertEqual(_email_probe(self.definition).status, "green")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="",
        IS_LOCAL=False,
    )
    def test_smtp_without_a_host_is_not_green(self):
        self.assertNotEqual(_email_probe(self.definition).status, "green")


class MemoryProbeTests(TestCase):
    def setUp(self):
        self.definition = capability_by_slug("memory")

    def _fact(self, *, embedded):
        from django.contrib.auth import get_user_model
        from messenger.models import AIMemoryFact

        user = get_user_model().objects.create_user(
            username=f"m{AIMemoryFact.objects.count()}",
            email=f"m{AIMemoryFact.objects.count()}@example.com",
            password="testpass123",
        )
        return AIMemoryFact.objects.create(
            user=user,
            category=AIMemoryFact.CATEGORY_PREFERENCE,
            key="k",
            value="v",
            status=AIMemoryFact.STATUS_ACTIVE,
            embedding=[0.1, 0.2] if embedded else [],
            embedding_dim=2 if embedded else 0,
        )

    def test_no_memories_is_green(self):
        """Xotira bo'sh bo'lishi nosozlik emas."""
        self.assertEqual(_memory_probe(self.definition).status, "green")

    def test_fully_embedded_memories_are_green(self):
        self._fact(embedded=True)
        self.assertEqual(_memory_probe(self.definition).status, "green")

    def test_mostly_unembedded_memories_are_amber(self):
        """Embedding'siz fakt semantik qidiruvda jim ko'rinmay qoladi."""
        for _ in range(4):
            self._fact(embedded=False)
        self._fact(embedded=True)

        result = _memory_probe(self.definition)
        self.assertEqual(result.status, "amber")
