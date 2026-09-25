"""PostgreSQL regression for concurrent Classbook resume/attendance finish."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from bot.models import TelegramLessonSession
from cohorts.models import Attendance
from . import services
from .tests import ClassbookFixtureMixin


@skipUnlessDBFeature('has_select_for_update')
class SessionLockOrderTests(ClassbookFixtureMixin, TransactionTestCase):
    def test_resume_inserting_activity_and_finish_cannot_invert_locks(self):
        # Legacy open session has no activity rows yet. Resume must insert one,
        # whose deferred PostgreSQL FK check needs a lock on the session.
        session = TelegramLessonSession.objects.create(cohort=self.cohort, lesson=self.lesson,
            chat_id=self.cohort.telegram_chat_id, started_by=self.teacher)
        resume_has_cohort = Event()
        finish_wants_cohort = Event()
        original_ensure = services._ensure_activity_runs

        def ensure_after_finish_attempt(existing, playbook):
            resume_has_cohort.set()
            self.assertTrue(finish_wants_cohort.wait(10), 'Finish never attempted the cohort lock')
            return original_ensure(existing, playbook)

        def observe_cohort_lock(execute, sql, params, many, context):
            if 'FOR UPDATE' in sql and 'FROM "cohorts_cohort"' in sql:
                finish_wants_cohort.set()
            return execute(sql, params, many, context)

        def resume():
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                return services.start_class_session(actor=self.teacher, cohort=self.cohort, lesson=self.lesson)
            finally:
                connections.close_all()

        def finish():
            try:
                self.assertTrue(resume_has_cohort.wait(10), 'Resume never acquired the cohort')
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                with connections['default'].execute_wrapper(observe_cohort_lock):
                    return services.finish_class_session(actor=self.teacher, session=session)
            finally:
                connections.close_all()

        with patch.object(services, '_ensure_activity_runs', side_effect=ensure_after_finish_attempt), \
                patch.object(services, 'broadcast_after_commit'):
            with ThreadPoolExecutor(max_workers=2) as pool:
                resumed, finished = pool.submit(resume), pool.submit(finish)
                self.assertEqual(resumed.result(timeout=20).code, 'already_open')
                self.assertTrue(finished.result(timeout=20).ok)
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramLessonSession.STATUS_CLOSED)
        self.assertEqual(session.classbook_activities.count(), 1)
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), 3)
