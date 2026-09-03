"""Namuna kontent generatori (katalog/blog bo'shligi).

`seed_demo` QA skeletini beradi — `[demo]` belgisi bilan, ataylab sun'iy.
Bu generator esa platformani ko'rsatib bo'ladigan holatga keltiradi. Shuning
uchun eng muhim da'volar boshqacha:

* darslar **ochiq** bo'ladi (bitta release qatori qolganini yopib qo'yadi);
* maqolalar haqiqatan **nashr etilgan** bo'ladi (qoralama blogda ko'rinmaydi);
* narx qo'yilmaydi — bu owner qarori;
* tozalash faqat o'zi yaratganini oladi.
"""

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from blog.models import BlogPost, BlogTag
from cohorts.models import Cohort
from core.content_seed import (
    ARTICLES, COURSES, SampleContentError, seed_sample_content,
    wipe_sample_content,
)
from courses.models import (
    Assignment, CohortLessonRelease, Course, Lesson, Module, Quiz,
)

User = get_user_model()


def _make_owner():
    return User.objects.create_superuser(
        username="owner", email="owner@example.com", password="x"
    )


class SeedGuardTests(TestCase):
    @override_settings(IS_LOCAL=False)
    def test_seeding_is_refused_outside_local(self):
        """Namuna kurs haqiqiy katalogga tushsa, qaysi kurs rost ekani bilinmaydi."""
        with self.assertRaises(CommandError):
            call_command("seed_content")

    @override_settings(IS_LOCAL=False)
    def test_wiping_is_refused_outside_local_too(self):
        with self.assertRaises(CommandError):
            call_command("seed_content", "--wipe")

    def test_missing_superuser_gives_an_actionable_error(self):
        """Soxta muallif yaratilmaydi — o'rniga nima qilish kerakligi aytiladi."""
        with self.assertRaises(SampleContentError) as caught:
            seed_sample_content()

        self.assertIn("createsuperuser", str(caught.exception))


class SeedContentTests(TestCase):
    def setUp(self):
        self.owner = _make_owner()

    def test_the_seed_builds_both_courses_with_walkable_structure(self):
        seed_sample_content()

        self.assertEqual(Course.objects.count(), len(COURSES))
        for spec in COURSES:
            course = Course.objects.get(title=spec["title"])
            self.assertEqual(
                Module.objects.filter(course=course).count(), len(spec["modules"])
            )
            self.assertGreaterEqual(
                Lesson.objects.filter(module__course=course).count(), 5
            )
            self.assertTrue(
                Assignment.objects.filter(lesson__module__course=course).exists()
            )
            self.assertTrue(Quiz.objects.filter(lesson__module__course=course).exists())

    def test_lessons_carry_real_teaching_text(self):
        """Bir qatorlik dars na o'quvchiga foyda beradi, na layoutni sinaydi."""
        seed_sample_content()

        for lesson in Lesson.objects.all():
            self.assertGreater(len(lesson.content), 400, lesson.title)

    def test_no_release_rows_are_written_so_every_lesson_stays_open(self):
        """Eng oson o'tkazib yuboriladigan tuzoq.

        `courses/views.py` drip rejimini **birorta** release qatori borligiga
        qarab yoqadi. Ya'ni bitta qator yozilsa, qolgan darslar yopiladi va
        katalog to'la ko'rinsa ham hech narsa ochilmaydi.
        """
        seed_sample_content()

        self.assertFalse(CohortLessonRelease.objects.exists())

    def test_each_course_gets_one_checkout_default_cohort(self):
        seed_sample_content()

        for course in Course.objects.all():
            self.assertEqual(
                Cohort.objects.filter(course=course, is_checkout_default=True).count(), 1
            )

    def test_courses_use_a_gradient_cover_because_no_image_is_uploaded(self):
        """`cover_mode` defaulti `image` — rasmsiz kurs katalogda bo'sh chiqadi."""
        seed_sample_content()

        for course in Course.objects.all():
            self.assertEqual(course.cover_mode, "gradient")

    def test_cover_title_is_short_enough_to_read_at_card_size(self):
        """**Tuzatilgan da'vo.**

        Ilgari bu yerda "matn kartadan chiqib ketdi" deb yozilgandi. Keyin
        brauzerda o'lchanganda ma'lum bo'ldiki, chiqmagan: eng uzun satr
        `1049px` bo'lib `1200px` canvas ichida sig'adi. O'sha xulosa
        skrinshotning eskirgan kadriga asoslangan edi.

        Qisqa cover sarlavhasi baribir beriladi, lekin sababi boshqa:
        kartadagi cover taxminan `318x128` ga siqiladi va uch satrli uzun
        nom o'sha o'lchamda o'qilmaydi. Bu dizayn tanlovi, nuqson tuzatishi
        emas.
        """
        seed_sample_content()

        for course in Course.objects.all():
            self.assertLessEqual(len(course.cover_display_title), 20, course.title)
            self.assertNotEqual(course.cover_display_title, course.title)

    def test_price_is_left_at_the_model_default(self):
        """Qaysi kurs qancha turishi — owner qarori, agent uni to'ldirmaydi."""
        seed_sample_content()

        for course in Course.objects.all():
            self.assertEqual(course.price, 0)

    def test_articles_are_long_enough_to_read_as_articles(self):
        """Birinchi urinishda maqolalar 106-190 so'z chiqdi — bu maqola emas, qayd.

        O'quv vaqti ham 1 daqiqa bo'lib turardi, ya'ni blog kartochkasi
        \"o'qishga arzimaydi\" degan signal berardi.
        """
        seed_sample_content()

        for post in BlogPost.objects.all():
            self.assertGreaterEqual(len(post.plain_text.split()), 350, post.slug)
            self.assertGreaterEqual(post.reading_time_minutes, 2, post.slug)

    def test_articles_are_published_not_drafts(self):
        """Qoralama blogda ko'rinmaydi — ya'ni blog yana bo'sh bo'lardi."""
        seed_sample_content()

        self.assertEqual(BlogPost.objects.published().count(), len(ARTICLES))
        for post in BlogPost.objects.all():
            self.assertTrue(post.tags.exists(), post.slug)

    def test_running_twice_changes_nothing(self):
        seed_sample_content()
        counts = (
            Course.objects.count(),
            Lesson.objects.count(),
            Quiz.objects.count(),
            Cohort.objects.count(),
            BlogPost.objects.count(),
            BlogTag.objects.count(),
        )

        seed_sample_content()

        self.assertEqual(
            (
                Course.objects.count(),
                Lesson.objects.count(),
                Quiz.objects.count(),
                Cohort.objects.count(),
                BlogPost.objects.count(),
                BlogTag.objects.count(),
            ),
            counts,
        )


