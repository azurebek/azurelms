import base64
import datetime
import asyncio
from unittest.mock import AsyncMock, patch

from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.test import TestCase
from django.utils import timezone

from bot.models import TelegramLessonCheckIn, TelegramLessonSession
from bot.services import (
    bind_chat_to_cohort,
    close_lesson_session,
    link_user_from_start_token,
    register_checkin,
    start_lesson_session,
)
from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module
from users.models import Notification


User = get_user_model()


class RunBotCommandTests(TestCase):
    @patch("bot.management.commands.runbot.get_dispatcher")
    @patch("bot.management.commands.runbot.get_bot")
    def test_runbot_uses_lazy_bot_and_dispatcher(self, mocked_get_bot, mocked_get_dispatcher):
        from bot.management.commands.runbot import Command

        mocked_bot = mocked_get_bot.return_value
        mocked_bot.delete_webhook = AsyncMock()
        mocked_dispatcher = mocked_get_dispatcher.return_value
        mocked_dispatcher.start_polling = AsyncMock()

        asyncio.run(Command().run_bot())

        mocked_bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
        mocked_dispatcher.start_polling.assert_awaited_once_with(mocked_bot)


class TelegramBotFlowTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="tg-teacher",
            email="tg-teacher@example.com",
            password="testpass123",
            is_staff=True,
            telegram_id=1001,
        )
        self.student_present = User.objects.create_user(
            username="tg-present",
            email="tg-present@example.com",
            password="testpass123",
            telegram_id=2001,
        )
        self.student_partial = User.objects.create_user(
            username="tg-partial",
            email="tg-partial@example.com",
            password="testpass123",
            telegram_id=2002,
        )
        self.student_absent = User.objects.create_user(
            username="tg-absent",
            email="tg-absent@example.com",
            password="testpass123",
            telegram_id=2003,
        )
        self.unlinked_user = User.objects.create_user(
            username="tg-unlinked",
            email="tg-unlinked@example.com",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Telegram Attendance Course",
            description="Course for telegram attendance tests",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="Modul 1", order=1)
        self.lesson_1 = Lesson.objects.create(module=self.module, title="Dars 1", order=1, xp_reward=10)
        self.lesson_2 = Lesson.objects.create(module=self.module, title="Dars 2", order=2, xp_reward=10)
        self.cohort = Cohort.objects.create(
            name="Telegram Cohort",
            course=self.course,
            start_date="2026-03-26",
            is_active=True,
        )
        self.present_enrollment = Enrollment.objects.create(
            student=self.student_present,
            cohort=self.cohort,
            status="active",
        )
        self.partial_enrollment = Enrollment.objects.create(
            student=self.student_partial,
            cohort=self.cohort,
            status="active",
        )
        self.absent_enrollment = Enrollment.objects.create(
            student=self.student_absent,
            cohort=self.cohort,
            status="active",
        )

    def _make_start_token(self, user):
        raw_token = Signer().sign(str(user.id))
        return base64.urlsafe_b64encode(raw_token.encode()).decode().rstrip("=")

    def test_start_token_link_saves_telegram_fields_and_notification(self):
        token = self._make_start_token(self.unlinked_user)

        result = link_user_from_start_token(token, 999001, "local_test_user")

        self.assertTrue(result.ok)
        self.unlinked_user.refresh_from_db()
        self.assertEqual(self.unlinked_user.telegram_id, 999001)
        self.assertEqual(self.unlinked_user.telegram_username, "local_test_user")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.unlinked_user,
                title="Telegram hisobi ulandi",
            ).exists()
        )

    def test_link_cohort_binds_group_chat_metadata(self):
        result = bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )

        self.assertTrue(result.ok)
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.telegram_chat_id, -1001234567890)
        self.assertEqual(self.cohort.telegram_chat_title, "A1 Evening Group")

    def test_start_session_and_checkin_flow(self):
        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )

        start_result = start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        checkin_result = register_checkin(
            session_id=start_result.session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )

        self.assertTrue(start_result.ok)
        self.assertEqual(start_result.lesson_index, 1)
        self.assertEqual(start_result.session.lesson, self.lesson_1)
        self.assertTrue(checkin_result.ok)
        self.assertEqual(checkin_result.code, "checked_in")
        self.assertEqual(
            TelegramLessonCheckIn.objects.filter(session=start_result.session).count(),
            1,
        )

        duplicate_result = register_checkin(
            session_id=start_result.session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )
        self.assertTrue(duplicate_result.ok)
        self.assertEqual(duplicate_result.code, "already_checked_in")

    def test_close_session_writes_present_partial_and_absent_attendance(self):
        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )
        start_result = start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        session = start_result.session
        session.started_at = timezone.now() - datetime.timedelta(minutes=30)
        session.save(update_fields=["started_at"])

        register_checkin(
            session_id=session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )
        present_checkin = TelegramLessonCheckIn.objects.get(session=session, enrollment=self.present_enrollment)
        present_checkin.checked_in_at = session.started_at + datetime.timedelta(minutes=5)
        present_checkin.save(update_fields=["checked_in_at"])

        register_checkin(
            session_id=session.id,
            telegram_user_id=self.student_partial.telegram_id,
            telegram_username="student_partial",
        )

        close_result = close_lesson_session(
            chat_id=-1001234567890,
            actor_telegram_id=self.teacher.telegram_id,
        )

        self.assertTrue(close_result.ok)
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramLessonSession.STATUS_CLOSED)

        present_record = Attendance.objects.get(
            enrollment=self.present_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )
        partial_record = Attendance.objects.get(
            enrollment=self.partial_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )
        absent_record = Attendance.objects.get(
            enrollment=self.absent_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )

        self.assertEqual(present_record.status, Attendance.STATUS_PRESENT)
        self.assertEqual(partial_record.status, Attendance.STATUS_PARTIAL)
        self.assertEqual(absent_record.status, Attendance.STATUS_ABSENT)
        self.assertEqual(close_result.summary[Attendance.STATUS_PRESENT], 1)
        self.assertEqual(close_result.summary[Attendance.STATUS_PARTIAL], 1)
        self.assertEqual(close_result.summary[Attendance.STATUS_ABSENT], 1)

    def test_close_session_returns_named_details_and_notifies_absent(self):
        """Davomat v2: yopishda ismli ro'yxatlar + kelmaganga platforma-bildirishnoma."""
        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )
        start_result = start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        register_checkin(
            session_id=start_result.session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )

        close_result = close_lesson_session(
            chat_id=-1001234567890,
            actor_telegram_id=self.teacher.telegram_id,
        )

        self.assertTrue(close_result.ok)
        details = close_result.details
        present_names = [i["name"] for i in details[Attendance.STATUS_PRESENT]]
        absent_names = [i["name"] for i in details[Attendance.STATUS_ABSENT]]
        self.assertIn("tg-present", present_names)
        self.assertIn("tg-absent", absent_names)
        self.assertIn("tg-partial", absent_names)  # check-in qilmagan

        absent_item = next(i for i in details[Attendance.STATUS_ABSENT] if i["name"] == "tg-absent")
        self.assertEqual(absent_item["telegram_id"], 2003)

        # Platforma-bildirishnoma yozildi (idempotent external_key bilan)
        note = Notification.objects.get(
            recipient=self.student_absent,
            external_key=f"tg-absent-{close_result.session.id}",
        )
        self.assertIn("davomatga belgilanmadingiz", note.message)
        self.assertIn(f"/lesson/{self.lesson_1.id}/", note.url)

    def test_open_session_status_query(self):
        from bot.services import get_open_session_status

        missing = get_open_session_status(chat_id=-1001234567890)
        self.assertFalse(missing.ok)

        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )
        start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        register_checkin(
            session_id=TelegramLessonSession.objects.get(chat_id=-1001234567890).id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )

        status = get_open_session_status(chat_id=-1001234567890)
        self.assertTrue(status.ok)
        self.assertEqual(status.checkin_count, 1)
        self.assertIn("tg-present", status.checkin_names)


