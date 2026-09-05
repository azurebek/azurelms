"""Har bir sahifa foydalanuvchiga javob qaytaradi.

UX auditda topilgan tizimli bo'shliq: xabar bloki faqat ilova, backoffice va
o'qituvchi shellarida bor edi. `base.html` va `base_public.html` da yo'q edi
— ya'ni dars, kurs va **to'lov** sahifalaridagi har bir
`messages.success/error` jimgina yo'qolardi.

Auditdagi ikki aniq holat:

* chek yuklamasdan «Chekni yuborish» bosilsa sahifa hech narsa demay qayta
  yuklanardi — foydalanuvchi yuborildi deb o'ylaydi;
* yopiq darsni ochmoqchi bo'lgan o'quvchi **sababsiz** birinchi darsga otib
  yuborilardi.

Endi blok `base.html` da bitta joyda, ya'ni hamma sahifada. Bu test uni
o'sha joyda ushlab turadi va ikki holatning ikkalasini ham tekshiradi.
"""

import datetime
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import Assignment, Course, Lesson, Module

User = get_user_model()


# Konteynerning yopuvchi tegi — yagona satr boshidagi `</div>`; ichkilari
# ikki bo'sh joy bilan chekinadi (`templates/includes/messages.html`).
TOASTS = re.compile(r'<div class="toasts".*?^</div>', re.S | re.M)


def toast_text(response):
    """Faqat toast blokining ichi.

    Sahifada matn borligining o'zi yetmaydi: qulf sababi allaqachon yon
    ro'yxatdagi `title=` atributida turardi — foydalanuvchi uni ko'rmasdi,
    ammo `assertContains` ko'rardi. Nazorat yugurishida aynan shu sabab
    blokni o'chirganda ham test yashil qolgan edi.
    """
    block = TOASTS.search(response.content.decode(response.charset))
    return block.group(0) if block else ""


class TheLessonPageExplainsWhyItRefusedTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        teacher = User.objects.create_user(
            username="javob-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="javob-student", email="s@example.test", password="x"
        )
        course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=teacher
        )
        module = Module.objects.create(course=course, title="M", order=1)
        self.first = Lesson.objects.create(module=module, title="Birinchi", order=1)
        self.second = Lesson.objects.create(module=module, title="Ikkinchi", order=2)
        # Ikkinchi dars birinchisining vazifasi tasdiqlanmaguncha yopiq.
        Assignment.objects.create(lesson=self.first, title="Vazifa", description="d")
        cohort = Cohort.objects.create(name="G", course=course, start_date=self.today)
        Enrollment.objects.create(
            student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )
        self.course = course

    def test_a_locked_lesson_says_why_instead_of_silently_bouncing(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.second.id}),
            follow=True,
        )

        self.assertIn("tasdiqlanmaguncha", toast_text(response))

    def test_marking_a_lesson_done_confirms_it(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("lesson_completion", kwargs={"course_id": self.course.id, "lesson_id": self.first.id}),
            follow=True,
        )

        self.assertIn("belgilandi", toast_text(response))


class TheCheckoutPageExplainsWhatWentWrongTests(TestCase):
    def setUp(self):
        from subscriptions.models import Plan

        self.today = timezone.localdate()
        teacher = User.objects.create_user(
            username="chek-teacher", email="t2@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="chek-student", email="s2@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=teacher
        )
        Cohort.objects.create(
            name="Guruh", course=self.course, start_date=self.today, is_checkout_default=True
        )
        Plan.objects.create(code="javob-starter", name="Starter", price=99000, description="d")

    def test_submitting_without_a_receipt_says_so(self):
        """Auditdagi aniq holat: sahifa jimgina qayta yuklanardi."""
        from subscriptions.models import Plan

        plan = Plan.objects.get(code="javob-starter")
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("cohorts:checkout", kwargs={"course_id": self.course.id}),
            {"plan_id": plan.id},
        )

        self.assertIn("chek rasmini yuklang", toast_text(response))

    def test_submitting_without_a_plan_says_so(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("cohorts:checkout", kwargs={"course_id": self.course.id}),
            {"plan_id": ""},
        )

        self.assertIn("mavjud tariflardan birini tanlang", toast_text(response))


class EveryShellStillRendersTests(TestCase):
    """Uchala qobiq haqiqatan ochiladi va xabarni bir marta ko'rsatadi.

    Bu test matn qidirmaydi, **sahifani chizadi**. Sababi bor: ichki
    xabar bloklarini olib tashlaganda uch qobiqda ham yopuvchi
    `{% endfor %}`/`{% endif %}` qolib ketgan edi — fayl matnini
    tekshiradigan test buni sezmadi, chunki qidirilgan satr rostdan
    yo'q edi. Sahifa esa `TemplateSyntaxError` bilan yiqilardi.
    """

    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="qobiq-owner", email="o@example.test", password="x"
        )
        self.teacher = User.objects.create_user(
            username="qobiq-teacher", email="t3@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="qobiq-student", email="s3@example.test", password="x"
        )

    def test_the_learner_shell_renders(self):
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_the_teacher_shell_renders(self):
        self.client.force_login(self.teacher)

        self.assertEqual(self.client.get(reverse("teacher_dashboard")).status_code, 200)

    def test_the_backoffice_shell_renders(self):
        self.client.force_login(self.owner)

        self.assertEqual(
            self.client.get(reverse("backoffice_feature_flags")).status_code, 200
        )

    def test_the_app_shell_shows_a_message_exactly_once(self):
        """Qobiqlar `base.html` dan meros oladi.

        Ichki nusxa qolib ketsa xabar ikki marta chizilardi — shuning
        uchun bu yerda «bor» emas, «bitta» tekshiriladi.
        """
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("update_password"),
            {"old_password": "notogri", "new_password1": "a", "new_password2": "a"},
            follow=True,
        )

        html = response.content.decode(response.charset)
        self.assertEqual(html.count("Joriy parol noto&#x27;g&#x27;ri."), 1)
        self.assertIn("Joriy parol", toast_text(response))
