"""A3 — vazifa baholanganda o'quvchi XP ham, xabar ham olishi kerak.

Grading queue A3 ning uchinchi asosiy amali. Ikkita nuqson bor edi.

**Berilgan XP o'quvchiga yetib bormasdi.** O'qituvchi `awarded_xp` kiritadi,
u `AssignmentSubmission` qatoriga yoziladi — va o'sha yerda qoladi.
`user.total_xp` ga hech qachon qo'shilmasdi. Mavjud test faqat maydonning
saqlanganini tekshirardi, o'quvchining balansini emas, shuning uchun bo'shliq
ko'rinmagan. Bu bugun davomatda topilgan xatoning aynan o'zi: XP qatorda bor,
o'quvchida yo'q.

**O'quvchi baholanganini bilmasdi.** Davomatga kelmagan odam xabar oladi,
to'lovi tasdiqlangan odam xabar oladi, dars ochilsa xabar boradi — ammo
kutayotgan narsasi, ya'ni vazifasi tekshirilganda hech narsa yuborilmasdi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from courses.models import Assignment, AssignmentSubmission, Course, Lesson, Module
from users.models import Notification

User = get_user_model()

MAX_XP = 50


class AssignmentReviewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="rev-teacher",
            email="rev-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="rev-student",
            email="rev-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Review Course",
            description="A3 grading",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, title="Dars 1", content="<p>x</p>", order=1
        )
        self.cohort = Cohort.objects.create(
            name="Review Cohort", course=self.course, start_date="2026-01-01", is_active=True
        )
        Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE
        )
        self.assignment = Assignment.objects.create(
            lesson=self.lesson, title="Vazifa 1", description="bajaring", max_xp=MAX_XP
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Mening javobim",
            status=AssignmentSubmission.STATUS_PENDING,
        )
        self.client.force_login(self.teacher)
        self.url = reverse("teacher_grade_assignment", kwargs={"submission_id": self.submission.id})

    def _review(self, action, xp=None, feedback="izoh"):
        payload = {"teacher_feedback": feedback, "action": action}
        if xp is not None:
            payload["awarded_xp"] = str(xp)
        return self.client.post(self.url, payload)

    def _student_xp(self):
        self.student.refresh_from_db()
        return self.student.total_xp

    # --- XP o'quvchiga yetib borishi ---

    def test_approving_credits_the_student_with_the_awarded_xp(self):
        self._review("approve", xp=15)

        self.assertEqual(self._student_xp(), 15)

    def test_reviewing_twice_with_the_same_xp_does_not_double_credit(self):
        self._review("approve", xp=15)
        self._review("approve", xp=15)

        self.assertEqual(self._student_xp(), 15)

    def test_lowering_the_awarded_xp_adjusts_the_balance_down(self):
        self._review("approve", xp=15)
        self._review("approve", xp=5)

        self.assertEqual(self._student_xp(), 5)

    def test_sending_back_for_revision_takes_the_xp_away(self):
        """Tasdiq qaytarilsa, u bilan berilgan XP ham qaytadi."""
        self._review("approve", xp=15)
        self._review("revision", xp=0)

        self.assertEqual(self._student_xp(), 0)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, AssignmentSubmission.STATUS_NEEDS_REVISION)

    def test_awarded_xp_is_capped_at_the_assignment_maximum(self):
        self._review("approve", xp=MAX_XP + 100)

        self.assertEqual(self._student_xp(), MAX_XP)

    # --- o'quvchi xabardor bo'lishi ---

    def test_the_student_is_notified_when_the_work_is_approved(self):
        self._review("approve", xp=10)

        notification = Notification.objects.filter(recipient=self.student).first()
        self.assertIsNotNone(notification, "Tasdiqlangani haqida xabar bormadi")
        self.assertIn("Vazifa 1", notification.message)

    def test_the_student_is_notified_when_revision_is_requested(self):
        self._review("revision")

        notification = Notification.objects.filter(recipient=self.student).first()
        self.assertIsNotNone(notification, "Qayta ishlash so'ralgani haqida xabar bormadi")

    def test_no_new_notification_when_the_verdict_does_not_change(self):
        self._review("approve", xp=10)
        Notification.objects.all().delete()

        self._review("approve", xp=10)

        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 0)

    # --- audit ---

    def test_the_review_is_written_to_the_audit_ledger(self):
        """`05-launch-ops.md` §3 minimal audit ro'yxatida "grade/review" bor."""
        self._review("approve", xp=15)

        event = SystemAuditEvent.objects.filter(action="assignment.review").first()
        self.assertIsNotNone(event, "Baholash audit ledgeriga yozilmadi")
        self.assertEqual(event.actor_label, "rev-teacher")
        self.assertEqual(event.after["status"], AssignmentSubmission.STATUS_APPROVED)

    # --- mavjud xulq buzilmasligi ---

    def test_the_submission_row_still_records_the_verdict(self):
        self._review("approve", xp=15)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, AssignmentSubmission.STATUS_APPROVED)
        self.assertEqual(self.submission.awarded_xp, 15)
        self.assertEqual(self.submission.reviewed_by, self.teacher)
        self.assertEqual(self.submission.teacher_feedback, "izoh")