class GroupOpsRenderingTests(TestCase):
    """group_ops router'ining sof (tarmoqsiz) yordamchi funksiyalari."""

    def test_parse_dars_args(self):
        from bot.routers.group_ops import parse_dars_args

        self.assertEqual(parse_dars_args("1"), ("start", "1"))
        self.assertEqual(parse_dars_args("  3  "), ("start", "3"))
        self.assertEqual(parse_dars_args("tugadi"), ("close", None))
        self.assertEqual(parse_dars_args("TUGADI"), ("close", None))
        self.assertEqual(parse_dars_args("tamom"), ("close", None))
        self.assertEqual(parse_dars_args(""), ("usage", None))
        self.assertEqual(parse_dars_args(None), ("usage", None))

    def test_render_close_announcement_mentions_absent(self):
        from types import SimpleNamespace

        from bot.routers.group_ops import render_close_announcement

        session = SimpleNamespace(
            lesson=SimpleNamespace(title="Dars 1"),
            attendance_date=datetime.date(2026, 7, 12),
        )
        summary = {"present": 1, "partial": 0, "absent": 2, "total": 3}
        details = {
            "present": [{"name": "Aziza", "telegram_id": 1, "telegram_username": "aziza"}],
            "partial": [],
            "absent": [
                {"name": "Bekzod", "telegram_id": 2, "telegram_username": "bekzod_t"},
                {"name": "Malika <X>", "telegram_id": 3, "telegram_username": ""},
            ],
        }

        text = render_close_announcement(session, summary, details)

        self.assertIn("Aziza", text)
        self.assertIn("@bekzod_t", text)  # username bor → @mention
        self.assertIn('tg://user?id=3', text)  # username yo'q → id-link
        self.assertIn("Malika &lt;X&gt;", text)  # HTML escape
        self.assertIn("Keldi (1)", text)
        self.assertIn("Kelmadi (2)", text)

    def test_render_close_announcement_all_present(self):
        from types import SimpleNamespace

        from bot.routers.group_ops import render_close_announcement

        session = SimpleNamespace(
            lesson=SimpleNamespace(title="Dars 1"),
            attendance_date=datetime.date(2026, 7, 12),
        )
        text = render_close_announcement(
            session,
            {"present": 2, "partial": 0, "absent": 0, "total": 2},
            {"present": [{"name": "A", "telegram_id": 1, "telegram_username": ""},
                         {"name": "B", "telegram_id": 2, "telegram_username": ""}],
             "partial": [], "absent": []},
        )
        self.assertIn("Hamma darsda", text)
        self.assertNotIn("Kelmadi", text)

    def test_render_absent_dm_contains_lesson_link(self):
        from types import SimpleNamespace

        from bot.routers.group_ops import render_absent_dm

        session = SimpleNamespace(
            lesson=SimpleNamespace(title="Alifbo"),
            lesson_id=7,
            attendance_date=datetime.date(2026, 7, 12),
            cohort=SimpleNamespace(course_id=4),
        )
        text = render_absent_dm(session)
        self.assertIn("Alifbo", text)
        self.assertIn("/courses/4/lesson/7/", text)
        self.assertIn("Darsni qoldirdingiz", text)


class OnboardingServiceTests(TestCase):
    """F2 — mehmon xizmatlari: ro'yxat, AI demo limiti, katalog."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="onb-teacher", email="onb-teacher@example.com", password="x",
        )
        Course.objects.create(
            title="Turk tili A1", description="<p>Boshlang'ich kurs</p>",
            instructor=self.instructor, level="beginner", is_active=True,
        )
        Course.objects.create(
            title="Yashirin kurs", description="t",
            instructor=self.instructor, level="beginner", is_active=False,
        )

    def test_list_public_courses_only_active_and_strips_html(self):
        from bot.services import list_public_courses

        courses = list_public_courses()
        titles = [c["title"] for c in courses]
        self.assertIn("Turk tili A1", titles)
        self.assertNotIn("Yashirin kurs", titles)
        course = next(c for c in courses if c["title"] == "Turk tili A1")
        self.assertEqual(course["description"], "Boshlang'ich kurs")

    def test_phone_register_creates_and_links(self):
        from bot.services import register_guest_via_phone

        result = register_guest_via_phone(
            telegram_id=7001, telegram_username="yangi_user",
            phone="+998 90 123-45-67", first_name="Yangi", last_name="User",
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.created)
        user = result.user
        self.assertEqual(user.phone_number, "+998901234567")
        self.assertEqual(user.telegram_id, 7001)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(Notification.objects.filter(recipient=user).exists())

        # Ikkinchi marta — allaqachon bog'langan
        again = register_guest_via_phone(
            telegram_id=7001, telegram_username="yangi_user", phone="+998901234567",
        )
        self.assertTrue(again.ok)
        self.assertEqual(again.code, "already_linked")

    def test_phone_register_links_existing_account_by_phone(self):
        from bot.services import register_guest_via_phone

        existing = User.objects.create_user(
            username="site-user", email="site@example.com",
            password="x", phone_number="+998911112233",
        )
        result = register_guest_via_phone(
            telegram_id=7002, telegram_username="site_tg", phone="911112233",
        )
        self.assertTrue(result.ok)
        self.assertFalse(result.created)
        existing.refresh_from_db()
        self.assertEqual(existing.telegram_id, 7002)

    def test_phone_register_rejects_foreign_linked_phone(self):
        from bot.services import register_guest_via_phone

        User.objects.create_user(
            username="taken", email="taken@example.com", password="x",
            phone_number="+998900000001", telegram_id=8888,
        )
        result = register_guest_via_phone(
            telegram_id=7003, telegram_username="x", phone="+998900000001",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "phone_taken")

    def test_phone_register_two_guests_no_email_collision(self):
        """email unique=True — ikki telefon-ro'yxat ''-email to'qnashuvisiz o'tishi shart."""
        from bot.services import register_guest_via_phone

        # Bazada allaqachon bo'sh-email user bor deb simulyatsiya qilamiz
        User.objects.create(username="legacy-empty-email", email="")

        first = register_guest_via_phone(telegram_id=7101, telegram_username="a", phone="+998901111111")
        second = register_guest_via_phone(telegram_id=7102, telegram_username="b", phone="+998902222222")

        self.assertTrue(first.ok, msg=first.message)
        self.assertTrue(second.ok, msg=second.message)
        self.assertNotEqual(first.user.email, second.user.email)
        self.assertTrue(first.user.email)

    def test_normalize_phone(self):
        from bot.services import normalize_phone

        self.assertEqual(normalize_phone("+998 90 123-45-67"), "+998901234567")
        self.assertEqual(normalize_phone("901234567"), "+998901234567")
        self.assertEqual(normalize_phone(""), "")

    def test_guest_demo_limit(self):
        from types import SimpleNamespace

        from bot.models import BotGuest
        from bot.services import GUEST_DEMO_QUESTION_LIMIT, guest_demo_answer

        fake_provider = SimpleNamespace(
            generate=lambda **kw: SimpleNamespace(text="Salom! Kurslar haqida...")
        )

        for i in range(GUEST_DEMO_QUESTION_LIMIT):
            result = guest_demo_answer(9001, "demo_guest", f"Savol {i}", provider=fake_provider)
            self.assertTrue(result.ok, msg=f"savol {i} rad etildi")
        self.assertEqual(result.remaining, 0)

        blocked = guest_demo_answer(9001, "demo_guest", "Yana savol", provider=fake_provider)
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.code, "limit_reached")
        self.assertEqual(
            BotGuest.objects.get(telegram_id=9001).demo_questions_used,
            GUEST_DEMO_QUESTION_LIMIT,
        )

    def test_guest_demo_provider_error_does_not_consume_quota(self):
        from types import SimpleNamespace

        from bot.models import BotGuest
        from bot.services import guest_demo_answer

        def boom(**kw):
            raise RuntimeError("down")

        result = guest_demo_answer(9002, "g", "Savol", provider=SimpleNamespace(generate=boom))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "provider_error")
        self.assertEqual(BotGuest.objects.get(telegram_id=9002).demo_questions_used, 0)


