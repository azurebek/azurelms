"""PUB1.6a — Blog umumiy ochiq kontrakti (domen o'zgarishisiz).

Asosiy da'volar, uchala rendererda (legacy, V1 va editorial):
* qidiruv kirishi katalog bilan bir chegarada; teg faqat slug; noma'lum qiymat 500 bermaydi;
* sahifa/teg havolalari faqat normallashgan parametrlardan (kodlangan), `aria-current`,
  `rel=prev/next`; ro'yxat to'liq tartibda (oxirida `id`);
* maqoladan "Blog"ga qaytish ayni filtr va sahifaga; tashqi `return_to` rad etiladi;
* ochiq sahifada login (username) chiqmaydi — hisobdagi ism yoki umumiy nom;
* qoralama ko'rinishida reaksiya/izoh yo'q, yopiq izohlar rost aytiladi, ko'rishlar soni yo'q;
* JavaScriptsiz olqish formasi maqolaga qaytadi (JSON klientlar o'zgarmaydi);
* so'rovlar soni maqolalar soniga bog'liq emas.
"""

import re
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog import listing
from blog.models import BlogComment, BlogPost, BlogPostRead, BlogTag
from courses import catalog
from frontend import public_query
from users.models import CustomUser

RENDERERS = (("legacy", False, False), ("v1", True, False), ("editorial", True, True))


