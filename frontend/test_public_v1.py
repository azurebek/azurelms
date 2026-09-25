import datetime
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog.models import BlogComment, BlogPost, BlogTag
from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, Module
from frontend.models import LandingNavItem, LegalPage, SiteSettings, Statistic
from frontend.templatetags.public_v1 import public_url
from sit.models import KnowledgeArticle, University, UniversityFaculty, UniversityProgram
from subscriptions.models import Plan, PlanFeature


class PublicV1Tests(TestCase):
    def setUp(self):
        self.flag = FeatureFlag.objects.create(slug='frontend_v1_public', enabled=True)
        self.user = get_user_model().objects.create_user('public-learner', email='public@example.test')
        self.staff = get_user_model().objects.create_user('public-editor', email='editor@example.test', is_staff=True)
        self.course = Course.objects.create(title='Turk tili A1', description='<p>Real kurs matni</p>', level='beginner')
        module = Module.objects.create(course=self.course, title='Birinchi modul')
        self.lesson = Lesson.objects.create(module=module, title='Ochiq sarlavha', content='<p>PRIVATE LESSON BODY</p>')
        self.post = BlogPost.objects.create(title='Haqiqiy maqola', author=self.staff, body='<p>Maqola matni</p>', status=BlogPost.STATUS_PUBLISHED)
        self.tag = BlogTag.objects.create(name='Mashq', slug='mashq')
        self.post.tags.add(self.tag)
        self.university = University.objects.create(name='Sinov universiteti', short_name='SU', city='Istanbul', is_published=True, source_url='https://example.edu.tr/', last_verified_on=datetime.date(2026, 9, 25), admission_status='open')
        faculty = UniversityFaculty.objects.create(university=self.university, name='Muhandislik')
        self.program = UniversityProgram.objects.create(faculty=faculty, name='Dasturlash', degree_level='bachelor', language='tr', duration='4 yil', tuition_fee=1250)
        self.article = KnowledgeArticle.objects.create(title='Hujjatlar', category='Qabul', body='<p>Qo‘llanma matni</p>', is_published=True, is_featured=True, source_url='https://example.edu.tr/docs', last_verified_on=datetime.date(2026, 9, 25))
        self.plan = Plan.objects.create(name='Faol tarif', price=230000)
        PlanFeature.objects.create(plan=self.plan, name='Ustoz yordami')

    def routes(self):
        return [
            ('home', [], 'index.html'), ('about', [], 'about.html'),
            ('courses', [], 'courses/course_list.html'), ('course_detail', [self.course.pk], 'courses/course_detail.html'),
            ('subscriptions:pricing', [], 'subscriptions/pricing.html'),
            ('privacy_policy', [], 'legal_page.html'), ('terms_of_service', [], 'legal_page.html'), ('faq_page', [], 'legal_page.html'),
            ('blog:list', [], 'blog/post_list.html'), ('blog:detail', [self.post.slug], 'blog/post_detail.html'),
            ('sit:home', [], 'sit/home.html'), ('sit:university_list', [], 'sit/university_list.html'),
            ('sit:university_detail', [self.university.slug], 'sit/university_detail.html'),
            ('sit:knowledge_detail', [self.article.slug], 'sit/knowledge_detail.html'),
        ]

    def test_all_fourteen_routes_on_and_off_use_separate_assets(self):
        for enabled in (True, False):
            self.flag.enabled = enabled; self.flag.save()
            for name, args, template in self.routes():
                with self.subTest(name=name, enabled=enabled):
                    response = self.client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, ('frontend_v1/public/' if enabled else '') + template)
                    if enabled:
                        self.assertContains(response, 'frontend_v1/css/public.css')
                        self.assertNotContains(response, 'css/public-shell.css')
                        self.assertNotContains(response, 'css/sit.css')
                        self.assertNotContains(response, 'preview-bootstrap')
                        self.assertIn('no-store', response['Cache-Control'])

    def test_flag_defaults_off_without_override(self):
        self.flag.delete()
        self.assertTemplateUsed(self.client.get(reverse('home')), 'index.html')

    def test_home_numeric_statistic_uses_canonical_formatted_value(self):
        statistic = Statistic.objects.create(label='Real count', numeric_value='42.5', decimals=1, suffix='%')
        statistic.refresh_from_db()
        self.assertContains(self.client.get(reverse('home')), statistic.display_value)

    def test_home_authenticated_redirect_and_public_does_not_grant_access(self):
        self.assertEqual(Enrollment.objects.count(), 0)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('home')), reverse('dashboard'), fetch_redirect_response=False)
        detail = self.client.get(reverse('course_detail', args=[self.course.pk]))
        self.assertContains(detail, reverse('cohorts:checkout', kwargs={'course_id': self.course.pk}))
        self.assertNotContains(detail, 'PRIVATE LESSON BODY')
        self.assertFalse(detail.context['is_enrolled'])
        self.assertEqual(Enrollment.objects.count(), 0)
        self.assertEqual(self.client.get(reverse('lesson_detail', kwargs={'course_id': self.course.pk, 'lesson_id': self.lesson.pk})).status_code, 302)

    def test_course_cta_uses_canonical_active_access_and_exact_login_next(self):
        url = reverse('course_detail', args=[self.course.pk])
        self.assertContains(self.client.get(url), '?next=' + quote(url, safe='/'))
        cohort = Cohort.objects.create(course=self.course, name='A1', start_date=datetime.date.today())
        enrollment = Enrollment.objects.create(student=self.user, cohort=cohort, status='active')
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertTrue(response.context['is_enrolled'])
        self.assertContains(response, reverse('course_study', kwargs={'course_id': self.course.pk}))
        enrollment.status = 'expired'; enrollment.save()
        self.assertFalse(self.client.get(url).context['is_enrolled'])

    def test_catalog_multi_level_search_and_pagination_preserve_query(self):
        Course.objects.bulk_create([Course(title=f'A1 kurs {i}', level='beginner') for i in range(10)])
        response = self.client.get(reverse('courses'), {'q': 'A1', 'level': ['beginner', 'intermediate'], 'sort': 'oldest'})
        self.assertEqual(response.context['page_obj'].paginator.count, 11)
        self.assertContains(response, 'level=beginner&amp;level=intermediate')
        self.assertContains(response, 'page=2')
        self.assertContains(self.client.get(reverse('courses'), {'q': 'ABSENT'}), 'Bu filtr bo‘yicha kurs yo‘q')

    def test_unpublished_and_scheduled_content_stays_private(self):
        self.course.is_active = False; self.course.save()
        self.post.published_at = timezone.now() + datetime.timedelta(days=1); self.post.save()
        self.university.is_published = False; self.university.save()
        self.article.is_published = False; self.article.save()
        for name, args in [('course_detail', [self.course.pk]), ('blog:detail', [self.post.slug]), ('sit:university_detail', [self.university.slug]), ('sit:knowledge_detail', [self.article.slug])]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args), {'preview': '1'}).status_code, 404)
        self.client.force_login(self.staff)
        for name, args in [('blog:detail', [self.post.slug]), ('sit:university_detail', [self.university.slug]), ('sit:knowledge_detail', [self.article.slug])]:
            response = self.client.get(reverse(name, args=args), {'preview': '1'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'noindex, nofollow')
            self.assertIn('private', response['Cache-Control'])

    def test_safe_return_links_keep_filter_but_never_leave_family(self):
        base = reverse('sit:university_list')
        target = base + '?city=Istanbul&status=all&page=2'
        url = self.university.get_absolute_url()
        self.assertEqual(self.client.get(url, {'return_to': target}).context['public_back_url'], target)
        for value in ['https://evil.test/', '//evil.test/', '/blog/', '/\\evil.test/', base + '\n']:
            self.assertEqual(self.client.get(url, {'return_to': value}).context['public_back_url'], base)

    def test_real_sit_filter_program_and_source(self):
        response = self.client.get(reverse('sit:university_list'), {'city': 'Istanbul', 'language': 'tr', 'level': 'bachelor'})
        self.assertEqual(response.context['result_count'], 1)
        self.assertContains(response, 'return_to=')
        self.assertEqual(self.client.get(reverse('sit:university_list'), {'city': 'No city'}).context['result_count'], 0)
        response = self.client.get(self.university.get_absolute_url())
        self.assertContains(response, 'Dasturlash')
        self.assertContains(response, 'example.edu.tr')
        self.program.is_active = False; self.program.save()
        self.assertNotContains(self.client.get(self.university.get_absolute_url()), 'Dasturlash')

    def test_pricing_uses_purchase_catalog_and_exact_database_amount(self):
        Plan.objects.create(name='CLOSED PLAN', price=990000, is_available_for_purchase=False)
        response = self.client.get(reverse('subscriptions:pricing'))
        self.assertContains(response, '230000')
        self.assertContains(response, 'Ustoz yordami')
        self.assertNotContains(response, 'CLOSED PLAN')
        self.assertNotContains(response, 'Istalgan vaqtda bekor')

    def test_admin_brand_nav_and_legal_content_are_not_replaced_by_fixture(self):
        settings = SiteSettings.load(); settings.brand_name = 'Til markazi'; settings.save()
        LandingNavItem.objects.create(key='custom', label='Owner link', custom_url='/faq/', order=1)
        LandingNavItem.objects.create(key='custom', label='BAD LINK', custom_url='javascript:alert(1)', order=2)
        LegalPage.objects.create(page_type='terms', title='Owner shartlari', content='<p>Real matn</p><script>alert(1)</script>')
        response = self.client.get(reverse('terms_of_service'))
        for value in ['Til markazi', 'Owner link', 'Owner shartlari', 'Real matn']:
            self.assertContains(response, value)
        self.assertNotContains(response, 'BAD LINK')
        self.assertNotContains(response, '<script>alert(1)</script>')
        for value in ['javascript:alert(1)', 'data:text/html,abc', '//evil.test', '/\\evil.test', 'https:\n//evil.test']:
            self.assertEqual(public_url(value), '')

    def test_blog_search_tag_return_and_native_comments_reply_reactions(self):
        response = self.client.get(reverse('blog:list'), {'q': 'Haqiqiy', 'tag': self.tag.slug})
        self.assertContains(response, self.post.title)
        self.assertContains(response, 'return_to=')
        self.client.force_login(self.user)
        response = self.client.post(reverse('blog:comment_create', args=[self.post.slug]), {'content': '<script>not executable</script>'})
        comment = BlogComment.objects.get(user=self.user)
        self.assertEqual(response.url, self.post.get_absolute_url() + f'#comment-{comment.pk}')
        self.client.post(reverse('blog:comment_create', args=[self.post.slug]), {'content': 'Real reply', 'parent_id': comment.pk})
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, 'Real reply')
        self.assertContains(response, '&lt;script&gt;not executable&lt;/script&gt;')
        self.assertTrue(self.client.post(reverse('blog:comment_like', args=[comment.pk])).json()['liked'])
        self.assertFalse(self.client.post(reverse('blog:comment_like', args=[comment.pk])).json()['liked'])
        self.assertEqual(self.client.post(reverse('blog:clap', args=[self.post.slug])).json()['clap_count'], 1)

    def test_blog_csrf_and_closed_comment_controls(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        for name in ['blog:clap', 'blog:comment_create']:
            self.assertEqual(client.post(reverse(name, args=[self.post.slug]), {'content': 'No csrf'}).status_code, 403)
        self.post.allow_comments = False; self.post.save()
        self.client.force_login(self.user)
        response = self.client.get(self.post.get_absolute_url())
        self.assertNotContains(response, 'data-public-comment')
        self.client.post(reverse('blog:comment_create', args=[self.post.slug]), {'content': 'Closed'})
        self.assertFalse(BlogComment.objects.exists())

    def test_blog_only_root_comments_offer_reply_forms(self):
        root = BlogComment.objects.create(post=self.post, user=self.staff, content='Root comment')
        reply = BlogComment.objects.create(post=self.post, user=self.user, parent=root, content='Existing reply')
        self.client.force_login(self.user)
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, 'Existing reply')
        self.assertContains(response, 'Javob yozish', count=1)
        self.assertContains(response, f'name="parent_id" value="{root.pk}"')
        self.assertNotContains(response, f'name="parent_id" value="{reply.pk}"')
        self.assertContains(response, reverse('blog:comment_like', args=[reply.pk]))

    def test_empty_lists_keep_navigation_and_no_fake_data(self):
        Course.objects.all().delete(); BlogPost.objects.all().delete()
        University.objects.all().delete(); Plan.objects.all().delete()
        for name in ['courses', 'blog:list', 'sit:university_list', 'subscriptions:pricing']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Footer navigatsiyasi')