class WorkspaceServiceTests(TestCase):
    """F3 — o'quvchi workspace servislari."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="ws-teacher", email="ws-teacher@example.com", password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="ws-student", email="ws-student@example.com", password="x", telegram_id=6001,
        )
        self.course = Course.objects.create(
            title="WS kursi", description="t", instructor=self.teacher, level="beginner",
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson = Lesson.objects.create(module=module, title="WS darsi", order=1, xp_reward=5)
        self.cohort = Cohort.objects.create(
            name="WS kohorti", course=self.course, start_date="2026-03-26", is_active=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status="active",
        )

    def test_student_overview_uses_dashboard_math(self):
        from bot.services import student_overview

        items = student_overview(self.student)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["course"], "WS kursi")
        self.assertEqual(item["total"], 1)
        self.assertEqual(item["completed"], 0)
        self.assertEqual(item["progress"], 0)

    def test_student_recent_attendance(self):
        from bot.services import student_recent_attendance
        from cohorts.attendance_service import upsert_attendance_and_xp

        upsert_attendance_and_xp(
            enrollment=self.enrollment, lesson=self.lesson,
            date=timezone.localdate(), status=Attendance.STATUS_PRESENT,
            marked_by=self.teacher,
        )
        items = student_recent_attendance(self.student)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["lesson"], "WS darsi")
        self.assertIn("Keldi", items[0]["status"])

    def test_telegram_ai_room_is_stable(self):
        from bot.services import TELEGRAM_AI_ROOM_NAME, get_or_create_telegram_ai_room

        room1 = get_or_create_telegram_ai_room(self.student)
        room2 = get_or_create_telegram_ai_room(self.student)
        self.assertEqual(room1.id, room2.id)
        self.assertEqual(room1.name, TELEGRAM_AI_ROOM_NAME)
        self.assertEqual(room1.room_type, "ai")
        self.assertIn(self.student, room1.participants.all())

    def test_telegram_ai_reply_creates_messages_in_room(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from bot.services import telegram_ai_reply
        from messenger.models import Message

        def fake_run(*, room_id, student_id, user_question, user_message_id):
            from messenger.models import ChatRoom
            room = ChatRoom.objects.get(id=room_id)
            msg = Message.objects.create(room=room, sender=None, text="Turkcha javob!")
            return msg.id

        with patch("messenger.tasks.generate_ai_response", SimpleNamespace(run=fake_run)):
            result = telegram_ai_reply(self.student, "Salom, rahmat turkchada nima?")

        self.assertTrue(result.ok, msg=result.message)
        self.assertEqual(result.answer, "Turkcha javob!")
        room_messages = Message.objects.filter(room__name="Telegram AI suhbati")
        self.assertEqual(room_messages.count(), 2)  # user savoli + AI javobi

    def test_telegram_ai_reply_engine_error_is_graceful(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from bot.services import telegram_ai_reply

        def boom(**kw):
            raise RuntimeError("engine down")

        with patch("messenger.tasks.generate_ai_response", SimpleNamespace(run=boom)):
            result = telegram_ai_reply(self.student, "Savol")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "engine_error")


class EnrollmentFlowTests(TestCase):
    """F3.5 — botdan kursga yozilish: tarif tanlash → chek yuborish."""

    def setUp(self):
        from subscriptions.models import Plan

        self.teacher = User.objects.create_user(
            username="enr-teacher", email="enr-teacher@example.com", password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="enr-student", email="enr-student@example.com", password="x", telegram_id=6101,
        )
        self.course = Course.objects.create(
            title="Yozilish kursi", description="t", instructor=self.teacher,
            level="beginner", is_active=True,
        )
        self.cohort = Cohort.objects.create(
            name="Yozilish kohorti", course=self.course, start_date="2026-03-26", is_active=True,
        )
        self.plan = Plan.objects.create(name="Standart", price=299000, description="t", order=1)

    def _fake_receipt(self):
        from django.core.files.base import ContentFile

        return ContentFile(b"fake-image-bytes", name="tg-receipt-test.jpg")

    def test_begin_enrollment_creates_pending_with_plan_and_card_info(self):
        from bot.services import begin_course_enrollment

        result = begin_course_enrollment(self.student, self.course.id, self.plan.id)
        self.assertTrue(result.ok, msg=result.message)
        self.assertEqual(result.amount, 299000)
        self.assertTrue(result.card_number)

        enrollment = Enrollment.objects.get(student=self.student)
        self.assertEqual(enrollment.status, "pending")
        self.assertEqual(enrollment.plan_id, self.plan.id)

        # Ikkinchi chaqiruv dublikat enrollment ochmaydi
        begin_course_enrollment(self.student, self.course.id, self.plan.id)
        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)

    def test_submit_receipt_creates_payment_receipt(self):
        from bot.services import begin_course_enrollment, submit_payment_receipt
        from cohorts.models import PaymentReceipt

        begin_course_enrollment(self.student, self.course.id, self.plan.id)
        result = submit_payment_receipt(self.student, self._fake_receipt())

        self.assertTrue(result.ok, msg=result.message)
        receipt = PaymentReceipt.objects.get(id=result.receipt_id)
        self.assertEqual(int(receipt.amount), 299000)
        self.assertFalse(receipt.is_verified)
        self.assertEqual(result.course_title, "Yozilish kursi")

    def test_submit_receipt_without_plan_selection_is_rejected(self):
        from bot.services import submit_payment_receipt

        result = submit_payment_receipt(self.student, self._fake_receipt())
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "no_target")

    def test_second_receipt_blocked_while_pending(self):
        from bot.services import (
            begin_course_enrollment,
            submit_payment_receipt,
        )

        begin_course_enrollment(self.student, self.course.id, self.plan.id)
        submit_payment_receipt(self.student, self._fake_receipt())

        # Chek kutilayotganda yana boshlash ham, yana chek ham bloklanadi
        again = begin_course_enrollment(self.student, self.course.id, self.plan.id)
        self.assertFalse(again.ok)
        self.assertEqual(again.code, "pending_receipt")

        second = submit_payment_receipt(self.student, self._fake_receipt())
        self.assertFalse(second.ok)
        self.assertEqual(second.code, "pending_receipt")


class OutboxTests(TestCase):
    """F4 — Notification → TelegramOutbox ko'zgusi va yuborish holatlari."""

    def setUp(self):
        self.linked = User.objects.create_user(
            username="ob-linked", email="ob-linked@example.com", password="x", telegram_id=6201,
        )
        self.unlinked = User.objects.create_user(
            username="ob-unlinked", email="ob-unlinked@example.com", password="x",
        )

    def test_notification_mirrors_to_outbox_only_for_linked(self):
        from bot.models import TelegramOutbox

        n1 = Notification.objects.create(recipient=self.linked, title="Salom", message="Xabar")
        Notification.objects.create(recipient=self.unlinked, title="Salom", message="Xabar")

        rows = TelegramOutbox.objects.all()
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertEqual(row.notification_id, n1.id)
        self.assertEqual(row.telegram_id, 6201)
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)

    def test_outbox_render_and_state_transitions(self):
        from bot.models import TelegramOutbox
        from bot.outbox import (
            MAX_ATTEMPTS,
            fetch_pending_outbox,
            mark_outbox_attempt_failed,
            mark_outbox_sent,
            render_outbox_text,
        )

        Notification.objects.create(
            recipient=self.linked, title="To'lov tasdiqlandi ✅", message="Kurs ochiq <3",
        )
        items = fetch_pending_outbox()
        self.assertEqual(len(items), 1)
        item = items[0]

        text = render_outbox_text(item)
        self.assertIn("To&#x27;lov tasdiqlandi", text)
        self.assertIn("&lt;3", text)  # HTML escape

        mark_outbox_sent(item)
        item.refresh_from_db()
        self.assertEqual(item.status, TelegramOutbox.STATUS_SENT)
        self.assertEqual(fetch_pending_outbox(), [])

        # Xato holati: MAX_ATTEMPTS'gacha pending, keyin failed
        n = Notification.objects.create(recipient=self.linked, title="X", message="Y")
        fail_item = TelegramOutbox.objects.get(notification=n)
        for i in range(MAX_ATTEMPTS):
            mark_outbox_attempt_failed(fail_item, RuntimeError("blocked"))
        fail_item.refresh_from_db()
        self.assertEqual(fail_item.status, TelegramOutbox.STATUS_FAILED)
        self.assertEqual(fail_item.attempts, MAX_ATTEMPTS)


