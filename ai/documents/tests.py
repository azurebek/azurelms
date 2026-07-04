"""PDF hujjat qatlami testlari: writer/reader/parser + messenger integratsiyasi."""
import io
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ai.agent.types import AIRequest, AIResponse
from ai.documents import build_pdf, extract_pdf_doc_block, extract_pdf_text
from ai.skills.registry import SkillRegistry
from messenger.models import ChatRoom, Message

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp(prefix="azurelms_test_media_")


def _sample_pdf_bytes(marker="gitmek"):
    return build_pdf(title="Sinov hujjati", body=f"Bu sinov matni. Kalit so'z: {marker}.\n- band")


class PdfWriterReaderTests(TestCase):
    def test_build_pdf_produces_valid_pdf_with_unicode_and_table(self):
        body = "# Sarlavha ığşçöü o'zbekcha\n| Turkcha | O'zbekcha |\n| gitmek | bormoq |\n- band"
        pdf = build_pdf(title="Lug'at", body=body)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)

    def test_reader_roundtrip_extracts_text(self):
        text = extract_pdf_text(io.BytesIO(_sample_pdf_bytes(marker="kalitso'z77")))
        self.assertIn("kalitso'z77", text)

    def test_reader_survives_broken_file(self):
        self.assertEqual(extract_pdf_text(io.BytesIO(b"bu pdf emas")), "")

    def test_extract_pdf_doc_block_cleans_reply(self):
        reply = "Tayyor! 📄\n<PDF_DOC title=\"So'z ro'yxati\">\n# A\n- b\n</PDF_DOC>"
        cleaned, title, body = extract_pdf_doc_block(reply)
        self.assertEqual(cleaned, "Tayyor! 📄")
        self.assertEqual(title, "So'z ro'yxati")
        self.assertIn("- b", body)

    def test_extract_pdf_doc_block_noop_without_block(self):
        cleaned, title, body = extract_pdf_doc_block("oddiy javob")
        self.assertEqual((cleaned, title, body), ("oddiy javob", None, None))


class DocumentSkillSelectionTests(TestCase):
    def setUp(self):
        self.registry = SkillRegistry()

    def _request(self, question, document_context=""):
        return SimpleNamespace(
            room=None,
            student=None,
            user_question=question,
            requested_skill_slug=None,
            context_lesson=None,
            document_context=document_context,
        )

    def test_pdf_keywords_route_to_document_qa(self):
        skill = self.registry.select_for_request(self._request("shu pdf faylni o'qib ber"))
        self.assertEqual(skill.slug, "document_qa")

    def test_neutral_question_with_document_routes_to_document_qa(self):
        skill = self.registry.select_for_request(
            self._request("bu nima haqida?", document_context="hujjat matni")
        )
        self.assertEqual(skill.slug, "document_qa")

    def test_without_document_neutral_question_stays_general(self):
        skill = self.registry.select_for_request(self._request("bu nima haqida?"))
        self.assertEqual(skill.slug, "general_chat")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class GenerateAiResponsePdfFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="pdf_u", email="pdf@t.uz", password="x")
        self.room = ChatRoom.objects.create(room_type="ai", name="PDF room")
        self.room.participants.add(self.student)

    def _run_task(self, question, user_message=None):
        from messenger.tasks import generate_ai_response

        generate_ai_response.run(
            room_id=self.room.id,
            student_id=self.student.id,
            user_question=question,
            user_message_id=user_message.id if user_message else None,
        )

    def test_pdf_doc_block_becomes_attached_pdf(self):
        fake = AIResponse(
            text="Mana tayyor! 📄\n<PDF_DOC title=\"Mini lug'at\">\n# So'zlar\n| T | O |\n| gitmek | bormoq |\n</PDF_DOC>",
            model_name="fake-model",
            skill_slug="document_qa",
            metadata={},
        )
        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.return_value = fake
            self._run_task("menga pdf lug'at yasab ber")

        ai_message = Message.objects.filter(room=self.room, is_ai_response=True).latest("created_at")
        self.assertEqual(ai_message.text, "Mana tayyor! 📄")
        self.assertTrue(ai_message.attachment_name.endswith(".pdf"))
        self.assertEqual(ai_message.attachment_content_type, "application/pdf")
        self.assertGreater(ai_message.attachment_size, 500)
        extracted = extract_pdf_text(ai_message.attachment)
        self.assertIn("gitmek", extracted)

    def test_uploaded_pdf_reaches_engine_as_document_context(self):
        with self.settings(MEDIA_ROOT=TEMP_MEDIA):
            upload_message = Message.objects.create(
                room=self.room,
                sender=self.student,
                text="",
                attachment=ContentFile(_sample_pdf_bytes(marker="maxsusbelgi42"), name="test.pdf"),
                attachment_name="test.pdf",
                attachment_content_type="application/pdf",
            )

        captured = {}

        def capture(request: AIRequest):
            captured["request"] = request
            return AIResponse(text="ok", model_name="fake", skill_slug="document_qa", metadata={})

        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.side_effect = capture
            self._run_task("hujjatda nima deyilgan?", user_message=upload_message)

        request = captured["request"]
        self.assertIn("maxsusbelgi42", request.document_context)
        self.assertEqual(request.document_name, "test.pdf")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadTriggersAiTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="pdf_up", email="pdfup@t.uz", password="pass-12345"
        )
        self.room = ChatRoom.objects.create(room_type="ai", name="Upload room")
        self.room.participants.add(self.student)
        self.client.force_login(self.student)

    def _upload(self, filename, content, content_type, text=""):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post(
            reverse("messenger:upload_message_attachment"),
            {
                "room_id": self.room.id,
                "text": text,
                "file": SimpleUploadedFile(filename, content, content_type=content_type),
            },
        )

    def test_pdf_upload_dispatches_ai_with_default_question(self):
        with patch("messenger.tasks.generate_ai_response.delay") as delay:
            response = self._upload("konspekt.pdf", _sample_pdf_bytes(), "application/pdf")
        self.assertEqual(response.status_code, 200)
        delay.assert_called_once()
        kwargs = delay.call_args.kwargs
        self.assertIn("PDF hujjat yukladim", kwargs["user_question"])

    def test_captionless_image_upload_does_not_dispatch_ai(self):
        with patch("messenger.tasks.generate_ai_response.delay") as delay:
            self._upload("rasm.png", b"\x89PNG fake", "image/png")
        delay.assert_not_called()
