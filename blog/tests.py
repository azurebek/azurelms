from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BlogComment, BlogPost
from users.models import CustomUser


class BlogFlowTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user(
            username="author",
            email="author@example.com",
            password="testpass123",
            first_name="Azure",
        )
        self.post = BlogPost.objects.create(
            title="Medium-style testing post",
            author=self.author,
            excerpt="Short summary",
            body="<h2>Intro</h2><p>This is a test article body.</p>",
            status=BlogPost.STATUS_PUBLISHED,
            published_at=timezone.now(),
        )

    def test_public_list_and_detail_are_accessible(self):
        list_response = self.client.get(reverse("blog:list"))
        detail_response = self.client.get(reverse("blog:detail", args=[self.post.slug]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.post.title)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, self.post.title)

    def test_unique_view_counter_counts_per_visitor(self):
        url = reverse("blog:detail", args=[self.post.slug])

        self.client.get(url)
        self.client.get(url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)

        second_client = Client()
        second_client.get(url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 2)

    def test_clap_endpoint_accumulates_for_same_visitor(self):
        url = reverse("blog:clap", args=[self.post.slug])

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.clap_count, 2)
        self.assertEqual(second.json()["my_clap_count"], 2)

    def test_authenticated_user_can_comment_and_toggle_like(self):
        commenter = CustomUser.objects.create_user(
            username="commenter",
            email="commenter@example.com",
            password="testpass123",
        )
        self.client.force_login(commenter)

        comment_response = self.client.post(
            reverse("blog:comment_create", args=[self.post.slug]),
            {"content": "Zo'r maqola."},
        )
        self.assertEqual(comment_response.status_code, 302)

        comment = BlogComment.objects.get(post=self.post, user=commenter)
        self.post.refresh_from_db()
        self.assertEqual(self.post.comment_count, 1)

        like_url = reverse("blog:comment_like", args=[comment.pk])
        like_response = self.client.post(like_url)
        unlike_response = self.client.post(like_url)

        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.json()["liked"])
        self.assertEqual(like_response.json()["like_count"], 1)
        self.assertEqual(unlike_response.status_code, 200)
        self.assertFalse(unlike_response.json()["liked"])
        self.assertEqual(unlike_response.json()["like_count"], 0)
