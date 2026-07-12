import base64
import datetime

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