class AdminReceiptActionTests(TestCase):
    """F4 — botdan chek tasdiqlash/rad etish."""

    def setUp(self):
        from subscriptions.models import Plan
        from django.core.files.base import ContentFile
        from cohorts.models import PaymentReceipt

        self.admin = User.objects.create_user(
            username="adm", email="adm@example.com", password="x",
            is_staff=True, telegram_id=6301,
        )
        self.student = User.objects.create_user(
            username="adm-student", email="adm-student@example.com", password="x", telegram_id=6302,
        )
        course = Course.objects.create(
            title="Chek kursi", description="t", instructor=self.admin, level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Chek kohorti", course=course, start_date="2026-03-26", is_active=True,
        )
        self.plan = Plan.objects.create(name="Oddiy", price=200000, description="t", order=1)
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=cohort, status="pending", plan=self.plan,
        )
        self.receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment,
            receipt_image=ContentFile(b"img", name="r.jpg"),
            amount=200000,
            period_start=timezone.localdate(),
            period_end=timezone.localdate() + datetime.timedelta(days=30),
        )

    def test_verify_receipt_activates_enrollment_and_notifies(self):
        from bot.services import verify_receipt

        result = verify_receipt(self.receipt.id, self.admin)
        self.assertTrue(result.ok, msg=result.message)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "active")
        self.assertIsNotNone(self.enrollment.next_payment_deadline)

        note = Notification.objects.get(recipient=self.student, title="To'lov tasdiqlandi ✅")
        # Outbox ko'zgusi ham ishlagan (student bog'langan)
        from bot.models import TelegramOutbox
        self.assertTrue(TelegramOutbox.objects.filter(notification=note).exists())

    def test_reject_receipt_deletes_and_notifies(self):
        from bot.services import reject_receipt
        from cohorts.models import PaymentReceipt

        result = reject_receipt(self.receipt.id, self.admin)
        self.assertTrue(result.ok, msg=result.message)
        self.assertFalse(PaymentReceipt.objects.filter(id=self.receipt.id).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student, title="To'lov cheki rad etildi"
            ).exists()
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "pending")  # faollashmagan

    def test_receipt_actions_require_staff(self):
        from bot.services import reject_receipt, verify_receipt

        result = verify_receipt(self.receipt.id, self.student)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "forbidden")
        result = reject_receipt(self.receipt.id, self.student)
        self.assertFalse(result.ok)


