import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, Module
from messenger.access import maybe_name_ai_room_from_first_prompt
from messenger.models import AIFeedback, AILongTermMemory, AIMemoryFact, ChatRoom, LessonRAGChunk, Message
from messenger.rag import ensure_pgvector_schema, reindex_lessons, retrieve_relevant_chunks
from messenger.signals import suppress_ai_signal
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
        pending_room_types = set(ChatRoom.objects.filter(participants=self.student).values_list("room_type", flat=True))
        self.assertEqual(pending_room_types, {"ai"})

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

        room_types = set(ChatRoom.objects.filter(participants=self.student).values_list("room_type", flat=True))
        self.assertEqual(room_types, {"ai"})

    def test_ai_room_is_available_without_course_enrollment(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:get_user_rooms"))

        self.assertEqual(response.status_code, 200)
        rooms = response.json()["rooms"]
        self.assertEqual([room["type"] for room in rooms], ["ai"])
        self.assertTrue(ChatRoom.objects.filter(room_type="ai", participants=self.student).exists())

    def test_new_ai_chat_creates_separate_room_and_redirects_to_it(self):
        self.client.force_login(self.student)
        self.client.get(reverse("messenger:ai"))

        response = self.client.post(reverse("messenger:new_ai_chat"))

        ai_rooms = ChatRoom.objects.filter(room_type="ai", participants=self.student)
        self.assertEqual(ai_rooms.count(), 2)
        new_room = ai_rooms.order_by("-created_at").first()
        self.assertRedirects(response, reverse("messenger:ai_room", args=[new_room.id]), fetch_redirect_response=False)

    def test_user_rooms_returns_all_ai_chats_with_latest_preview(self):
        older_room = ChatRoom.objects.create(room_type="ai", name="Grammar mashqi")
        older_room.participants.add(self.student)
        newer_room = ChatRoom.objects.create(room_type="ai", name="Essay feedback")
        newer_room.participants.add(self.student)
        with suppress_ai_signal():
            Message.objects.create(room=older_room, sender=self.student, text="Present perfectni tushuntir")
            Message.objects.create(room=newer_room, text="Essay yaxshi, lekin thesis aniqroq bo'lsin", is_ai_response=True)
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:get_user_rooms"))

        self.assertEqual(response.status_code, 200)
        ai_rooms = [room for room in response.json()["rooms"] if room["type"] == "ai"]
        self.assertEqual(len(ai_rooms), 2)
        self.assertEqual(ai_rooms[0]["name"], "Essay feedback")
        self.assertEqual(ai_rooms[0]["last_message_text"], "Essay yaxshi, lekin thesis aniqroq bo'lsin")
        self.assertEqual(ai_rooms[1]["last_message_text"], "Present perfectni tushuntir")

    def test_messenger_pages_render_without_course_enrollment(self):
        self.client.force_login(self.student)

        ai_response = self.client.get(reverse("messenger:ai"))
        group_response = self.client.get(reverse("messenger:group"))
        tutor_response = self.client.get(reverse("messenger:tutor"))

        self.assertEqual(ai_response.status_code, 200)
        self.assertContains(ai_response, "Azure AI tayyor")
        self.assertContains(ai_response, "Gemini 3.5 Flash")
        self.assertContains(ai_response, "Gemini 3.1 Pro")
        self.assertContains(ai_response, "Gemini 3.1 Flash Lite")
        self.assertContains(ai_response, "Javob uslubi")
        self.assertContains(ai_response, "Qisqa va aniq")
        self.assertEqual(group_response.status_code, 200)
        self.assertContains(group_response, "Guruh chati yopiq")
        self.assertEqual(tutor_response.status_code, 200)
        self.assertContains(tutor_response, "Tutor chati yopiq")

    def test_ai_page_lists_separate_ai_chats_and_latest_previews(self):
        first_room = ChatRoom.objects.create(room_type="ai", name="Present perfect")
        first_room.participants.add(self.student)
        second_room = ChatRoom.objects.create(room_type="ai", name="IELTS essay")
        second_room.participants.add(self.student)
        with suppress_ai_signal():
            Message.objects.create(room=first_room, sender=self.student, text="Present perfect nima?")
            Message.objects.create(room=second_room, sender=self.student, text="Essay introduction tekshir")
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:ai_room", args=[first_room.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Present perfect")
        self.assertContains(response, "IELTS essay")
        self.assertContains(response, "Present perfect nima?")
        self.assertContains(response, "Essay introduction tekshir")

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
        self.assertEqual([room["type"] for room in list_response.json()["rooms"]], ["ai"])

        message_response = self.client.get(reverse("messenger:get_room_messages", args=[group_room.id]))
        self.assertEqual(message_response.status_code, 403)

        ai_response = self.client.get(reverse("messenger:get_room_messages", args=[ai_room.id]))
        self.assertEqual(ai_response.status_code, 200)


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

    @patch("ai.agent.engine.logger.exception")
    @patch("ai.providers.gemini.genai.Client", side_effect=RuntimeError("provider down"))
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

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_prompt_keeps_emoji_enabled_for_formal_tone(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        self.student.ai_tone = User.AI_TONE_FORMAL
        self.student.ai_model = User.AI_MODEL_31_PRO
        self.student.save(update_fields=["ai_tone", "ai_model"])
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Rasmiy javob ber",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        model_name = mocked_client.return_value.models.generate_content.call_args.kwargs["model"]
        self.assertEqual(model_name, User.AI_MODEL_31_PRO)
        self.assertIn("Har javobda tabiiy joyda mos emoji ishlat", prompt)
        self.assertIn("Faqat 1 ta neytral, mavzuga mos emoji ishlat", prompt)
        self.assertNotIn("emoji ishlatma", prompt)
        self.assertEqual(Message.objects.get(id=message_id).text, "Javob tayyor.")

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_hides_memory_tag_and_saves_fact(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="**Tushunarli.** <SAVE_MEMORY>weak_topic: Python funksiyalarini o'rganyapti</SAVE_MEMORY>"
        )

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Funksiyalarni eslab qol",
        )

        ai_message = Message.objects.get(id=message_id)
        self.assertEqual(ai_message.text, "Tushunarli.")
        self.assertNotIn("SAVE_MEMORY", ai_message.text)
        memory = AIMemoryFact.objects.get(user=self.student)
        self.assertEqual(memory.category, AIMemoryFact.CATEGORY_WEAK_TOPIC)
        self.assertEqual(memory.value, "Python funksiyalarini o'rganyapti")
        self.assertEqual(memory.source_room, room)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_deduplicates_structured_memory(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="<SAVE_MEMORY>weak_topic: Python funksiyalarida qiynalyapti</SAVE_MEMORY>Javob."
        )

        generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="Buni eslab qol")
        generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="Yana eslab qol")

        self.assertEqual(AIMemoryFact.objects.filter(user=self.student).count(), 1)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_skips_sensitive_memory(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="<SAVE_MEMORY>preference: API key ABC123 ni eslab qol</SAVE_MEMORY>Mayli."
        )

        generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="kalitni eslab qol")

        self.assertFalse(AIMemoryFact.objects.filter(user=self.student).exists())

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_respects_do_not_remember_request(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="<SAVE_MEMORY>profile: Python beginner darajada</SAVE_MEMORY>Mayli."
        )

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Buni eslab qolma: men Python beginner darajadaman",
        )

        self.assertFalse(AIMemoryFact.objects.filter(user=self.student).exists())

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_includes_relevant_memory_in_prompt(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_WEAK_TOPIC,
            key="weak_topic:python-functions",
            value="Python funksiyalarida qiynalyapti",
            fingerprint="test-python-functions",
        )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Python funksiyalarini tushuntir",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("[weak_topic] Python funksiyalarida qiynalyapti", prompt)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_keeps_legacy_memory_fallback_in_prompt(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        AILongTermMemory.objects.create(user=self.student, learned_facts="- Qisqa izohlarni yoqtiradi")
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_PROFILE,
            key="profile:student",
            value="Python beginner darajada",
            fingerprint="test-profile",
        )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Python funksiyalarini tushuntir",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("[profile] Python beginner darajada", prompt)
        self.assertIn("Legacy memory:", prompt)
        self.assertIn("Qisqa izohlarni yoqtiradi", prompt)

    def test_first_prompt_can_name_ai_room(self):
        room = ChatRoom.objects.create(room_type="ai", name="Yangi AI chat")
        room.participants.add(self.student)
        with suppress_ai_signal():
            Message.objects.create(room=room, sender=self.student, text="Past simple va present perfect farqi nima?")

        renamed = maybe_name_ai_room_from_first_prompt(room, "Past simple va present perfect farqi nima?")

        self.assertTrue(renamed)
        room.refresh_from_db()
        self.assertEqual(room.name, "Past simple va present perfect farqi nima")


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
