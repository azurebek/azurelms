"""Bounded lesson authoring preserves learner work and shared writer ordering."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from copy import deepcopy
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from courses.authoring_service import (
    AuthoringConflict, PracticeInUse, PracticeUnavailable, PracticeUnsupported,
    assignment_revision, lesson_quiz_revision, save_assignment, save_lesson_quiz,
    validate_assignment_data, validate_lesson_quiz_data,
)
from courses.models import (
    Assignment, AssignmentSubmission, Choice, Course, Exam, ExamAttempt, ExamSection,
    Lesson, Module, Question, Quiz, QuizAnswer, QuizAttempt, StudentAnswer,
)
from courses.submission_service import grade_quiz, submit_assignment


class PracticeFixture:
    def setUp(self):
        user = get_user_model()
        self.teacher = user.objects.create_user(username="practice-writer", email="writer@example.test", is_staff=True)
        self.other = user.objects.create_user(username="practice-other", email="other@example.test", is_staff=True)
        self.owner = user.objects.create_user(username="practice-owner", email="owner@example.test", is_superuser=True, is_staff=True)
        self.student = user.objects.create_user(username="practice-learner", email="learner@example.test")
        self.course = Course.objects.create(title="A1", instructor=self.teacher)
        self.module = Module.objects.create(course=self.course, title="Module")
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson", content="<p>Lesson</p>")
        self.foreign_course = Course.objects.create(title="Other", instructor=self.other)
        self.foreign_module = Module.objects.create(course=self.foreign_course, title="Other")
        self.foreign_lesson = Lesson.objects.create(module=self.foreign_module, title="Other")
        self.assignment = Assignment.objects.create(lesson=self.lesson, title="Speak", description="<p>Introduce yourself.</p>", max_xp=50)
        self.quiz = Quiz.objects.create(lesson=self.lesson, title="Words", xp_reward=20)
        self.question = Question.objects.create(quiz=self.quiz, text="<p>Hello?</p>")
        self.correct = Choice.objects.create(question=self.question, text="Merhaba", is_correct=True)
        self.wrong = Choice.objects.create(question=self.question, text="Güle güle", is_correct=False)
        cohort = Cohort.objects.create(course=self.course, name="Cohort", start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=cohort, status="active")
        FeatureFlag.objects.create(slug="backoffice_practice_authoring", enabled=True)

    def assignment_data(self, **changes):
        data = {"title": "Speak", "description": "<p>Introduce yourself.</p>", "max_xp": 50}
        data.update(changes)
        return data

    def questions(self):
        return [{"id": self.question.pk, "text": "<p>Hello?</p>", "choices": [
            {"id": self.correct.pk, "text": "Merhaba", "is_correct": True},
            {"id": self.wrong.pk, "text": "Güle güle", "is_correct": False},
        ]}]

    def write_assignment(self, *, actor=None, token=None, **changes):
        actor = actor or self.teacher
        return save_assignment(actor=actor, course_id=self.course.pk, lesson_id=self.lesson.pk,
                               assignment_id=self.assignment.pk, data=self.assignment_data(**changes),
                               expected_revision=token if token is not None else assignment_revision(actor, self.lesson, self.assignment))

    def write_quiz(self, *, actor=None, token=None, questions=None, **changes):
        actor = actor or self.teacher
        data = {"title": "Words", "xp_reward": 20}
        data.update(changes)
        return save_lesson_quiz(actor=actor, course_id=self.course.pk, lesson_id=self.lesson.pk,
                                quiz_id=self.quiz.pk, data=data, questions=questions if questions is not None else self.questions(),
                                expected_revision=token if token is not None else lesson_quiz_revision(actor, self.lesson, self.quiz))


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class PracticeAuthoringTests(PracticeFixture, TestCase):
    def test_flag_off_blocks_both_writers_and_keeps_content(self):
        FeatureFlag.objects.filter(slug="backoffice_practice_authoring").update(enabled=False)
        for write in (self.write_assignment, self.write_quiz):
            with self.subTest(write=write.__name__), self.assertRaises(PracticeUnavailable):
                write(title="Denied")
        self.assertEqual(Assignment.objects.get().title, "Speak")
        self.assertEqual(Quiz.objects.get().title, "Words")
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_current_actor_scope_and_course_membership_are_required(self):
        for write in (self.write_assignment, self.write_quiz):
            for actor in (AnonymousUser(), self.student):
                with self.subTest(write=write.__name__, actor=actor), self.assertRaises(PermissionDenied):
                    write(actor=actor)
            with self.assertRaises(Course.DoesNotExist):
                write(actor=self.other)
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=False)
        for write in (self.write_assignment, self.write_quiz):
            with self.assertRaises(PermissionDenied):
                write()
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_course_revocation_and_parent_change_after_opening_editor_fail(self):
        assignment_token = assignment_revision(self.teacher, self.lesson, self.assignment)
        quiz_token = lesson_quiz_revision(self.teacher, self.lesson, self.quiz)
        next_module = Module.objects.create(course=self.course, title="Next")
        Lesson.objects.filter(pk=self.lesson.pk).update(module=next_module)
        with self.assertRaises(AuthoringConflict):
            self.write_assignment(token=assignment_token, title="Denied")
        with self.assertRaises(AuthoringConflict):
            self.write_quiz(token=quiz_token, title="Denied")
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        with self.assertRaises(Course.DoesNotExist):
            self.write_assignment(title="Denied")

    def test_foreign_lesson_and_record_never_move_even_for_owner(self):
        for lesson_id in (self.foreign_lesson.pk, True, "١", "1.0"):
            with self.subTest(lesson_id=lesson_id), self.assertRaises((Lesson.DoesNotExist, ValidationError)):
                save_assignment(actor=self.owner, course_id=self.course.pk, lesson_id=lesson_id,
                                assignment_id=self.assignment.pk, data=self.assignment_data(), expected_revision="")
        with self.assertRaises(Assignment.DoesNotExist):
            save_assignment(actor=self.owner, course_id=self.foreign_course.pk, lesson_id=self.foreign_lesson.pk,
                            assignment_id=self.assignment.pk, data=self.assignment_data(), expected_revision="")
        with self.assertRaises(Quiz.DoesNotExist):
            save_lesson_quiz(actor=self.owner, course_id=self.foreign_course.pk, lesson_id=self.foreign_lesson.pk,
                            quiz_id=self.quiz.pk, data={"title": "Denied", "xp_reward": 1},
                            questions=self.questions(), expected_revision="")

    def test_assignment_create_update_noop_and_replay(self):
        token = assignment_revision(self.teacher, self.lesson)
        kwargs = dict(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                      data=self.assignment_data(title="New"), expected_revision=token)
        assignment, changed = save_assignment(**kwargs)
        self.assertTrue(changed)
        self.assertEqual(assignment.lesson_id, self.lesson.pk)
        with self.assertRaises(AuthoringConflict):
            save_assignment(**kwargs)
        self.assertEqual(Assignment.objects.count(), 2)
        self.assertFalse(self.write_assignment()[1])
        self.assertTrue(self.write_assignment(max_xp=35)[1])
        self.assertEqual(list(SystemAuditEvent.objects.order_by("pk").values_list("action", flat=True)),
                         ["assignment.create", "assignment.update"])
        self.assertNotIn("description", SystemAuditEvent.objects.last().after)

    def test_assignment_rejects_stale_cross_actor_and_absent_revisions(self):
        token = assignment_revision(self.teacher, self.lesson, self.assignment)
        self.write_assignment(title="Updated")
        for invalid in (token, "", assignment_revision(self.owner, self.lesson, self.assignment)):
            with self.subTest(token=invalid), self.assertRaises(AuthoringConflict):
                self.write_assignment(token=invalid, title="Denied")
        self.assertEqual(Assignment.objects.get().title, "Updated")

    def test_assignment_validates_rich_empty_title_and_typed_xp(self):
        invalid = ({"description": "<p>&nbsp;</p>"}, {"title": " "}, {"title": "x" * 201},
                   *({"max_xp": value} for value in (True, -1, 1.5, "1.0", "١", 2147483648)))
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.write_assignment(**changes)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_all_assignment_submission_statuses_block_every_field(self):
        submission = AssignmentSubmission.objects.create(assignment=self.assignment, student=self.student, answer_text="Work")
        for status, _label in AssignmentSubmission.STATUS_CHOICES:
            AssignmentSubmission.objects.filter(pk=submission.pk).update(status=status, awarded_xp=12, teacher_feedback="Feedback")
            with self.subTest(status=status), self.assertRaises(PracticeInUse):
                self.write_assignment(title="Changed", description="<p>Changed</p>", max_xp=3)
        submission.refresh_from_db()
        self.assertEqual((submission.answer_text, submission.awarded_xp, submission.teacher_feedback), ("Work", 12, "Feedback"))
        self.assertEqual(Assignment.objects.get().max_xp, 50)

    def test_three_question_quiz_create_is_atomic_and_create_replay_rejected(self):
        rows = [{"text": f"<p>Savol {number}</p>", "choices": [
            {"text": "Ha", "is_correct": True}, {"text": "Yo‘q", "is_correct": False},
        ]} for number in range(3)]
        kwargs = dict(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                      data={"title": "Three", "xp_reward": 15}, questions=rows,
                      expected_revision=lesson_quiz_revision(self.teacher, self.lesson))
        quiz, changed = save_lesson_quiz(**kwargs)
        self.assertTrue(changed)
        self.assertEqual(quiz.questions.count(), 3)
        self.assertEqual(Choice.objects.filter(question__quiz=quiz).count(), 6)
        with self.assertRaises(AuthoringConflict):
            save_lesson_quiz(**kwargs)
        self.assertEqual(Quiz.objects.count(), 2)
        self.assertEqual(SystemAuditEvent.objects.count(), 1)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_quiz_noop_retains_ids_and_audit_is_absent(self):
        self.assertFalse(self.write_quiz()[1])
        self.assertEqual(list(self.quiz.questions.values_list("pk", flat=True)), [self.question.pk])
        self.assertEqual(list(self.question.choices.order_by("pk").values_list("pk", flat=True)), [self.correct.pk, self.wrong.pk])
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_quiz_update_keeps_existing_ids_adds_and_removes_only_unused_nodes(self):
        rows = self.questions()
        rows[0]["text"] = "<p>Changed</p>"
        rows[0]["choices"][1] = {"text": "New answer", "is_correct": False}
        rows.append({"text": "<p>New question</p>", "choices": [
            {"text": "A", "is_correct": False}, {"text": "B", "is_correct": True}]})
        self.assertTrue(self.write_quiz(questions=rows, xp_reward=30)[1])
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())
        self.assertTrue(Choice.objects.filter(pk=self.correct.pk).exists())
        self.assertFalse(Choice.objects.filter(pk=self.wrong.pk).exists())
        self.assertEqual(self.quiz.questions.count(), 2)
        self.assertEqual(SystemAuditEvent.objects.get().action, "quiz.update")

    def test_quiz_stale_choice_and_cross_actor_snapshot_cannot_overwrite(self):
        token = lesson_quiz_revision(self.teacher, self.lesson, self.quiz)
        Choice.objects.filter(pk=self.wrong.pk).update(text="External change")
        for revision in (token, "", lesson_quiz_revision(self.owner, self.lesson, self.quiz)):
            with self.subTest(revision=revision), self.assertRaises(AuthoringConflict):
                self.write_quiz(token=revision, title="Denied")

    def test_question_errors_identify_exact_question_or_choice(self):
        cases = []
        for key, value in (("text", "<p>&nbsp;</p>"), ("id", True), ("id", "١")):
            rows = self.questions()
            rows[0][key] = value
            cases.append((rows, "questions-0-" + key))
        rows = self.questions()
        rows[0]["choices"][1]["text"] = " "
        cases.append((rows, "questions-0-choices-1-text"))
        for correct_values in ((False, False), (True, True), (True, "false")):
            rows = self.questions()
            for choice, value in zip(rows[0]["choices"], correct_values):
                choice["is_correct"] = value
            cases.append((rows, "questions-0-correct"))
        cases.append(([], "questions"))
        for rows, key in cases:
            with self.subTest(key=key), self.assertRaises(ValidationError) as caught:
                self.write_quiz(questions=rows)
            self.assertIn(key, caught.exception.message_dict)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_foreign_duplicate_and_cross_question_choice_ids_rejected(self):
        foreign = Quiz.objects.create(lesson=self.foreign_lesson, title="Other")
        question = Question.objects.create(quiz=foreign, text="Foreign")
        choice = Choice.objects.create(question=question, text="A", is_correct=True)
        for value in (question.pk, True, "١"):
            rows = self.questions()
            rows[0]["id"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.write_quiz(questions=rows)
        for value in (choice.pk, self.correct.pk):
            rows = self.questions()
            rows[0]["choices"][1]["id"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.write_quiz(questions=rows)
        with self.assertRaises(ValidationError):
            self.write_quiz(questions=self.questions() * 2)
        self.assertEqual(Choice.objects.get(pk=choice.pk).text, "A")

    def test_unanswered_attempt_protects_quiz_and_all_child_values(self):
        attempt = QuizAttempt.objects.create(quiz=self.quiz, student=self.student, xp_earned=9, score=50)
        with self.assertRaises(PracticeInUse):
            self.write_quiz(title="Changed", xp_reward=1)
        self.assertEqual(Quiz.objects.get().title, "Words")
        self.assertEqual(attempt.answers.count(), 0)
        attempt.refresh_from_db()
        self.assertEqual((attempt.xp_earned, attempt.score), (9, 50))

    def test_cross_quiz_answer_reference_also_blocks_child_replacement(self):
        foreign = Quiz.objects.create(lesson=self.foreign_lesson, title="Other")
        foreign_question = Question.objects.create(quiz=foreign, text="Other")
        attempt = QuizAttempt.objects.create(quiz=foreign, student=self.student)
        answer = QuizAnswer.objects.create(attempt=attempt, question=foreign_question,
                                          selected_choice=self.correct, is_correct=True)
        with self.assertRaises(PracticeInUse):
            self.write_quiz(title="Denied")
        self.assertTrue(QuizAnswer.objects.filter(pk=answer.pk).exists())

    def test_exam_answer_reference_also_protects_legacy_child(self):
        exam = Exam.objects.create(course=self.course, title="Exam", exam_type="final", weight_percentage=100)
        attempt = ExamAttempt.objects.create(student=self.student, exam=exam)
        answer = StudentAnswer.objects.create(attempt=attempt, question=self.question, selected_choice=self.correct)
        with self.assertRaises(PracticeInUse):
            self.write_quiz(title="Denied")
        self.assertTrue(StudentAnswer.objects.filter(pk=answer.pk).exists())

    def test_unsupported_existing_question_shapes_remain_untouched(self):
        exam = Exam.objects.create(course=self.course, title="Exam", exam_type="final", weight_percentage=100)
        section = ExamSection.objects.create(exam=exam, title="Writing", section_type="writing", max_score=20)
        for changes in ({"points": 2}, {"min_word_count": 1}, {"max_word_count": 5}, {"exam_section": section}):
            Question.objects.filter(pk=self.question.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(PracticeUnsupported):
                self.write_quiz(title="Denied")
            Question.objects.filter(pk=self.question.pk).update(points=1, min_word_count=0, max_word_count=0, exam_section=None)
        Quiz.objects.filter(pk=self.quiz.pk).update(exam_section=section)
        with self.assertRaises(PracticeUnsupported):
            self.write_quiz(title="Denied")
        self.assertEqual(Quiz.objects.get(pk=self.quiz.pk).title, "Words")

    def test_unsupported_empty_and_multiple_correct_legacy_quiz_not_repaired_silently(self):
        Choice.objects.filter(pk=self.wrong.pk).update(is_correct=True)
        with self.assertRaises(PracticeUnsupported):
            self.write_quiz()
        self.question.delete()
        with self.assertRaises(PracticeUnsupported):
            self.write_quiz()

    def test_audit_failure_rolls_back_entire_assignment_and_quiz_trees(self):
        rows = self.questions()
        rows[0]["choices"][1] = {"text": "New", "is_correct": False}
        with patch("courses.authoring_service.record_audit_event", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.write_assignment(title="Rollback")
            with self.assertRaises(RuntimeError):
                self.write_quiz(title="Rollback", questions=rows)
        self.assertEqual(Assignment.objects.get().title, "Speak")
        self.assertEqual(Quiz.objects.get().title, "Words")
        self.assertTrue(Choice.objects.filter(pk=self.wrong.pk).exists())
        self.assertEqual(Choice.objects.count(), 2)

    def test_preview_validation_and_html_sanitizer_make_no_writes(self):
        rich = '<p><strong>Keep</strong><img src="x" onerror="alert(1)"></p>'
        with self.assertNumQueries(0):
            data = validate_assignment_data(self.assignment_data(description=rich))
        self.assertIn("<strong>Keep</strong>", data["description"])
        self.assertNotIn("onerror", data["description"])
        rows = deepcopy(self.questions())
        rows[0]["text"] = rich
        meta, normalized = validate_lesson_quiz_data({"title": "Words", "xp_reward": 20}, rows, self.quiz)
        self.assertEqual(meta["xp_reward"], 20)
        self.assertNotIn("onerror", normalized[0]["text"])
        self.assertFalse(QuizAttempt.objects.exists())
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_grader_refreshes_stale_cached_questions_and_reward_before_reading(self):
        stale = Quiz.objects.prefetch_related("questions__choices").get(pk=self.quiz.pk)
        rows = self.questions()
        rows[0]["choices"][0]["is_correct"] = False
        rows[0]["choices"][1]["is_correct"] = True
        self.write_quiz(questions=rows, xp_reward=70)
        result = grade_quiz(user=self.student, quiz=stale, answers={self.question.pk: self.wrong.pk})
        self.assertTrue(result.ok)
        self.assertEqual((result.score, result.xp_earned), (100, 70))


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
@skipUnlessDBFeature("has_select_for_update")
class PracticeAuthoringConcurrencyTests(PracticeFixture, TransactionTestCase):
    def run_workers(self, first, second, locked, release):
        entered = Event()

        def worker(call, signal=False):
            close_old_connections()
            try:
                if signal:
                    entered.set()
                return call()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first_result = pool.submit(worker, first)
            self.assertTrue(locked.wait(10))
            second_result = pool.submit(worker, second, True)
            try:
                self.assertTrue(entered.wait(10))
                with self.assertRaises(TimeoutError):
                    second_result.result(timeout=0.2)
            finally:
                release.set()
            return first_result.result(timeout=15), second_result.result(timeout=15)

    def submit(self, kind):
        if kind == "assignment":
            return submit_assignment(user=self.student, assignment=self.assignment, answer_text="My answer")
        return grade_quiz(user=self.student, quiz=self.quiz, answers={self.question.pk: self.correct.pk})

    def test_first_learner_write_serializes_then_blocks_authoring(self):
        from courses.access_service import check_lesson_access

        for kind in ("assignment", "quiz"):
            with self.subTest(kind=kind):
                locked, release = Event(), Event()
                write = self.write_assignment if kind == "assignment" else self.write_quiz

                def access(**kwargs):
                    result = check_lesson_access(**kwargs)
                    locked.set()
                    if not release.wait(10):
                        raise RuntimeError("release timeout")
                    return result

                def learner():
                    with patch("courses.access_service.check_lesson_access", side_effect=access):
                        return self.submit(kind).ok

                def author():
                    try:
                        write(title="Denied")
                        return "saved"
                    except PracticeInUse:
                        return "in_use"

                self.assertEqual(self.run_workers(learner, author, locked, release), (True, "in_use"))
        self.assertEqual(Assignment.objects.get().title, "Speak")
        self.assertEqual(Quiz.objects.get().title, "Words")

    def test_authoring_first_then_learner_reads_committed_content(self):
        from core.audit import record_audit_event

        for kind in ("assignment", "quiz"):
            with self.subTest(kind=kind):
                locked, release = Event(), Event()

                def audit(**kwargs):
                    locked.set()
                    if not release.wait(10):
                        raise RuntimeError("release timeout")
                    return record_audit_event(**kwargs)

                def author():
                    with patch("courses.authoring_service.record_audit_event", side_effect=audit):
                        return (self.write_assignment(title="Changed") if kind == "assignment"
                                else self.write_quiz(xp_reward=70))[1]

                def learner():
                    result = self.submit(kind)
                    self.assertTrue(result.ok)
                    return result.submission.assignment.title if kind == "assignment" else result.xp_earned

                first, second = self.run_workers(author, learner, locked, release)
                self.assertTrue(first)
                self.assertEqual(second, "Changed" if kind == "assignment" else 70)

    def test_two_actors_editing_same_snapshot_produce_one_write_one_conflict(self):
        from core.audit import record_audit_event

        for kind in ("assignment", "quiz"):
            with self.subTest(kind=kind):
                locked, release = Event(), Event()
                write = self.write_assignment if kind == "assignment" else self.write_quiz
                revision = (assignment_revision(self.owner, self.lesson, self.assignment) if kind == "assignment"
                            else lesson_quiz_revision(self.owner, self.lesson, self.quiz))

                def audit(**kwargs):
                    locked.set()
                    if not release.wait(10):
                        raise RuntimeError("release timeout")
                    return record_audit_event(**kwargs)

                def first():
                    with patch("courses.authoring_service.record_audit_event", side_effect=audit):
                        return write(title="First")[1]

                def second():
                    try:
                        write(actor=self.owner, token=revision, title="Second")
                        return "saved"
                    except AuthoringConflict:
                        return "stale"

                self.assertEqual(self.run_workers(first, second, locked, release), (True, "stale"))
        self.assertEqual(SystemAuditEvent.objects.count(), 2)