class StaffServiceTests(TestCase):
    """F4 — o'qituvchi servislari."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="stf-teacher", email="stf-teacher@example.com", password="x",
        )
        self.other_instructor = User.objects.create_user(
            username="stf-other", email="stf-other@example.com", password="x",
        )
        course = Course.objects.create(
            title="Staff kursi", description="t", instructor=self.instructor, level="beginner",
        )
        other_course = Course.objects.create(
            title="Begona kurs", description="t", instructor=self.other_instructor, level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Staff kohorti", course=course, start_date="2026-03-26", is_active=True,
        )
        Cohort.objects.create(
            name="Begona kohorti", course=other_course, start_date="2026-03-26", is_active=True,
        )
        student = User.objects.create_user(
            username="stf-student", email="stf-student@example.com", password="x",
        )
        Enrollment.objects.create(student=student, cohort=self.cohort, status="active")

    def test_teacher_sees_only_own_cohorts(self):
        from bot.services import teacher_cohorts_overview

        items = teacher_cohorts_overview(self.instructor)
        names = [i["name"] for i in items]
        self.assertIn("Staff kohorti", names)
        self.assertNotIn("Begona kohorti", names)
        item = next(i for i in items if i["name"] == "Staff kohorti")
        self.assertEqual(item["students"], 1)
        self.assertFalse(item["tg_bound"])

    def test_admin_stats_counts(self):
        from bot.services import admin_stats

        stats = admin_stats()
        self.assertGreaterEqual(stats["students"], 3)
        self.assertGreaterEqual(stats["active_enrollments"], 1)
        self.assertEqual(stats["unverified_receipts"], 0)


class AdminExpansionTests(TestCase):
    """F6 — admin qidiruv, bloklash, broadcast, AI stat."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="f6-admin", email="f6-admin@example.com", password="x",
            is_staff=True, telegram_id=6401,
        )
        self.student_tg = User.objects.create_user(
            username="f6-student-tg", email="f6-tg@example.com", password="x",
            telegram_id=6402, first_name="Aziza", phone_number="+998901112233",
        )
        self.student_plain = User.objects.create_user(
            username="f6-student-plain", email="f6-plain@example.com", password="x",
        )
        course = Course.objects.create(
            title="F6 kursi", description="t", instructor=self.admin, level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="F6 kohorti", course=course, start_date="2026-03-26", is_active=True,
        )
        Enrollment.objects.create(student=self.student_tg, cohort=self.cohort, status="active")

    def test_search_finds_by_name_and_phone(self):
        from bot.services import admin_search_users

        by_name = admin_search_users("Aziza")
        self.assertEqual(len(by_name), 1)
        self.assertEqual(by_name[0]["username"], "f6-student-tg")
        self.assertEqual(by_name[0]["role"], "O'quvchi")
        self.assertEqual(len(by_name[0]["enrollments"]), 1)

        by_phone = admin_search_users("901112233")
        self.assertEqual(len(by_phone), 1)

        too_short = admin_search_users("Az")
        self.assertEqual(too_short, [])

    def test_toggle_active_with_guards(self):
        from bot.services import admin_toggle_user_active

        result = admin_toggle_user_active(self.student_plain.id, self.admin)
        self.assertTrue(result.ok)
        self.student_plain.refresh_from_db()
        self.assertFalse(self.student_plain.is_active)

        back = admin_toggle_user_active(self.student_plain.id, self.admin)
        self.assertTrue(back.ok)
        self.student_plain.refresh_from_db()
        self.assertTrue(self.student_plain.is_active)

        self.assertFalse(admin_toggle_user_active(self.admin.id, self.admin).ok)  # o'zini
        self.assertFalse(admin_toggle_user_active(self.student_plain.id, self.student_tg).ok)  # oddiy user

    def test_broadcast_full_flow(self):
        from bot.models import BotBroadcastDraft, TelegramOutbox
        from bot.services import (
            broadcast_recipient_count,
            create_broadcast_draft,
            execute_broadcast,
        )
        from users.models import NotificationBroadcast

        draft, error = create_broadcast_draft(self.admin, "Ertaga dars soat 19:00 da!")
        self.assertIsNone(error)

        self.assertEqual(broadcast_recipient_count(str(self.cohort.id)), 1)
        self.assertGreaterEqual(broadcast_recipient_count("all"), 3)

        result = execute_broadcast(draft.id, str(self.cohort.id), self.admin)
        self.assertTrue(result.ok, msg=result.message)

        # Kohortdagi 1 o'quvchiga Notification + (tg bog'langani uchun) outbox
        note = Notification.objects.get(recipient=self.student_tg, title="E'lon 📢")
        self.assertIn("19:00", note.message)
        self.assertTrue(TelegramOutbox.objects.filter(notification=note).exists())

        broadcast = NotificationBroadcast.objects.get(created_by=self.admin)
        self.assertTrue(broadcast.is_sent)
        self.assertFalse(BotBroadcastDraft.objects.filter(id=draft.id).exists())  # sarflandi

        # Qoralama yo'q — qayta yuborib bo'lmaydi
        again = execute_broadcast(draft.id, "all", self.admin)
        self.assertFalse(again.ok)
        self.assertEqual(again.code, "draft_missing")

    def test_broadcast_draft_validation(self):
        from bot.services import create_broadcast_draft

        _, err = create_broadcast_draft(self.admin, "qis")
        self.assertIsNotNone(err)
        _, err = create_broadcast_draft(self.student_tg, "Yetarlicha uzun matn")
        self.assertIsNotNone(err)

    def test_admin_ai_usage_empty(self):
        from bot.services import admin_ai_usage

        usage = admin_ai_usage()
        self.assertEqual(usage["today"]["runs"], 0)
        self.assertEqual(usage["week"]["tokens"], 0)
        self.assertEqual(usage["top_users"], [])