class WipeTests(TestCase):
    def setUp(self):
        self.owner = _make_owner()

    def test_wipe_removes_what_the_seed_created(self):
        seed_sample_content()

        wipe_sample_content()

        self.assertFalse(Course.objects.exists())
        self.assertFalse(Cohort.objects.exists())
        self.assertFalse(BlogPost.objects.exists())

    def test_a_real_record_with_the_same_title_is_not_adopted(self):
        """PR #53 Codex reviewining topilmasi.

        Sarlavha egalik dalili emas. Ilgari `get_or_create` shu nomli
        haqiqiy kursni "namuna" deb qabul qilardi va `--wipe` uni modul,
        dars va imtihoni bilan birga cascade'ga tushirardi.
        """
        clash = Course.objects.create(
            title=COURSES[0]["title"],
            description="Ownerning haqiqiy kursi",
            level="beginner",
        )
        module = Module.objects.create(course=clash, title="Ownerning moduli", order=1)

        with self.assertRaises(SampleContentError) as caught:
            seed_sample_content()

        self.assertIn("seeder yaratmagan", str(caught.exception))
        clash.refresh_from_db()
        self.assertEqual(clash.description, "Ownerning haqiqiy kursi")
        self.assertTrue(Module.objects.filter(pk=module.pk).exists())

    def test_wipe_never_touches_a_same_titled_record_it_did_not_create(self):
        """Rad etish ishlamay qolsa ham, tozalash uni o'chirmasligi kerak."""
        clash = Course.objects.create(
            title=COURSES[0]["title"], description="Ownerniki", level="beginner"
        )
        clash_post = BlogPost.objects.create(
            title="Ownerning maqolasi",
            slug=ARTICLES[0]["slug"],
            author=self.owner,
            body="<p>tegilmasin</p>",
            status=BlogPost.STATUS_PUBLISHED,
        )

        wipe_sample_content()

        self.assertTrue(Course.objects.filter(pk=clash.pk).exists())
        self.assertTrue(BlogPost.objects.filter(pk=clash_post.pk).exists())

    def test_wipe_leaves_real_data_alone(self):
        """Eng muhim da'vo: tozalash faqat o'zi yaratganini oladi."""
        real_course = Course.objects.create(
            title="Haqiqiy kurs", description="tegilmasin", level="beginner"
        )
        real_post = BlogPost.objects.create(
            title="Haqiqiy maqola",
            author=self.owner,
            body="<p>tegilmasin</p>",
            status=BlogPost.STATUS_PUBLISHED,
        )
        seed_sample_content()

        wipe_sample_content()

        self.assertTrue(Course.objects.filter(pk=real_course.pk).exists())
        self.assertTrue(BlogPost.objects.filter(pk=real_post.pk).exists())

    def test_wipe_keeps_a_tag_the_owner_still_uses(self):
        """Teg umumiy resurs: owner uni o'z maqolasiga ilgan bo'lishi mumkin."""
        seed_sample_content()
        owner_post = BlogPost.objects.create(
            title="Owner maqolasi",
            author=self.owner,
            body="<p>matn</p>",
            status=BlogPost.STATUS_PUBLISHED,
        )
        shared_tag = BlogTag.objects.get(name="Grammatika")
        owner_post.tags.add(shared_tag)

        wipe_sample_content()

        self.assertTrue(BlogTag.objects.filter(pk=shared_tag.pk).exists())
        self.assertFalse(BlogTag.objects.filter(name="Metodika").exists())
