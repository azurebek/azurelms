"""Readable studio copy must keep the existing form and publishing contract."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.flags import set_flag

from .forms import BlogPostForm
from .models import BlogPost


class BlogStudioCopyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = get_user_model().objects.create_user(
            username="studio-copy-author", email="studio-copy@example.test", is_staff=True,
        )
        cls.post = BlogPost.objects.create(
            author=cls.author, title="Mavjud maqola", body="<p>Mavjud matn.</p>",
            status=BlogPost.STATUS_DRAFT,
        )

    def setUp(self):
        self.client.force_login(self.author)

    def set_navigation(self, enabled):
        set_flag("backoffice_unified_navigation", enabled=enabled, reason="Studio copy regression")

    def payload(self, **changes):
        data = {
            "title": "Talaffuz mashqi", "excerpt": "Qisqa tavsif", "body": "<p>Turkcha gapiring.</p>",
            "status": "draft", "featured_quote": "Har kuni mashq qiling.", "tag_names": "grammatika, maslahat",
            "featured": "on", "allow_comments": "on", "cover_alt_text": "Kitob rasmi",
            "seo_title": "Talaffuz", "meta_description": "Har kunlik mashq",
        }
        data.update(changes)
        return data

    def test_simple_copy_keeps_fields_widgets_media_and_validation(self):
        legacy = BlogPostForm(data=self.payload())
        simple = BlogPostForm(data=self.payload(), simple_copy=True)
        self.assertEqual(list(simple.fields), list(legacy.fields))
        for name, field in legacy.fields.items():
            counterpart = simple.fields[name]
            with self.subTest(name=name):
                self.assertIs(type(counterpart), type(field))
                self.assertIs(type(counterpart.widget), type(field.widget))
                self.assertEqual(counterpart.required, field.required)
                self.assertEqual(counterpart.validators, field.validators)
                self.assertEqual(
                    {key: value for key, value in counterpart.widget.attrs.items() if key != "placeholder"},
                    {key: value for key, value in field.widget.attrs.items() if key != "placeholder"},
                )
        self.assertEqual(str(simple.media), str(legacy.media))
        self.assertTrue(legacy.is_valid(), legacy.errors)
        self.assertTrue(simple.is_valid(), simple.errors)
        self.assertEqual(simple.cleaned_data, legacy.cleaned_data)
        # Constructing a simpler form must not mutate the next legacy form.
        self.assertIn("excerpt", BlogPostForm().fields["excerpt"].widget.attrs["placeholder"])

    def test_create_and_edit_use_flag_scoped_copy_and_preserve_multipart_editor(self):
        for enabled in (False, True):
            self.set_navigation(enabled)
            for url in (reverse("blog:studio_create"), reverse("blog:studio_edit", args=[self.post.slug])):
                with self.subTest(enabled=enabled, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'method="post" enctype="multipart/form-data"')
                    self.assertContains(response, 'name="body"')
                    self.assertContains(response, 'name="csrfmiddlewaretoken"')
                    self.assertContains(response, "django_ckeditor_5")
                    form = response.context["form"]
                    if enabled:
                        self.assertEqual(form.fields["excerpt"].widget.attrs["placeholder"], "Maqola haqida qisqacha yozing...")
                        self.assertContains(response, "Ajratib ko‘rsatiladigan iqtibos")
                        self.assertContains(response, '<details class="bo-settings-detail">')
                        self.assertNotContains(response, "Highlight iqtibos")
                        self.assertNotContains(response, "Share preview")
                    else:
                        self.assertContains(response, "Highlight iqtibos")
                        self.assertNotContains(response, '<details class="bo-settings-detail">')
                        self.assertIn("excerpt", form.fields["excerpt"].widget.attrs["placeholder"])

    def test_bound_errors_open_extra_section_and_preserve_input_without_write(self):
        self.set_navigation(True)
        before = BlogPost.objects.count()
        response = self.client.post(reverse("blog:studio_create"), self.payload(seo_title="x" * 181))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="bo-settings-detail" open>')
        self.assertTrue(response.context["form"]["seo_title"].errors)
        self.assertEqual(response.context["form"]["title"].value(), "Talaffuz mashqi")
        self.assertEqual(BlogPost.objects.count(), before)

    def test_existing_create_and_update_keep_saved_fields_for_both_flags(self):
        for enabled in (False, True):
            self.set_navigation(enabled)
            with self.subTest(enabled=enabled):
                response = self.client.post(reverse("blog:studio_create"), self.payload())
                self.assertEqual(response.status_code, 302)
                post = BlogPost.objects.order_by("-pk").first()
                self.assertEqual(post.author, self.author)
                self.assertEqual(post.status, "draft")
                self.assertEqual(post.featured_quote, "Har kuni mashq qiling.")
                self.assertEqual(post.seo_title, "Talaffuz")
                self.assertEqual(set(post.tags.values_list("name", flat=True)), {"grammatika", "maslahat"})
                self.assertTrue(post.featured)
                self.assertRedirects(response, reverse("blog:studio_edit", args=[post.slug]), fetch_redirect_response=False)
                response = self.client.post(
                    reverse("blog:studio_edit", args=[post.slug]),
                    self.payload(title="Rejadagi maqola", status="published", published_at="2030-01-02T10:00"),
                )
                self.assertEqual(response.status_code, 302)
                post.refresh_from_db()
                self.assertEqual(post.title, "Rejadagi maqola")
                self.assertEqual(post.status, "published")
                self.assertEqual(post.published_at.year, 2030)
                self.assertFalse(post.is_live)
