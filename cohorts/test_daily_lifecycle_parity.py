"""Kunlik obuna xizmati bitta ta'rifdan yuguradi.

Audit paytida topilgan naqsh: bu ish uchta joyda alohida yozilgan edi va
uchtasi uch xil qadamni bajarardi.

| yuza | muddatni yopadi | tarifni yoqadi | bildirishnoma |
|---|---|---|---|
| Celery beat (production'da shu yuguradi) | ha | **yo'q** | ha |
| `expire_overdue_enrollments` buyrug'i | ha | ha | **yo'q** |
| `generate_subscription_notifications` | ha | **yo'q** | ha |

Oqibati amaliy edi: davri kelgan tarifni yoqish qadami faqat buyruqqa
qo'shilgan, production esa Celery orqali yuguradi — ya'ni u yerda hech
qachon ishlamasdi. Bu "bir boshqaruv nuqtasi, ko'p adapter" qoidasining
buzilishi: adapterlar qadamlarni o'zlari sanab chiqargan edi.

Shu sababli bu yerda ikki xil tekshiruv bor: qadamlar haqiqatan
bajarilishi, **va** uchala yuza aynan shu funksiyani chaqirishi. Ikkinchisi
bo'lmasa, kelajakda yana bitta yuzaga qadam qo'shilib, boshqasida unutiladi.
"""

import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from cohorts.enrollment_service import DailyLifecycleResult, run_daily_subscription_lifecycle
from cohorts.models import Cohort, Enrollment
from cohorts.receipt_service import verify_receipt
from cohorts.tasks import run_subscription_lifecycle
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo

User = get_user_model()

#: Har bir yuza va u canonical funksiyani **qayerda** ko'radi.
#: Patch aynan ishlatilgan joyga qo'yiladi: manba modulini patch qilish
#: `from ... import ...` qilgan modulga ta'sir qilmaydi, ya'ni test yolg'on
#: yashil berardi.
SURFACES = (
    ("celery beat", "cohorts.tasks", lambda: run_subscription_lifecycle()),
    (
        "expire_overdue_enrollments",
        "cohorts.management.commands.expire_overdue_enrollments",
        lambda: call_command("expire_overdue_enrollments"),
    ),
    (
        "generate_subscription_notifications",
        "users.management.commands.generate_subscription_notifications",
        lambda: call_command("generate_subscription_notifications"),
    ),
)


class EverySurfaceRunsTheSameLifecycleTests(TestCase):
    """Shartnoma: hech bir yuzada qadamlarning o'z nusxasi bo'lmaydi."""

    def test_every_surface_delegates_to_the_canonical_service(self):
        for name, module, run in SURFACES:
            with self.subTest(surface=name):
                target = f"{module}.run_daily_subscription_lifecycle"
                with patch(target, return_value=DailyLifecycleResult(expired=0, promoted=0)) as canonical:
                    run()
                self.assertTrue(canonical.called, f"{name} o'z nusxasini yugurtiryapti")


class DailyLifecycleStepsTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="lifecycle-owner", email="owner@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=self.today
        )
        self.cheap = Plan.objects.create(
            code="lifecycle-economic", name="Economic", price=89000, description="d"
        )
        self.rich = Plan.objects.create(
            code="lifecycle-intensive", name="Intensive", price=399000, description="d"
        )

    def _student(self, username):
        return User.objects.create_user(
            username=username, email=f"{username}@example.test", password="x"
        )

    def _overdue_enrollment(self):
        return Enrollment.objects.create(
            student=self._student("kechikkan"), cohort=self.cohort, plan=self.cheap,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today - datetime.timedelta(days=30),
        )

    def _enrollment_with_a_due_but_unapplied_plan(self):
        """Davri boshlangan, ammo ustunga hali yozilmagan tarif.

        Bu holatni servis orqali to'g'ridan-to'g'ri yasab bo'lmaydi:
        tasdiqlash paytida davr allaqachon boshlangan bo'lsa, ustun darhol
        yoziladi. Shuning uchun tasdiqlashdan keyin ustun ataylab eski
        qiymatga qaytariladi — bu aynan "davr boshlanishidan oldin
        tasdiqlangan" chekning ertasiga qoladigan izi.
        """
        enrollment = Enrollment.objects.create(
            student=self._student("oldindan"), cohort=self.cohort, plan=self.cheap,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today - datetime.timedelta(days=1),
        )
        start = self.today - datetime.timedelta(days=1)
        receipt, _, _ = create_checkout_receipt_with_promo(
            enrollment=enrollment, plan=self.rich, receipt_image=None,
            period_start=start, period_end=start + datetime.timedelta(days=30),
        )
        verify_receipt(receipt.id, self.owner)
        Enrollment.objects.filter(pk=enrollment.pk).update(plan=self.cheap)
        return enrollment

    def test_the_service_expires_overdue_enrollments(self):
        enrollment = self._overdue_enrollment()

        result = run_daily_subscription_lifecycle()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.STATUS_EXPIRED)
        self.assertEqual(result.expired, 1)

    def test_the_service_activates_a_plan_whose_period_has_started(self):
        enrollment = self._enrollment_with_a_due_but_unapplied_plan()
        self.assertEqual(enrollment.plan_id, self.cheap.id)

        result = run_daily_subscription_lifecycle()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.plan_id, self.rich.id)
        self.assertEqual(result.promoted, 1)

    def test_the_service_generates_subscription_notifications(self):
        # Servis funksiyani ichkarida import qiladi, shuning uchun manba
        # modulidagi nom patch qilinadi.
        with patch(
            "users.notification_service.ensure_subscription_notifications_for_all_users"
        ) as notify:
            run_daily_subscription_lifecycle()

        self.assertTrue(notify.called)

    def test_the_celery_task_activates_the_plan_too(self):
        """Production'da aynan shu yo'l yuguradi — qadam shu yerda ham bo'lsin."""
        enrollment = self._enrollment_with_a_due_but_unapplied_plan()

        run_subscription_lifecycle()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.plan_id, self.rich.id)
