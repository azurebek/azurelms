"""A2 — private-media rad etilishi ledgerga tushishi kerak.

`05-launch-ops.md` §3 minimal audit ro'yxatida "private-media denial" bor.
Bu boshqa bandlardan farq qiladi: bu owner qarori emas, **xavfsizlik signali**.
Kimdir boshqa odamning to'lov chekiga yoki topshirig'iga tegishga urinsa, buni
bilish kerak.

Hajm masalasi ataylab hisobga olingan. Ledger append-only va hech qachon
tozalanmaydi, ya'ni cheksiz yozuv o'z-o'ziga qarshi vosita bo'lib qoladi.
Shuning uchun ikkita chegara:

1. **Faqat autentifikatsiyadan o'tgan foydalanuvchi yoziladi.** Anonim
   so'rovchi baribir aktor emas — uni yozish shovqin, ammo hisobdan
   urinayotgan odam aynan qidirilayotgan signal.
2. **Qisqa takrorlanish oynasi.** URL'larni ketma-ket sinab ko'rayotgan odam
   minglab qator emas, oynada bittadan qator qoldiradi — skaner baribir
   ko'rinadi, ammo ledgerni bosib ketmaydi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()


class PrivateMediaDenialAuditTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="pm-owner", email="pm-owner@example.com", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="pm-student", email="pm-student@example.com", password="x"
        )
        self.intruder = User.objects.create_user(
            username="pm-intruder", email="pm-intruder@example.com", password="x"
        )
        self.course = Course.objects.create(
            title="PM Course", description="A2", instructor=self.owner, level="beginner"
        )
        self.cohort = Cohort.objects.create(
            name="PM Cohort", course=self.course, start_date="2026-01-01", is_active=True
        )
        self.plan = Plan.objects.create(name="PM Plan", price=1000, order=1)
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, plan=self.plan,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.receipt = PaymentReceipt.objects.create(enrollment=self.enrollment, amount=1000)
        self.url = reverse("cohorts:receipt_file", kwargs={"receipt_id": self.receipt.id})

    def test_a_stranger_reaching_for_a_receipt_is_recorded(self):
        self.client.force_login(self.intruder)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        event = SystemAuditEvent.objects.get(action="private_media.denied")
        self.assertEqual(event.actor_label, "pm-intruder")
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_DENIED)

    def test_an_anonymous_probe_is_not_recorded(self):
        """Anonim so'rovchi aktor emas — uni yozish faqat shovqin."""
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_a_burst_from_one_account_collapses_to_one_event(self):
        """Ledger append-only: skaner uni bosib ketmasligi kerak."""
        self.client.force_login(self.intruder)

        for _ in range(5):
            self.client.get(self.url)

        self.assertEqual(SystemAuditEvent.objects.filter(action="private_media.denied").count(), 1)

    def test_a_later_attempt_after_the_window_is_recorded_again(self):
        """Skaner baribir ko'rinadi — oynada bittadan qator qoldiradi."""
        self.client.force_login(self.intruder)
        self.client.get(self.url)

        SystemAuditEvent.objects.filter(action="private_media.denied").update(
            created_at=timezone.now() - datetime.timedelta(hours=1)
        )
        self.client.get(self.url)

        self.assertEqual(SystemAuditEvent.objects.filter(action="private_media.denied").count(), 2)

    def test_the_rightful_owner_is_not_recorded(self):
        self.client.force_login(self.student)

        self.client.get(self.url)

        self.assertEqual(SystemAuditEvent.objects.filter(action="private_media.denied").count(), 0)

    def test_the_event_names_what_was_reached_for(self):
        self.client.force_login(self.intruder)

        self.client.get(self.url)

        event = SystemAuditEvent.objects.get(action="private_media.denied")
        self.assertEqual(event.target_type, "PaymentReceipt")
        self.assertEqual(event.target_id, str(self.receipt.id))
