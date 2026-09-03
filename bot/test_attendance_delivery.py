"""Davomat yopilganda learner xabari faqat canonical outbox orqali ketadi."""

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from bot.models import TelegramOutbox
from bot.routers.group_ops import _close_lesson
from bot.services import start_lesson_session
from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, Module
from users.models import Notification


User = get_user_model()
CHAT_ID = -1009876500012


class AttendanceDeliveryTests(TransactionTestCase):
    """Handler group UI'ni saqlaydi, learnerga esa ikkinchi DM yubormaydi."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="delivery-teacher",
            email="delivery-teacher@example.com",
            password="testpass123",
            is_staff=True,
            telegram_id=880000001,
        )
        self.student = User.objects.create_user(
            username="delivery-student",
            email="delivery-student@example.com",
            password="testpass123",
            telegram_id=880000002,
            telegram_username="delivery_student",
        )
        course = Course.objects.create(
            title="Attendance Delivery Course",
            description="A3 delivery contract",
            instructor=self.teacher,
            level="beginner",
        )
        module = Module.objects.create(course=course, title="M1", order=1)
        self.lesson = Lesson.objects.create(
            module=module,
            title="Dars 1",
            content="<p>x</p>",
            order=1,
            xp_reward=30,
        )
        cohort = Cohort.objects.create(
            name="Attendance Delivery Cohort",
            course=course,
            start_date="2026-01-01",
            is_active=True,
            telegram_chat_id=CHAT_ID,
        )
        Enrollment.objects.create(
            student=self.student,
            cohort=cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        started = start_lesson_session(
            chat_id=CHAT_ID,
            chat_title="Delivery Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        self.assertTrue(started.ok, started.message)
        self.session = started.session
        self.session.started_at = timezone.now() - datetime.timedelta(minutes=20)
        self.session.attendance_message_id = 7711
        self.session.save(update_fields=["started_at", "attendance_message_id"])

    def test_absent_delivery_is_queued_once_without_direct_dm(self):
        bot = SimpleNamespace(
            edit_message_text=AsyncMock(),
            send_message=AsyncMock(),
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=CHAT_ID, title="Delivery Group"),
            from_user=SimpleNamespace(id=self.teacher.telegram_id),
            bot=bot,
            answer=AsyncMock(),
        )

        asyncio.run(_close_lesson(message))

        notifications = Notification.objects.filter(
            recipient=self.student,
            external_key=f"tg-absent-{self.session.id}",
        )
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()
        self.assertEqual(
            TelegramOutbox.objects.filter(
                notification=notification,
                telegram_id=self.student.telegram_id,
                status=TelegramOutbox.STATUS_PENDING,
            ).count(),
            1,
        )
        bot.send_message.assert_not_awaited()

        bot.edit_message_text.assert_awaited_once()
        edit_call = bot.edit_message_text.await_args.kwargs
        self.assertEqual(edit_call["chat_id"], CHAT_ID)
        self.assertEqual(edit_call["message_id"], 7711)
        self.assertIn("Davomat sessiyasi yopildi", edit_call["text"])
        self.assertIsNone(edit_call["reply_markup"])

        message.answer.assert_awaited_once()
        group_summary = message.answer.await_args.args[0]
        self.assertIn("Davomat yakunlandi", group_summary)
        self.assertIn("@delivery_student", group_summary)
