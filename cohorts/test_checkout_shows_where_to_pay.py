"""To'lov sahifasi qayerga pul yuborishni aytadi.

UX auditda topilgan eng qimmat uzilish. Sahifada yozilgan edi: «To'lovni
administrator ko'rsatgan hisobga o'tkazing» — ammo hisob **hech qayerda**
ko'rsatilmasdi.

Ma'lumot bor edi: `SiteSettings.payment_card_number` va yondosh maydonlar
to'ldirilgan, Telegram boti esa ularni checkout xabarida chiqaradi
(`bot/services.begin_course_enrollment`). Ya'ni botdan kelgan mijoz to'lay
olardi, saytdan kelgani — yo'q. Bu ikki adapter orasidagi farq edi, xususiyat
yetishmasligi emas.

Shu sababli bu yerdagi asosiy tekshiruv — **parity**: bot ko'rsatadigan
raqam sahifada ham turadi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort
from courses.models import Course
from frontend.models import SiteSettings
from subscriptions.models import Plan

User = get_user_model()


class CheckoutShowsThePaymentDetailsTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.teacher = User.objects.create_user(
            username="tolov-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="tolov-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.teacher
        )
        Cohort.objects.create(
            name="Guruh", course=self.course, start_date=self.today,
            is_checkout_default=True,
        )
        Plan.objects.create(code="tolov-starter", name="Starter", price=99000, description="d")
        site = SiteSettings.load()
        site.payment_card_number = "8600 1111 2222 3333"
        site.payment_card_holder = "Azizbek Sirojiddinov"
        site.payment_provider_label = "Uzcard / Humo"
        site.payment_instruction = "To'lovni ushbu kartaga o'tkazing va chekni yuklang."
        site.save()
        self.url = reverse("cohorts:checkout", kwargs={"course_id": self.course.id})

    def test_the_card_number_is_on_the_page(self):
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertContains(response, "8600 1111 2222 3333")

    def test_the_holder_and_the_bank_are_shown_too(self):
        """Raqamning o'zi yetmaydi: o'tkazishda ism ham so'raladi."""
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertContains(response, "Azizbek Sirojiddinov")
        self.assertContains(response, "Uzcard / Humo")

    def test_the_owner_written_instruction_is_used(self):
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertContains(response, "To&#x27;lovni ushbu kartaga o&#x27;tkazing")

    def test_the_page_no_longer_points_at_nothing(self):
        """Eski matn hisobni ko'rsatmasdan «ko'rsatilgan hisob» derdi."""
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertNotContains(response, "administrator ko&#x27;rsatgan hisobga")

    def test_the_web_shows_what_the_bot_shows(self):
        """Parity: ikki yuza bir xil hisobni aytadi."""
        from bot.services import begin_course_enrollment

        plan = Plan.objects.get(code="tolov-starter")
        bot_result = begin_course_enrollment(self.student, self.course.id, plan.id)
        self.assertTrue(bot_result.ok, bot_result.message)

        self.client.force_login(self.student)
        response = self.client.get(self.url)

        self.assertContains(response, bot_result.card_number)
        self.assertContains(response, bot_result.card_holder)

    def test_nothing_is_promised_when_the_owner_left_it_empty(self):
        """Bo'sh sozlamada bo'sh quti ko'rsatilmaydi."""
        site = SiteSettings.load()
        site.payment_card_number = ""
        site.save(update_fields=["payment_card_number"])
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertNotContains(response, "Shu hisobga o&#x27;tkazing")
