"""A0b — upload gate: fayl nomiga emas, baytlariga ishonish (`core.upload_validation`).

Tekshiriladigan asosiy da'vo: `name` va `content_type` ni klient yuboradi va
ularni soxtalashtirish mumkin, shuning uchun turni faqat fayl boshidagi baytlar
aniqlaydi. Endpoint testlari esa gate haqiqatan upload yo'lida turganini
tasdiqlaydi — model field validatorlari `Model.objects.create()` va
`instance.save()` yo'llarida ishga tushmaydi.
"""

import base64
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.upload_validation import sniff_kind, validate_upload

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
JPEG_HEAD = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
OGG_BYTES = b"OggS" + b"\x00" * 64
WAV_BYTES = b"RIFF\x24\x00\x00\x00WAVE" + b"\x00" * 32
MP3_BYTES = b"ID3\x03\x00\x00\x00" + b"\x00" * 32
MP4_BYTES = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 32
SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
HTML_BYTES = b"<!doctype html><html><body><script>alert(1)</script></body></html>"


def _upload(name, content, content_type="application/octet-stream"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class TempMediaMixin:
    """Qabul qilingan fayllar repo ichidagi `media/` ga tushib qolmasin.

    (Mavjud testlarning bir qismi hali ham haqiqiy MEDIA_ROOT ga yozadi — bu
    alohida tozalash ishi.)
    """

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="azurelms-upload-test-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


class UploadSniffTests(TestCase):
    def test_known_containers_are_recognised(self):
        cases = (
            ("a.png", PNG_1X1, "png"),
            ("a.jpg", JPEG_HEAD, "jpeg"),
            ("a.pdf", PDF_BYTES, "pdf"),
            ("a.webm", WEBM_BYTES, "webm"),
            ("a.ogg", OGG_BYTES, "ogg"),
            ("a.wav", WAV_BYTES, "wav"),
            ("a.mp3", MP3_BYTES, "mp3"),
            ("a.m4a", MP4_BYTES, "mp4"),
            ("a.docx", b"PK\x03\x04" + b"\x00" * 32, "zip"),
            ("a.txt", "salom dunyo".encode("utf-8"), "text"),
        )
        for name, content, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(sniff_kind(_upload(name, content)), expected)

    def test_unknown_bytes_are_not_guessed(self):
        self.assertIsNone(sniff_kind(_upload("a.bin", b"\x01\x02\x03\x04not-a-known-type")))

    def test_sniffing_rewinds_so_the_file_can_still_be_saved(self):
        upload = _upload("a.png", PNG_1X1)
        sniff_kind(upload)
        self.assertEqual(upload.read(), PNG_1X1)


class UploadValidationTests(TestCase):
    def test_real_image_passes_image_profile(self):
        self.assertEqual(validate_upload(_upload("x.png", PNG_1X1), profile="image"), "png")

    def test_content_type_header_cannot_smuggle_a_file_in(self):
        """Klient `image/png` desa ham baytlar rasm bo'lmasa o'tmaydi."""
        upload = _upload("evil.png", b"<?php system($_GET['c']); ?>", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_upload(upload, profile="image")

    def test_extension_must_match_the_real_type(self):
        """Haqiqiy PDF `.png` nomi bilan kelsa — chalg'ituvchi nom, rad etiladi."""
        with self.assertRaises(ValidationError) as ctx:
            validate_upload(_upload("report.png", PDF_BYTES), profile="document")
        self.assertIn("kengaytma", ctx.exception.messages[0])

    def test_svg_and_html_are_rejected_as_documents(self):
        for name, content in (("x.svg", SVG_BYTES), ("x.html", HTML_BYTES)):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    validate_upload(_upload(name, content), profile="document")

    def test_markup_disguised_as_text_is_rejected(self):
        """`.txt` nomi bilan kelgan HTML matn deb qabul qilinmasligi kerak."""
        with self.assertRaises(ValidationError):
            validate_upload(_upload("note.txt", HTML_BYTES), profile="document")

    def test_pdf_is_a_document_but_not_an_image(self):
        self.assertEqual(validate_upload(_upload("x.pdf", PDF_BYTES), profile="document"), "pdf")
        with self.assertRaises(ValidationError):
            validate_upload(_upload("x.pdf", PDF_BYTES), profile="image")

    def test_audio_profile_accepts_browser_recorder_containers(self):
        for name, content in (
            ("r.webm", WEBM_BYTES), ("r.ogg", OGG_BYTES),
            ("r.wav", WAV_BYTES), ("r.mp3", MP3_BYTES), ("r.m4a", MP4_BYTES),
        ):
            with self.subTest(name=name):
                self.assertTrue(validate_upload(_upload(name, content), profile="audio"))

    def test_audio_profile_rejects_an_image(self):
        with self.assertRaises(ValidationError):
            validate_upload(_upload("r.png", PNG_1X1), profile="audio")

    def test_empty_file_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_upload(_upload("x.png", b""), profile="image")

    def test_oversize_file_is_rejected_before_reading(self):
        upload = _upload("big.png", PNG_1X1)
        upload.size = 6 * 1024 * 1024
        with self.assertRaises(ValidationError) as ctx:
            validate_upload(upload, profile="image")
        self.assertIn("MB", ctx.exception.messages[0])

    def test_field_label_is_included_in_the_error(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_upload(_upload("x.png", b"nope"), profile="image", field_label="Chek rasmi")
        self.assertTrue(ctx.exception.messages[0].startswith("Chek rasmi: "))


class UploadEndpointGateTests(TempMediaMixin, TestCase):
    """Gate haqiqatan upload yo'lida turibdimi — model validatori yetmaydi."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="upl_user", email="upl@example.test", password="pass-12345",
        )
        self.client.force_login(self.user)

    def test_avatar_endpoint_rejects_a_disguised_file(self):
        response = self.client.post(
            reverse("update_avatar"),
            {"avatar": _upload("avatar.png", HTML_BYTES, content_type="image/png")},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_avatar_endpoint_accepts_a_real_image(self):
        self.client.post(
            reverse("update_avatar"),
            {"avatar": _upload("avatar.png", PNG_1X1, content_type="image/png")},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)

    def test_messenger_attachment_endpoint_rejects_a_disguised_file(self):
        from messenger.models import ChatRoom, Message

        room = ChatRoom.objects.create(room_type="ai", name="upload test")
        room.participants.add(self.user)
        response = self.client.post(
            reverse("messenger:upload_message_attachment"),
            {
                "room_id": str(room.id),
                "file": _upload("photo.png", SVG_BYTES, content_type="image/png"),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.filter(room=room).count(), 0)


class AssignmentAttachmentGateTests(TempMediaMixin, TestCase):
    """Vazifa biriktirmasi gate'i canonical servisda — web va bot ulashadi."""

    def setUp(self):
        import datetime

        from cohorts.models import Cohort, Enrollment
        from courses.models import Assignment, Course, Lesson, Module

        User = get_user_model()
        self.student = User.objects.create_user(
            username="upl_student", email="upl_student@example.test", password="pass-12345",
        )
        course = Course.objects.create(title="Upload Course", description="d", level="beginner")
        cohort = Cohort.objects.create(
            name="Upload Cohort", course=course, start_date=datetime.date(2026, 5, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=cohort, status="active")
        module = Module.objects.create(course=course, title="1-modul", order=1)
        lesson = Lesson.objects.create(module=module, title="Upload Lesson", order=1)
        self.assignment = Assignment.objects.create(
            lesson=lesson, title="HW", description="<p>d</p>", max_xp=10,
        )

    def _submit(self, upload):
        from courses.submission_service import submit_assignment

        return submit_assignment(
            user=self.student, assignment=self.assignment, answer_text="javob", attachment=upload,
        )

    def test_disguised_attachment_is_rejected(self):
        from courses.models import AssignmentSubmission

        result = self._submit(_upload("solution.png", HTML_BYTES, content_type="image/png"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_attachment")
        self.assertFalse(
            AssignmentSubmission.objects.filter(assignment=self.assignment).exclude(
                attachment=""
            ).exists()
        )

    def test_real_pdf_attachment_is_accepted(self):
        result = self._submit(_upload("solution.pdf", PDF_BYTES, content_type="application/pdf"))
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.submission.attachment)
