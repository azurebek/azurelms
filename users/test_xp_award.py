"""XP qo'shish atomik: eskirgan nusxa boshqasining XP'sini o'chirmaydi.

Bu nuqson oltin oqim testida chiqdi. XP uch joyda `read-modify-write`
bilan yozilardi (davomat, vazifa review, quiz baholash). Bot bitta
`lms_user` nusxasini bir necha servis chaqiruvi bo'ylab uzatgani uchun
o'qituvchi bergan +25 XP quiz baholanganda **jimgina yo'qolardi**: jami
XP `25` dan `20` ga tushardi, xato ham berilmasdi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import Assignment, AssignmentSubmission, Course, Lesson, Module
from courses.submission_service import review_assignment_submission
from users.xp import award_xp

User = get_user_model()


class AwardXpTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="xp-student", email="xp-student@example.test", password="x"
        )

    def test_a_stale_instance_does_not_erase_someone_elses_award(self):
        """Asosiy da'vo. Ilgari ikkinchi yozuv birinchisini bosib ketardi."""
        stale = User.objects.get(pk=self.student.pk)  # total_xp = 0
        award_xp(User.objects.get(pk=self.student.pk), 25)  # boshqa yo'l XP berdi

        award_xp(stale, 20)  # eskirgan nusxa o'z ishini qiladi

        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 45)

    def test_the_in_memory_copy_is_refreshed(self):
        """Chaqiruvchilar obyektni keyin ham ishlatadi (xabar matni, payload)."""
        award_xp(self.student, 30)

        self.assertEqual(self.student.total_xp, 30)

    def test_a_negative_delta_subtracts(self):
        award_xp(self.student, 40)

        award_xp(self.student, -15)

        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 25)

    def test_the_balance_never_goes_below_zero(self):
        award_xp(self.student, 10)

        award_xp(self.student, -50)

        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 0)

    def test_a_zero_delta_writes_nothing(self):
        award_xp(self.student, 25)

        self.assertEqual(award_xp(self.student, 0), 25)
        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 25)


class ReviewXpIsAtomicTests(TestCase):
    """Servis darajasidagi takrorlash: review ham eskirgan nusxaga tayanmaydi."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="xp-teacher", email="xp-teacher@example.test",
            password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="xp-learner", email="xp-learner@example.test", password="x"
        )
        course = Course.objects.create(
            title="XP kursi", description="d", level="beginner", instructor=self.teacher
        )
        module = Module.objects.create(course=course, title="M1", order=1)
        lesson = Lesson.objects.create(
            module=module, title="Dars 1", content="<p>x</p>", order=1, xp_reward=10
        )
        self.assignment = Assignment.objects.create(
            lesson=lesson, title="V1", description="d", max_xp=30
        )
        cohort = Cohort.objects.create(
            name="XP guruhi", course=course, start_date=timezone.now().date()
        )
        Enrollment.objects.create(
            student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment, student=self.student,
            answer_text="javob", status=AssignmentSubmission.STATUS_PENDING,
        )

    def test_review_adds_on_top_of_xp_awarded_elsewhere(self):
        # Boshqa yo'l (masalan davomat) XP berdi — review buni bilmaydi.
        award_xp(User.objects.get(pk=self.student.pk), 12)

        review_assignment_submission(
            submission=self.submission, approved=True,
            reviewer=self.teacher, awarded_xp=25,
        )

        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 37)

    def test_lowering_the_grade_only_removes_the_difference(self):
        review_assignment_submission(
            submission=self.submission, approved=True,
            reviewer=self.teacher, awarded_xp=25,
        )
        award_xp(User.objects.get(pk=self.student.pk), 12)

        review_assignment_submission(
            submission=self.submission, approved=True,
            reviewer=self.teacher, awarded_xp=10,
        )

        # 25 berilgan, 12 boshqa yo'ldan, keyin baho 10 ga tushdi: 25+12-15.
        self.assertEqual(User.objects.get(pk=self.student.pk).total_xp, 22)
