import datetime
import json
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramLessonCheckIn, TelegramLessonSession, TelegramOutbox
from bot.services import close_lesson_session, start_lesson_session
from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import CohortLessonRelease, Course, Lesson, Module
from users.models import Notification

from .grading import parse_author_definition
from .models import ActivityRun, Exercise, LessonPlaybook, PlaybookExercise, StudentResponse, TelegramGroupDelivery
from .services import close_activity, finish_class_session, open_activity, start_class_session, submit_response


User = get_user_model()


class ClassbookFixtureMixin:
    def setUp(self):
        super().setUp()
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@classbook.test", password="x", is_staff=True, telegram_id=1001
        )
        self.other_teacher = User.objects.create_user(
            username="other-teacher", email="other@classbook.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", email="student@classbook.test", password="x", telegram_id=2001
        )
        self.second = User.objects.create_user(
            username="second", email="second@classbook.test", password="x", telegram_id=2002
        )
        self.absent = User.objects.create_user(
            username="absent", email="absent@classbook.test", password="x", telegram_id=2003
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@classbook.test", password="x"
        )
        self.course = Course.objects.create(
            title="Turk tili A1", description="Classbook test kursi", instructor=self.teacher, level="beginner"
        )
        self.module = Module.objects.create(course=self.course, title="Modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Tanishuv", order=1, xp_reward=20)
        self.cohort = Cohort.objects.create(
            name="Massiv 50", course=self.course, start_date=timezone.localdate(), is_active=True,
            telegram_chat_id=-1001234567, telegram_chat_title="Massiv 50 Telegram",
        )
        deadline = timezone.localdate() + datetime.timedelta(days=30)
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=deadline,
        )
        self.second_enrollment = Enrollment.objects.create(
            student=self.second, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=deadline,
        )
        self.absent_enrollment = Enrollment.objects.create(
            student=self.absent, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=deadline,
        )
        config, key = parse_author_definition("single_choice", "Anqara\n*Istanbul\nIzmir")
        self.exercise = Exercise.objects.create(
            course=self.course, lesson=self.lesson, created_by=self.teacher, title="Poytaxt",
            kind="single_choice", prompt="Turkiyaning eng katta shahri?", config=config,
            answer_key=key, explanation="Istanbul eng katta shahardir.", time_limit_seconds=60,
            max_points=100, speed_bonus_percent=10,
        )
        self.playbook = LessonPlaybook.objects.create(
            cohort=self.cohort, lesson=self.lesson, status=LessonPlaybook.STATUS_READY,
            opening_message="Bugun tanishamiz.", materials_message="Daftar va qalam tayyorlang.",
            homework_message="Tanishuv dialogini qaytaring.", created_by=self.teacher,
        )
        self.step = PlaybookExercise.objects.create(
            playbook=self.playbook, exercise=self.exercise, order=1
        )

    def start(self):
        result = start_class_session(
            actor=self.teacher, cohort=self.cohort, lesson=self.lesson
        )
        self.assertTrue(result.ok, result.message)
        return result.session


