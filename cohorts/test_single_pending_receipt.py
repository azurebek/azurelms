"""A4 — bitta enrollmentda bir vaqtda bitta tasdiqlanmagan chek.

Web ham, bot ham chek yaratishdan oldin "pending chek bormi?" deb **o'qib**,
keyin **yozardi**. Orada hech qanday qulf yo'q edi, ya'ni ikki marta bosilgan
tugma yoki ketma-ket yuborilgan ikkita rasm ikkala tekshiruvdan ham o'tib
ketardi. SQLite'da `select_for_update()` no-op bo'lgani uchun qulf bilan
tuzatish lokalda umuman ishlamasdi.

Shuning uchun kafolat bazada: `is_verified=False` sharti bilan partial unique
indeks. Kod darajasidagi tekshiruv qolmoqda — u foydalanuvchiga chiroyli xabar
beradi — ammo endi u yagona himoya emas.
"""

import base64
import threading

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.test.utils import override_settings
from django.urls import reverse

from core.qa_support import skip_unless_file_backed_db
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo

from .models import Cohort, Enrollment, PaymentReceipt, PendingReceiptExists

User = get_user_model()

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

TEST_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {
                        "cohorts/checkout.html": "Checkout page",
                        "cohorts/checkout_pending.html": "Pending receipt {{ receipt.id }}",
                    },
                )
            ],
        },
    }
]


def build_receipt_file(name="receipt.png"):
    return SimpleUploadedFile(name, PNG_1X1, content_type="image/png")


class ReceiptFixtureMixin:
    def build_enrollment(self, *, username="pending-student"):
        self.student = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username=f"{username}-teacher",
            email=f"{username}-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Pending Receipt Course",
            description="A4 duplicate receipt test",
            instructor=self.teacher,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Pending Cohort",
            course=self.course,
            start_date="2026-12-01",
            is_active=True,
            is_checkout_default=True,
        )
        self.plan = Plan.objects.create(name="Pending Plan", price=100000, order=1)
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            plan=self.plan,
            status=Enrollment.STATUS_PENDING,
            # Foydalanuvchi checkoutni boshlagan holat: Telegram adapteri
            # chekni aynan shu belgiga qarab joylashtiradi (A4).
            checkout_started_at=timezone.now(),
        )

    def submit(self, name="receipt.png"):
        return create_checkout_receipt_with_promo(
            enrollment=self.enrollment,
            plan=self.plan,
            receipt_image=build_receipt_file(name),
            period_start="2026-08-16",
            period_end="2026-09-15",
        )


class DatabaseRefusesASecondPendingReceiptTests(ReceiptFixtureMixin, TestCase):
    def setUp(self):
        self.build_enrollment()

    def test_a_second_pending_receipt_is_refused(self):
        self.submit("first.png")

        with self.assertRaises(PendingReceiptExists):
            self.submit("second.png")

        self.assertEqual(PaymentReceipt.objects.filter(enrollment=self.enrollment).count(), 1)

    def test_a_verified_receipt_does_not_block_the_next_payment(self):
        """Har oylik to'lov yangi chek — cheklov faqat tasdiqlanmaganlarga."""
        first, _, _ = self.submit("first.png")
        first.is_verified = True
        first.save()

        second, _, _ = self.submit("second.png")

        self.assertNotEqual(second.pk, first.pk)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=self.enrollment).count(), 2)

    def test_another_enrollment_is_unaffected(self):
        """Cheklov enrollment bo'yicha, global emas."""
        self.submit("first.png")
        other_student = User.objects.create_user(
            username="other-pending", email="other-pending@example.com", password="x"
        )
        other_enrollment = Enrollment.objects.create(
            student=other_student,
            cohort=self.cohort,
            plan=self.plan,
            status=Enrollment.STATUS_PENDING,
        )

        create_checkout_receipt_with_promo(
            enrollment=other_enrollment,
            plan=self.plan,
            receipt_image=build_receipt_file("other.png"),
            period_start="2026-08-16",
            period_end="2026-09-15",
        )

        self.assertEqual(PaymentReceipt.objects.count(), 2)


@override_settings(TEMPLATES=TEST_TEMPLATES)
class WebAdapterShowsAFriendlyMessageTests(ReceiptFixtureMixin, TestCase):
    def setUp(self):
        self.build_enrollment(username="web-pending-student")
        self.client.force_login(self.student)

    def _post(self):
        return self.client.post(
            reverse("cohorts:checkout", args=[self.course.id]),
            {"plan_id": self.plan.id, "receipt_image": build_receipt_file()},
        )

    def test_a_second_submission_does_not_crash_and_creates_nothing(self):
        self.assertEqual(self._post().status_code, 302)
        second = self._post()

        self.assertEqual(second.status_code, 302)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=self.enrollment).count(), 1)


class BotAdapterReportsPendingReceiptTests(ReceiptFixtureMixin, TestCase):
    def setUp(self):
        self.build_enrollment(username="bot-pending-student")

    def test_the_bot_reports_the_pending_receipt_instead_of_crashing(self):
        from bot.services import submit_payment_receipt

        first = submit_payment_receipt(self.student, build_receipt_file("bot1.png"))
        second = submit_payment_receipt(self.student, build_receipt_file("bot2.png"))

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(second.code, "pending_receipt")
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=self.enrollment).count(), 1)


class ConcurrentSubmissionTests(ReceiptFixtureMixin, TransactionTestCase):
    """Asl da'vo: parallel yuborish ham bitta chek qoldiradi.

    SQLite in-memory rejimida skip bo'ladi (qulflash semantikasi boshqacha);
    CI ning PostgreSQL ishida haqiqiy indeks bilan yugiradi.
    """

    reset_sequences = True

    def setUp(self):
        skip_unless_file_backed_db(self)
        self.build_enrollment(username="race-student")

    def test_two_simultaneous_submissions_leave_exactly_one_receipt(self):
        barrier = threading.Barrier(2, timeout=15)
        outcomes = []
        lock = threading.Lock()

        def worker(index):
            try:
                barrier.wait()
                self.submit(f"race{index}.png")
                result = "created"
            except PendingReceiptExists:
                result = "refused"
            except Exception as exc:  # noqa: BLE001 — kutilmagan xato ham yozilsin
                result = f"{type(exc).__name__}: {exc}"
            finally:
                connection.close()
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(outcomes.count("created"), 1, outcomes)
        self.assertEqual(outcomes.count("refused"), 1, outcomes)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=self.enrollment).count(), 1)
