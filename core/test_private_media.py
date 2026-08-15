"""A0b/3 — private fayllar faqat huquqi borlarga ochiladi.

Ikki qatlamli da'vo tekshiriladi:

1. **Fayl public ildizda emas.** To'lov cheki, vazifa fayli, chat biriktirmasi
   va speaking yozuvi `PRIVATE_MEDIA_ROOT` ichida saqlanadi, ya'ni `/media/...`
   orqali umuman yetib bo'lmaydi — himoya faqat view mantiqiga tayanmaydi.
2. **View ruxsatni tekshiradi.** Anonim, begona o'quvchi va biriktirilmagan
   staff `404` oladi (`403` faylning mavjudligini tasdiqlab qo'yardi).

Uchinchi nozik nuqta: `Content-Type` fayl baytlaridan aniqlanadi. Saqlangan
`attachment_content_type` ni brauzer yuborgan va u yolg'on bo'lishi mumkin.
"""

import base64
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"\x00" * 64

User = get_user_model()


class PrivateMediaAccessTests(TestCase):
    def setUp(self):
        from cohorts.models import Cohort, Enrollment, PaymentReceipt
        from courses.models import (
            Assignment, AssignmentSubmission, Course, Exam, ExamAttempt,
            ExamSection, Lesson, Module, Question, StudentAnswer,
        )
        from messenger.models import ChatRoom, Message

        self.student = User.objects.create_user(
            username="pm_student", email="pm_student@t.uz", password="pass-12345")
        self.other = User.objects.create_user(
            username="pm_other", email="pm_other@t.uz", password="pass-12345")
        self.teacher = User.objects.create_user(
            username="pm_teacher", email="pm_teacher@t.uz", password="pass-12345", is_staff=True)
        self.unassigned_staff = User.objects.create_user(
            username="pm_staff", email="pm_staff@t.uz", password="pass-12345", is_staff=True)

        self.course = Course.objects.create(
            title="PM Course", description="d", level="beginner", instructor=self.teacher)
        cohort = Cohort.objects.create(
            name="PM Cohort", course=self.course, start_date=datetime.date(2026, 5, 1))
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=cohort, status="active")

        self.receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=1000,
            receipt_image=ContentFile(PNG_1X1, name="receipt.png"),
        )

        module = Module.objects.create(course=self.course, title="M1", order=1)
        lesson = Lesson.objects.create(module=module, title="L1", order=1)
        assignment = Assignment.objects.create(
            lesson=lesson, title="HW", description="<p>d</p>", max_xp=10)
        self.submission = AssignmentSubmission.objects.create(
            assignment=assignment, student=self.student, answer_text="javob",
            attachment=ContentFile(PDF_BYTES, name="ish.pdf"),
        )

        self.room = ChatRoom.objects.create(room_type="ai", name="PM room")
        self.room.participants.add(self.student)
        self.message = Message.objects.create(
            room=self.room, sender=self.student, text="fayl",
            attachment=ContentFile(PNG_1X1, name="rasm.png"),
            attachment_name="rasm.png",
            # Ataylab yolg'on: brauzer yuborgan qiymatga ishonilmasligi kerak.
            attachment_content_type="text/html",
        )

        exam = Exam.objects.create(
            course=self.course, title="PM Exam", exam_type="final",
            weight_percentage=100, passing_score=50, max_attempts=2)
        section = ExamSection.objects.create(
            exam=exam, title="Speaking", section_type="speaking",
            instructions="Gapiring.", max_score=10, time_limit_minutes=10, order=1)
        question = Question.objects.create(exam_section=section, text="Ayting", points=10)
        attempt = ExamAttempt.objects.create(student=self.student, exam=exam, attempt_number=1)

        from core.private_storage import private_media_storage
        self.audio_key = private_media_storage().save(
            "exam_audio/test/answer.webm", ContentFile(WEBM_BYTES))
        self.answer = StudentAnswer.objects.create(
            attempt=attempt, question=question, audio_key=self.audio_key)

        self.urls = {
            "receipt": reverse("cohorts:receipt_file", args=[self.receipt.id]),
            "submission": reverse("submission_file", args=[self.submission.id]),
            "message": reverse("messenger:message_attachment", args=[self.message.id]),
            "audio": reverse("exam_answer_audio", args=[self.answer.id]),
        }

    # --- fayl qayerda yotibdi -------------------------------------------

    def test_private_files_are_stored_outside_media_root(self):
        media_root = str(settings.MEDIA_ROOT)
        for label, path in (
            ("chek", self.receipt.receipt_image.path),
            ("vazifa", self.submission.attachment.path),
            ("biriktirma", self.message.attachment.path),
        ):
            with self.subTest(fayl=label):
                self.assertTrue(str(path).startswith(str(settings.PRIVATE_MEDIA_ROOT)))
                self.assertFalse(str(path).startswith(media_root))

    # --- anonim ----------------------------------------------------------

    def test_anonymous_gets_404_everywhere(self):
        for label, url in self.urls.items():
            with self.subTest(resurs=label):
                self.assertEqual(self.client.get(url).status_code, 404)

    # --- begona foydalanuvchi -------------------------------------------

    def test_unrelated_student_gets_404_everywhere(self):
        self.client.force_login(self.other)
        for label, url in self.urls.items():
            with self.subTest(resurs=label):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_unassigned_staff_cannot_read_learner_work(self):
        """Biriktirilmagan staff teacher scope'dan o'tmaydi (A0b/1 bilan bog'liq)."""
        self.client.force_login(self.unassigned_staff)
        for label in ("submission", "audio"):
            with self.subTest(resurs=label):
                self.assertEqual(self.client.get(self.urls[label]).status_code, 404)

    # --- huquqi borlar ----------------------------------------------------

    def test_owner_student_can_read_own_files(self):
        self.client.force_login(self.student)
        for label, url in self.urls.items():
            with self.subTest(resurs=label):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_course_teacher_can_read_learner_work(self):
        self.client.force_login(self.teacher)
        for label in ("submission", "audio"):
            with self.subTest(resurs=label):
                self.assertEqual(self.client.get(self.urls[label]).status_code, 200)

    def test_staff_can_read_payment_receipt(self):
        self.client.force_login(self.unassigned_staff)
        self.assertEqual(self.client.get(self.urls["receipt"]).status_code, 200)

    # --- javob sarlavhalari ----------------------------------------------

    def test_content_type_comes_from_bytes_not_from_the_stored_header(self):
        self.client.force_login(self.student)
        response = self.client.get(self.urls["message"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_documents_are_sent_as_attachment_and_images_inline(self):
        self.client.force_login(self.student)
        pdf = self.client.get(self.urls["submission"])
        self.assertIn("attachment", pdf["Content-Disposition"])
        image = self.client.get(self.urls["message"])
        self.assertIn("inline", image["Content-Disposition"])

    def test_private_files_are_not_cached(self):
        self.client.force_login(self.student)
        response = self.client.get(self.urls["receipt"])
        self.assertIn("no-store", response["Cache-Control"])

    # --- chegaraviy holatlar ----------------------------------------------

    def test_deleted_message_attachment_is_no_longer_served(self):
        self.message.is_deleted = True
        self.message.save(update_fields=["is_deleted"])
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.urls["message"]).status_code, 404)

    def test_missing_object_is_404_not_500(self):
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse("cohorts:receipt_file", args=[999999])).status_code, 404
        )