class LessonDeliveryTests(TestCase):
    """F8 — botda o'qish: kurs xaritasi, dars ochish (=o'tildi), deep-link."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="f8-teacher", email="f8-teacher@example.com", password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="f8-student", email="f8-student@example.com", password="x", telegram_id=6601,
        )
        self.outsider = User.objects.create_user(
            username="f8-outsider", email="f8-outsider@example.com", password="x", telegram_id=6602,
        )
        self.course = Course.objects.create(
            title="F8 kursi", description="t", instructor=self.teacher, level="beginner",
        )
        module = Module.objects.create(course=self.course, title="Alifbo moduli", order=1)
        self.lesson1 = Lesson.objects.create(
            module=module, title="Harflar", order=1, xp_reward=10,
            video_url="https://youtu.be/test123",
            content="<p>Turk alifbosida <b>29 ta</b> harf bor.</p><ul><li>A harfi</li></ul>",
        )
        self.lesson2 = Lesson.objects.create(module=module, title="Talaffuz", order=2, xp_reward=10)
        self.cohort = Cohort.objects.create(
            name="F8 kohorti", course=self.course, start_date="2026-03-26", is_active=True,
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")

    def test_html_to_text(self):
        from bot.services import html_to_text

        text = html_to_text("<p>Salom <b>dunyo</b>!</p><ul><li>Bir</li><li>Ikki &amp; uch</li></ul>")
        self.assertIn("Salom dunyo!", text)
        self.assertIn("• Bir", text)
        self.assertIn("Ikki & uch", text)
        self.assertNotIn("<", text)

    def test_course_map_states(self):
        from bot.services import student_course_map

        data = student_course_map(self.student, self.course.id)
        self.assertEqual(data["course"], "F8 kursi")
        lessons = data["modules"]["Alifbo moduli"]
        self.assertEqual(len(lessons), 2)
        self.assertFalse(lessons[0]["locked"])
        self.assertFalse(lessons[0]["completed"])

        # Obunasiz user uchun hammasi qulf
        outsider_map = student_course_map(self.outsider, self.course.id)
        self.assertTrue(all(
            lesson["locked"] for lesson in outsider_map["modules"]["Alifbo moduli"]
        ))

    def test_open_lesson_marks_completed_like_site(self):
        from bot.services import student_course_map, student_open_lesson
        from courses.models import LessonProgress

        result = student_open_lesson(self.student, self.lesson1.id)
        self.assertTrue(result.ok, msg=result.message)
        lesson = result.lesson
        self.assertEqual(lesson["title"], "Harflar")
        self.assertEqual(lesson["video_url"], "https://youtu.be/test123")
        self.assertIn("29 ta harf", lesson["content"])
        self.assertIn("• A harfi", lesson["content"])

        # Sayt bilan bir xil: ochish = LessonProgress completed
        self.assertTrue(
            LessonProgress.objects.filter(
                enrollment__student=self.student, lesson=self.lesson1, is_completed=True
            ).exists()
        )
        data = student_course_map(self.student, self.course.id)
        first = data["modules"]["Alifbo moduli"][0]
        self.assertTrue(first["completed"])

    def test_open_lesson_guards(self):
        from bot.services import student_open_lesson

        blocked = student_open_lesson(self.outsider, self.lesson1.id)
        self.assertFalse(blocked.ok)

        missing = student_open_lesson(self.student, 99999)
        self.assertFalse(missing.ok)
        self.assertEqual(missing.code, "missing")

    def test_parse_start_payload(self):
        from bot.services import parse_start_payload

        self.assertEqual(parse_start_payload("dars_12"), ("lesson", 12))
        self.assertEqual(parse_start_payload("sometoken"), ("token", "sometoken"))
        self.assertEqual(parse_start_payload(""), ("none", None))
        self.assertEqual(parse_start_payload("dars_abc"), ("token", "dars_abc"))


class AssignmentAndQuizTests(TestCase):
    """F9 — botda vazifa topshirish va quiz yechish."""

    def setUp(self):
        from courses.models import Assignment, Choice, Question, Quiz

        self.teacher = User.objects.create_user(
            username="f9-teacher", email="f9-teacher@example.com", password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="f9-student", email="f9-student@example.com", password="x", telegram_id=6701,
        )
        self.outsider = User.objects.create_user(
            username="f9-outsider", email="f9-outsider@example.com", password="x", telegram_id=6702,
        )
        self.course = Course.objects.create(
            title="F9 kursi", description="t", instructor=self.teacher, level="beginner",
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson = Lesson.objects.create(module=module, title="F9 darsi", order=1, xp_reward=10)
        self.cohort = Cohort.objects.create(
            name="F9 kohorti", course=self.course, start_date="2026-03-26", is_active=True,
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")

        self.assignment = Assignment.objects.create(
            lesson=self.lesson, title="Matn yozing",
            description="<p>Turkcha <b>5 ta</b> gap yozing.</p>", max_xp=50,
        )
        self.quiz = Quiz.objects.create(title="F9 quiz", lesson=self.lesson, xp_reward=20)
        q1 = Question.objects.create(quiz=self.quiz, text="Rahmat turkchada?")
        Choice.objects.create(question=q1, text="Teşekkür", is_correct=True)
        Choice.objects.create(question=q1, text="Merhaba", is_correct=False)
        q2 = Question.objects.create(quiz=self.quiz, text="Salom turkchada?")
        Choice.objects.create(question=q2, text="Güle güle", is_correct=False)
        Choice.objects.create(question=q2, text="Merhaba", is_correct=True)
        self.q1, self.q2 = q1, q2

    # ---- vazifa

    def test_assignment_flow_text_answer(self):
        from bot.models import BotPendingAction
        from bot.services import (
            lesson_assignments,
            start_assignment_answer,
            submit_assignment_answer,
        )
        from courses.models import AssignmentSubmission

        prompt = start_assignment_answer(self.student, self.assignment.id)
        self.assertTrue(prompt.ok, msg=prompt.message)
        self.assertIn("5 ta gap", prompt.assignment["description"])
        self.assertTrue(
            BotPendingAction.objects.filter(
                user=self.student, kind=BotPendingAction.KIND_ASSIGNMENT
            ).exists()
        )

        result = submit_assignment_answer(self.student, self.assignment.id, text="Ben iyiyim.")
        self.assertTrue(result.ok, msg=result.message)
        submission = AssignmentSubmission.objects.get(
            assignment=self.assignment, student=self.student
        )
        self.assertEqual(submission.answer_text, "Ben iyiyim.")
        self.assertEqual(submission.status, AssignmentSubmission.STATUS_PENDING)
        # Holat tozalandi
        self.assertFalse(BotPendingAction.objects.filter(user=self.student).exists())

        # Ro'yxatda holat ko'rinadi
        data = lesson_assignments(self.student, self.lesson.id)
        self.assertIn("Tekshiruvda", data["assignments"][0]["status"])

    def test_assignment_guards(self):
        from bot.services import start_assignment_answer, submit_assignment_answer

        locked = start_assignment_answer(self.outsider, self.assignment.id)
        self.assertFalse(locked.ok)
        self.assertEqual(locked.code, "locked")

        missing = start_assignment_answer(self.student, 99999)
        self.assertFalse(missing.ok)

        empty = submit_assignment_answer(self.student, self.assignment.id, text="   ")
        self.assertFalse(empty.ok)
        self.assertEqual(empty.code, "empty")

    # ---- quiz

    def test_quiz_full_flow_awards_xp(self):
        from bot.models import BotPendingAction
        from bot.services import answer_quiz_question, start_quiz

        start = start_quiz(self.student, self.quiz.id)
        self.assertTrue(start.ok, msg=start.message)
        self.assertEqual(start.question["index"], 0)
        self.assertEqual(start.question["total"], 2)
        self.assertEqual(len(start.question["choices"]), 2)

        correct1 = next(c for c in start.question["choices"] if c["text"] == "Teşekkür")
        step = answer_quiz_question(self.student, self.quiz.id, self.q1.id, correct1["id"])
        self.assertTrue(step.ok)
        self.assertFalse(step.finished)
        self.assertEqual(step.question["index"], 1)

        correct2 = next(c for c in step.question["choices"] if c["text"] == "Merhaba")
        final = answer_quiz_question(self.student, self.quiz.id, self.q2.id, correct2["id"])
        self.assertTrue(final.ok)
        self.assertTrue(final.finished)
        self.assertEqual(final.total_correct, 2)
        self.assertEqual(final.score, 100.0)
        self.assertEqual(final.xp_earned, 20)

        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 20)
        self.assertFalse(BotPendingAction.objects.filter(user=self.student).exists())

    def test_quiz_retake_does_not_double_xp(self):
        from bot.services import answer_quiz_question, start_quiz

        def _run(correct):
            start = start_quiz(self.student, self.quiz.id)
            c1 = next(
                c for c in start.question["choices"]
                if (c["text"] == "Teşekkür") == correct
            )
            step = answer_quiz_question(self.student, self.quiz.id, self.q1.id, c1["id"])
            c2 = next(
                c for c in step.question["choices"]
                if (c["text"] == "Merhaba") == correct
            )
            return answer_quiz_question(self.student, self.quiz.id, self.q2.id, c2["id"])

        first = _run(correct=True)
        self.assertEqual(first.xp_earned, 20)
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 20)

        second = _run(correct=True)
        self.assertEqual(second.xp_earned, 0)  # takroriy urinish XP bermaydi
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 20)

    def test_quiz_guards(self):
        from bot.services import answer_quiz_question, start_quiz

        locked = start_quiz(self.outsider, self.quiz.id)
        self.assertFalse(locked.ok)
        self.assertEqual(locked.code, "locked")

        no_session = answer_quiz_question(self.student, self.quiz.id, self.q1.id, 1)
        self.assertFalse(no_session.ok)
        self.assertEqual(no_session.code, "no_session")


class AiControlTests(TestCase):
    """F7 — AI nazorat botdan: sozlamalar, reset/bonus, user blok."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="f7-admin", email="f7-admin@example.com", password="x",
            is_staff=True, telegram_id=6501,
        )
        self.student = User.objects.create_user(
            username="f7-student", email="f7-student@example.com", password="x", telegram_id=6502,
        )
        # _scope_users qamroviga tushishi uchun allowance yaratamiz
        from aicontrol.service import get_allowance
        get_allowance(self.student)

    def test_toggle_enforcement_and_guard(self):
        from aicontrol.models import AISettings
        from bot.services import ai_toggle_enforcement

        before = AISettings.load().enforcement_enabled
        result = ai_toggle_enforcement(self.admin)
        self.assertTrue(result.ok)
        self.assertNotEqual(AISettings.load().enforcement_enabled, before)
        # qaytarib qo'yamiz
        ai_toggle_enforcement(self.admin)
        self.assertEqual(AISettings.load().enforcement_enabled, before)

        self.assertFalse(ai_toggle_enforcement(self.student).ok)

    def test_set_global_limits_validation(self):
        from aicontrol.models import AISettings
        from bot.services import ai_set_global_limits

        ok = ai_set_global_limits(self.admin, "200000", "2000000")
        self.assertTrue(ok.ok, msg=ok.message)
        s = AISettings.load()
        self.assertEqual(s.default_5h_token_limit, 200000)
        self.assertEqual(s.default_weekly_token_limit, 2000000)

        self.assertFalse(ai_set_global_limits(self.admin, "abc", "10").ok)
        self.assertFalse(ai_set_global_limits(self.admin, "1000", "500").ok)  # haftalik < 5h
        self.assertFalse(ai_set_global_limits(self.student, "1000", "5000").ok)

    def test_reset_action_sets_markers_with_audit(self):
        from aicontrol.models import AIUsageResetEvent
        from aicontrol.service import get_allowance
        from bot.services import ai_action_preview, ai_execute_action

        preview = ai_action_preview("r", 0, "a", 0, "both")
        self.assertGreaterEqual(preview, 1)

        result = ai_execute_action(self.admin, "r", 0, "a", 0, "both")
        self.assertTrue(result.ok, msg=result.message)

        allowance = get_allowance(self.student)
        self.assertIsNotNone(allowance.reset_5h_at)
        self.assertIsNotNone(allowance.reset_weekly_at)

        event = AIUsageResetEvent.objects.get()
        self.assertEqual(event.kind, AIUsageResetEvent.KIND_RESET)
        self.assertEqual(event.created_by, self.admin)
        self.assertGreaterEqual(event.affected_count, 1)
        self.assertEqual(event.reason, "Telegram bot orqali")

    def test_bonus_action_adds_tokens(self):
        from aicontrol.service import get_allowance
        from bot.services import ai_execute_action

        result = ai_execute_action(self.admin, "b", 50000, "a", 0, "5h")
        self.assertTrue(result.ok, msg=result.message)
        allowance = get_allowance(self.student)
        self.assertEqual(allowance.bonus_5h_tokens, 50000)
        self.assertEqual(allowance.bonus_weekly_tokens, 0)

        self.assertFalse(ai_execute_action(self.admin, "b", 0, "a", 0, "5h").ok)  # miqdor 0
        self.assertFalse(ai_execute_action(self.student, "b", 100, "a", 0, "5h").ok)  # huquq

    def test_plan_policy_set_disable_and_list(self):
        from aicontrol.models import AIPlanPolicy
        from bot.services import (
            ai_disable_plan_policy,
            ai_plan_policies,
            ai_set_plan_policy,
        )
        from subscriptions.models import Plan

        plan = Plan.objects.create(name="F7 tarif", price=150000, description="t", order=1)

        # Boshida siyosat yo'q
        items = ai_plan_policies()
        item = next(i for i in items if i["plan_id"] == plan.id)
        self.assertIsNone(item["policy"])

        # O'rnatish
        result = ai_set_plan_policy(self.admin, plan.id, "40000", "400000")
        self.assertTrue(result.ok, msg=result.message)
        policy = AIPlanPolicy.objects.get(plan=plan)
        self.assertEqual(policy.token_limit_5h, 40000)
        self.assertTrue(policy.is_active)

        # Validatsiya va huquq
        self.assertFalse(ai_set_plan_policy(self.admin, plan.id, "5000", "100").ok)
        self.assertFalse(ai_set_plan_policy(self.student, plan.id, "1000", "10000").ok)
        self.assertFalse(ai_set_plan_policy(self.admin, 99999, "1000", "10000").ok)

        # O'chirish → global defaultga qaytadi; qayta o'rnatish is_active'ni tiklaydi
        off = ai_disable_plan_policy(self.admin, plan.id)
        self.assertTrue(off.ok)
        policy.refresh_from_db()
        self.assertFalse(policy.is_active)

        ai_set_plan_policy(self.admin, plan.id, "60000", "600000")
        policy.refresh_from_db()
        self.assertTrue(policy.is_active)
        self.assertEqual(policy.token_limit_5h, 60000)

    def test_user_ai_block_toggle_and_card_field(self):
        from bot.services import admin_user_card, ai_toggle_user_block

        result = ai_toggle_user_block(self.student.id, self.admin)
        self.assertTrue(result.ok)
        card = admin_user_card(self.student)
        self.assertTrue(card["ai"]["blocked"])

        ai_toggle_user_block(self.student.id, self.admin)
        card = admin_user_card(self.student)
        self.assertFalse(card["ai"]["blocked"])