class SessionLifecycleTests(ClassbookFixtureMixin, TestCase):
    def test_one_start_builds_the_whole_prepared_flow(self):
        session = self.start()
        self.assertEqual(session.classbook_activities.count(), 1)
        activity = session.classbook_activities.get()
        self.assertEqual(activity.snapshot["answer_key"], self.exercise.answer_key)
        self.assertNotIn("answer_key", activity.public_snapshot)
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(
                session=session, kind=TelegramGroupDelivery.KIND_ATTENDANCE
            ).exists()
        )
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(session=session, external_key__endswith="materials").exists()
        )

    def test_start_is_resumable_not_duplicate(self):
        first = self.start()
        second = start_class_session(actor=self.teacher, cohort=self.cohort, lesson=self.lesson)
        self.assertTrue(second.ok)
        self.assertEqual(second.code, "already_open")
        self.assertEqual(second.session.id, first.id)
        self.assertEqual(TelegramLessonSession.objects.count(), 1)

    def test_existing_legacy_session_is_adopted_without_duplicate_attendance_post(self):
        legacy = TelegramLessonSession.objects.create(
            cohort=self.cohort,
            lesson=self.lesson,
            chat_id=self.cohort.telegram_chat_id,
            attendance_message_id=777,
            started_by=self.teacher,
        )

        result = start_class_session(actor=self.teacher, cohort=self.cohort, lesson=self.lesson)

        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.code, "already_open")
        self.assertEqual(result.session.id, legacy.id)
        self.assertEqual(legacy.classbook_activities.count(), 1)
        self.assertFalse(
            TelegramGroupDelivery.objects.filter(
                session=legacy, kind=TelegramGroupDelivery.KIND_ATTENDANCE
            ).exists()
        )

    def test_unassigned_teacher_cannot_start(self):
        result = start_class_session(actor=self.other_teacher, cohort=self.cohort, lesson=self.lesson)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "permission_denied")

    def test_telegram_binding_and_ready_playbook_are_hard_gates(self):
        self.cohort.telegram_chat_id = None
        self.cohort.save()
        result = start_class_session(actor=self.teacher, cohort=self.cohort, lesson=self.lesson)
        self.assertEqual(result.code, "telegram_missing")
        self.cohort.telegram_chat_id = -1001234567
        self.cohort.save()
        self.playbook.status = LessonPlaybook.STATUS_DRAFT
        self.playbook.save()
        result = start_class_session(actor=self.teacher, cohort=self.cohort, lesson=self.lesson)
        self.assertEqual(result.code, "playbook_not_ready")

    def test_open_activity_serializes_on_session_and_rejects_second_open(self):
        second_exercise = Exercise.objects.create(
            course=self.course,
            lesson=self.lesson,
            created_by=self.teacher,
            title="Ikkinchi mashq",
            kind="single_choice",
            prompt="2 + 2 = ?",
            config={"options": [{"id": "a", "text": "4"}, {"id": "b", "text": "5"}]},
            answer_key={"correct": ["a"]},
        )
        PlaybookExercise.objects.create(playbook=self.playbook, exercise=second_exercise, order=2)
        session = self.start()
        first_act, second_act = list(session.classbook_activities.order_by("order"))
        opened1 = open_activity(actor=self.teacher, activity=first_act)
        self.assertTrue(opened1.ok)

        opened2 = open_activity(actor=self.teacher, activity=second_act)
        self.assertFalse(opened2.ok)
        self.assertEqual(opened2.code, "another_open")

    def test_activity_submission_results_and_finish_are_one_persistent_flow(self):
        session = self.start()
        activity = session.classbook_activities.get()
        opened = open_activity(actor=self.teacher, activity=activity)
        self.assertTrue(opened.ok)
        activity.refresh_from_db()
        self.assertEqual(activity.status, ActivityRun.STATUS_OPEN)
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(activity=activity, kind=TelegramGroupDelivery.KIND_LINK).exists()
        )

        correct = submit_response(user=self.student, activity=activity, answer="o2")
        incorrect = submit_response(user=self.second, activity=activity, answer="o1")
        self.assertTrue(correct.ok)
        self.assertTrue(incorrect.ok)
        self.assertGreaterEqual(correct.response.score, Decimal("100"))
        self.assertEqual(incorrect.response.score, Decimal("0"))
        self.assertEqual(TelegramLessonCheckIn.objects.filter(session=session).count(), 2)

        duplicate = submit_response(user=self.student, activity=activity, answer="o1")
        self.assertEqual(duplicate.code, "already_submitted")
        self.assertEqual(StudentResponse.objects.filter(activity=activity, enrollment=self.enrollment).count(), 1)

        closed = close_activity(actor=self.teacher, activity=activity)
        self.assertTrue(closed.ok)
        activity.refresh_from_db()
        self.assertEqual(activity.status, ActivityRun.STATUS_REVEALED)
        self.assertEqual(
            Notification.objects.filter(external_key=f"classbook-activity-result-{activity.id}").count(), 3
        )
        self.assertEqual(
            TelegramOutbox.objects.filter(
                notification__external_key=f"classbook-activity-result-{activity.id}"
            ).count(),
            3,
        )
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(
                activity=activity,
                kind=TelegramGroupDelivery.KIND_TEXT,
                external_key=f"classbook-activity-{activity.id}-result",
            ).exists()
        )
        student_result = Notification.objects.get(
            recipient=self.student, external_key=f"classbook-activity-result-{activity.id}"
        )
        self.assertIn("Javobingiz", student_result.message)
        self.assertIn("Istanbul", student_result.message)
        absent_result = Notification.objects.get(
            recipient=self.absent, external_key=f"classbook-activity-result-{activity.id}"
        )
        self.assertIn("javob yubormadingiz", absent_result.message)

        finished = finish_class_session(actor=self.teacher, session=session)
        self.assertTrue(finished.ok, finished.message)
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramLessonSession.STATUS_CLOSED)
        self.assertEqual(Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson).status, "present")
        self.assertEqual(Attendance.objects.get(enrollment=self.second_enrollment, lesson=self.lesson).status, "present")
        self.assertEqual(Attendance.objects.get(enrollment=self.absent_enrollment, lesson=self.lesson).status, "absent")
        self.assertTrue(CohortLessonRelease.objects.filter(cohort=self.cohort, lesson=self.lesson, is_released=True).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.absent, external_key=f"classbook-absent-{session.id}").exists())
        self.assertTrue(TelegramGroupDelivery.objects.filter(external_key__endswith="attendance-close").exists())
        self.assertTrue(TelegramGroupDelivery.objects.filter(external_key__endswith="homework").exists())

    def test_outsider_and_deadline_are_rejected(self):
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)
        denied = submit_response(user=self.outsider, activity=activity, answer="o2")
        self.assertEqual(denied.code, "no_access")
        ActivityRun.objects.filter(pk=activity.pk).update(closes_at=timezone.now() - datetime.timedelta(seconds=1))
        expired = submit_response(user=self.student, activity=activity, answer="o2")
        self.assertEqual(expired.code, "deadline")


