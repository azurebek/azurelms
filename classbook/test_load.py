from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from bot.models import TelegramOutbox
from cohorts.models import Enrollment
from users.models import Notification

from .models import ActivityRun, StudentResponse
from .services import close_activity, open_activity, session_leaderboard, submit_response
from .tests import ClassbookFixtureMixin


User = get_user_model()


class FiftyLearnerContractTests(ClassbookFixtureMixin, TestCase):
    """Mahsulot va'dasi: bitta activity 50 learner natijasini qo'lda tekshirtirmaydi."""

    def test_fifty_answers_are_graded_and_ranked_without_duplicates(self):
        users = [
            User(
                username=f"mass-{index}",
                email=f"mass-{index}@classbook.test",
                telegram_id=30000 + index,
            )
            for index in range(50)
        ]
        User.objects.bulk_create(users)
        users = list(User.objects.filter(username__startswith="mass-").order_by("id"))
        Enrollment.objects.bulk_create([
            Enrollment(student=user, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE)
            for user in users
        ])
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)

        for index, user in enumerate(users):
            answer = "o2" if index % 2 == 0 else "o1"
            result = submit_response(user=user, activity=activity, answer=answer)
            self.assertTrue(result.ok, result.message)

        self.assertEqual(StudentResponse.objects.filter(activity=activity).count(), 50)
        leaderboard = session_leaderboard(session)
        self.assertEqual(len(leaderboard), 50)
        self.assertTrue(all(row["score"] > 0 for row in leaderboard[:25]))
        self.assertTrue(all(row["score"] == 0 for row in leaderboard[25:]))

        closed = close_activity(actor=self.teacher, activity=activity)
        self.assertTrue(closed.ok, closed.message)
        result_notes = Notification.objects.filter(
            external_key=f"classbook-activity-result-{activity.id}"
        )
        self.assertEqual(result_notes.count(), 53)
        self.assertEqual(
            TelegramOutbox.objects.filter(notification__in=result_notes).count(),
            53,
        )


class PostgreSQLConcurrentSubmissionTests(ClassbookFixtureMixin, TransactionTestCase):
    """CI PostgreSQL jobida 50 bir vaqtdagi request uchun release gate."""

    reset_sequences = True

    def test_fifty_simultaneous_submissions_are_each_recorded_once(self):
        if connection.vendor != "postgresql":
            self.skipTest("Haqiqiy parallel DB gate PostgreSQL CI ishida yuguradi.")

        users = [
            User(username=f"parallel-{index}", email=f"parallel-{index}@classbook.test")
            for index in range(50)
        ]
        User.objects.bulk_create(users)
        user_ids = list(User.objects.filter(username__startswith="parallel-").values_list("id", flat=True))
        Enrollment.objects.bulk_create([
            Enrollment(student_id=user_id, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE)
            for user_id in user_ids
        ])
        session = self.start()
        activity = session.classbook_activities.get()
        open_activity(actor=self.teacher, activity=activity)

        def worker(user_id):
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                fresh_activity = ActivityRun.objects.get(pk=activity.pk)
                return submit_response(user=user, activity=fresh_activity, answer="o2").code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(worker, user_ids))

        self.assertEqual(codes.count("submitted"), 50)
        self.assertEqual(StudentResponse.objects.filter(activity=activity).count(), 50)
