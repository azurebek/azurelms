import datetime
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ai.agent.types import AIRequest
from ai.skills.registry import SkillRegistry
from cohorts.models import Cohort, Enrollment
from courses.models import (
    Assignment,
    AssignmentSubmission,
    Choice,
    Course,
    Lesson,
    LessonProgress,
    Module,
    Question,
    Quiz,
)
from messenger.access import maybe_name_ai_room_from_first_prompt
from messenger.models import (
    AIFeedback,
    AIConversationSummary,
    AIResponseRun,
    AILongTermMemory,
    AIMemoryFact,
    AIMemoryTrace,
    ChatRoomUserState,
    ChatRoom,
    LessonRAGChunk,
    Message,
)
from messenger.rag import ensure_pgvector_schema, get_rag_index_status, reindex_lessons, retrieve_relevant_chunks
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

    def test_user_rooms_include_pinned_and_unread_state(self):
        pinned_room = ChatRoom.objects.create(room_type="ai", name="Pinned grammar")
        pinned_room.participants.add(self.student)
        normal_room = ChatRoom.objects.create(room_type="ai", name="Normal chat")
        normal_room.participants.add(self.student)
        ChatRoomUserState.objects.create(
            room=pinned_room,
            user=self.student,
            is_pinned=True,
            last_read_at=timezone.now() - datetime.timedelta(minutes=5),
        )
        with suppress_ai_signal():
            Message.objects.create(room=pinned_room, text="Yangi AI javob", is_ai_response=True)
            Message.objects.create(room=normal_room, sender=self.student, text="Oddiy xabar")
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:get_user_rooms"))

        self.assertEqual(response.status_code, 200)
        ai_rooms = [room for room in response.json()["rooms"] if room["type"] == "ai"]
        self.assertEqual(ai_rooms[0]["id"], pinned_room.id)
        self.assertTrue(ai_rooms[0]["is_pinned"])
        self.assertEqual(ai_rooms[0]["unread_count"], 1)

    def test_toggle_room_pin_api_flips_user_state(self):
        room = ChatRoom.objects.create(room_type="ai", name="Pin me")
        room.participants.add(self.student)
        self.client.force_login(self.student)

        response = self.client.post(reverse("messenger:toggle_room_pin", args=[room.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_pinned"])
        self.assertTrue(ChatRoomUserState.objects.get(room=room, user=self.student).is_pinned)

        second_response = self.client.post(reverse("messenger:toggle_room_pin", args=[room.id]))

        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(second_response.json()["is_pinned"])

    def test_message_edit_and_delete_apis_soft_delete_own_message(self):
        room = ChatRoom.objects.create(room_type="ai", name="Editable")
        room.participants.add(self.student)
        with suppress_ai_signal():
            message = Message.objects.create(room=room, sender=self.student, text="Eski matn")
        self.client.force_login(self.student)

        edit_response = self.client.post(
            reverse("messenger:edit_message", args=[message.id]),
            data='{"text": "Yangi matn"}',
            content_type="application/json",
        )

        self.assertEqual(edit_response.status_code, 200)
        message.refresh_from_db()
        self.assertEqual(message.text, "Yangi matn")
        self.assertIsNotNone(message.edited_at)
        self.assertEqual(edit_response.json()["message"]["message"], "Yangi matn")

        delete_response = self.client.post(reverse("messenger:delete_message", args=[message.id]))

        self.assertEqual(delete_response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
        self.assertEqual(message.text, "")
        self.assertEqual(delete_response.json()["message"]["message"], "Xabar o'chirilgan")

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_upload_message_attachment_api_creates_file_message(self):
        room = ChatRoom.objects.create(room_type="ai", name="Upload")
        room.participants.add(self.student)
        upload = SimpleUploadedFile("hello.txt", b"salom", content_type="text/plain")
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("messenger:upload_message_attachment"),
            data={"room_id": room.id, "text": "Mana fayl", "file": upload},
        )

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(room=room, sender=self.student)
        self.assertEqual(message.text, "Mana fayl")
        self.assertEqual(message.attachment_name, "hello.txt")
        payload = response.json()["message"]
        self.assertEqual(payload["attachment"]["name"], "hello.txt")
        self.assertEqual(payload["attachment"]["content_type"], "text/plain")

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

    def test_ai_page_uses_lesson_query_for_enrolled_student_context(self):
        module = Module.objects.create(course=self.course, title="Context Module", order=1)
        lesson = Lesson.objects.create(
            module=module,
            title="Context Lesson",
            content="<p>Context body</p>",
            order=1,
        )
        Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.client.force_login(self.student)

        response = self.client.get(f"{reverse('messenger:ai')}?lesson={lesson.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-context-lesson-id="{lesson.id}"')
        self.assertContains(response, "RAG scope")
        self.assertContains(response, "Context Lesson")

    def test_ai_page_ignores_lesson_query_without_course_access(self):
        other_course = Course.objects.create(title="Private Course", description="Private", level="beginner")
        other_module = Module.objects.create(course=other_course, title="Private Module", order=1)
        other_lesson = Lesson.objects.create(
            module=other_module,
            title="Private Lesson",
            content="<p>Private body</p>",
            order=1,
        )
        self.client.force_login(self.student)

        response = self.client.get(f"{reverse('messenger:ai')}?lesson={other_lesson.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-context-lesson-id=""')
        self.assertNotContains(response, "Private Lesson")

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

    def _make_course_with_lesson(self, *, title="AI English", lesson_title="Present Perfect"):
        course = Course.objects.create(
            title=title,
            description="English course for AI tool tests",
            level="beginner",
        )
        module = Module.objects.create(course=course, title="Module 1", order=1)
        lesson = Lesson.objects.create(
            module=module,
            title=lesson_title,
            content="<p>Present perfect connects past actions with present results.</p>",
            order=1,
        )
        cohort = Cohort.objects.create(
            name=f"{title} Cohort",
            course=course,
            start_date=datetime.date(2026, 1, 1),
        )
        enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        return course, module, lesson, enrollment

    def test_skill_registry_routes_core_skill_requests(self):
        registry = SkillRegistry()
        cases = {
            "Shu darsdan quiz tuz": "quiz_generator",
            "Vazifamni tekshirib ber": "homework_checker",
            "Bu gapimni grammatika bo'yicha tuzat": "grammar_corrector",
            "Speaking uchun og'zaki practice qilaylik": "speaking_coach",
            "Essay yozganimga feedback ber": "writing_feedback",
            "Keyingi dars qaysi?": "course_navigator",
            "Progressim qanday, reja tuz": "student_progress_coach",
            "Bugun motivatsiya ber": "general_chat",
            "Bugungi yangiliklarni qidirib ber": "web_search",
            "Dollar kursi qancha hozir": "web_search",
            "Internetdan izlab ber: Tashkentda ob-havo": "web_search",
        }

        for question, expected_slug in cases.items():
            skill = registry.select_for_request(
                AIRequest(room=None, student=self.student, user_question=question)
            )
            self.assertEqual(skill.slug, expected_slug, question)

    def test_skill_registry_medium_effort_routes_time_info_pair_without_explicit_keyword(self):
        """Medium rejimda vaqt + ma'lumot juftligi alohida keyword bo'lmasa ham web_search'ga ketadi."""
        registry = SkillRegistry()
        self.student.ai_web_search_effort = "medium"

        cases = [
            "Hozir kim chempion bo'lib turibdi",
            "Kechagi natija nima bo'ldi",
            "Endi qaerda yashaydi",
        ]
        for question in cases:
            skill = registry.select_for_request(
                AIRequest(room=None, student=self.student, user_question=question)
            )
            self.assertEqual(skill.slug, "web_search", question)

    def test_skill_registry_medium_effort_skips_time_without_info_signal(self):
        """Vaqt belgisi bor lekin INFO_HINTS yo'q bo'lsa, pair-detection ishlamaydi."""
        registry = SkillRegistry()
        self.student.ai_web_search_effort = "medium"

        cases = [
            "Hozir tushuntirib ber",
            "Bugun motivatsiya ber",
            "Endi charchadim",
        ]
        for question in cases:
            skill = registry.select_for_request(
                AIRequest(room=None, student=self.student, user_question=question)
            )
            self.assertNotEqual(skill.slug, "web_search", question)

    def test_skill_registry_light_effort_ignores_pair_only_signals(self):
        """Light rejimda pair-detection ishlamaydi; faqat aniq keyword'lar trigger qiladi."""
        registry = SkillRegistry()
        self.student.ai_web_search_effort = "light"

        skill = registry.select_for_request(
            AIRequest(room=None, student=self.student, user_question="Hozir kim chempion bo'lib turibdi")
        )
        self.assertNotEqual(skill.slug, "web_search")

    def test_skill_registry_honors_valid_requested_skill(self):
        registry = SkillRegistry()

        skill = registry.select_for_request(
            AIRequest(
                room=None,
                student=self.student,
                user_question="Oddiy savol",
                requested_skill_slug="writing_feedback",
            )
        )

        self.assertEqual(skill.slug, "writing_feedback")

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
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.status, AIResponseRun.STATUS_FALLBACK)
        self.assertEqual(run.ai_message, ai_message)
        self.assertEqual(run.model_name, "")
        self.assertGreaterEqual(run.duration_ms, 0)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_records_successful_run_with_user_message(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        with suppress_ai_signal():
            user_message = Message.objects.create(room=room, sender=self.student, text="Present perfect nima?")
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question=user_message.text,
            user_message_id=user_message.id,
            client_message_id="client-123",
        )

        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.status, AIResponseRun.STATUS_SUCCEEDED)
        self.assertEqual(run.user_message, user_message)
        self.assertEqual(run.ai_message_id, message_id)
        self.assertEqual(run.client_message_id, "client-123")
        self.assertTrue(run.model_name)
        self.assertGreaterEqual(run.duration_ms, 0)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_routes_quiz_skill_and_includes_tool_context(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        _course, _module, lesson, _enrollment = self._make_course_with_lesson()
        quiz = Quiz.objects.create(title="Present Perfect Quiz", lesson=lesson)
        question = Question.objects.create(quiz=quiz, text="<p>I ____ finished my homework.</p>")
        Choice.objects.create(question=question, text="have", is_correct=True)
        Choice.objects.create(question=question, text="has", is_correct=False)
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Shu darsdan quiz tuz",
            context_lesson_id=lesson.id,
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("ACTIVE SKILL: Quiz Generator (quiz_generator)", prompt)
        self.assertIn("AGENT TOOL KONTEXTI", prompt)
        self.assertIn("[tool:lesson_context]", prompt)
        self.assertIn("[tool:quiz_context]", prompt)
        self.assertIn("Existing quiz context for lesson: Present Perfect", prompt)
        self.assertIn("Do not expose stored correct-answer flags", prompt)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.skill_slug, "quiz_generator")
        self.assertEqual(run.metadata["active_skill"], "quiz_generator")
        self.assertIn("quiz_context", run.metadata["used_tools"])

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_routes_web_search_skill_and_enables_grounding(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Bugun dollar kursi ~12 600 so'm.",
            candidates=[
                SimpleNamespace(
                    grounding_metadata=SimpleNamespace(
                        web_search_queries=["bugungi dollar kursi"],
                        grounding_chunks=[
                            SimpleNamespace(
                                web=SimpleNamespace(
                                    uri="https://example.uz/usd",
                                    title="Markaziy bank kursi",
                                )
                            )
                        ],
                    )
                )
            ],
        )

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Bugungi dollar kursi qancha, internetdan qidirib ber",
        )

        call_kwargs = mocked_client.return_value.models.generate_content.call_args.kwargs
        self.assertIn("ACTIVE SKILL: Web Search (web_search)", call_kwargs["contents"])
        self.assertIn("[tool:web_search]", call_kwargs["contents"])
        self.assertIn("config", call_kwargs)
        self.assertTrue(getattr(call_kwargs["config"], "tools", None))
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.skill_slug, "web_search")
        self.assertTrue(run.metadata.get("web_search_enabled"))
        self.assertEqual(run.metadata.get("web_search_queries"), ["bugungi dollar kursi"])
        sources = run.metadata.get("web_search_sources") or []
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "Markaziy bank kursi")
        self.assertEqual(sources[0]["uri"], "https://example.uz/usd")

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_omits_web_search_config_for_default_skill(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Javob tayyor.",
            candidates=[],
        )

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Bugun motivatsiya ber",
        )

        call_kwargs = mocked_client.return_value.models.generate_content.call_args.kwargs
        self.assertNotIn("config", call_kwargs)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertFalse(run.metadata.get("web_search_enabled"))

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_enables_grounding_for_heavy_effort_even_on_general_chat(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        self.student.ai_web_search_effort = "heavy"
        self.student.save(update_fields=["ai_web_search_effort"])
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Javob tayyor.",
            candidates=[],
        )

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Bugun motivatsiya ber",
        )

        call_kwargs = mocked_client.return_value.models.generate_content.call_args.kwargs
        self.assertIn("config", call_kwargs)
        self.assertTrue(getattr(call_kwargs["config"], "tools", None))
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertTrue(run.metadata.get("web_search_enabled"))

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_strips_inline_source_markers_and_trailing_sources_list(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        raw_reply = (
            "Bugun dollar kursi 12 600 so'm (Manba 1).\n"
            "Inflyatsiya darajasi 9.5% (Manba 1, Manba 2).\n\n"
            "Manbalar:\n"
            "- Markaziy bank (cbu.uz)\n"
            "- Statistika qo'mitasi (stat.uz)"
        )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text=raw_reply,
            candidates=[
                SimpleNamespace(
                    grounding_metadata=SimpleNamespace(
                        web_search_queries=["dollar kursi"],
                        grounding_chunks=[
                            SimpleNamespace(web=SimpleNamespace(uri="https://cbu.uz", title="CBU"))
                        ],
                    )
                )
            ],
        )

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Bugungi dollar kursi qancha, qidirib ber",
        )

        ai_message = Message.objects.get(id=message_id)
        self.assertNotIn("(Manba", ai_message.text)
        self.assertNotIn("Manbalar:", ai_message.text)
        self.assertIn("12 600 so'm", ai_message.text)
        self.assertIn("Inflyatsiya darajasi 9.5%", ai_message.text)
        run = AIResponseRun.objects.get(ai_message=ai_message)
        self.assertEqual(len(run.metadata["web_search_sources"]), 1)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_strips_leading_greeting_in_followup_message(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        with suppress_ai_signal():
            Message.objects.create(room=room, sender=self.student, text="Birinchi savol")
            Message.objects.create(room=room, text="Birinchi javob", is_ai_response=True)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Salom, Aziz! 😊\n\nXitoyda Tiananmen voqealari 1989-yilda bo'lib o'tgan.",
            candidates=[],
        )

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Tiananmen voqealari qachon bo'lgan",
        )

        ai_message = Message.objects.get(id=message_id)
        self.assertNotIn("Salom, Aziz", ai_message.text)
        self.assertTrue(ai_message.text.startswith("Xitoyda Tiananmen"))
        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("DIQQAT: bu davomli suhbat", prompt)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_keeps_greeting_in_first_message(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Salom! Bugun nima qilamiz? 😊",
            candidates=[],
        )

        message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Salom",
        )

        ai_message = Message.objects.get(id=message_id)
        self.assertTrue(ai_message.text.startswith("Salom"))
        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("BIRINCHI javobingiz", prompt)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_routes_homework_skill_with_submission_context(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        _course, _module, lesson, _enrollment = self._make_course_with_lesson(lesson_title="Daily Routine")
        assignment = Assignment.objects.create(
            lesson=lesson,
            title="Write your routine",
            description="<p>Write five sentences about your daily routine.</p>",
        )
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            answer_text="I wakes up at seven and go to school.",
            status=AssignmentSubmission.STATUS_PENDING,
        )
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Vazifamni tekshirib ber",
            context_lesson_id=lesson.id,
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("ACTIVE SKILL: Homework Checker (homework_checker)", prompt)
        self.assertIn("[tool:homework_context]", prompt)
        self.assertIn("Student draft excerpt: I wakes up at seven and go to school.", prompt)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.skill_slug, "homework_checker")
        self.assertIn("homework_context", run.metadata["used_tools"])

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_routes_progress_skill_with_progress_tool(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        _course, module, lesson, enrollment = self._make_course_with_lesson(lesson_title="First Lesson")
        Lesson.objects.create(module=module, title="Second Lesson", content="Next topic", order=2)
        LessonProgress.objects.create(enrollment=enrollment, lesson=lesson, is_completed=True)
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Progressim qanday, reja tuz",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("ACTIVE SKILL: Student Progress Coach (student_progress_coach)", prompt)
        self.assertIn("[tool:student_progress]", prompt)
        self.assertIn("1/2 lessons completed", prompt)
        self.assertIn("Suggested next lesson by progress: Module 1 -> Second Lesson", prompt)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.skill_slug, "student_progress_coach")
        self.assertIn("student_progress", run.metadata["used_tools"])

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_honors_requested_skill_slug(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Oddiy savol",
            requested_skill_slug="grammar_corrector",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("ACTIVE SKILL: Grammar Corrector (grammar_corrector)", prompt)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.skill_slug, "grammar_corrector")
        self.assertEqual(run.metadata["requested_skill"], "grammar_corrector")

    @patch("messenger.tasks.logger.exception")
    @patch("messenger.tasks.Message.objects.create", side_effect=RuntimeError("db write failed"))
    @patch("messenger.tasks.AIEngine.generate_reply")
    def test_generate_ai_response_records_failed_run_when_message_create_fails(
        self,
        mocked_generate_reply,
        _mocked_message_create,
        mocked_logger_exception,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_generate_reply.return_value = SimpleNamespace(
            text="Javob tayyor.",
            model_name="gemini-test",
            skill_slug="general_chat",
            metadata={},
        )

        result = generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="salom")

        self.assertIsNone(result)
        run = AIResponseRun.objects.get(room=room, student=self.student)
        self.assertEqual(run.status, AIResponseRun.STATUS_FAILED)
        self.assertIn("db write failed", run.error_message)
        self.assertGreaterEqual(run.duration_ms, 0)
        mocked_logger_exception.assert_called()

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
        self.assertIn("last_seen_at", memory.metadata)
        trace = AIMemoryTrace.objects.get(user=self.student, event_type=AIMemoryTrace.EVENT_SAVED)
        self.assertIn("SAVE_MEMORY", trace.reason)
        self.assertTrue(trace.metadata["quality_eval"]["passed"])

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
    def test_generate_ai_response_uses_semantic_alias_memory_scoring(
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
            value="Python funksiyalar mavzusida qiynalyapti",
            fingerprint="test-semantic-functions",
        )
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_SCHEDULE,
            key="schedule:evening",
            value="Kechqurun o'qishni afzal ko'radi",
            fingerprint="test-semantic-schedule",
        )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="def qanday ishlaydi?",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("[weak_topic] Python funksiyalar mavzusida qiynalyapti", prompt)
        trace = AIMemoryTrace.objects.filter(
            user=self.student,
            event_type=AIMemoryTrace.EVENT_RETRIEVED,
        ).latest("created_at")
        self.assertIn("semantic_overlap", " ".join(trace.metadata["selected"][0]["reasons"]))

    @patch("ai.memory.semantic.embed_texts", return_value=[[1.0, 0.0]])
    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_uses_vector_memory_score_when_embeddings_exist(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
        _mocked_embed_texts,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_WEAK_TOPIC,
            key="weak_topic:pronunciation",
            value="Mandarin pronunciation practice",
            fingerprint="test-vector-pronunciation",
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_OTHER,
            key="other:billing",
            value="Billing portal details",
            fingerprint="test-vector-billing",
            embedding=[0.0, 1.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="completely unrelated query",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertLess(
            prompt.index("Mandarin pronunciation practice"),
            prompt.index("Billing portal details"),
        )
        trace = AIMemoryTrace.objects.filter(
            user=self.student,
            event_type=AIMemoryTrace.EVENT_RETRIEVED,
        ).latest("created_at")
        self.assertIn("semantic_vector", " ".join(trace.metadata["selected"][0]["reasons"]))

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

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_summarizes_older_dialogue_in_prompt(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        with suppress_ai_signal():
            for index in range(1, 15):
                Message.objects.create(
                    room=room,
                    sender=self.student if index % 2 else None,
                    text=f"Topic {index} haqida gaplashdik",
                    is_ai_response=index % 2 == 0,
                )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Davom etamiz.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Davom ettir",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        summary = AIConversationSummary.objects.get(room=room)
        self.assertEqual(summary.covered_message_count, 6)
        self.assertIn("Suhbat summarysi", prompt)
        self.assertIn("Oldingi suhbat qisqa mazmuni", prompt)
        self.assertIn("Topic 1 haqida gaplashdik", prompt)
        self.assertIn("Topic 14 haqida gaplashdik", prompt)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_does_not_persist_summary_when_memory_disabled(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        self.student.ai_memory_enabled = False
        self.student.save(update_fields=["ai_memory_enabled"])
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        with suppress_ai_signal():
            for index in range(1, 15):
                Message.objects.create(
                    room=room,
                    sender=self.student if index % 2 else None,
                    text=f"Disabled memory topic {index}",
                    is_ai_response=index % 2 == 0,
                )
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(text="Javob tayyor.")

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Davom ettir",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertFalse(AIConversationSummary.objects.filter(room=room).exists())
        self.assertIn("Suhbat summarysi", prompt)
        self.assertNotIn("ai-student: Disabled memory topic 1\n", prompt)
        self.assertIn("Disabled memory topic 14", prompt)

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_archives_conflicting_memory_slot(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        mocked_client.return_value.models.generate_content.side_effect = [
            SimpleNamespace(text="<SAVE_MEMORY>preference: Qisqa javoblarni yoqtiradi</SAVE_MEMORY>Mayli."),
            SimpleNamespace(text="<SAVE_MEMORY>preference: Batafsil javoblarni yoqtiradi</SAVE_MEMORY>Mayli."),
        ]

        generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="Qisqa javob ber")
        generate_ai_response.run(room_id=room.id, student_id=self.student.id, user_question="Endi batafsil javob ber")

        active = AIMemoryFact.objects.get(user=self.student, status=AIMemoryFact.STATUS_ACTIVE)
        archived = AIMemoryFact.objects.get(user=self.student, status=AIMemoryFact.STATUS_ARCHIVED)
        self.assertEqual(active.key, "preference:answer_length")
        self.assertEqual(archived.key, "preference:answer_length")
        self.assertEqual(active.value, "Batafsil javoblarni yoqtiradi")
        self.assertEqual(archived.value, "Qisqa javoblarni yoqtiradi")

    def test_first_prompt_can_name_ai_room(self):
        room = ChatRoom.objects.create(room_type="ai", name="Yangi AI chat")
        room.participants.add(self.student)
        with suppress_ai_signal():
            Message.objects.create(room=room, sender=self.student, text="Past simple va present perfect farqi nima?")

        renamed = maybe_name_ai_room_from_first_prompt(room, "Past simple va present perfect farqi nima?")

        self.assertTrue(renamed)
        room.refresh_from_db()
        self.assertEqual(room.name, "Past simple va present perfect farqi nima")

    @patch("ai.rag.context.retrieve_relevant_chunks", return_value=[])
    @patch("ai.providers.gemini.genai.Client")
    def test_generate_ai_response_skips_memory_when_user_disabled_it(
        self,
        mocked_client,
        _mocked_retrieve_chunks,
    ):
        self.student.ai_memory_enabled = False
        self.student.save(update_fields=["ai_memory_enabled"])
        room = ChatRoom.objects.create(room_type="ai", name="Azure AI - ai-student")
        room.participants.add(self.student)
        AIMemoryFact.objects.create(
            user=self.student,
            category=AIMemoryFact.CATEGORY_PROFILE,
            key="profile:disabled",
            value="Eski fakt eslab qolingan",
            fingerprint="test-disabled-profile",
        )
        AILongTermMemory.objects.create(user=self.student, learned_facts="- Legacy ham bo'lsin")
        mocked_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Tushundim. <SAVE_MEMORY>profile: Yangi fakt</SAVE_MEMORY>"
        )

        generate_ai_response.run(
            room_id=room.id,
            student_id=self.student.id,
            user_question="Profil yangilab qo'y",
        )

        prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertNotIn("Eski fakt eslab qolingan", prompt)
        self.assertNotIn("Legacy ham bo'lsin", prompt)
        self.assertNotIn("Legacy memory:", prompt)
        self.assertEqual(AIMemoryFact.objects.filter(user=self.student).count(), 1)


class AIMemoryControlTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="memory-control-student",
            email="memory-control@example.com",
            password="testpass123",
        )
        self.client.force_login(self.student)

    def _make_fact(self, value, category=None, fingerprint=None):
        return AIMemoryFact.objects.create(
            user=self.student,
            category=category or AIMemoryFact.CATEGORY_PROFILE,
            key=f"{category or AIMemoryFact.CATEGORY_PROFILE}:{value[:20]}",
            value=value,
            fingerprint=fingerprint or value,
        )

    def test_toggle_off_disables_memory_and_persists(self):
        self.assertTrue(self.student.ai_memory_enabled)

        response = self.client.post(
            reverse("ai_memory_toggle"),
            data={"ai_memory_enabled": "0"},
        )

        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertFalse(self.student.ai_memory_enabled)

    def test_toggle_endpoint_returns_json_for_ajax(self):
        response = self.client.post(
            reverse("ai_memory_toggle"),
            data={"ai_memory_enabled": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "ai_memory_enabled": True})

    def test_archive_view_soft_deletes_fact_for_user_but_keeps_row(self):
        fact = self._make_fact("Past simple ni yaxshi biladi", fingerprint="fp-archive-one")

        response = self.client.post(reverse("ai_memory_archive", args=[fact.id]))

        self.assertEqual(response.status_code, 302)
        fact.refresh_from_db()
        self.assertEqual(fact.status, AIMemoryFact.STATUS_ARCHIVED)
        active_for_user = AIMemoryFact.objects.filter(
            user=self.student,
            status=AIMemoryFact.STATUS_ACTIVE,
        )
        self.assertFalse(active_for_user.exists())
        self.assertTrue(AIMemoryFact.objects.filter(id=fact.id).exists())

    def test_archive_ignores_other_user_facts(self):
        other = User.objects.create_user(
            username="other-student",
            email="other@example.com",
            password="testpass123",
        )
        foreign_fact = AIMemoryFact.objects.create(
            user=other,
            category=AIMemoryFact.CATEGORY_PROFILE,
            key="profile:foreign",
            value="Foreign user fakti",
            fingerprint="fp-foreign",
        )

        self.client.post(reverse("ai_memory_archive", args=[foreign_fact.id]))

        foreign_fact.refresh_from_db()
        self.assertEqual(foreign_fact.status, AIMemoryFact.STATUS_ACTIVE)

    def test_clear_all_archives_active_and_clears_legacy(self):
        self._make_fact("Fact A", fingerprint="fp-clear-a")
        self._make_fact("Fact B", category=AIMemoryFact.CATEGORY_PREFERENCE, fingerprint="fp-clear-b")
        AILongTermMemory.objects.create(user=self.student, learned_facts="- eski qator")

        response = self.client.post(reverse("ai_memory_clear"))

        self.assertEqual(response.status_code, 302)
        active = AIMemoryFact.objects.filter(user=self.student, status=AIMemoryFact.STATUS_ACTIVE)
        archived = AIMemoryFact.objects.filter(user=self.student, status=AIMemoryFact.STATUS_ARCHIVED)
        self.assertEqual(active.count(), 0)
        self.assertEqual(archived.count(), 2)
        legacy = AILongTermMemory.objects.get(user=self.student)
        self.assertEqual(legacy.learned_facts, "")

    def test_list_page_groups_facts_by_category(self):
        self._make_fact("Beginner darajada", fingerprint="fp-list-profile")
        self._make_fact(
            "IELTS 7.0 olishni xohlaydi",
            category=AIMemoryFact.CATEGORY_LEARNING_GOAL,
            fingerprint="fp-list-goal",
        )

        response = self.client.get(reverse("ai_memory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beginner darajada")
        self.assertContains(response, "IELTS 7.0 olishni xohlaydi")
        self.assertContains(response, "Saqlangan faktlar (2)")

    def test_reject_view_marks_fact_rejected_and_records_trace(self):
        fact = self._make_fact("Birinchi tilim turkcha", fingerprint="fp-reject-one")

        response = self.client.post(reverse("ai_memory_reject", args=[fact.id]))

        self.assertEqual(response.status_code, 302)
        fact.refresh_from_db()
        self.assertEqual(fact.status, AIMemoryFact.STATUS_REJECTED)
        self.assertEqual(fact.confidence, 0.0)
        self.assertIn("rejected_by_user_at", fact.metadata)
        trace = AIMemoryTrace.objects.filter(
            user=self.student,
            fact=fact,
            event_type=AIMemoryTrace.EVENT_ARCHIVED,
        ).first()
        self.assertIsNotNone(trace)
        self.assertEqual(trace.metadata.get("action"), "user_reject")

    def test_reject_ignores_other_user_facts(self):
        other = User.objects.create_user(
            username="reject-other",
            email="reject-other@example.com",
            password="testpass123",
        )
        foreign_fact = AIMemoryFact.objects.create(
            user=other,
            category=AIMemoryFact.CATEGORY_PROFILE,
            key="profile:foreign-reject",
            value="Foreign user fakti reject",
            fingerprint="fp-reject-foreign",
        )

        self.client.post(reverse("ai_memory_reject", args=[foreign_fact.id]))

        foreign_fact.refresh_from_db()
        self.assertEqual(foreign_fact.status, AIMemoryFact.STATUS_ACTIVE)
        self.assertEqual(foreign_fact.confidence, 0.8)

    def test_reject_endpoint_returns_json_for_ajax(self):
        fact = self._make_fact("JSON reject test", fingerprint="fp-reject-json")

        response = self.client.post(
            reverse("ai_memory_reject", args=[fact.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})

    def test_list_page_renders_report_stats_and_reject_button(self):
        fact = self._make_fact("Hisobot uchun fakt", fingerprint="fp-report-fact")

        response = self.client.get(reverse("ai_memory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Xotira hisoboti")
        self.assertContains(response, "Faol fakt")
        self.assertContains(response, "Promptga olingan")
        self.assertContains(response, reverse("ai_memory_reject", args=[fact.id]))
        self.assertContains(response, "Noto'g'ri")

    def test_maintenance_archives_stale_fact_after_prior_decay_write(self):
        from ai.memory.repository import MemoryRepository

        repo = MemoryRepository()
        now = timezone.now()
        first_seen_at = now - datetime.timedelta(days=179)
        fact = self._make_fact("Juda eski lekin ilgari decay qilingan fakt", fingerprint="fp-stale-decay")
        AIMemoryFact.objects.filter(id=fact.id).update(
            confidence=0.8,
            created_at=first_seen_at,
            updated_at=first_seen_at,
            metadata={"last_seen_at": first_seen_at.isoformat()},
        )

        first_report = repo.maintain_user_memory(user=self.student, now=now)
        fact.refresh_from_db()

        self.assertEqual(first_report, {"decayed": 1, "archived": 0})
        self.assertEqual(fact.status, AIMemoryFact.STATUS_ACTIVE)
        self.assertLess(fact.confidence, 0.8)

        second_report = repo.maintain_user_memory(
            user=self.student,
            now=first_seen_at + datetime.timedelta(days=181),
        )
        fact.refresh_from_db()

        self.assertEqual(second_report, {"decayed": 0, "archived": 1})
        self.assertEqual(fact.status, AIMemoryFact.STATUS_ARCHIVED)
        self.assertTrue(
            AIMemoryTrace.objects.filter(
                user=self.student,
                fact=fact,
                event_type=AIMemoryTrace.EVENT_ARCHIVED,
                metadata__action="auto_archive_stale",
            ).exists()
        )


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
        with suppress_ai_signal():
            user_message = Message.objects.create(
                room=self.room,
                sender=self.student,
                text="Javobni qayta yoz",
            )
        AIResponseRun.objects.create(
            room=self.room,
            student=self.student,
            user_message=user_message,
            ai_message=self.ai_message,
            user_question=user_message.text,
            status=AIResponseRun.STATUS_SUCCEEDED,
            skill_slug="quiz_generator",
            metadata={"used_tools": ["lesson_context", "quiz_context"]},
        )
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
        self.assertEqual(message_payload["regenerate_user_message_id"], user_message.id)
        self.assertEqual(message_payload["ai_skill_slug"], "quiz_generator")
        self.assertEqual(message_payload["ai_skill_label"], "Quiz Generator")
        self.assertEqual(message_payload["ai_used_tools"], ["lesson_context", "quiz_context"])

    def test_ai_room_page_renders_feedback_controls_for_existing_ai_messages(self):
        with suppress_ai_signal():
            user_message = Message.objects.create(
                room=self.room,
                sender=self.student,
                text="Javobni qayta yoz",
            )
        AIResponseRun.objects.create(
            room=self.room,
            student=self.student,
            user_message=user_message,
            ai_message=self.ai_message,
            user_question=user_message.text,
            status=AIResponseRun.STATUS_SUCCEEDED,
            skill_slug="homework_checker",
            metadata={"used_tools": ["homework_context"]},
        )
        AIFeedback.objects.create(
            message=self.ai_message,
            student=self.student,
            rating=AIFeedback.RATING_NEGATIVE,
            comment="Aniqroq bo'lsin",
        )
        AIFeedback.objects.create(
            message=self.ai_message,
            student=self.peer,
            rating=AIFeedback.RATING_POSITIVE,
            comment="Foydali",
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse("messenger:ai_room", args=[self.room.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ai-feedback')
        self.assertContains(response, f'data-message-id="{self.ai_message.id}"')
        self.assertContains(response, 'data-user-rating="-1"')
        self.assertContains(response, 'data-copy-message')
        self.assertContains(response, 'data-regenerate-message')
        self.assertContains(response, f'data-user-message-id="{user_message.id}"')
        self.assertContains(response, 'data-feedback-positive>1</span>')
        self.assertContains(response, 'data-feedback-negative>1</span>')
        self.assertContains(response, "Homework Checker")
        self.assertContains(response, "homework_context")
        self.assertContains(response, "feedback-btn--skill")
        self.assertNotContains(response, "message-ai-run")
        self.assertContains(response, 'data-ai-skill-option="quiz_generator"')
        self.assertContains(response, 'data-ai-skill-option="writing_feedback"')


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

    @patch("messenger.rag.embed_texts", return_value=[[1.0, 0.0]])
    def test_retrieval_scopes_current_lesson_to_its_module(self, _mocked_embed_texts):
        other_module = Module.objects.create(course=self.course, title="Other Module", order=2)
        other_lesson = Lesson.objects.create(
            module=other_module,
            title="Other Module Lesson",
            content="Different module topic",
            order=1,
        )

        LessonRAGChunk.objects.create(
            lesson=self.lesson,
            course=self.course,
            chunk_index=0,
            chunk_text="Python funksiyasi qiymat qaytaradi.",
            chunk_hash="chunk-context-1",
            content_hash="content-context-1",
            token_count=5,
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )
        LessonRAGChunk.objects.create(
            lesson=other_lesson,
            course=self.course,
            chunk_index=0,
            chunk_text="Boshqa moduldagi mavzu.",
            chunk_hash="chunk-context-2",
            content_hash="content-context-2",
            token_count=4,
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )

        chunks = retrieve_relevant_chunks(
            user=self.student,
            question="funksiya nimani qaytaradi",
            context_lesson=self.lesson,
            top_k=4,
        )

        self.assertEqual({chunk["module_id"] for chunk in chunks}, {self.module.id})
        self.assertEqual(chunks[0]["module_title"], "Module 1")
        self.assertIn("RAG Course", chunks[0]["source_label"])

    def test_rag_index_status_reports_missing_lessons(self):
        LessonRAGChunk.objects.filter(lesson=self.lesson).delete()
        status = get_rag_index_status()

        self.assertEqual(status["eligible_lessons"], 1)
        self.assertEqual(status["missing_lessons"], 1)
        self.assertEqual(status["ready_lessons"], 0)
        self.assertIn("reindex_rag", status["index_command"])

    def test_pgvector_setup_skips_on_non_postgres(self):
        result = ensure_pgvector_schema(backfill=False)
        self.assertEqual(result.get("status"), "skipped_non_postgres")