class BlogWorld(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user(username="muallif_login", email="m@example.test", password="x")
        self.named = CustomUser.objects.create_user(
            username="nomli_login", email="n@example.test", password="x", first_name="Ali", last_name="Valiyev")
        self.tag = BlogTag.objects.create(name="Grammatika")
        self.now = timezone.now()

    def make_post(self, title, *, minutes_ago=10, author=None, featured=False, status=BlogPost.STATUS_PUBLISHED, **extra):
        post = BlogPost.objects.create(
            title=title, author=author or self.author, excerpt=f"{title} qisqa", body=f"<p>{title} matni</p>",
            status=status, featured=featured, published_at=self.now - timedelta(minutes=minutes_ago), **extra)
        return post

    def renderer(self, v1, editorial=False):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": v1})
        FeatureFlag.objects.update_or_create(slug="public_editorial_v1", defaults={"enabled": editorial})


class QueryBoundsTests(BlogWorld):
    def test_the_blog_and_the_catalog_share_one_input_rule(self):
        self.assertIs(catalog.fold, public_query.fold)
        noisy = "  bir\x00ikki\tuch to'rt besh olti yetti " + "x" * 200
        self.assertEqual(listing.BlogListQuery.from_params({"q": noisy}).q, public_query.bounded_text(noisy))
        self.assertEqual(catalog.CatalogQuery.from_params(_Params(q=noisy)).q, public_query.bounded_text(noisy))
        bounded = public_query.bounded_text(noisy)
        self.assertLessEqual(len(bounded), public_query.MAX_QUERY_CHARS)
        self.assertLessEqual(len(bounded.split(" ")), public_query.MAX_TERMS)
        self.assertNotIn("\x00", bounded)

    def test_unknown_or_malformed_filters_never_break_the_page(self):
        self.make_post("Birinchi maqola")
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                weird = self.client.get(reverse("blog:list"), {"tag": "<script>", "q": "\x00" * 50})
                self.assertEqual(weird.status_code, 200)
                self.assertContains(weird, "Birinchi maqola")  # noto'g'ri teg e'tiborsiz
                missing = self.client.get(reverse("blog:list"), {"tag": "yoq-teg"})
                self.assertContains(missing, "Maqola topilmadi")
                self.assertEqual(self.client.get(reverse("blog:list"), {"page": "99"}).status_code, 404)

    def test_the_search_form_keeps_the_bounded_value(self):
        long_query = "so'z " * 20
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                response = self.client.get(reverse("blog:list"), {"q": long_query})
                self.assertContains(response, f'maxlength="{public_query.MAX_QUERY_CHARS}"')
                self.assertEqual(response.context["search_query"], public_query.bounded_text(long_query))


class PaginationAndOrderTests(BlogWorld):
    def setUp(self):
        super().setUp()
        same_time = self.now - timedelta(hours=1)
        self.posts = []
        for index in range(20):
            post = self.make_post(f"Maqola {index:02d} a&b")
            BlogPost.objects.filter(pk=post.pk).update(published_at=same_time, created_at=same_time)
            post.tags.add(self.tag)
            self.posts.append(post)

    def test_ties_are_broken_by_id(self):
        expected = [post.pk for post in sorted(self.posts, key=lambda post: -post.pk)]
        self.assertEqual([post.pk for post in listing.list_queryset(listing.BlogListQuery())], expected)
        related = listing.related_posts(BlogPost.objects.get(pk=self.posts[0].pk))
        self.assertEqual([post.pk for post in related], expected[:listing.RELATED_LIMIT])

    def test_page_links_are_encoded_current_and_ordered(self):
        query = listing.BlogListQuery(q="a&b", tag=self.tag.slug)
        page_two = query.url(page=2)
        self.assertEqual(page_two, f"/blog/?q=a%26b&tag={self.tag.slug}&page=2")
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                response = self.client.get(reverse("blog:list"), {"q": "a&b", "tag": self.tag.slug})
                html = response.content.decode()
                self.assertIn(f'href="{page_two.replace("&", "&amp;")}" rel="next"', html)
                self.assertIn('aria-label="1-sahifa" aria-current="page"', html)
                self.assertIn('aria-label="Maqolalar sahifalari"', html)
                self.assertNotIn("&q=a&b", html)  # kodlanmagan eski havola yo'q
                second = self.client.get(page_two)
                self.assertContains(second, 'rel="prev"')

    def test_tag_links_keep_the_search_and_mark_the_current_tag(self):
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                response = self.client.get(reverse("blog:list"), {"q": "Maqola", "tag": self.tag.slug})
                links = response.context["tag_links"]
                self.assertEqual(links[0]["url"], f"/blog/?q=Maqola&tag={self.tag.slug}")
                self.assertTrue(links[0]["current"])


class FeaturedAndCardTests(BlogWorld):
    def test_featured_is_shown_once_and_the_empty_state_is_truthful(self):
        featured = self.make_post("Yagona tanlangan", featured=True)
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                response = self.client.get(reverse("blog:list"))
                self.assertEqual(response.content.decode().count(f'{featured.get_absolute_url()}'), 1)
                self.assertNotContains(response, "Maqola topilmadi")
                self.assertNotContains(response, "Hozircha maqola")
                self.assertContains(response, "Boshqa maqola hozircha yo")

    def test_v1_cards_have_unique_link_names_and_machine_dates(self):
        first, second = self.make_post("Birinchi"), self.make_post("Ikkinchi", minutes_ago=20)
        self.renderer(True)
        response = self.client.get(reverse("blog:list"))
        self.assertContains(response, 'aria-label="Birinchi — maqolani o‘qish"')
        self.assertContains(response, 'aria-label="Ikkinchi — maqolani o‘qish"')
        for post in (first, second):
            self.assertContains(response, f'<time datetime="{timezone.localtime(post.published_at).isoformat()}')
        self.assertNotContains(response, "?return_to=")  # toza ro'yxatdan qaytish ortiqcha emas


class ReturnToTests(BlogWorld):
    def test_detail_returns_to_the_same_filter_and_page_in_all_renderers(self):
        post = self.make_post("Qaytish")
        back = "/blog/?q=Qaytish"
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                listing_page = self.client.get(reverse("blog:list"), {"q": "Qaytish"})
                self.assertContains(listing_page, f"{post.get_absolute_url()}?return_to=/blog/%3Fq%3DQaytish")
                detail = self.client.get(post.get_absolute_url(), {"return_to": back})
                self.assertContains(detail, f'href="{back}"')
                hostile = self.client.get(post.get_absolute_url(), {"return_to": "//evil.example/blog/"})
                self.assertNotContains(hostile, 'href="//evil.example')
                self.assertEqual(hostile.context["public_back_url"], "/blog/")


class PeopleTests(BlogWorld):
    def test_logins_never_appear_on_public_blog_pages(self):
        post = self.make_post("Ismlar", allow_comments=True)
        BlogComment.objects.create(post=post, user=self.author, content="Login egasi izohi")
        BlogComment.objects.create(post=post, user=self.named, content="Ismli izoh")
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                for url in (reverse("blog:list"), post.get_absolute_url()):
                    response = self.client.get(url)
                    self.assertNotContains(response, "muallif_login")
                    self.assertNotContains(response, "nomli_login")
                detail = self.client.get(post.get_absolute_url())
                self.assertContains(detail, "Platforma muallifi")
                self.assertContains(detail, "Ali Valiyev")
                self.assertContains(detail, "Foydalanuvchi")


class LegacyTruthTests(BlogWorld):
    def setUp(self):
        super().setUp()
        self.renderer(False)
        self.staff = CustomUser.objects.create_user(username="xodim", email="x@example.test", password="x", is_staff=True)

    def test_preview_has_no_reactions_or_comment_form(self):
        draft = self.make_post("Qoralama", status=BlogPost.STATUS_DRAFT)
        self.client.force_login(self.staff)
        response = self.client.get(draft.get_absolute_url(), {"preview": "1"})
        self.assertContains(response, "Bu qoralama")
        self.assertNotContains(response, reverse("blog:clap", args=[draft.slug]))
        self.assertNotContains(response, reverse("blog:comment_create", args=[draft.slug]))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_closed_comments_and_counters_are_told_truthfully(self):
        post = self.make_post("Yopiq", allow_comments=False)
        BlogPost.objects.filter(pk=post.pk).update(view_count=42)
        self.client.force_login(self.named)
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, "yangi izohlar yopilgan")
        self.assertNotContains(response, reverse("blog:comment_create", args=[post.slug]))
        self.assertNotContains(response, "ko'rish")  # anonim o'qish sanalmaydi — son rost emas
        self.assertContains(response, f"{post.reading_time_minutes} daqiqa")

    def test_comment_login_returns_to_the_comments(self):
        post = self.make_post("Izohga kirish")
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                response = self.client.get(post.get_absolute_url())
                self.assertContains(response, f"?next={post.get_absolute_url()}%23comments")