class MiniAppAuthTests(TestCase):
    """F5 — Telegram Mini App initData validatsiyasi va avto-login."""

    TEST_TOKEN = "123456:TEST-TOKEN-FOR-MINIAPP"

    def _make_init_data(self, telegram_id, auth_date=None, tamper=False):
        import json as jsonlib
        import time as timelib
        from urllib.parse import urlencode

        from bot.miniapp import compute_init_data_hash

        pairs = {
            "auth_date": str(int(auth_date if auth_date is not None else timelib.time())),
            "query_id": "AAtest",
            "user": jsonlib.dumps({"id": telegram_id, "first_name": "Test"}),
        }
        digest = compute_init_data_hash(pairs, self.TEST_TOKEN)
        if tamper:
            digest = "0" * 64
        return urlencode({**pairs, "hash": digest})

    def test_validate_init_data_roundtrip(self):
        from bot.miniapp import validate_init_data

        init_data = self._make_init_data(telegram_id=9911)
        result = validate_init_data(init_data, self.TEST_TOKEN)
        self.assertIsNotNone(result)
        self.assertEqual(result["user"]["id"], 9911)

    def test_validate_init_data_rejects_tampered_and_expired(self):
        import time as timelib

        from bot.miniapp import validate_init_data

        tampered = self._make_init_data(telegram_id=9911, tamper=True)
        self.assertIsNone(validate_init_data(tampered, self.TEST_TOKEN))

        expired = self._make_init_data(telegram_id=9911, auth_date=timelib.time() - 100000)
        self.assertIsNone(validate_init_data(expired, self.TEST_TOKEN))

        wrong_token = self._make_init_data(telegram_id=9911)
        self.assertIsNone(validate_init_data(wrong_token, "boshqa:token"))

    def test_safe_next_path(self):
        from bot.miniapp import safe_next_path

        self.assertEqual(safe_next_path("/courses/4/"), "/courses/4/")
        self.assertEqual(safe_next_path("//evil.com"), "/users/dashboard/")
        self.assertEqual(safe_next_path("https://evil.com"), "/users/dashboard/")
        self.assertEqual(safe_next_path(""), "/users/dashboard/")

    def test_miniapp_entry_defaults_to_dedicated_home(self):
        regular_response = self.client.get("/users/login/")
        response = self.client.get("/bot/miniapp/")

        self.assertEqual(regular_response["X-Frame-Options"], "DENY")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next_path"], "/bot/miniapp/home/")
        self.assertNotIn("X-Frame-Options", response)

    def test_local_preview_requires_login_then_opens_home(self):
        from unittest.mock import patch

        with patch("bot.views.settings.IS_LOCAL", True):
            anonymous = self.client.get("/bot/miniapp/?preview=1")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/users/login/", anonymous.url)

        user = User.objects.create_user(
            username="mini-preview", email="preview@example.com", password="x"
        )
        self.client.force_login(user)
        with patch("bot.views.settings.IS_LOCAL", True):
            authenticated = self.client.get("/bot/miniapp/?preview=1")
        self.assertRedirects(
            authenticated,
            "/bot/miniapp/home/",
            fetch_redirect_response=False,
        )

    def test_preview_parameter_is_ignored_outside_local_environment(self):
        from unittest.mock import patch

        with patch("bot.views.settings.IS_LOCAL", False):
            response = self.client.get("/bot/miniapp/?preview=1")
        self.assertEqual(response.status_code, 200)

    def test_miniapp_home_requires_login_and_renders_platform_links(self):
        anonymous = self.client.get("/bot/miniapp/home/")
        self.assertEqual(anonymous.status_code, 302)

        user = User.objects.create_user(
            username="mini-home", email="home@example.com", password="x", total_xp=120
        )
        self.client.force_login(user)
        response = self.client.get("/bot/miniapp/home/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Frame-Options", response)
        self.assertContains(response, "Azure AI")
        self.assertContains(response, "Darslarim")
        self.assertContains(response, "Imtihonlar")
        self.assertContains(response, "120")
        self.assertContains(response, "/static/css/miniapp.css?v=20260721-1")

    def test_miniapp_dedicated_pages_require_login_and_render_navigation(self):
        routes = (
            ("/bot/miniapp/courses/", "O‘qishni davom ettiring", "Darslar"),
            ("/bot/miniapp/ai/", "Bugun nimani o‘rganamiz?", "Azure AI"),
            ("/bot/miniapp/profile/", "O‘quv profili", "Profil"),
        )

        for path, heading, active_label in routes:
            with self.subTest(path=path):
                anonymous = self.client.get(path)
                self.assertEqual(anonymous.status_code, 302)

                user = User.objects.create_user(
                    username=f"mini-{active_label.lower().replace(' ', '-')}",
                    email=f"{active_label.lower().replace(' ', '-')}@example.com",
                    password="x",
                )
                self.client.force_login(user)
                response = self.client.get(path)

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("X-Frame-Options", response)
                self.assertContains(response, heading)
                self.assertContains(response, 'class="miniapp-nav"')
                self.client.logout()

    def test_miniapp_auth_logs_user_in(self):
        import json as jsonlib
        from unittest.mock import patch

        user = User.objects.create_user(
            username="ma-user", email="ma-user@example.com", password="x", telegram_id=9922,
        )
        init_data = self._make_init_data(telegram_id=9922)

        with patch("bot.views.settings.TELEGRAM_BOT_TOKEN", self.TEST_TOKEN):
            response = self.client.post(
                "/bot/miniapp/auth/",
                data=jsonlib.dumps({"init_data": init_data, "next": "/courses/"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["redirect"], "/courses/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
        self.assertTrue(self.client.session["telegram_miniapp"])

        framed_response = self.client.get("/users/dashboard/")
        self.assertNotIn("X-Frame-Options", framed_response)
        self.assertIn(
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
            framed_response["Content-Security-Policy"],
        )

    def test_miniapp_auth_rejects_unlinked_and_invalid(self):
        import json as jsonlib
        from unittest.mock import patch

        init_data = self._make_init_data(telegram_id=555000)  # hech kimga ulanmagan
        with patch("bot.views.settings.TELEGRAM_BOT_TOKEN", self.TEST_TOKEN):
            response = self.client.post(
                "/bot/miniapp/auth/",
                data=jsonlib.dumps({"init_data": init_data, "next": "/"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 404)

        with patch("bot.views.settings.TELEGRAM_BOT_TOKEN", self.TEST_TOKEN):
            response = self.client.post(
                "/bot/miniapp/auth/",
                data=jsonlib.dumps({"init_data": "hash=abc&auth_date=1", "next": "/"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)


class OnboardingMarkupTests(TestCase):
    """Telegram localhost URL-tugmani rad etadi — lokal muhitda callback bo'lishi shart."""

    def test_register_markup_has_no_localhost_url_button(self):
        from bot.routers.onboarding import register_menu_markup

        markup = register_menu_markup()
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    self.assertNotIn("localhost", btn.url)
                    self.assertNotIn("127.0.0.1", btn.url)

    def test_register_markup_url_button_on_public_domain(self):
        from unittest.mock import patch

        from bot.routers import onboarding

        with patch.object(onboarding.settings, "APP_DOMAIN", "azurelms.uz"):
            markup = onboarding.register_menu_markup()
        urls = [btn.url for row in markup.inline_keyboard for btn in row if btn.url]
        self.assertEqual(urls, ["https://azurelms.uz/users/register/"])

    def test_student_menu_miniapp_opens_dedicated_home(self):
        from unittest.mock import patch

        from bot.routers import workspace

        with patch.object(workspace.settings, "APP_DOMAIN", "azurelms.uz"):
            markup = workspace.student_menu_markup()

        webapps = [
            button.web_app.url
            for row in markup.inline_keyboard
            for button in row
            if button.web_app
        ]
        self.assertEqual(
            webapps,
            ["https://azurelms.uz/bot/miniapp/?next=%2Fbot%2Fminiapp%2Fhome%2F"],
        )


class IdentityResolveTests(TestCase):
    """bot/middleware.resolve_identity — rol aniqlash."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="id-staff", email="id-staff@example.com",
            password="x", is_staff=True, telegram_id=5001,
        )
        self.instructor = User.objects.create_user(
            username="id-instructor", email="id-instructor@example.com",
            password="x", telegram_id=5002,
        )
        self.student = User.objects.create_user(
            username="id-student", email="id-student@example.com",
            password="x", telegram_id=5003,
        )
        self.linked_only = User.objects.create_user(
            username="id-linked", email="id-linked@example.com",
            password="x", telegram_id=5004,
        )
        course = Course.objects.create(
            title="Rol kursi", description="t", instructor=self.instructor, level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Rol kohorti", course=course, start_date="2026-03-26", is_active=True,
        )
        Enrollment.objects.create(student=self.student, cohort=cohort, status="active")

    def test_roles(self):
        from bot.middleware import resolve_identity

        self.assertEqual(resolve_identity(5001)[1], "admin")
        self.assertEqual(resolve_identity(5002)[1], "teacher")
        self.assertEqual(resolve_identity(5003)[1], "student")
        self.assertEqual(resolve_identity(5004)[1], "linked")
        user, role = resolve_identity(999999)
        self.assertIsNone(user)
        self.assertEqual(role, "guest")