class ClassbookViewTests(ClassbookFixtureMixin, TestCase):
    def test_teacher_can_prepare_and_start_from_one_surface(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("classbook:teacher_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Darsni boshlash")
        response = self.client.post(reverse("classbook:session_start", args=[self.cohort.id, self.lesson.id]))
        self.assertEqual(response.status_code, 302)
        session = TelegramLessonSession.objects.get()
        self.assertEqual(response.url, reverse("classbook:teacher_session", args=[session.id]))

    def test_student_cannot_open_teacher_surface(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("classbook:teacher_home"))
        self.assertEqual(response.status_code, 302)

    def test_teacher_can_reorder_playbook_without_rebuilding_it(self):
        config, key = parse_author_definition("true_false", "true")
        second_exercise = Exercise.objects.create(
            course=self.course,
            created_by=self.teacher,
            title="Ikkinchi mashq",
            kind="true_false",
            prompt="To'g'rimi?",
            config=config,
            answer_key=key,
        )
        second_step = PlaybookExercise.objects.create(
            playbook=self.playbook, exercise=second_exercise, order=2
        )
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse("classbook:playbook_move_exercise", args=[second_step.id, "up"])
        )

        self.assertEqual(response.status_code, 302)
        self.step.refresh_from_db()
        second_step.refresh_from_db()
        self.assertEqual((second_step.order, self.step.order), (1, 2))

    def test_live_payload_does_not_leak_answer_key(self):
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)
        self.client.force_login(self.student)
        response = self.client.get(reverse("classbook:live_activity", args=[activity.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '"answer_key"')
        self.assertNotContains(response, '"correct": ["o2"]')
        self.assertNotContains(response, "Istanbul eng katta shahardir.")

    def test_queued_activity_and_media_cannot_be_guessed_early(self):
        config, key = parse_author_definition("true_false", "ha")
        future = Exercise.objects.create(
            course=self.course,
            created_by=self.teacher,
            title="Keyingi mashq",
            kind="true_false",
            prompt="Oldindan ko'rinmasin",
            config=config,
            answer_key=key,
        )
        PlaybookExercise.objects.create(playbook=self.playbook, exercise=future, order=2)
        session = self.start()
        queued = session.classbook_activities.get(order=2)
        self.client.force_login(self.student)

        self.assertEqual(
            self.client.get(reverse("classbook:live_activity", args=[queued.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("classbook:live_activity_state", args=[queued.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("classbook:activity_media", args=[queued.id])).status_code,
            404,
        )

    def test_activity_media_uses_the_session_snapshot_not_later_exercise_edits(self):
        old_bytes = b"\x89PNG\r\n\x1a\nold-classbook-media"
        new_bytes = b"\x89PNG\r\n\x1a\nnew-classbook-media"
        with tempfile.TemporaryDirectory() as private_root, override_settings(
            PRIVATE_MEDIA_ROOT=private_root
        ):
            self.exercise.media.save("old.png", ContentFile(old_bytes), save=False)
            self.exercise.media_kind = "image"
            self.exercise.save(update_fields=["media", "media_kind"])
            session = self.start()
            activity = session.classbook_activities.get()
            open_activity(actor=self.teacher, activity=activity)

            self.exercise.media.save("new.png", ContentFile(new_bytes), save=False)
            self.exercise.save(update_fields=["media"])
            self.client.force_login(self.student)
            response = self.client.get(reverse("classbook:activity_media", args=[activity.id]))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), old_bytes)
            # `response.close()` ATAYLAB ishlatilmaydi: u Django'ning
            # `request_finished` signalini yuboradi, signal esa `TestCase`
            # tranzaksiyasini tutib turgan DB ulanishini yopadi. SQLite bunga
            # e'tibor bermaydi, PostgreSQL esa shu testdan keyingi hammasini
            # `InterfaceError: connection already closed` bilan yiqitadi —
            # CI'ning `integration` ishida aynan 9 ta test shundan qizargan.
            # Bu yerda faqat fayl oqimi yopiladi: Windowsda fayl qulfi
            # bo'shaydi (`TemporaryDirectory` tozalanadi), ulanish tirik qoladi.
            #
            # Ikkinchi yechim ham bor edi — testni `TransactionTestCase` ga
            # ko'chirish. U ishlaydi, ammo har testdan keyin 125 jadvalni
            # `TRUNCATE` qiladi va testni qo'shnilaridan ajratib, fixture
            # sinfini takrorlashni talab qiladi. 2026-09-11 da shu variant
            # rad etildi (marinebook).
            if hasattr(response, "file_to_stream") and response.file_to_stream:
                response.file_to_stream.close()

            self.client.force_login(self.outsider)
            self.assertEqual(
                self.client.get(reverse("classbook:activity_media", args=[activity.id])).status_code,
                404,
            )

    def test_outsider_sees_404_not_resource_existence(self):
        session = self.start()
        activity = session.classbook_activities.get()
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("classbook:live_activity", args=[activity.id])).status_code, 404
        )

    def test_json_submit_hides_score_until_teacher_reveals(self):
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("classbook:live_activity_submit", args=[activity.id]),
            data=json.dumps({"answer": "o2"}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertNotIn("score", payload)
        live_page = self.client.get(reverse("classbook:live_session", args=[session.id]))
        self.assertEqual(live_page.context["leaderboard"], [])
        self.assertEqual(
            self.client.get(reverse("classbook:activity_result", args=[activity.id])).status_code, 404
        )
        close_activity(actor=self.teacher, activity=activity)
        live_page = self.client.get(reverse("classbook:live_session", args=[session.id]))
        self.assertEqual(len(live_page.context["leaderboard"]), 1)
        result_page = self.client.get(reverse("classbook:activity_result", args=[activity.id]))
        self.assertEqual(result_page.status_code, 200)
        self.assertContains(result_page, "To'g'ri javob")

    def test_teacher_has_separate_results_surface_and_safe_csv_exports(self):
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)
        submit_response(user=self.student, activity=activity, answer="o2")
        close_activity(actor=self.teacher, activity=activity)
        self.student.first_name = "=FORMULA"
        self.student.save(update_fields=["first_name"])
        Enrollment.objects.create(
            student=self.teacher,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate() + datetime.timedelta(days=30),
        )

        self.client.force_login(self.teacher)
        result_redirect = self.client.get(
            reverse("classbook:activity_result", args=[activity.id])
        )
        self.assertRedirects(
            result_redirect,
            reverse("classbook:teacher_activity_result", args=[activity.id]),
        )
        page = self.client.get(reverse("classbook:teacher_activity_result", args=[activity.id]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Dars boshqaruvi")
        self.assertNotContains(page, "Siz bu mashqda javob yubormagansiz")

        activity_csv = self.client.get(reverse("classbook:teacher_activity_export", args=[activity.id]))
        self.assertEqual(activity_csv.status_code, 200)
        self.assertIn("text/csv", activity_csv["Content-Type"])
        self.assertIn("'=FORMULA", activity_csv.content.decode("utf-8-sig"))

        session_csv = self.client.get(reverse("classbook:teacher_session_export", args=[session.id]))
        self.assertEqual(session_csv.status_code, 200)
        body = session_csv.content.decode("utf-8-sig")
        self.assertIn("Davomat", body)
        self.assertIn("Poytaxt", body)

        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse("classbook:teacher_activity_result", args=[activity.id])).status_code,
            302,
        )


class TelegramGroupDeliveryTests(ClassbookFixtureMixin, TestCase):
    def test_attendance_delivery_renders_existing_bot_callback(self):
        from .delivery import claim_pending_group_deliveries, mark_group_delivery_sent, render_group_delivery_markup

        session = self.start()
        claimed = claim_pending_group_deliveries(limit=10)
        attendance = next(item for item in claimed if item.kind == TelegramGroupDelivery.KIND_ATTENDANCE)
        markup = render_group_delivery_markup(attendance)
        self.assertEqual(markup.inline_keyboard[0][0].callback_data, f"attendance:{session.id}")
        mark_group_delivery_sent(attendance, telegram_message_id=987)
        session.refresh_from_db()
        self.assertEqual(session.attendance_message_id, 987)

    @override_settings(TELEGRAM_BOT_TOKEN="1234567890:configured-token")
    def test_group_queue_is_visible_in_control_center(self):
        from core.control_center import build_control_center_snapshot

        self.start()
        snapshot = build_control_center_snapshot()
        result = next(item for item in snapshot.results if item.definition.slug == "telegram_outbox")
        details = dict(result.details)
        self.assertEqual(details["group_pending"], "2")
        self.assertEqual(details["dm_pending"], "0")


class TelegramAdapterParityTests(ClassbookFixtureMixin, TestCase):
    def test_dars_command_uses_ready_classbook_playbook(self):
        result = start_lesson_session(
            chat_id=self.cohort.telegram_chat_id,
            chat_title=self.cohort.telegram_chat_title,
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.session.classbook_activities.count(), 1)
        # Handler davomat postini darhol yuboradi; orchestrator uni dublikat
        # qilib outboxga qo'ymaydi, material esa baribir navbatga tushadi.
        self.assertFalse(
            TelegramGroupDelivery.objects.filter(
                session=result.session, kind=TelegramGroupDelivery.KIND_ATTENDANCE
            ).exists()
        )
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(session=result.session, external_key__endswith="materials").exists()
        )

    def test_dars_tugadi_cannot_bypass_classbook_wrap_up(self):
        session = self.start()
        result = close_lesson_session(
            chat_id=self.cohort.telegram_chat_id,
            actor_telegram_id=self.teacher.telegram_id,
        )
        self.assertTrue(result.ok, result.message)
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramLessonSession.STATUS_CLOSED)
        self.assertTrue(
            CohortLessonRelease.objects.filter(cohort=self.cohort, lesson=self.lesson, is_released=True).exists()
        )
        self.assertTrue(
            TelegramGroupDelivery.objects.filter(session=session, external_key__endswith="homework").exists()
        )
        self.assertFalse(
            TelegramGroupDelivery.objects.filter(session=session, external_key__endswith="attendance-close").exists()
        )
        self.assertFalse(result.announce_names)
        self.assertEqual(result.details["present"], [])
        self.assertEqual(result.details["absent"], [])