class PrivateFileAdminSafetyTests(TestCase):
    """Legacy admin yoqilsa ham private fayl maydonlari sahifani buzmaydi.

    Private storage ataylab public URL bermaydi (`url()` `ValueError` ko'taradi).
    Django'ning `ClearableFileInput` widgeti esa render paytida `value.url` ni
    o'qiydi — ya'ni xom `FileField` admin formasida qolsa sahifa `500` berardi.
    Shuning uchun uchala admin ham maydonni formadan chiqarib, o'rniga ruxsat
    tekshiradigan havolani ko'rsatadi.
    """

    def setUp(self):
        self.request = type("R", (), {"user": None, "GET": {}, "method": "GET"})()

    def _admin(self, model, admin_class):
        from django.contrib.admin.sites import AdminSite

        return admin_class(model, AdminSite())

    def test_raw_file_fields_are_excluded_from_admin_forms(self):
        from cohorts.admin import PaymentReceiptAdmin
        from cohorts.models import PaymentReceipt
        from courses.admin import AssignmentSubmissionAdmin
        from courses.models import AssignmentSubmission
        from messenger.admin import MessageAdmin
        from messenger.models import Message

        cases = (
            (PaymentReceipt, PaymentReceiptAdmin, "receipt_image"),
            (AssignmentSubmission, AssignmentSubmissionAdmin, "attachment"),
            (Message, MessageAdmin, "attachment"),
        )
        for model, admin_class, field in cases:
            with self.subTest(model=model.__name__):
                form = self._admin(model, admin_class).get_form(self.request)
                self.assertNotIn(
                    field,
                    form.base_fields,
                    f"{model.__name__}.{field} admin formasida qoldi — sahifa 500 beradi",
                )

    def test_private_storage_refuses_to_produce_a_public_url(self):
        from core.private_storage import private_media_storage

        with self.assertRaises(ValueError):
            private_media_storage().url("receipts/2026/08/x.png")
