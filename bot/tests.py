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
