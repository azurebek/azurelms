"""Exam authoring shares the first-attempt boundary; no learner state rewrites."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from courses.authoring_service import AuthoringConflict
from courses.exam_authoring_service import ExamInUse, exam_revision, save_exam
from courses.exam_service import ExamAttemptStartBlocked, start_exam_attempt
from courses.models import Course, Exam, ExamAttempt, ExamSection


class AuthoringFixture:
    def setUp(self):
        user = get_user_model()
        self.teacher = user.objects.create_user(username="exam-writer", email="writer@example.test", is_staff=True)
        self.other = user.objects.create_user(username="exam-other", email="other@example.test", is_staff=True)
        self.student = user.objects.create_user(username="exam-learner", email="learner@example.test")
        self.course = Course.objects.create(title="Course", instructor=self.teacher)
        self.exam = Exam.objects.create(course=self.course, title="Exam", exam_type="final", weight_percentage=100)
        self.section = ExamSection.objects.create(exam=self.exam, title="Section", section_type="writing", instructions="Write", max_score=20)
        cohort = Cohort.objects.create(course=self.course, name="Cohort", start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=cohort, status="active")

    def payload(self, **changes):
        data = {"title": "Exam", "course": self.course.pk, "exam_type": "final", "weight_percentage": 100,
                "passing_score": 60, "max_attempts": 2, "prerequisite_exam": "",
                "minimum_lesson_completion_percent": 0, "minimum_attendance_percent": 0,
                "section-title": "Section", "section-section_type": "writing", "section-instructions": "Write",
                "section-reading_text": "", "section-media_url": "", "section-max_score": 20,
                "section-time_limit_minutes": 30, "section-order": 0}
        data.update(changes)
        return data

    def save(self, actor=None, token=None, **changes):
        actor = actor or self.teacher
        return save_exam(actor=actor, course_id=self.course.pk, exam_id=self.exam.pk,
                         section_id=self.section.pk, data=self.payload(**changes),
                         expected_revision=token or exam_revision(actor, self.course, self.exam, self.section.pk))


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class ExamAuthoringServiceTests(AuthoringFixture, TestCase):
    def test_actor_scope_is_rechecked_from_current_database(self):
        for actor in (AnonymousUser(), self.student):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.save(actor=actor)
        with self.assertRaises(Course.DoesNotExist):
            self.save(actor=self.other)
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(SystemAuditEvent.objects.filter(action="exam.update").exists())

    def test_revoked_course_scope_and_cross_actor_revision_fail(self):
        token = exam_revision(self.other, self.course, self.exam, self.section.pk)
        with self.assertRaises(AuthoringConflict):
            self.save(token=token, title="Denied")
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        with self.assertRaises(Course.DoesNotExist):
            self.save(title="Denied")

    def test_attempt_created_after_opening_editor_blocks_save(self):
        token = exam_revision(self.teacher, self.course, self.exam, self.section.pk)
        attempt, created = start_exam_attempt(student=self.student, exam=self.exam)
        self.assertTrue(created)
        with self.assertRaises(ExamInUse):
            self.save(token=token, **{"passing_score": 90, "section-time_limit_minutes": 1})
        self.exam.refresh_from_db()
        self.section.refresh_from_db()
        self.assertEqual((self.exam.passing_score, self.section.time_limit_minutes), (60, 30))
        self.assertEqual(ExamAttempt.objects.get(pk=attempt.pk).score, 0)

    def test_first_start_rechecks_policy_on_fresh_locked_exam(self):
        prerequisite = Exam.objects.create(course=self.course, title="First", exam_type="visa", weight_percentage=0)
        # The stale object still says there is no prerequisite.
        self.save(prerequisite_exam=prerequisite.pk)
        with self.assertRaises(ExamAttemptStartBlocked) as error:
            start_exam_attempt(student=self.student, exam=self.exam)
        self.assertEqual(error.exception.code, "prerequisite_exam")
        self.assertFalse(ExamAttempt.objects.exists())


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
@skipUnlessDBFeature("has_select_for_update")
class ExamAuthoringConcurrencyTests(AuthoringFixture, TransactionTestCase):
    def test_authoring_waits_for_first_attempt_then_refuses_to_write(self):
        from courses.policy_service import check_exam_entry_policy
        locked, release, writer_entered = Event(), Event(), Event()
        calls = 0
        token = exam_revision(self.teacher, self.course, self.exam, self.section.pk)

        def policy(**kwargs):
            nonlocal calls
            calls += 1
            result = check_exam_entry_policy(**kwargs)
            if calls == 2:  # second check holds the exam row lock
                locked.set()
                if not release.wait(10):
                    raise RuntimeError("Test release timeout")
            return result

        def start():
            close_old_connections()
            try:
                with patch("courses.exam_service.check_exam_entry_policy", side_effect=policy):
                    return start_exam_attempt(student=self.student, exam=self.exam)[1]
            finally:
                close_old_connections()

        def write():
            close_old_connections()
            try:
                writer_entered.set()
                try:
                    self.save(token=token, passing_score=90)
                    return "saved"
                except ExamInUse:
                    return "in_use"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            starter = pool.submit(start)
            self.assertTrue(locked.wait(10))
            writer = pool.submit(write)
            try:
                self.assertTrue(writer_entered.wait(10))
                with self.assertRaises(TimeoutError):
                    writer.result(timeout=0.2)
            finally:
                release.set()
            self.assertTrue(starter.result(timeout=15))
            self.assertEqual(writer.result(timeout=15), "in_use")
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.passing_score, 60)
        self.assertEqual(ExamAttempt.objects.count(), 1)

    def test_first_attempt_waits_for_authoring_then_reads_new_policy(self):
        from core.audit import record_audit_event
        locked, release, reader_entered = Event(), Event(), Event()
        prerequisite = Exam.objects.create(course=self.course, title="First", exam_type="visa", weight_percentage=0)

        def audit(**kwargs):
            locked.set()
            if not release.wait(10):
                raise RuntimeError("Test release timeout")
            return record_audit_event(**kwargs)

        def write():
            close_old_connections()
            try:
                with patch("courses.exam_authoring_service.record_audit_event", side_effect=audit):
                    return self.save(prerequisite_exam=prerequisite.pk)[2]
            finally:
                close_old_connections()

        def start():
            close_old_connections()
            try:
                reader_entered.set()
                try:
                    start_exam_attempt(student=self.student, exam=self.exam)
                    return "started"
                except ExamAttemptStartBlocked as error:
                    return error.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            writer = pool.submit(write)
            self.assertTrue(locked.wait(10))
            starter = pool.submit(start)
            try:
                self.assertTrue(reader_entered.wait(10))
                with self.assertRaises(TimeoutError):
                    starter.result(timeout=0.2)
            finally:
                release.set()
            self.assertTrue(writer.result(timeout=15))
            self.assertEqual(starter.result(timeout=15), "prerequisite_exam")
        self.assertFalse(ExamAttempt.objects.exists())
