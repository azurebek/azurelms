from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature

from aicontrol.models import SystemAuditEvent
from courses.authoring_service import (
    AuthoringConflict, course_revision, lesson_revision, move_module,
    outline_revision, save_course, save_lesson, save_module,
)
from courses.models import CohortLessonRelease, Course, Lesson, Module


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class AuthoringServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user(username="author", email="author@example.test", is_staff=True)
        cls.other = User.objects.create_user(username="other-author", email="other@example.test", is_staff=True)
        cls.owner = User.objects.create_user(username="owner-author", email="owner@example.test", is_staff=True, is_superuser=True)
        cls.student = User.objects.create_user(username="student-author", email="student@example.test")
        cls.course = Course.objects.create(title="A1", description="Kurs", instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title="B1", description="Boshqa", instructor=cls.other)
        cls.module = Module.objects.create(course=cls.course, title="Birinchi", order=4)
        cls.second_module = Module.objects.create(course=cls.course, title="Ikkinchi", order=8)
        cls.foreign_module = Module.objects.create(course=cls.foreign_course, title="Begona", order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title="Salom", content="<p>Merhaba</p>", order=3)

    def lesson_data(self, **changes):
        data = {"title": self.lesson.title, "module": self.lesson.module,
                "content": self.lesson.content, "video_url": "", "order": self.lesson.order,
                "xp_reward": self.lesson.xp_reward}
        data.update(changes)
        return data

    def course_data(self, **changes):
        from core.backoffice_forms import CourseBackofficeForm

        data = {name: self.course._meta.get_field(name).value_from_object(self.course)
                for name in CourseBackofficeForm.Meta.fields}
        data.update(changes)
        return data

    def test_create_module_appends_and_audits(self):
        module, changed = save_module(
            actor=self.teacher, course_id=self.course.pk, title="  Uchinchi  ",
            expected_revision=outline_revision(self.teacher, self.course),
        )
        self.assertTrue(changed)
        self.assertEqual((module.title, module.course_id, module.order), ("Uchinchi", self.course.pk, 9))
        event = SystemAuditEvent.objects.get(action="module.create")
        self.assertEqual(event.actor, self.teacher)
        self.assertEqual(event.after["course_id"], self.course.pk)

    def test_replayed_module_create_does_not_duplicate(self):
        revision = outline_revision(self.teacher, self.course)
        kwargs = dict(actor=self.teacher, course_id=self.course.pk, title="Yangi", expected_revision=revision)
        save_module(**kwargs)
        with self.assertRaises(AuthoringConflict):
            save_module(**kwargs)
        self.assertEqual(Module.objects.filter(course=self.course, title="Yangi").count(), 1)
        self.assertEqual(SystemAuditEvent.objects.count(), 1)

    def test_rename_noop_and_invalid_title_have_no_audit(self):
        kwargs = dict(actor=self.teacher, course_id=self.course.pk, module_id=self.module.pk,
                      expected_revision=outline_revision(self.teacher, self.course))
        _module, changed = save_module(title=self.module.title, **kwargs)
        self.assertFalse(changed)
        for title in ("  ", "a" * 201):
            with self.subTest(title_length=len(title)), self.assertRaises(ValidationError):
                save_module(title=title, **kwargs)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_foreign_module_cannot_be_renamed_with_owned_course(self):
        with self.assertRaises(Module.DoesNotExist):
            save_module(actor=self.owner, course_id=self.course.pk, module_id=self.foreign_module.pk,
                        title="Hijack", expected_revision=outline_revision(self.owner, self.course))
        self.foreign_module.refresh_from_db()
        self.assertEqual(self.foreign_module.title, "Begona")

    def test_reorder_moves_one_module_and_normalizes_tied_positions(self):
        Module.objects.filter(pk=self.second_module.pk).update(order=self.module.order)
        changed = move_module(actor=self.teacher, course_id=self.course.pk, module_id=self.second_module.pk,
                              direction="up", expected_revision=outline_revision(self.teacher, self.course))
        self.assertTrue(changed)
        self.assertEqual(list(self.course.modules.order_by("order", "pk").values_list("pk", "order")),
                         [(self.second_module.pk, 1), (self.module.pk, 2)])
        self.assertEqual(SystemAuditEvent.objects.get().action, "module.reorder")

    def test_reorder_at_boundary_is_noop_and_bad_direction_rejected(self):
        kwargs = dict(actor=self.teacher, course_id=self.course.pk, module_id=self.module.pk,
                      expected_revision=outline_revision(self.teacher, self.course))
        self.assertFalse(move_module(direction="up", **kwargs))
        with self.assertRaises(ValidationError):
            move_module(direction="delete", **kwargs)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_stale_outline_rejects_rename_after_other_editor(self):
        revision = outline_revision(self.teacher, self.course)
        Module.objects.filter(pk=self.second_module.pk).update(title="Boshqa oynada")
        with self.assertRaises(AuthoringConflict):
            save_module(actor=self.teacher, course_id=self.course.pk, module_id=self.module.pk,
                        title="Eskirgan", expected_revision=revision)
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, "Birinchi")

    def test_lesson_create_appends_without_release_or_overwriting_existing(self):
        data = {"module": self.module, "title": "Yangi dars", "content": "<p>Dars</p>"}
        lesson, changed = save_lesson(actor=self.teacher, course_id=self.course.pk, data=data,
                                      expected_revision=outline_revision(self.teacher, self.course))
        self.assertTrue(changed)
        self.assertEqual((lesson.order, lesson.xp_reward, lesson.module_id), (4, 10, self.module.pk))
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Salom")
        self.assertFalse(CohortLessonRelease.objects.exists())
        event = SystemAuditEvent.objects.get(action="lesson.create")
        self.assertNotIn("content", event.after)
        self.assertEqual(len(event.after["content_sha256"]), 64)

    def test_lesson_create_replay_and_cross_actor_snapshot_rejected(self):
        revision = outline_revision(self.teacher, self.course)
        kwargs = dict(course_id=self.course.pk, data={"module": self.module.pk, "title": "Yangi"},
                      expected_revision=revision)
        with self.assertRaises(AuthoringConflict):
            save_lesson(actor=self.owner, **kwargs)
        save_lesson(actor=self.teacher, **kwargs)
        with self.assertRaises(AuthoringConflict):
            save_lesson(actor=self.teacher, **kwargs)
        self.assertEqual(Lesson.objects.filter(title="Yangi").count(), 1)

    def test_lesson_cannot_move_to_another_course_even_for_owner(self):
        with self.assertRaises(ValidationError) as caught:
            save_lesson(actor=self.owner, course_id=self.course.pk, lesson_id=self.lesson.pk,
                        data=self.lesson_data(module=self.foreign_module),
                        expected_revision=lesson_revision(self.owner, self.lesson))
        self.assertIn("module", caught.exception.message_dict)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.module, self.module)

    def test_lesson_moves_inside_course_and_audits_content_update(self):
        lesson, changed = save_lesson(
            actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
            data=self.lesson_data(module=self.second_module.pk, content="<p>Yeni ders</p>"),
            expected_revision=lesson_revision(self.teacher, self.lesson),
        )
        self.assertTrue(changed)
        self.assertEqual(lesson.module_id, self.second_module.pk)
        event = SystemAuditEvent.objects.get(action="lesson.update")
        self.assertNotEqual(event.before["content_sha256"], event.after["content_sha256"])

    def test_lesson_full_validation_and_missing_fields_prevent_writes(self):
        invalid = [self.lesson_data(title=""), self.lesson_data(video_url="javascript:alert(1)"),
                   self.lesson_data(order=-1), self.lesson_data(xp_reward=-1), {"title": "Partial"}]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                save_lesson(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                            data=data, expected_revision=lesson_revision(self.teacher, self.lesson))
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Salom")
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_lesson_noop_preserves_audit_and_does_not_dispatch_save_signal(self):
        with patch("courses.models.Lesson.save") as save:
            _lesson, changed = save_lesson(
                actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                data=self.lesson_data(), expected_revision=lesson_revision(self.teacher, self.lesson),
            )
        self.assertFalse(changed)
        save.assert_not_called()
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_stale_lesson_content_and_missing_revision_rejected(self):
        revision = lesson_revision(self.teacher, self.lesson)
        Lesson.objects.filter(pk=self.lesson.pk).update(content="<p>Other window</p>")
        for expected in (revision, "", None):
            with self.subTest(expected=expected), self.assertRaises(AuthoringConflict):
                save_lesson(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                            data=self.lesson_data(), expected_revision=expected)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.content, "<p>Other window</p>")

    def test_inactive_nonstaff_and_anonymous_cannot_write(self):
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
        for actor in (self.teacher, self.student, AnonymousUser()):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                save_module(actor=actor, course_id=self.course.pk, title="No access", expected_revision="")
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_revoked_staff_membership_is_checked_fresh(self):
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=False)
        with self.assertRaises(PermissionDenied):
            save_lesson(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                        data=self.lesson_data(), expected_revision=lesson_revision(self.teacher, self.lesson))

    def test_foreign_course_is_not_found_and_reassigned_scope_is_checked_fresh(self):
        with self.assertRaises(Course.DoesNotExist):
            save_module(actor=self.teacher, course_id=self.foreign_course.pk, title="No access", expected_revision="")
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        with self.assertRaises(Course.DoesNotExist):
            save_lesson(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                        data=self.lesson_data(), expected_revision=lesson_revision(self.teacher, self.lesson))

    def test_audit_failure_rolls_back_lesson_and_module_writes(self):
        with patch("courses.authoring_service.record_audit_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                save_lesson(actor=self.teacher, course_id=self.course.pk, lesson_id=self.lesson.pk,
                            data=self.lesson_data(title="Must roll back"),
                            expected_revision=lesson_revision(self.teacher, self.lesson))
            with self.assertRaises(RuntimeError):
                save_module(actor=self.teacher, course_id=self.course.pk, title="Must roll back",
                            expected_revision=outline_revision(self.teacher, self.course))
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Salom")
        self.assertEqual(self.course.modules.count(), 2)

    def test_course_create_is_inactive_with_first_module_and_retry_is_safe(self):
        kwargs = dict(actor=self.teacher, data=self.course_data(title="A2", is_active=False),
                      expected_revision=course_revision(self.teacher))
        course, changed = save_course(**kwargs)
        self.assertTrue(changed)
        self.assertFalse(course.is_active)
        self.assertEqual(course.instructor, self.teacher)
        self.assertEqual(list(course.modules.values_list("title", "order")), [("1. Boshlanish", 1)])
        with self.assertRaises(AuthoringConflict):
            save_course(**kwargs)
        self.assertEqual(Course.objects.filter(title="A2").count(), 1)
        self.assertEqual(SystemAuditEvent.objects.get().action, "course.create")

    def test_course_change_and_noop_use_canonical_form(self):
        _course, changed = save_course(actor=self.teacher, course_id=self.course.pk,
                                      data=self.course_data(), expected_revision=course_revision(self.teacher, self.course))
        self.assertFalse(changed)
        course, changed = save_course(actor=self.teacher, course_id=self.course.pk,
                                     data=self.course_data(title="Updated"),
                                     expected_revision=course_revision(self.teacher, self.course))
        self.assertTrue(changed)
        self.assertEqual(course.title, "Updated")
        self.assertEqual(SystemAuditEvent.objects.get().action, "course.update")

    def test_course_cannot_assign_foreign_instructor_or_invalid_fields(self):
        for data in (self.course_data(instructor=self.other.pk), self.course_data(level="invented"),
                     self.course_data(certificate_min_attendance_percent=101)):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                save_course(actor=self.teacher, course_id=self.course.pk, data=data,
                            expected_revision=course_revision(self.teacher, self.course))
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_owner_can_assign_another_staff_but_not_student(self):
        revision = course_revision(self.owner, self.course)
        with self.assertRaises(ValidationError):
            save_course(actor=self.owner, course_id=self.course.pk,
                        data=self.course_data(instructor=self.student.pk), expected_revision=revision)
        course, changed = save_course(actor=self.owner, course_id=self.course.pk,
                                     data=self.course_data(instructor=self.other), expected_revision=revision)
        self.assertTrue(changed)
        self.assertEqual(course.instructor, self.other)

    def test_stale_course_and_new_course_cross_actor_tokens_rejected(self):
        revision = course_revision(self.teacher, self.course)
        Course.objects.filter(pk=self.course.pk).update(description="Different content")
        with self.assertRaises(AuthoringConflict):
            save_course(actor=self.teacher, course_id=self.course.pk, data=self.course_data(), expected_revision=revision)
        with self.assertRaises(AuthoringConflict):
            save_course(actor=self.owner, data=self.course_data(), expected_revision=course_revision(self.teacher))

    def test_course_create_audit_failure_rolls_back_first_module_too(self):
        count = Module.objects.count()
        with patch("courses.authoring_service.record_audit_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                save_course(actor=self.teacher, data=self.course_data(title="Rollback"),
                            expected_revision=course_revision(self.teacher))
        self.assertFalse(Course.objects.filter(title="Rollback").exists())
        self.assertEqual(Module.objects.count(), count)


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class AuthoringConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_actors_cannot_create_from_the_same_outline(self):
        """Real connections exercise the course lock on PostgreSQL CI."""
        User = get_user_model()
        teacher = User.objects.create_user(username="race-teacher", email="race-teacher@example.test", is_staff=True)
        owner = User.objects.create_user(username="race-owner", email="race-owner@example.test", is_staff=True, is_superuser=True)
        course = Course.objects.create(title="Race", description="Race", instructor=teacher)
        revisions = {actor.pk: outline_revision(actor, course) for actor in (teacher, owner)}
        start = Barrier(2)

        def create(actor_id):
            close_old_connections()
            try:
                actor = User.objects.get(pk=actor_id)
                start.wait(timeout=10)
                try:
                    save_module(actor=actor, course_id=course.pk, title="Only one",
                                expected_revision=revisions[actor_id])
                    return "saved"
                except AuthoringConflict:
                    return "stale"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(create, actor.pk) for actor in (teacher, owner)]
            results = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(results, ["saved", "stale"])
        self.assertEqual(course.modules.count(), 1)
        self.assertEqual(SystemAuditEvent.objects.filter(action="module.create").count(), 1)
