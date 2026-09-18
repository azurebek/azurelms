"""Kutubxona manbalari: yuklash, almashtirish, arxiv/o'chirish va qidiruv."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from courses.models import Course, Lesson, Module

from . import selectors, services
from .models import (
    LessonMaterial,
    LibraryResource,
    LibrarySettings,
    LibraryTag,
    MaterialAudience,
    ResourceLevel,
    ResourceType,
)

PDF_BYTES = b"%PDF-1.4\n" + b"a" * 400
MP3_BYTES = b"ID3" + b"b" * 400


def pdf_upload(name="deck.pdf", payload=PDF_BYTES):
    return SimpleUploadedFile(name, payload, content_type="application/pdf")


@override_settings(GEMINI_API_KEY=None)
class ResourceUploadTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_superuser(
            username="library_owner",
            email="owner@example.test",
            password="pass-12345",
        )

    def _resource(self, **kwargs):
        resource = LibraryResource(title=kwargs.pop("title", "A1 tanishuv taqdimoti"), **kwargs)
        services.apply_upload(resource, pdf_upload(), actor=self.author)
        resource.save()
        return resource

    def test_upload_fills_metadata_from_the_bytes(self):
        resource = self._resource()

        self.assertEqual(resource.file_kind, "pdf")
        self.assertEqual(resource.file_size, len(PDF_BYTES))
        self.assertEqual(resource.original_filename, "deck.pdf")
        self.assertEqual(len(resource.checksum), 64)
        self.assertEqual(resource.version, 1)
        self.assertEqual(resource.created_by, self.author)

    def test_file_lives_outside_public_media(self):
        """Private storage public havola bermaydi — bu A0b qoidasi."""
        resource = self._resource()
        with self.assertRaises(ValueError):
            resource.file.url

    def test_replacing_the_file_bumps_version_and_removes_the_old_bytes(self):
        resource = self._resource()
        first_name = resource.file.name
        storage = resource.file.storage

        with self.captureOnCommitCallbacks(execute=True):
            services.apply_upload(resource, pdf_upload("yangi.pdf", PDF_BYTES + b"x"), actor=self.author)
            resource.save()

        self.assertEqual(resource.version, 2)
        self.assertNotEqual(resource.file.name, first_name)
        self.assertFalse(storage.exists(first_name), "eski fayl yetim qolmasligi kerak")
        self.assertTrue(storage.exists(resource.file.name))

    def test_upload_rejects_a_type_outside_the_allowlist(self):
        resource = LibraryResource(title="Skript")
        with self.assertRaises(ValidationError):
            services.apply_upload(
                resource,
                SimpleUploadedFile("evil.html", b"<html>hi</html>", content_type="text/html"),
            )

    def test_upload_limit_comes_from_the_owner_setting(self):
        settings_row = LibrarySettings.load()
        settings_row.max_upload_mb = 1
        settings_row.save()

        oversized = pdf_upload("katta.pdf", b"%PDF-1.4\n" + b"c" * (2 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            services.apply_upload(LibraryResource(title="Katta"), oversized)

        settings_row.max_upload_mb = 5
        settings_row.save()
        resource = LibraryResource(title="Katta")
        services.apply_upload(resource, pdf_upload("katta.pdf", b"%PDF-1.4\n" + b"c" * (2 * 1024 * 1024)))
        resource.save()
        self.assertEqual(resource.file_kind, "pdf")

    def test_tags_are_normalized_and_deduplicated(self):
        resource = self._resource()
        services.sync_tags(resource, "A1, Speaking , a1;tanishuv")

        self.assertEqual(
            sorted(resource.tags.values_list("name", flat=True)),
            ["a1", "speaking", "tanishuv"],
        )
        self.assertEqual(LibraryTag.objects.count(), 3)

    def test_duplicate_candidates_find_the_same_bytes(self):
        first = self._resource(title="Birinchi")
        second = self._resource(title="Ikkinchi")

        matches = services.duplicate_candidates(second.checksum, exclude_pk=second.pk)
        self.assertEqual([r.pk for r in matches], [first.pk])


@override_settings(GEMINI_API_KEY=None)
class ResourceLifecycleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_superuser(
            username="lifecycle_owner",
            email="lifecycle@example.test",
            password="pass-12345",
        )
        self.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=self.author,
            level="beginner",
            duration=20,
        )
        module = Module.objects.create(course=self.course, title="Modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="1-dars", order=1)
        self.second_lesson = Lesson.objects.create(module=module, title="2-dars", order=2)

        self.resource = LibraryResource(title="Tarqatma", resource_type=ResourceType.HANDOUT)
        services.apply_upload(self.resource, pdf_upload(), actor=self.author)
        self.resource.save()

    def test_one_resource_serves_many_lessons_without_copying_the_file(self):
        first, created_first = services.attach_to_lesson(self.lesson, self.resource, actor=self.author)
        second, created_second = services.attach_to_lesson(
            self.second_lesson, self.resource, actor=self.author
        )

        self.assertTrue(created_first)
        self.assertTrue(created_second)
        self.assertEqual(first.resource.file.name, second.resource.file.name)
        self.assertEqual(LibraryResource.objects.count(), 1)
        self.assertEqual(self.resource.usage_total, 2)

    def test_attaching_twice_does_not_duplicate_the_row(self):
        first, created_first = services.attach_to_lesson(self.lesson, self.resource, actor=self.author)
        second, created_second = services.attach_to_lesson(self.lesson, self.resource, actor=self.author)

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(LessonMaterial.objects.filter(lesson=self.lesson).count(), 1)

    def test_a_used_resource_cannot_be_deleted_but_can_be_archived(self):
        services.attach_to_lesson(self.lesson, self.resource, actor=self.author)

        with self.assertRaises(services.ResourceInUse):
            services.delete_resource(self.resource)

        self.resource.archive(actor=self.author)
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.is_archived)
        self.assertIsNotNone(self.resource.archived_at)
        # Arxiv mavjud biriktirmani buzmaydi.
        self.assertEqual(LessonMaterial.objects.filter(lesson=self.lesson).count(), 1)

    def test_deleting_an_unused_resource_removes_its_file(self):
        storage = self.resource.file.storage
        name = self.resource.file.name

        with self.captureOnCommitCallbacks(execute=True):
            services.delete_resource(self.resource)

        self.assertFalse(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        self.assertFalse(storage.exists(name))

    def test_teacher_only_resource_cannot_be_attached_for_students(self):
        secret = LibraryResource(title="Javoblar kaliti", is_teacher_only=True)
        services.apply_upload(secret, pdf_upload("kalit.pdf"), actor=self.author)
        secret.save()

        material, _ = services.attach_to_lesson(self.lesson, secret, actor=self.author)
        self.assertEqual(material.audience, MaterialAudience.TEACHER)

        material.audience = MaterialAudience.STUDENT
        with self.assertRaises(ValidationError):
            material.full_clean(exclude=["lesson", "resource", "added_by"])
        self.assertFalse(material.is_open_for_student())

    def test_reorder_rewrites_positions_without_gaps(self):
        second_resource = LibraryResource(title="Ikkinchi manba")
        services.apply_upload(second_resource, pdf_upload("ikki.pdf", PDF_BYTES + b"y"), actor=self.author)
        second_resource.save()

        first, _ = services.attach_to_lesson(self.lesson, self.resource, actor=self.author)
        second, _ = services.attach_to_lesson(self.lesson, second_resource, actor=self.author)

        services.reorder_materials(self.lesson, [second.pk, first.pk])

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.order, first.order), (1, 2))


@override_settings(GEMINI_API_KEY=None)
class ResourceSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.author = User.objects.create_superuser(
            username="search_owner",
            email="search@example.test",
            password="pass-12345",
        )
        cls.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=cls.author,
            level="beginner",
            duration=20,
        )

    def _make(self, title, *, tags="", **kwargs):
        resource = LibraryResource(title=title, **kwargs)
        services.apply_upload(resource, pdf_upload(), actor=self.author)
        resource.save()
        if tags:
            services.sync_tags(resource, tags)
        return resource

    def test_every_token_must_match_somewhere(self):
        """«A1 + speaking + tanishuv» ssenariysi: uchta belgi birdan."""
        target = self._make(
            "Tanishuv mashqi",
            tags="a1, speaking",
            level=ResourceLevel.A1,
            topic="tanishuv",
        )
        self._make("Grammatika jadvali", tags="a1", level=ResourceLevel.A1, topic="kelasi zamon")

        found = selectors.search_resources(query="a1 speaking tanishuv")
        self.assertEqual([r.pk for r in found], [target.pk])

    def test_a_resource_matches_once_even_with_several_tag_hits(self):
        self._make("Yozuv mashqi", tags="a1, speaking, tanishuv")
        found = selectors.search_resources(query="a1 speaking")
        self.assertEqual(found.count(), 1)

    def test_filters_narrow_by_type_level_language_and_file_kind(self):
        deck = self._make(
            "Jonli dars taqdimoti",
            resource_type=ResourceType.LIVE_DECK,
            level=ResourceLevel.A1,
            course=self.course,
        )
        audio = LibraryResource(title="Tinglash", resource_type=ResourceType.MEDIA)
        services.apply_upload(
            audio, SimpleUploadedFile("audio.mp3", MP3_BYTES, content_type="audio/mpeg")
        )
        audio.save()

        self.assertEqual(
            [r.pk for r in selectors.search_resources(resource_type=ResourceType.LIVE_DECK)],
            [deck.pk],
        )
        self.assertEqual(
            [r.pk for r in selectors.search_resources(level=ResourceLevel.A1)], [deck.pk]
        )
        self.assertEqual([r.pk for r in selectors.search_resources(file_kind="mp3")], [audio.pk])
        self.assertEqual(
            [r.pk for r in selectors.search_resources(course_id=self.course.pk)], [deck.pk]
        )

    def test_archived_resources_stay_out_of_the_default_list(self):
        active = self._make("Faol material")
        archived = self._make("Eski material")
        archived.archive(actor=self.author)

        self.assertEqual([r.pk for r in selectors.search_resources()], [active.pk])
        self.assertEqual(
            [r.pk for r in selectors.search_resources(only_archived=True)], [archived.pk]
        )
        self.assertEqual(selectors.search_resources(include_archived=True).count(), 2)
