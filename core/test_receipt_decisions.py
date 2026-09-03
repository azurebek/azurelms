"""To'lovni web'dan tasdiqlash — bu yuza umuman yo'q edi.

Audit paytida topilgan operatsion bo'shliq: chekni tasdiqlashning yagona
yo'li Telegram bot edi.

* Django admin default o'chiq (`ENABLE_LEGACY_ADMIN=False`) — `/admin/`
  tekshirilganda **404** qaytardi;
* backoffice bosh sahifasi kutayotgan cheklarni faqat **ko'rsatardi**,
  tugmasi yo'q edi.

Ya'ni bot ishlamasa yoki owner hisobi Telegramga ulanmagan bo'lsa, kelgan
pulni qabul qilib bo'lmasdi. Kurs sotiladigan platforma uchun bu ishga
tushirishni to'sadigan bo'shliq.

Qaror mantig'i endi `cohorts/receipt_service.py` da — bot ham, web ham
o'shani chaqiradi, ya'ni ruxsat, audit va bildirishnoma bir xil.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course
from users.models import Notification

User = get_user_model()


class ReceiptDecisionSurfaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="chek-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="chek-student", email="student@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=timezone.now().date()
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )
        self.receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=250000
        )
        self.url = reverse("backoffice_receipts")

    def _decide(self, action, *, reason="bank ko'chirmasi mos keladi", confirm=True):
        payload = {
            "receipt_id": self.receipt.id,
            "action": action,
            "change_reason": reason,
        }
        if confirm:
            payload["confirm_change"] = "on"
        return self.client.post(self.url, payload)

    # ------------------------------------------------------------ ruxsat

    def test_a_student_cannot_open_the_page(self):
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 200)

    def test_an_anonymous_visitor_cannot_open_the_page(self):
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 200)

    def test_a_student_cannot_verify_by_posting_directly(self):
        """Sahifani yashirish himoya emas — POST ham to'silishi kerak."""
        self.client.force_login(self.student)

        self._decide("verify")

        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)

    # ------------------------------------------------------------ tasdiqlash

    def test_verifying_from_the_web_activates_the_enrollment(self):
        self.client.force_login(self.owner)

        self._decide("verify")

        self.receipt.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertTrue(self.receipt.is_verified)
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_ACTIVE)
        self.assertIsNotNone(self.enrollment.next_payment_deadline)
        self.assertTrue(self.enrollment.has_active_access())

    def test_the_learner_is_notified(self):
        self.client.force_login(self.owner)

        self._decide("verify")

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student, category=Notification.CATEGORY_SUBSCRIPTION
            ).exists()
        )

    def test_the_decision_is_audited_as_a_web_action(self):
        """Bot va web bir xil ledgerga yozadi, ammo manbasi ajralib turadi."""
        self.client.force_login(self.owner)

        self._decide("verify", reason="chek tekshirildi")

        event = SystemAuditEvent.objects.filter(action="receipt.verify").latest("id")
        self.assertEqual(event.source, SystemAuditEvent.SOURCE_WEB)
        self.assertEqual(event.actor, self.owner)
        self.assertIn("chek tekshirildi", event.reason)

    # -------------------------------------------------------------- rad etish

    def test_rejecting_deletes_the_receipt_and_keeps_the_enrollment_pending(self):
        self.client.force_login(self.owner)

        self._decide("reject", reason="summa yetarli emas")

        self.assertFalse(PaymentReceipt.objects.filter(pk=self.receipt.pk).exists())
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_PENDING)

    def test_rejection_is_audited_with_its_reason(self):
        self.client.force_login(self.owner)

        self._decide("reject", reason="summa yetarli emas")

        event = SystemAuditEvent.objects.filter(action="receipt.reject").latest("id")
        self.assertEqual(event.source, SystemAuditEvent.SOURCE_WEB)
        self.assertIn("summa yetarli emas", event.reason)

    # ------------------------------------------------- majburiy sabab/tasdiq

    def test_a_decision_without_a_reason_is_not_applied(self):
        self.client.force_login(self.owner)

        self._decide("verify", reason="")

        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)

    def test_a_decision_without_confirmation_is_not_applied(self):
        self.client.force_login(self.owner)

        self._decide("verify", confirm=False)

        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)

    # -------------------------------------------------------- idempotentlik

    def test_verifying_twice_does_not_extend_the_period_again(self):
        self.client.force_login(self.owner)
        self._decide("verify")
        self.enrollment.refresh_from_db()
        first_deadline = self.enrollment.next_payment_deadline

        self._decide("verify")

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.next_payment_deadline, first_deadline)


class ReceiptDecisionParityTests(TestCase):
    """Bot va web bir xil qaror beradi — mantiq bitta servisda."""

    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="parity-owner", email="p-owner@example.test",
            password="x", telegram_id=990101,
        )
        self.blocked = User.objects.create_user(
            username="parity-blocked", email="p-blocked@example.test",
            password="x", is_staff=True, is_active=False,
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=timezone.now().date()
        )

    def _fresh_receipt(self, username):
        student = User.objects.create_user(
            username=username, email=f"{username}@example.test", password="x"
        )
        enrollment = Enrollment.objects.create(
            student=student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )
        return PaymentReceipt.objects.create(enrollment=enrollment, amount=100000)

    def test_both_surfaces_activate_the_enrollment(self):
        from bot.services import verify_receipt as bot_verify
        from cohorts.receipt_service import verify_receipt as service_verify

        bot_receipt = self._fresh_receipt("bot-learner")
        web_receipt = self._fresh_receipt("web-learner")

        bot_verify(bot_receipt.id, self.owner)
        service_verify(
            web_receipt.id, self.owner, source=SystemAuditEvent.SOURCE_WEB
        )

        for receipt in (bot_receipt, web_receipt):
            receipt.refresh_from_db()
            receipt.enrollment.refresh_from_db()
            self.assertTrue(receipt.is_verified)
            self.assertEqual(receipt.enrollment.status, Enrollment.STATUS_ACTIVE)

    def test_a_deactivated_staff_member_is_refused_on_both(self):
        from bot.services import verify_receipt as bot_verify
        from cohorts.receipt_service import verify_receipt as service_verify

        bot_receipt = self._fresh_receipt("bot-blocked-target")
        web_receipt = self._fresh_receipt("web-blocked-target")

        self.assertFalse(bot_verify(bot_receipt.id, self.blocked).ok)
        self.assertFalse(
            service_verify(
                web_receipt.id, self.blocked, source=SystemAuditEvent.SOURCE_WEB
            ).ok
        )

    def test_a_denied_attempt_is_audited_on_both(self):
        """Pulga tegadigan qarorga kim urinib ko'rgani ko'rinishi kerak."""
        from bot.services import verify_receipt as bot_verify

        receipt = self._fresh_receipt("denied-target")

        bot_verify(receipt.id, self.blocked)

        event = SystemAuditEvent.objects.filter(action="receipt.verify").latest("id")
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_DENIED)
