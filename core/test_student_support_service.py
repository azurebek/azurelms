from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from cohorts.models import Cohort, Enrollment, PaymentReceipt, enrollment_grace_limit
from core.student_support_service import build_student_support, support_student_queryset
from courses.models import Assignment, AssignmentSubmission, CohortLessonRelease, Course, Lesson, Module


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class StudentSupportServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user(username="support-teacher", email="support-teacher@example.test", is_staff=True)
        cls.other_teacher = User.objects.create_user(username="other-teacher", email="other-teacher@example.test", is_staff=True)
        cls.owner = User.objects.create_user(username="support-owner", email="support-owner@example.test", is_staff=True, is_superuser=True)
        cls.student = User.objects.create_user(username="support-student", email="support-student@example.test")
        cls.other_student = User.objects.create_user(username="other-student", email="other-student@example.test")
        cls.unenrolled = User.objects.create_user(username="unenrolled", email="unenrolled@example.test")
        cls.course = Course.objects.create(title="Turk tili A1", description="Darslar", instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title="Begona kurs", description="Darslar", instructor=cls.other_teacher)
        cls.module = Module.objects.create(course=cls.course, title="Asoslar", order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title="Salom", order=1)
        cls.next_lesson = Lesson.objects.create(module=cls.module, title="Tanishuv", order=2)
        cls.foreign_lesson = Lesson.objects.create(
            module=Module.objects.create(course=cls.foreign_course, title="Foreign"), title="Foreign lesson")
        cls.cohort = Cohort.objects.create(name="Ertalab", course=cls.course, start_date=timezone.localdate())
        cls.foreign_cohort = Cohort.objects.create(name="Boshqa guruh", course=cls.foreign_course, start_date=timezone.localdate())
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status=Enrollment.STATUS_ACTIVE)
        cls.foreign_enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.foreign_cohort, status=Enrollment.STATUS_ACTIVE)
        Enrollment.objects.create(student=cls.other_student, cohort=cls.foreign_cohort, status=Enrollment.STATUS_PENDING)

    def inspect(self, **kwargs):
        defaults = {"actor": self.teacher, "student_id": self.student.pk, "course_id": self.course.pk}
        defaults.update(kwargs)
        return build_student_support(**defaults)

    def receipt(self, enrollment=None, **changes):
        data = {"enrollment": enrollment or self.enrollment, "receipt_image": "receipts/synthetic.png", "amount": 1000}
        data.update(changes)
        return PaymentReceipt.objects.create(**data)

    def test_teacher_scope_includes_historical_learners_but_not_foreign_or_unenrolled(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.STATUS_FROZEN)
        self.assertEqual(set(support_student_queryset(self.teacher).values_list("pk", flat=True)), {self.student.pk})
        self.assertEqual(set(support_student_queryset(self.owner).values_list("pk", flat=True)),
                         {self.student.pk, self.other_student.pk, self.unenrolled.pk})

    def test_staff_and_superuser_targets_are_always_excluded(self):
        Enrollment.objects.create(student=self.other_teacher, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE)
        User = get_user_model()
        unusual_owner = User.objects.create_user(username="super-only", email="super-only@example.test", is_superuser=True)
        for target in (self.teacher, self.owner, self.other_teacher, unusual_owner):
            with self.subTest(target=target.pk), self.assertRaises(User.DoesNotExist):
                self.inspect(actor=self.owner, student_id=target.pk)

    def test_inactive_nonstaff_and_anonymous_actors_are_denied(self):
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
        for actor in (self.teacher, self.student, AnonymousUser()):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                support_student_queryset(actor)
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.inspect(actor=actor)

    def test_revoked_staff_and_reassigned_course_permissions_are_fresh(self):
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=False)
        with self.assertRaises(PermissionDenied):
            self.inspect()
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=True)
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other_teacher)
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect()

    def test_other_student_and_forged_course_lesson_parents_are_not_found(self):
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect(student_id=self.other_student.pk)
        with self.assertRaises(Course.DoesNotExist):
            self.inspect(course_id=self.foreign_course.pk)
        for actor in (self.teacher, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(Lesson.DoesNotExist):
                self.inspect(actor=actor, lesson_id=self.foreign_lesson.pk)

    def test_default_course_comes_from_latest_visible_enrollment_only(self):
        result = self.inspect(course_id=None)
        self.assertEqual(result["selected_course"].pk, self.course.pk)
        owner_result = self.inspect(actor=self.owner, course_id=None)
        self.assertEqual(owner_result["selected_course"].pk, self.foreign_course.pk)
        self.assertEqual([course.pk for course in result["course_options"]], [self.course.pk])

    def test_owner_can_select_course_for_a_learner_without_enrollment(self):
        result = self.inspect(actor=self.owner, student_id=self.unenrolled.pk, course_id=None)
        self.assertIsNone(result["selected_course"])
        self.assertEqual(result["diagnosis"]["code"], "no_course")
        self.assertEqual(result["enrollments"], [])
        self.assertEqual(result["pending_receipts"], [])
        result = self.inspect(actor=self.owner, student_id=self.unenrolled.pk)
        self.assertEqual(result["diagnosis"]["code"], "no_enrollment")
        self.assertEqual(result["selected_lesson"].pk, self.lesson.pk)

    def test_a_lesson_without_a_selected_or_default_course_is_rejected(self):
        with self.assertRaises(Lesson.DoesNotExist):
            self.inspect(actor=self.owner, student_id=self.unenrolled.pk, course_id=None, lesson_id=self.lesson.pk)

    def test_active_account_and_enrollment_get_canonical_open_result(self):
        result = self.inspect()
        self.assertEqual(result["diagnosis"]["state"], "open")
        self.assertEqual(result["diagnosis"]["code"], "open")
        self.assertEqual(result["effective_enrollment"].pk, self.enrollment.pk)
        self.assertEqual([lesson.pk for lesson in result["lessons"]], [self.lesson.pk, self.next_lesson.pk])
        self.assertTrue(result["enrollment_access_open"])
        self.assertEqual(result["enrollments"][0].support_effective_status, Enrollment.STATUS_ACTIVE)

    def test_inactive_account_takes_priority_without_reclassifying_enrollment(self):
        get_user_model().objects.filter(pk=self.student.pk).update(is_active=False)
        result = self.inspect()
        self.assertEqual(result["diagnosis"]["code"], "account_inactive")
        self.assertTrue(result["enrollment_access_open"])
        self.assertEqual(result["effective_enrollment"].pk, self.enrollment.pk)

    def test_pending_expired_frozen_and_overdue_rows_explain_the_real_access_state(self):
        cases = [(Enrollment.STATUS_PENDING, None, "pending"),
                 (Enrollment.STATUS_EXPIRED, timezone.localdate() + timedelta(days=90), "expired"),
                 (Enrollment.STATUS_FROZEN, None, "frozen"),
                 (Enrollment.STATUS_ACTIVE, enrollment_grace_limit() - timedelta(days=1), "expired")]
        for status, deadline, code in cases:
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status, next_payment_deadline=deadline)
            with self.subTest(status=status, deadline=deadline):
                result = self.inspect()
                self.assertEqual(result["diagnosis"]["code"], code)
                self.assertIsNone(result["effective_enrollment"])
                self.assertEqual(result["relevant_enrollment"].pk, self.enrollment.pk)

    def test_canonical_grace_boundary_and_missing_deadline_remain_open(self):
        for deadline in (enrollment_grace_limit(), None):
            Enrollment.objects.filter(pk=self.enrollment.pk).update(next_payment_deadline=deadline)
            with self.subTest(deadline=deadline):
                self.assertEqual(self.inspect()["diagnosis"]["code"], "open")

    def test_pending_renewal_receipt_does_not_block_active_access(self):
        receipt = self.receipt()
        result = self.inspect()
        self.assertEqual(result["diagnosis"]["code"], "open")
        self.assertEqual([item.pk for item in result["pending_receipts"]], [receipt.pk])

    def test_catalog_visibility_cohort_activity_and_future_start_are_not_extra_gates(self):
        Course.objects.filter(pk=self.course.pk).update(is_active=False)
        Cohort.objects.filter(pk=self.cohort.pk).update(is_active=False, start_date=timezone.localdate() + timedelta(days=90))
        self.assertEqual(self.inspect()["diagnosis"]["code"], "open")

    def test_newer_pending_membership_does_not_override_older_active_membership(self):
        later = Cohort.objects.create(name="Kechqurun", course=self.course, start_date=timezone.localdate())
        pending = Enrollment.objects.create(student=self.student, cohort=later, status=Enrollment.STATUS_PENDING)
        result = self.inspect()
        self.assertEqual([item.pk for item in result["enrollments"]], [pending.pk, self.enrollment.pk])
        self.assertEqual(result["effective_enrollment"].pk, self.enrollment.pk)
        self.assertEqual(result["relevant_enrollment"].pk, self.enrollment.pk)

    def test_historical_multiple_active_rows_use_joined_then_id_and_their_own_drip(self):
        later = Cohort.objects.create(name="Ikkinchi", course=self.course, start_date=timezone.localdate())
        extra = Enrollment.objects.create(student=self.student, cohort=later, status=Enrollment.STATUS_PENDING)
        # Simulate historical/imported rows, bypassing today's one-active validation.
        Enrollment.objects.filter(pk=extra.pk).update(status=Enrollment.STATUS_ACTIVE, joined_at=self.enrollment.joined_at)
        CohortLessonRelease.objects.create(cohort=later, lesson=self.lesson, is_released=False)
        result = self.inspect()
        self.assertEqual(result["effective_enrollment"].pk, extra.pk)
        self.assertTrue(result["multiple_active_enrollments"])
        self.assertEqual(result["diagnosis"]["code"], "drip")

    def test_no_lesson_is_distinct_from_a_blocked_subscription(self):
        empty = Course.objects.create(title="Bo‘sh", description="Bo‘sh", instructor=self.teacher)
        cohort = Cohort.objects.create(course=empty, name="Bo‘sh", start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE)
        result = self.inspect(course_id=empty.pk)
        self.assertEqual(result["diagnosis"]["code"], "no_lessons")
        self.assertIsNone(result["selected_lesson"])

    def test_first_explicit_release_locks_unspecified_lessons(self):
        self.assertEqual(self.inspect(lesson_id=self.next_lesson.pk)["diagnosis"]["code"], "open")
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson, is_released=True)
        self.assertEqual(self.inspect(lesson_id=self.next_lesson.pk)["diagnosis"]["code"], "drip")
        self.assertEqual(self.inspect()["diagnosis"]["code"], "open")

    def test_sequence_evidence_separates_missing_pending_and_revision_requests(self):
        missing = Assignment.objects.create(lesson=self.lesson, title="Topshirilmagan", description="Task")
        pending = Assignment.objects.create(lesson=self.lesson, title="Kutilmoqda", description="Task")
        revise = Assignment.objects.create(lesson=self.lesson, title="Qayta", description="Task")
        approved = Assignment.objects.create(lesson=self.lesson, title="Tayyor", description="Task")
        p = AssignmentSubmission.objects.create(assignment=pending, student=self.student, status="pending")
        r = AssignmentSubmission.objects.create(assignment=revise, student=self.student, status="needs_revision")
        AssignmentSubmission.objects.create(assignment=approved, student=self.student, status="approved")
        AssignmentSubmission.objects.create(assignment=missing, student=self.other_student, status="approved")
        result = self.inspect(lesson_id=self.next_lesson.pk)
        self.assertEqual(result["diagnosis"]["code"], "sequence")
        self.assertEqual(result["previous_lesson"].pk, self.lesson.pk)
        self.assertEqual([item.pk for item in result["previous_assignments_missing"]], [missing.pk])
        self.assertEqual({item.pk for item in result["previous_submissions"]}, {p.pk, r.pk})
        self.assertIn("answer_text", result["previous_submissions"][0].get_deferred_fields())

    def test_only_immediately_previous_lesson_assignments_gate_access(self):
        Assignment.objects.create(lesson=self.lesson, title="Old incomplete", description="Task")
        third = Lesson.objects.create(module=self.module, title="Third", order=3)
        self.assertEqual(self.inspect(lesson_id=self.next_lesson.pk)["diagnosis"]["code"], "sequence")
        result = self.inspect(lesson_id=third.pk)
        self.assertEqual(result["diagnosis"]["code"], "open")
        self.assertEqual(result["previous_lesson"].pk, self.next_lesson.pk)

    def test_drip_takes_priority_over_unapproved_previous_assignment(self):
        Assignment.objects.create(lesson=self.lesson, title="Task", description="Task")
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.next_lesson, is_released=False)
        result = self.inspect(lesson_id=self.next_lesson.pk)
        self.assertEqual(result["diagnosis"]["code"], "drip")
        self.assertEqual(len(result["previous_assignments_missing"]), 1)

    def test_receipts_and_enrollments_never_cross_selected_course_or_target(self):
        own = self.receipt()
        foreign = self.receipt(self.foreign_enrollment)
        another = Enrollment.objects.get(student=self.other_student, cohort=self.foreign_cohort)
        self.receipt(another)
        for actor in (self.teacher, self.owner):
            with self.subTest(actor=actor.pk):
                result = self.inspect(actor=actor)
                self.assertEqual([row.pk for row in result["enrollments"]], [self.enrollment.pk])
                self.assertEqual([row.pk for row in result["pending_receipts"]], [own.pk])
                self.assertIn("receipt_image", result["pending_receipts"][0].get_deferred_fields())
                self.assertNotIn(foreign.pk, [row.pk for row in result["pending_receipts"]])

    def test_pending_receipt_projection_is_bounded(self):
        for index in range(22):
            cohort = Cohort.objects.create(course=self.course, name=f"Historical {index}", start_date=timezone.localdate())
            enrollment = Enrollment.objects.create(student=self.student, cohort=cohort, status=Enrollment.STATUS_PENDING)
            self.receipt(enrollment)
        self.assertEqual(len(self.inspect()["pending_receipts"]), 20)

    def test_relevant_receipt_survives_course_evidence_limit(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.STATUS_PENDING)
        historical_enrollments = []
        for index in range(21):
            cohort = Cohort.objects.create(
                course=self.course, name=f"Old group {index}", start_date=timezone.localdate())
            historical_enrollments.append(Enrollment.objects.create(
                student=self.student, cohort=cohort, status=Enrollment.STATUS_PENDING))
        current_cohort = Cohort.objects.create(
            course=self.course, name="Current group", start_date=timezone.localdate())
        current = Enrollment.objects.create(
            student=self.student, cohort=current_cohort, status=Enrollment.STATUS_PENDING)
        current_receipt = self.receipt(current)
        for historical in historical_enrollments:
            self.receipt(historical)

        result = self.inspect()
        self.assertEqual(result["diagnosis"]["code"], "pending")
        self.assertEqual(result["relevant_enrollment"].pk, current.pk)
        self.assertEqual(len(result["pending_receipts"]), 20)
        self.assertNotIn(current_receipt.pk, [receipt.pk for receipt in result["pending_receipts"]])
        self.assertEqual(result["relevant_pending_receipt"].pk, current_receipt.pk)
        self.assertEqual(result["relevant_pending_receipt"].enrollment_id, current.pk)

    def test_diagnosis_performs_only_reads_and_never_invokes_learner_view(self):
        with patch("courses.views.LessonDetailView.dispatch", side_effect=AssertionError("Learner view must not run")):
            with CaptureQueriesContext(connection) as captured:
                result = self.inspect(lesson_id=self.next_lesson.pk)
                list(support_student_queryset(self.teacher))
        self.assertEqual(result["diagnosis"]["code"], "open")
        writes = [row["sql"] for row in captured if row["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))]
        self.assertEqual(writes, [])

    def test_lesson_access_decision_is_consumed_from_canonical_bundle(self):
        from courses.access_service import build_lesson_access_bundle

        with patch("core.student_support_service.build_lesson_access_bundle", wraps=build_lesson_access_bundle) as policy:
            result = self.inspect()
        policy.assert_called_once()
        self.assertEqual(policy.call_args.args[2].pk, self.enrollment.pk)
        self.assertEqual(result["diagnosis"]["code"], "open")
