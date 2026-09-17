"""Kutubxonaning ichki yuzasi: ruxsat, qidiruv, biriktirish va hayotiy sikl."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import Course, Lesson, Module

from . import services
from .models import LessonMaterial, LibraryResource, MaterialAudience
from .test_resources import pdf_upload


@override_settings(GEMINI_API_KEY=None)
class LibraryBackofficeAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="bo_owner", email="bo@example.test", password="pass-12345"
        )
        self.student = User.objects.create_user(
            username="bo_student", email="student@example.test", password="pass-12345"
        )
        self.resource = LibraryResource(title="Ichki material")
        services.apply_upload(self.resource, pdf_upload(), actor=self.owner)
        self.resource.save()

    def test_student_has_no_route_into_the_library(self):
        self.client.force_login(self.student)
        for url in (
            reverse("library_backoffice:resources"),
            reverse("library_backoffice:resource_create"),
            reverse("library_backoffice:resource_edit", args=[self.resource.pk]),
            reverse("library_backoffice:resource_file", args=[self.resource.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotEqual(response.status_code, 200)
                self.assertEqual(response.status_code, 302)

    def test_anonymous_visitor_is_redirected(self):
        response = self.client.get(reverse("library_backoffice:resources"))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_post_a_mutation(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("library_backoffice:resource_archive", args=[self.resource.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.is_archived)

    def test_staff_sees_the_list_and_can_filter(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("library_backoffice:resources"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ichki material")

        response = self.client.get(reverse("library_backoffice:resources"), {"q": "topilmaydi"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Ichki material")

    def test_staff_can_open_the_private_file(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("library_backoffice:resource_file", args=[self.resource.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")


@override_settings(GEMINI_API_KEY=None)
class LibraryEditorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="editor_owner", email="editor@example.test", password="pass-12345"
        )
        self.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=self.owner,
            level="beginner",
            duration=20,
        )
        self.client.force_login(self.owner)

    def test_upload_form_creates_a_resource_with_tags(self):
        response = self.client.post(
            reverse("library_backoffice:resource_create"),
            {
                "title": "A1 tanishuv taqdimoti",
                "description": "Jonli dars uchun",
                "resource_type": "live_deck",
                "language": "uz",
                "level": "a1",
                "topic": "tanishuv",
                "course": self.course.pk,
                "tags_text": "a1, speaking",
                "file": pdf_upload(),
            },
        )
        resource = LibraryResource.objects.get(title="A1 tanishuv taqdimoti")
        self.assertRedirects(
            response, reverse("library_backoffice:resource_edit", args=[resource.pk])
        )
        self.assertEqual(resource.file_kind, "pdf")
        self.assertEqual(resource.created_by, self.owner)
        self.assertEqual(
            sorted(resource.tags.values_list("name", flat=True)), ["a1", "speaking"]
        )

    def test_upload_form_rejects_a_disallowed_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("library_backoffice:resource_create"),
            {
                "title": "Skript",
                "resource_type": "other",
                "language": "uz",
                "level": "any",
                "tags_text": "",
                "file": SimpleUploadedFile("evil.html", b"<html>x</html>", content_type="text/html"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LibraryResource.objects.filter(title="Skript").exists())
        self.assertContains(response, "qabul qilinmaydi")

    def test_archive_and_restore_are_recorded(self):
        from aicontrol.models import SystemAuditEvent

        resource = LibraryResource(title="Eski material")
        services.apply_upload(resource, pdf_upload(), actor=self.owner)
        resource.save()

        self.client.post(reverse("library_backoffice:resource_archive", args=[resource.pk]))
        resource.refresh_from_db()
        self.assertTrue(resource.is_archived)

        self.client.post(reverse("library_backoffice:resource_archive", args=[resource.pk]))
        resource.refresh_from_db()
        self.assertFalse(resource.is_archived)

        actions = set(
            SystemAuditEvent.objects.filter(target_type="LibraryResource").values_list(
                "action", flat=True
            )
        )
        self.assertIn("library.resource.archive", actions)
        self.assertIn("library.resource.restore", actions)


@override_settings(GEMINI_API_KEY=None)
class LessonMaterialFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="flow_owner", email="flow@example.test", password="pass-12345"
        )
        self.teacher = User.objects.create_user(
            username="flow_teacher",
            email="teacher@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.other_teacher = User.objects.create_user(
            username="flow_other",
            email="other@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=self.teacher,
            level="beginner",
            duration=20,
        )
        module = Module.objects.create(course=self.course, title="Modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="1-dars", order=1)

        self.resource = LibraryResource(title="Sinov varaqasi")
        services.apply_upload(self.resource, pdf_upload(), actor=self.owner)
        self.resource.save()

    def test_attach_from_the_picker_links_instead_of_copying(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("library_backoffice:material_attach", args=[self.lesson.pk]),
            {"resource": self.resource.pk},
        )
        self.assertRedirects(response, reverse("backoffice_lesson_edit", args=[self.lesson.pk]))

        material = LessonMaterial.objects.get(lesson=self.lesson)
        self.assertEqual(material.resource, self.resource)
        self.assertEqual(LibraryResource.objects.count(), 1)
        self.assertEqual(material.added_by, self.teacher)

    def test_a_teacher_cannot_touch_another_teachers_lesson(self):
        self.client.force_login(self.other_teacher)

        attach = self.client.post(
            reverse("library_backoffice:material_attach", args=[self.lesson.pk]),
            {"resource": self.resource.pk},
        )
        self.assertEqual(attach.status_code, 404)
        self.assertFalse(LessonMaterial.objects.exists())

        picker = self.client.get(
            reverse("library_backoffice:lesson_picker", args=[self.lesson.pk])
        )
        self.assertEqual(picker.status_code, 404)

    def test_detach_keeps_the_resource_in_the_library(self):
        material, _ = services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse("library_backoffice:material_detach", args=[material.pk])
        )
        self.assertRedirects(response, reverse("backoffice_lesson_edit", args=[self.lesson.pk]))
        self.assertFalse(LessonMaterial.objects.exists())
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())

    def test_lesson_specific_settings_are_saved(self):
        material, _ = services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        self.client.force_login(self.teacher)

        self.client.post(
            reverse("library_backoffice:material_update", args=[material.pk]),
            {
                "display_title": "Darsdagi nomi",
                "audience": MaterialAudience.TEACHER,
                "is_required": "on",
                "available_from": "",
            },
        )
        material.refresh_from_db()
        self.assertEqual(material.display_title, "Darsdagi nomi")
        self.assertEqual(material.audience, MaterialAudience.TEACHER)
        self.assertTrue(material.is_required)
        self.assertFalse(material.is_visible, "checkbox yuborilmasa o'chadi")
        self.assertEqual(material.title, "Darsdagi nomi")

    def test_reorder_uses_the_submitted_numbers(self):
        second = LibraryResource(title="Ikkinchi")
        services.apply_upload(second, pdf_upload("ikki.pdf"), actor=self.owner)
        second.save()
        first_material, _ = services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        second_material, _ = services.attach_to_lesson(self.lesson, second, actor=self.teacher)

        self.client.force_login(self.teacher)
        self.client.post(
            reverse("library_backoffice:material_reorder", args=[self.lesson.pk]),
            {f"order-{first_material.pk}": "9", f"order-{second_material.pk}": "1"},
        )

        first_material.refresh_from_db()
        second_material.refresh_from_db()
        self.assertEqual((second_material.order, first_material.order), (1, 2))

    def test_lesson_editor_lists_attached_materials(self):
        services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("backoffice_lesson_edit", args=[self.lesson.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sinov varaqasi")
        self.assertContains(response, "Kutubxonadan tanlash")

    def test_delete_is_refused_while_the_resource_is_attached(self):
        services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("library_backoffice:resource_delete", args=[self.resource.pk]),
            follow=True,
        )
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        self.assertContains(response, "arxivlang")

    def test_picker_hides_archived_resources(self):
        self.resource.archive(actor=self.owner)
        self.client.force_login(self.teacher)

        response = self.client.get(
            reverse("library_backoffice:lesson_picker", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sinov varaqasi")

        blocked = self.client.post(
            reverse("library_backoffice:material_attach", args=[self.lesson.pk]),
            {"resource": self.resource.pk},
        )
        self.assertEqual(blocked.status_code, 404)