class NoScriptClapTests(BlogWorld):
    def test_a_plain_form_returns_to_the_post_and_json_clients_are_unchanged(self):
        post = self.make_post("Olqish")
        self.client.force_login(self.named)
        url = reverse("blog:clap", args=[post.slug])
        page = self.client.post(url, HTTP_ACCEPT="text/html,application/xhtml+xml")
        self.assertRedirects(page, f"{post.get_absolute_url()}#clap", fetch_redirect_response=False)
        api = self.client.post(url, HTTP_ACCEPT="application/json")
        self.assertEqual(api.json()["my_clap_count"], 2)
        self.assertEqual(self.client.post(url).json()["my_clap_count"], 3)


class PublicContractTests(BlogWorld):
    def test_filtered_lists_are_not_indexed_and_guests_leave_no_trace(self):
        post = self.make_post("Iz")
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                filtered = self.client.get(reverse("blog:list"), {"q": "Iz"})
                self.assertContains(filtered, '<meta name="robots" content="noindex, follow">')
                canonical = re.search(r'<link rel="canonical" href="([^"]+)">', filtered.content.decode()).group(1)
                self.assertTrue(canonical.endswith("/blog/"), canonical)
                detail = self.client.get(post.get_absolute_url())
                self.assertEqual(detail.cookies.get("blog_visitor"), None)
        self.assertEqual(BlogPostRead.objects.count(), 0)
        self.assertEqual(self.client.get(self.make_post("Yashirin", status=BlogPost.STATUS_DRAFT).get_absolute_url()).status_code, 404)

    def test_query_count_does_not_grow_with_posts(self):
        def count(url):
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(url).status_code, 200)
            return len(queries)

        first = self.make_post("Boshlang'ich", featured=True)
        first.tags.add(self.tag)
        self.make_post("Ikkinchi", minutes_ago=20).tags.add(self.tag)  # ro'yxat bo'sh emas
        for name, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=name):
                small_list, small_detail = count(reverse("blog:list")), count(first.get_absolute_url())
                extra = [self.make_post(f"Qo'shimcha {index}", minutes_ago=30 + index) for index in range(12)]
                for post in extra:
                    post.tags.add(self.tag)
                self.assertEqual(count(reverse("blog:list")), small_list)
                self.assertEqual(count(first.get_absolute_url()), small_detail)
                BlogPost.objects.filter(pk__in=[post.pk for post in extra]).delete()


class _Params(dict):
    def getlist(self, key):
        value = self.get(key)
        return [] if value is None else [value]
