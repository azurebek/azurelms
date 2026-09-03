"""Mini App sessiyasi uchinchi adapter sifatida bir xil javob beradi (A3).

A3 dan qolgan band: *"Mini App deep action parity"*. Mini App o'z sahifalari
uchun allaqachon sinalgan (initData imzosi, login gate, frame nazorati), ammo
uning **asosiy amali** o'z sahifalarida emas: "Davom ettirish" tugmasi
platforma sahifalariga olib boradi va o'quvchi darsni, vazifani va quizni
o'sha yerda ochadi.

Ya'ni Mini App — uchinchi adapter va u ham parity shartnomasiga kirishi kerak:
`telegram_miniapp` sessiyasi web sessiyasi qila oladigan narsani qila olsin,
qila olmaydiganini qila olmasin.

Bu bo'shliq nazariy emas. Sessiyada `telegram_miniapp` bayrog'i bor va u
allaqachon middleware xulqini o'zgartiradi (`X-Frame-Options` olib
tashlanadi). Kelajakda kimdir o'sha bayroqni "ishonchli Telegram sessiyasi"
deb talqin qilib, ruxsat qarorini unga bog'lashi mumkin. Bu testlar shu
yo'lni oldindan yopadi.
"""

import json as jsonlib
import time as timelib
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bot.miniapp import compute_init_data_hash
from cohorts.models import Cohort, Enrollment
from courses.models import (
    Assignment, AssignmentSubmission, CohortLessonRelease, Course, Lesson, Module,
)

User = get_user_model()

TEST_TOKEN = "123456:TEST-TOKEN-FOR-MINIAPP"


def make_init_data(telegram_id):
    pairs = {
        "auth_date": str(int(timelib.time())),
        "query_id": "AAtest",
        "user": jsonlib.dumps({"id": telegram_id, "first_name": "Test"}),
    }
    digest = compute_init_data_hash(pairs, TEST_TOKEN)
    return urlencode({**pairs, "hash": digest})


@override_settings(TELEGRAM_BOT_TOKEN=TEST_TOKEN)
class MiniAppDeepActionParityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="mp-teacher", email="mp-teacher@example.test",
            password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="mp-student", email="mp-student@example.test",
            password="parol12345", telegram_id=660001,
        )
        self.course = Course.objects.create(
            title="Mini App kursi", description="d", level="beginner",
            instructor=self.teacher,
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        self.open_lesson = Lesson.objects.create(
            module=module, title="Ochiq dars", content="<p>a</p>", order=1, xp_reward=10
        )
        self.locked_lesson = Lesson.objects.create(
            module=module, title="Yopiq dars", content="<p>b</p>", order=2, xp_reward=10
        )
        self.locked_assignment = Assignment.objects.create(
            lesson=self.locked_lesson, title="Yopiq vazifa", description="d", max_xp=20
        )
        self.cohort = Cohort.objects.create(
            name="Mini App guruhi", course=self.course,
            start_date=timezone.now().date(),
        )
        Enrollment.objects.create(
            student=self.student, cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        # Faqat birinchi dars ochiq — bitta qator butun kursni drip'ga o'tkazadi.
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.open_lesson, is_released=True
        )

    # ---------------------------------------------------------------- sessiya

    def _login_through_miniapp(self):
        response = self.client.post(
            reverse("bot:miniapp_auth"),
            data=jsonlib.dumps({
                "init_data": make_init_data(self.student.telegram_id),
                "next": f"/courses/{self.course.id}/study/",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(self.client.session.get("telegram_miniapp"))
        return response.json()

    def _submit_url(self, lesson, assignment):
        return reverse(
            "assignment_submit",
            kwargs={
                "course_id": self.course.id,
                "lesson_id": lesson.id,
                "assignment_id": assignment.id,
            },
        )

    # ------------------------------------------------------------------ auth

    def test_the_miniapp_session_lands_on_the_requested_page(self):
        payload = self._login_through_miniapp()

        self.assertEqual(payload["redirect"], f"/courses/{self.course.id}/study/")

    def test_a_deactivated_account_gets_no_miniapp_session(self):
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("bot:miniapp_auth"),
            data=jsonlib.dumps({"init_data": make_init_data(self.student.telegram_id)}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.client.session.get("telegram_miniapp"))

    # --------------------------------------------------------- deep actionlar

    def test_an_open_lesson_opens_inside_the_miniapp_session(self):
        self._login_through_miniapp()

        response = self.client.get(
            reverse(
                "lesson_detail",
                kwargs={"course_id": self.course.id, "lesson_id": self.open_lesson.id},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_a_locked_lesson_is_refused_in_the_miniapp_session_too(self):
        """Bayroq imtiyoz emas: Telegram sessiyasi qulfni ochmaydi."""
        self._login_through_miniapp()

        response = self.client.get(
            reverse(
                "lesson_detail",
                kwargs={"course_id": self.course.id, "lesson_id": self.locked_lesson.id},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(
            f"/lesson/{self.locked_lesson.id}/", response.headers.get("Location", "")
        )

    def test_a_locked_assignment_cannot_be_submitted_from_the_miniapp_session(self):
        self._login_through_miniapp()

        self.client.post(
            self._submit_url(self.locked_lesson, self.locked_assignment),
            {"answer_text": "chetlab o'tish"},
        )

        self.assertFalse(
            AssignmentSubmission.objects.filter(
                assignment=self.locked_assignment, student=self.student
            ).exists()
        )

    # -------------------------------------------------------- parity da'vosi

    def test_the_miniapp_session_answers_exactly_like_a_web_session(self):
        """Uchinchi adapter shartnomasi: ikkala sessiya bir xil javob beradi.

        Bir xil foydalanuvchi, bir xil URL'lar — farq faqat sessiya qanday
        ochilganida. Javoblar bir-biriga teng bo'lishi kerak.
        """
        urls = [
            reverse(
                "lesson_detail",
                kwargs={"course_id": self.course.id, "lesson_id": self.open_lesson.id},
            ),
            reverse(
                "lesson_detail",
                kwargs={"course_id": self.course.id, "lesson_id": self.locked_lesson.id},
            ),
            reverse("course_study", kwargs={"course_id": self.course.id}),
            reverse("dashboard"),
        ]

        self.client.force_login(self.student)
        web_statuses = [self.client.get(url).status_code for url in urls]

        self.client.logout()
        self._login_through_miniapp()
        miniapp_statuses = [self.client.get(url).status_code for url in urls]

        self.assertEqual(miniapp_statuses, web_statuses)

    def test_the_miniapp_flag_does_not_survive_a_normal_login(self):
        """Bayroq sessiyaga bog'langan — u boshqa sessiyaga ko'chmasligi kerak."""
        self._login_through_miniapp()
        self.client.logout()

        self.client.force_login(self.student)

        self.assertFalse(self.client.session.get("telegram_miniapp"))
