"""Exam selection, first section creation and protected authoring contracts."""
from django.test import TestCase, override_settings
from django.urls import reverse

from unittest.mock import patch
from django.test import Client
from aicontrol.models import SystemAuditEvent
from courses.models import Exam, ExamAttempt, ExamSection, Lesson, Module
from core import test_backoffice_exams as fixtures


@override_settings(GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="")
class ExamAuthoringFlowTests(TestCase):
    setUp = fixtures.BackofficeExamEditorScopeTests.setUp
    _payload = fixtures.BackofficeExamEditorScopeTests._payload
    _edit_url = fixtures.BackofficeExamEditorScopeTests._edit_url

    def page_data(self, url, **changes):
        response = self.client.get(url)
        data = self._payload(editor_revision=response.context["editor_revision"], section_id="")
        if response.context["section"]:
            data["section_id"] = response.context["section"].pk
        data.update(changes)
        return data

    def test_exam_without_sections_renders_required_first_section_fields(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.earlier_exam))
        self.assertContains(response, 'name="section-title"')
        self.assertContains(response, 'name="section-max_score"')

    def test_create_first_section_save_reopen_and_replay_is_rejected(self):
        self.client.force_login(self.teacher)
        url = reverse("backoffice_exams") + f"?course={self.course.pk}&new=1"
        data = self.page_data(url, title="Yangi yakuniy")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        exam = Exam.objects.get(title="Yangi yakuniy")
        section = exam.sections.get()
        self.assertRedirects(response, self._edit_url(exam) + f"?section={section.pk}")
        self.assertEqual(SystemAuditEvent.objects.filter(action="exam.create").count(), 1)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(Exam.objects.filter(title="Yangi yakuniy").count(), 1)

    def test_existing_empty_exam_can_save_its_first_section(self):
        self.client.force_login(self.teacher)
        url = self._edit_url(self.earlier_exam)
        response = self.client.post(url, self.page_data(url, title=self.earlier_exam.title))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.earlier_exam.sections.count(), 1)

    def test_invalid_first_section_is_visible_and_exam_is_not_partially_saved(self):
        self.client.force_login(self.teacher)
        url = reverse("backoffice_exams") + f"?course={self.course.pk}&new=1"
        data = self.page_data(url, title="Saqlanmasin", **{"section-title": "", "section-max_score": "xato"})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Saqlanmasin", status_code=400)
        self.assertIn("title", response.context["section_form"].errors)
        self.assertContains(response, "xato", status_code=400)
        self.assertContains(response, 'type="text" name="section-max_score" value="xato"', status_code=400)
        self.assertFalse(Exam.objects.filter(title="Saqlanmasin").exists())
        self.assertFalse(SystemAuditEvent.objects.filter(action="exam.create").exists())

    def test_selected_second_section_changes_only_that_section(self):
        second = ExamSection.objects.create(exam=self.exam, title="Ikkinchi", section_type="writing", max_score=10)
        self.client.force_login(self.teacher)
        url = self._edit_url(self.exam) + f"?section={second.pk}"
        data = self.page_data(url, **{"section-title": "Yangilangan", "section-section_type": "writing"})
        self.assertEqual(self.client.post(url, data).status_code, 302)
        second.refresh_from_db()
        self.section.refresh_from_db()
        self.assertEqual(second.title, "Yangilangan")
        self.assertEqual(self.section.title, "Grammatika")

    def test_no_section_is_implicitly_selected(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.exam))
        self.assertIsNone(response.context["section"])
        self.assertIsNone(response.context["section_form"])
        self.assertContains(response, f"?section={self.section.pk}")

    def test_foreign_course_or_section_cannot_be_selected_or_posted(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse("backoffice_exams"), {"course": self.foreign_course.pk}).status_code, 404)
        foreign = self.foreign_exam.sections.get()
        self.assertEqual(self.client.get(self._edit_url(self.exam), {"section": foreign.pk}).status_code, 404)
        self.assertEqual(self.client.post(self._edit_url(self.exam), self._payload(section_id=foreign.pk)).status_code, 404)

    def test_stale_form_and_missing_revision_do_not_write(self):
        self.client.force_login(self.teacher)
        data = self._payload(title="Eski tahrir")
        Exam.objects.filter(pk=self.exam.pk).update(title="Yangi tahrir")
        response = self.client.post(self._edit_url(self.exam), data)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "Eski tahrir", status_code=409)
        self.assertEqual(self.client.post(self._edit_url(self.exam), self._payload(editor_revision="")).status_code, 409)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "Yangi tahrir")

    def test_active_and_completed_attempts_block_all_editor_writes(self):
        self.client.force_login(self.teacher)
        attempt = ExamAttempt.objects.create(student=self.student, exam=self.exam)
        for completed in (False, True):
            attempt.is_completed = completed
            attempt.save(update_fields=["is_completed"])
            response = self.client.get(self._edit_url(self.exam), {"section": self.section.pk})
            self.assertContains(response, "<fieldset disabled", html=False)
            response = self.client.post(self._edit_url(self.exam), self._payload(title="O‘zgarmasin"))
            self.assertEqual(response.status_code, 409)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "A1 yakuniy")
        self.assertFalse(SystemAuditEvent.objects.filter(action="exam.update").exists())

    def test_audit_failure_rolls_back_both_exam_and_section(self):
        self.client.force_login(self.teacher)
        url = reverse("backoffice_exams") + f"?course={self.course.pk}&new=1"
        data = self.page_data(url, title="Rollback")
        before = ExamSection.objects.count()
        with patch("courses.exam_authoring_service.record_audit_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.client.post(url, data)
        self.assertFalse(Exam.objects.filter(title="Rollback").exists())
        self.assertEqual(ExamSection.objects.count(), before)

    def test_noop_does_not_write_audit(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self._edit_url(self.exam), self._payload()).status_code, 302)
        self.assertFalse(SystemAuditEvent.objects.filter(action="exam.update").exists())

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        self.assertEqual(client.post(self._edit_url(self.exam), self._payload()).status_code, 403)

    def test_duplicate_selections_and_fields_are_rejected_without_writes(self):
        self.client.force_login(self.teacher)
        for name in ("course", "lesson", "section", "new", "page"):
            with self.subTest(query=name):
                self.assertEqual(self.client.get(reverse("backoffice_exams"), {name: [1, 2]}).status_code, 400)
        for name in ("course", "section_id", "editor_revision", "title", "section-title"):
            data = self._payload()
            data[name] = [data[name], data[name]]
            with self.subTest(post=name):
                self.assertEqual(self.client.post(self._edit_url(self.exam), data).status_code, 400)
        self.assertFalse(SystemAuditEvent.objects.filter(action="exam.update").exists())

    def test_validated_lesson_context_survives_list_save_and_back(self):
        from core.flags import set_flag
        set_flag("backoffice_course_workspace", enabled=True, reason="test")
        module = Module.objects.create(course=self.course, title="Modul")
        lesson = Lesson.objects.create(module=module, title="Dars")
        self.client.force_login(self.teacher)
        url = reverse("backoffice_exams") + f"?course={self.course.pk}&lesson={lesson.pk}&new=1"
        response = self.client.get(url)
        self.assertEqual(response.context["back_url"], reverse("backoffice_workspace_course", args=[self.course.pk]) + f"?lesson={lesson.pk}")
        response = self.client.post(url, self.page_data(url, title="Kontekst"))
        self.assertIn(f"lesson={lesson.pk}", response.url)
        self.assertEqual(self.client.get(url.replace(f"course={self.course.pk}", f"course={self.foreign_course.pk}")).status_code, 404)

    def test_new_exam_form_does_not_silently_edit_an_existing_exam(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("backoffice_exams"), {"course": self.course.pk, "new": 1})
        self.assertIsNone(response.context["exam"])
        self.assertContains(response, 'name="section-title"')
