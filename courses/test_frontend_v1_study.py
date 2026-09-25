"""I2a: actual scoped release/read/private file/completion, both renderers."""
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from core.flags import flag_by_slug, set_flag
from courses.models import Assignment, CohortLessonRelease, Course, Lesson, LessonProgress, Module, Quiz
from library import services
from library.models import LibraryResource
from library.test_resources import PDF_BYTES, pdf_upload
from users.models import Notification


class FrontendStudyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('study-teacher', 'study-teacher@example.test', is_staff=True)
        cls.student = User.objects.create_user('study-student', 'study-student@example.test')
        cls.other = User.objects.create_user('study-outsider', 'study-outsider@example.test', is_staff=True)
        cls.course = Course.objects.create(title='Real A1 course', instructor=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title='Real module', order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title='Real lesson', content='<p>Merhaba — real content.</p>', order=1)
        cls.second = Lesson.objects.create(module=cls.module, title='Second lesson', order=2)
        cls.cohort = Cohort.objects.create(course=cls.course, name='Morning group', start_date=timezone.localdate())
        cls.other_cohort = Cohort.objects.create(course=cls.course, name='Evening group', start_date=timezone.localdate())
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='active')

    def setUp(self):
        self.scratch = TemporaryDirectory(prefix='v1-study-test-')
        self.addCleanup(self.scratch.cleanup)
        settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.scratch.name, MEDIA_ROOT=self.scratch.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.release_url = reverse('teacher_release')
        self.lesson_url = reverse('lesson_detail', args=[self.course.pk, self.lesson.pk])

    def enable(self):
        for name in ('frontend_v1_lesson', 'frontend_v1_teacher'):
            set_flag(name, enabled=True, reason='I2 regression')

    def post_release(self, **extra):
        data = dict(cohort=self.cohort.pk, lesson=self.lesson.pk, action='release', confirm_scope='yes', confirm_impact='yes')
        data.update(extra)
        return self.client.post(self.release_url, data)

    def material(self):
        resource = LibraryResource(title='Real private material')
        services.apply_upload(resource, pdf_upload(), actor=self.teacher)
        resource.save()
        material, _ = services.attach_to_lesson(self.lesson, resource, actor=self.teacher)
        return material

    def test_flags_default_off_and_independent(self):
        for name in ('frontend_v1_teacher', 'frontend_v1_lesson'):
            self.assertFalse(flag_by_slug(name).default)
        self.client.force_login(self.teacher)
        self.assertTemplateUsed(self.client.get(reverse('teacher_dashboard')), 'teacher/dashboard.html')
        self.assertTemplateUsed(self.client.get(self.release_url), 'teacher/release.html')
        self.client.force_login(self.student)
        self.assertTemplateUsed(self.client.get(self.lesson_url), 'courses/lesson_detail.html')
        self.enable()
        self.assertTemplateUsed(self.client.get(self.lesson_url), 'frontend_v1/lesson.html')
        self.assertTemplateUsed(self.client.get(reverse('dashboard')), 'users/dashboard.html')

    def test_teacher_scoped_context_and_no_store(self):
        self.enable()
        self.client.force_login(self.teacher)
        for name in ('teacher_dashboard', 'teacher_release'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.cohort.name)
            self.assertContains(response, 'data-frontend="v1"')
            self.assertIn('no-store', response['Cache-Control'])
        self.client.force_login(self.other)
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertNotContains(response, self.cohort.name)
        self.assertContains(response, 'Faol guruh yo‘q')
        self.assertContains(self.client.get(self.release_url), 'Faol guruh yo‘q')

    def test_anonymous_and_learner_cannot_use_teacher_pages(self):
        self.enable()
        for name in ('teacher_dashboard', 'teacher_release'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.release_url).status_code, 302)
        self.assertEqual(self.post_release().status_code, 302)
        self.assertFalse(CohortLessonRelease.objects.exists())

    def test_forged_missing_and_ambiguous_targets_never_fall_back_even_off(self):
        self.client.force_login(self.teacher)
        for enabled in (False, True):
            set_flag('frontend_v1_teacher', enabled=enabled, reason='Target regression')
            for target in ('', 'junk', '999999', '²', '9' * 4400):
                self.assertIn(self.post_release(cohort=target).status_code, (400, 404))
                self.assertIn(self.client.get(self.release_url, {'cohort': target}).status_code, (400, 404))
            response = self.client.post(f'{self.release_url}?cohort={self.other_cohort.pk}', {
                'cohort': self.cohort.pk, 'lesson': self.lesson.pk, 'action': 'release',
            })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.client.post(self.release_url, {'lesson': self.lesson.pk, 'action': 'release'}).status_code, 400)
        self.assertFalse(CohortLessonRelease.objects.exists())
        self.assertFalse(SystemAuditEvent.objects.filter(action='lesson.release').exists())

    def test_foreign_or_inactive_cohort_is_rejected(self):
        self.enable()
        self.client.force_login(self.other)
        self.assertEqual(self.post_release().status_code, 404)
        self.client.force_login(self.teacher)
        Cohort.objects.filter(pk=self.cohort.pk).update(is_active=False)
        self.assertEqual(self.post_release().status_code, 404)
        self.assertFalse(CohortLessonRelease.objects.exists())

    def test_get_confirmation_does_not_write_and_shows_scope_and_impact(self):
        self.enable()
        self.client.force_login(self.teacher)
        response = self.client.get(self.release_url, {'cohort': self.cohort.pk, 'lesson': self.lesson.pk, 'action': 'release'})
        self.assertContains(response, 'data-release-form')
        self.assertContains(response, self.lesson.title)
        self.assertContains(response, 'name="confirm_impact"')
        self.assertFalse(CohortLessonRelease.objects.exists())

    def test_confirmation_and_length_errors_preserve_note_without_write(self):
        self.enable()
        self.client.force_login(self.teacher)
        for fields in ({'confirm_scope': ''}, {'confirm_impact': ''}, {'note': 'x' * 256}):
            note = fields.pop('note', 'My unsaved note <safe>')
            response = self.post_release(note=note, **fields)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.context['release_note'], note)
            self.assertFalse(CohortLessonRelease.objects.exists())

    def test_invalid_lesson_and_action_never_write(self):
        self.enable()
        self.client.force_login(self.teacher)
        for fields in ({'lesson': '999999'}, {'action': 'delete'}):
            self.post_release(**fields)
        self.assertFalse(CohortLessonRelease.objects.exists())

    def test_native_csrf_is_required(self):
        self.enable()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        payload = dict(cohort=self.cohort.pk, lesson=self.lesson.pk, action='release', confirm_scope='yes', confirm_impact='yes')
        self.assertEqual(client.post(self.release_url, payload).status_code, 403)
        response = client.get(self.release_url, {'cohort': self.cohort.pk, 'lesson': self.lesson.pk, 'action': 'release'})
        payload['csrfmiddlewaretoken'] = response.cookies['csrftoken'].value
        self.assertEqual(client.post(self.release_url, payload).status_code, 302)

    def test_open_duplicate_lock_drives_real_read_file_and_completion(self):
        material = self.material()
        file_url = reverse('library:material_file', args=[material.pk])
        self.enable()
        self.client.force_login(self.teacher)
        for _ in range(2):
            self.assertEqual(self.post_release(note='week one').status_code, 302)
        self.assertEqual(SystemAuditEvent.objects.filter(action='lesson.release').count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.assertContains(self.client.get(self.release_url, {'cohort': self.cohort.pk}), 'Izoh: week one')
        self.assertFalse(CohortLessonRelease.objects.filter(cohort=self.other_cohort).exists())
        self.client.force_login(self.student)
        self.assertTemplateUsed(self.client.get(self.lesson_url), 'frontend_v1/lesson.html')
        file_response = self.client.get(file_url)
        self.assertEqual(file_response.status_code, 200)
        # Consume via Django's test-client wrapper: direct close() emits
        # request_finished and closes PostgreSQL's TestCase transaction.
        self.assertEqual(b''.join(file_response.streaming_content), PDF_BYTES)
        self.assertTrue(file_response.closed)
        self.assertEqual(self.client.get(reverse('lesson_detail', args=[self.course.pk, self.second.pk])).status_code, 302)
        completion = reverse('lesson_completion', args=[self.course.pk, self.lesson.pk]) + f'?cohort={self.cohort.pk}'
        self.client.post(completion)
        self.assertTrue(LessonProgress.objects.get(enrollment=self.enrollment, lesson=self.lesson).is_completed)
        self.client.force_login(self.teacher)
        self.post_release(action='lock')
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.lesson_url).status_code, 302)
        self.assertEqual(self.client.get(file_url).status_code, 404)
        self.client.post(completion, {'action': 'clear'})
        self.assertTrue(LessonProgress.objects.get(enrollment=self.enrollment, lesson=self.lesson).is_completed)

    def test_content_materials_queries_progress_and_rollback(self):
        material = self.material()
        self.enable()
        self.client.force_login(self.student)
        response = self.client.get(self.lesson_url, {'cohort': self.cohort.pk, 'tab': 'text'})
        self.assertContains(response, 'Merhaba — real content.')
        self.assertContains(response, 'value="0" max="2"')
        self.assertContains(response, f'?cohort={self.cohort.pk}&amp;tab=materials')
        self.assertIn('no-store', response['Cache-Control'])
        response = self.client.get(self.lesson_url, {'tab': 'materials'})
        self.assertContains(response, reverse('library:material_file', args=[material.pk]))
        self.assertNotContains(response, material.resource.file.name)
        set_flag('frontend_v1_lesson', enabled=False, reason='Rollback regression')
        self.assertTemplateUsed(self.client.get(self.lesson_url), 'courses/lesson_detail.html')
        self.assertFalse(LessonProgress.objects.filter(is_completed=True).exists())

    def test_empty_content_invalid_tab_and_video(self):
        self.enable()
        self.client.force_login(self.student)
        empty_url = reverse('lesson_detail', args=[self.course.pk, self.second.pk])
        self.assertContains(self.client.get(empty_url), 'Dars mazmuni hali qo‘shilmagan')
        self.assertContains(self.client.get(self.lesson_url, {'tab': 'unknown'}), 'Merhaba — real content.')
        Lesson.objects.filter(pk=self.lesson.pk).update(video_url='https://www.youtube-nocookie.com/embed/example')
        self.assertContains(self.client.get(self.lesson_url), 'title="Real lesson — videodars"')

    def test_completion_keeps_current_tab_and_exact_cohort(self):
        self.enable()
        self.client.force_login(self.student)
        completion = reverse('lesson_completion', args=[self.course.pk, self.lesson.pk]) + f'?cohort={self.cohort.pk}'
        response = self.client.post(completion, {'tab': 'materials'})
        self.assertRedirects(response, self.lesson_url + f'?cohort={self.cohort.pk}&tab=materials', fetch_redirect_response=False)
        response = self.client.post(completion, {'tab': 'https://example.test/'})
        self.assertRedirects(response, self.lesson_url + f'?cohort={self.cohort.pk}', fetch_redirect_response=False)

    def assert_practice_legacy(self, tab):
        response = self.client.get(self.lesson_url, {'tab': tab})
        self.assertTemplateUsed(response, 'courses/lesson_detail.html')
        self.assertNotContains(response, 'data-frontend="v1"')
        self.assertEqual(response.context['default_study_tab'], tab)

    def test_assignment_keeps_whole_legacy_renderer(self):
        self.enable()
        self.client.force_login(self.student)
        Assignment.objects.create(lesson=self.lesson, title='Existing assignment')
        self.assert_practice_legacy('homework')

    def test_quiz_keeps_whole_legacy_renderer(self):
        self.enable()
        self.client.force_login(self.student)
        Quiz.objects.create(lesson=self.lesson, title='Existing quiz')
        self.assert_practice_legacy('quiz')

    def test_outsider_and_inactive_student_cannot_read(self):
        self.enable()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.lesson_url).status_code, 302)
        self.client.force_login(self.student)
        for status in ('pending', 'frozen', 'expired'):
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status)
            self.assertEqual(self.client.get(self.lesson_url).status_code, 302)
