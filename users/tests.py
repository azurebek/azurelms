from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from users.context_processors import notification_context
from users.models import Notification


User = get_user_model()


class NotificationContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="notif-user",
            email="notif-user@example.com",
            password="testpass123",
        )

    def test_context_returns_full_unread_count_while_limiting_preview_list(self):
        for index in range(10):
            Notification.objects.create(
                recipient=self.user,
                title=f"Notif {index}",
                message=f"Message {index}",
            )

        request = self.factory.get("/")
        request.user = self.user

        context = notification_context(request)

        self.assertEqual(context["unread_notifications_count"], 10)
        self.assertEqual(len(context["notifications"]), 8)
