import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, Module
from messenger.models import AIFeedback, ChatRoom, LessonRAGChunk, Message
from messenger.rag import ensure_pgvector_schema, reindex_lessons, retrieve_relevant_chunks
from messenger.tasks import generate_ai_response


User = get_user_model()


class ChatAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="chat-student",
            email="chat-student@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_superuser(
            username="chat-admin",
            email="chat-admin@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Chat Course",
            description="Chat course",
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Chat Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )

    def test_pending_enrollment_does_not_grant_chat_access_until_activation(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status="pending",
        )
        self.assertEqual(ChatRoom.objects.filter(participants=self.student).count(), 0)

        enrollment.status = "active"
        enrollment.save()

        room_types = set(ChatRoom.objects.filter(participants=self.student).values_list("room_type", flat=True))
        self.assertEqual(room_types, {"group", "ai", "private"})

    def test_expired_enrollment_revokes_student_room_access(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status="active",
        )
        self.assertEqual(ChatRoom.objects.filter(participants=self.student).count(), 3)

        enrollment.status = "expired"
        enrollment.save()

        self.assertEqual(ChatRoom.objects.filter(participants=self.student).count(), 0)

    def test_room_apis_filter_stale_participants(self):
        group_room = ChatRoom.objects.get(cohort=self.cohort, room_type="group")
        ai_room = ChatRoom.objects.create(room_type="ai", name=f"Azure AI - {self.student.username}")
        private_room = ChatRoom.objects.create(room_type="private", name=f"Ustoz bilan aloqa - {self.student.username}")

        for room in (group_room, ai_room, private_room):
            room.participants.add(self.student)

        Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status="expired",
        )

        self.client.force_login(self.student)

        list_response = self.client.get(reverse("messenger:get_user_rooms"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["rooms"], [])

        message_response = self.client.get(reverse("messenger:get_room_messages", args=[group_room.id]))
        self.assertEqual(message_response.status_code, 403)


class GenerateAiResponseTaskTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="ai-student",
            email="ai-student@example.com",
            password="testpass123",
        )

    @patch("messenger.tasks.logger.warning")
    def test_generate_ai_response_returns_safely_when_room_is_missing(self, mocked_warning):
        result = generate_ai_response.run(room_id=999999, student_id=self.student.id, user_question="salom")

        self.assertIsNone(result)
        self.assertEqual(Message.objects.count(), 0)
        mocked_warning.assert_called_once()

    @patch("messenger.tasks.logger.exception")
    @patch("messenger.tasks.genai.Client", side_effect=RuntimeError("provider down"))
    def test_generate_ai_response_creates_fallback_message_when_provider_fails(
        self,
        mocked_client,
        mocked_logger_exception,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)

        message_id = generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="salom")

        self.assertIsNotNone(message_id)
        ai_message = Message.objects.get(id=message_id)
        self.assertTrue(ai_message.is_ai_response)
        self.assertEqual(ai_message.room, room)
        self.assertIn("Kechirasiz", ai_message.text)
        self.assertTrue(mocked_client.called)
        mocked_logger_exception.assert_called_once()


class AIFeedbackApiTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="feedback-student",
            email="feedback-student@example.com",
            password="testpass123",
        )
        self.peer = User.objects.create_user(
            username="feedback-peer",
            email="feedback-peer@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Feedback Course",
            description="Feedback course",
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Feedback Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")
        Enrollment.objects.create(student=self.peer, cohort=self.cohort, status="active")

        self.room = ChatRoom.objects.create(room_type="ai", name=f"Azure AI - {self.student.username}")
        self.room.participants.add(self.student, self.peer)
        self.ai_message = Message.objects.create(
            room=self.room,
            text="Bu AI javobi.",
            is_ai_response=True,
        )

    def test_submit_ai_feedback_saves_comment_and_returns_totals(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("messenger:submit_ai_feedback", args=[self.ai_message.id]),
            data='{"rating": 1, "comment": "Grammar xatosi bor"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["feedback"]["rating"], 1)
        self.assertEqual(payload["feedback"]["comment"], "Grammar xatosi bor")
        self.assertEqual(payload["feedback_totals"]["positive"], 1)
        self.assertEqual(payload["feedback_totals"]["negative"], 0)

        feedback = AIFeedback.objects.get(message=self.ai_message, student=self.student)
        self.assertEqual(feedback.comment, "Grammar xatosi bor")

    def test_submit_ai_feedback_keeps_rows_separate_per_student(self):
        self.client.force_login(self.student)
        self.client.post(
            reverse("messenger:submit_ai_feedback", args=[self.ai_message.id]),
            data='{"rating": 1, "comment": "Like"}',
            content_type="application/json",
        )
        self.client.force_login(self.peer)
        response = self.client.post(
            reverse("messenger:submit_ai_feedback", args=[self.ai_message.id]),
            data='{"rating": -1, "comment": "Noto\'g\'ri javob"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AIFeedback.objects.filter(message=self.ai_message).count(), 2)
        self.assertEqual(response.json()["feedback_totals"]["positive"], 1)
        self.assertEqual(response.json()["feedback_totals"]["negative"], 1)

    def test_get_room_messages_returns_my_feedback_and_totals_for_ai_messages(self):
        AIFeedback.objects.create(
            message=self.ai_message,
            student=self.student,
            rating=AIFeedback.RATING_NEGATIVE,
            comment="Mana shu joyini tuzatish kerak",
        )
        AIFeedback.objects.create(
            message=self.ai_message,
            student=self.peer,
            rating=AIFeedback.RATING_POSITIVE,
            comment="Menga foydali bo'ldi",
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:get_room_messages", args=[self.room.id]))

        self.assertEqual(response.status_code, 200)
        message_payload = response.json()["messages"][0]
        self.assertEqual(message_payload["feedback"]["rating"], AIFeedback.RATING_NEGATIVE)
        self.assertEqual(message_payload["feedback"]["comment"], "Mana shu joyini tuzatish kerak")
        self.assertEqual(message_payload["feedback_totals"]["positive"], 1)
        self.assertEqual(message_payload["feedback_totals"]["negative"], 1)


class RagPipelineTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="rag-student",
            email="rag-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="RAG Course",
            description="RAG course",
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="Module 1", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="RAG Lesson",
            content="<p>Python funksiyasi argument qabul qiladi va qiymat qaytaradi.</p>",
            order=1,
        )
        self.cohort = Cohort.objects.create(
            name="RAG Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")

    @patch("messenger.rag.embed_texts")
    def test_reindex_creates_rag_chunks(self, mocked_embed_texts):
        mocked_embed_texts.side_effect = lambda texts, embedding_model=None: [[1.0, 0.5] for _ in texts]

        stats = reindex_lessons(lesson_ids=[self.lesson.id], force=True)

        self.assertEqual(stats["indexed_lessons"], 1)
        self.assertGreater(LessonRAGChunk.objects.filter(lesson=self.lesson).count(), 0)

    @patch("messenger.rag.embed_texts")
    def test_reindex_skips_unchanged_content_without_force(self, mocked_embed_texts):
        mocked_embed_texts.side_effect = lambda texts, embedding_model=None: [[1.0, 0.5] for _ in texts]
        first_stats = reindex_lessons(lesson_ids=[self.lesson.id], force=True)
        self.assertEqual(first_stats["indexed_lessons"], 1)

        with patch("messenger.rag.embed_texts", side_effect=AssertionError("embed_texts should not be called")):
            second_stats = reindex_lessons(lesson_ids=[self.lesson.id], force=False)

        self.assertEqual(second_stats["skipped_unchanged"], 1)

    @patch("messenger.rag.embed_texts", return_value=[[1.0, 0.0]])
    def test_retrieval_filters_chunks_by_student_active_courses(self, mocked_embed_texts):
        other_course = Course.objects.create(
            title="Other Course",
            description="Other",
            level="beginner",
        )
        other_module = Module.objects.create(course=other_course, title="Other Module", order=1)
        other_lesson = Lesson.objects.create(module=other_module, title="Other Lesson", content="Other", order=1)

        LessonRAGChunk.objects.create(
            lesson=self.lesson,
            course=self.course,
            chunk_index=0,
            chunk_text="Python funksiyasi argument qabul qiladi.",
            chunk_hash="chunk-1",
            content_hash="content-1",
            token_count=6,
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )
        LessonRAGChunk.objects.create(
            lesson=other_lesson,
            course=other_course,
            chunk_index=0,
            chunk_text="Rust ownership qoidalari.",
            chunk_hash="chunk-2",
            content_hash="content-2",
            token_count=4,
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )

        chunks = retrieve_relevant_chunks(
            user=self.student,
            question="funksiya nima qiladi",
            top_k=3,
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["course_id"], self.course.id)
        self.assertTrue(mocked_embed_texts.called)

    def test_pgvector_setup_skips_on_non_postgres(self):
        result = ensure_pgvector_schema(backfill=False)
        self.assertEqual(result.get("status"), "skipped_non_postgres")
