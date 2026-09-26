"""Library port uses real writers on temporary files, never provider calls."""
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.flags import flag_by_slug, set_flag
from courses.models import Course, Lesson, Module
from . import frontend_v1 as v1, selectors, services
from .models import LessonMaterial, LibraryResource
from .test_resources import pdf_upload, PDF_BYTES


class LibraryV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('library-v1-teacher', 'teacher-library@example.test', is_staff=True)
        cls.other = User.objects.create_user('library-v1-other', 'other-library@example.test', is_staff=True)
        cls.student = User.objects.create_user('library-v1-student', 'student-library@example.test')
        cls.course = Course.objects.create(title='Own course', instructor=cls.teacher)
        cls.foreign = Course.objects.create(title='Other course', instructor=cls.other)
        cls.module = Module.objects.create(course=cls.course, title='Module', order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title='Own lesson', order=1)
        foreign_module = Module.objects.create(course=cls.foreign, title='Other module', order=1)
        cls.foreign_lesson = Lesson.objects.create(module=foreign_module, title='Other lesson', order=1)

    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='library-v1-test-')
        self.addCleanup(scratch.cleanup)
        override = override_settings(PRIVATE_MEDIA_ROOT=scratch.name, GEMINI_API_KEY='')
        override.enable()
        self.addCleanup(override.disable)
        set_flag('frontend_v1_library', enabled=True, reason='Isolated regression')
        self.client.force_login(self.teacher)
        self.resource = LibraryResource(title='Saved title', course=self.course)
        services.apply_upload(self.resource, pdf_upload(), actor=self.teacher)
        self.resource.save()

    def url(self, name, pk=None):
        return reverse('library_backoffice:' + name, args=[pk] if pk else [])

    def token(self, action='save', resource=True, lesson=None):
        if resource is True:
            self.resource.refresh_from_db()
            resource = self.resource
        return dict(frontend_v1_library='1', confirm_scope='yes',
                    library_revision=v1.revision(self.teacher, resource, action, lesson))

    def data(self, **extra):
        return dict(self.token(), title='Edited title', description='Real description',
                    resource_type='handout', language='tr', level='a1', topic='Speaking',
                    course=self.course.pk, tags_text='A1, speaking; a1', **extra)

    def test_all_four_routes_real_private_renderer_and_no_demo(self):
        routes = [('resources', None, 'list'), ('resource_create', None, 'form'),
                  ('resource_edit', self.resource.pk, 'form'), ('lesson_picker', self.lesson.pk, 'picker')]
        for name, pk, template in routes:
            with self.subTest(name=name):
                response = self.client.get(self.url(name, pk))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f'frontend_v1/library/{template}.html')
                self.assertIn('no-store', response['Cache-Control'])
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, '/static/js/app.js')

    def test_default_off_and_independent_rollback(self):
        self.assertFalse(flag_by_slug('frontend_v1_library').default)
        set_flag('frontend_v1_library', enabled=False, reason='Rollback')
        for name, pk, page in [('resources', None, 'list'), ('resource_create', None, 'form'),
                              ('resource_edit', self.resource.pk, 'form'), ('lesson_picker', self.lesson.pk, 'picker')]:
            self.assertTemplateUsed(self.client.get(self.url(name, pk)), f'backoffice/library_{page}.html')

    def test_all_ten_fields_and_dynamic_limit(self):
        response = self.client.get(self.url('resource_edit', self.resource.pk))
        for field in ('title', 'description', 'resource_type', 'language', 'level', 'topic', 'course', 'is_teacher_only', 'file', 'tags_text'):
            self.assertContains(response, f'name="{field}"')
        self.assertContains(response, 'multipart/form-data')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertNotContains(response, '.txt,text/plain')

    def test_create_uses_canonical_upload_tags_audit_and_prg(self):
        data = self.data(file=pdf_upload())
        data.update(self.token(resource=None))
        response = self.client.post(self.url('resource_create'), data)
        created = LibraryResource.objects.get(title='Edited title')
        self.assertRedirects(response, self.url('resource_edit', created.pk))
        self.assertEqual(created.version, 1)
        self.assertEqual(created.file_kind, 'pdf')
        self.assertEqual(created.created_by, self.teacher)
        self.assertEqual(set(created.tags.values_list('name', flat=True)), {'a1', 'speaking'})
        self.assertFalse(created.lesson_links.exists())
        self.assertContains(self.client.get(response.url), 'library.resource.create')

    def test_metadata_only_preserves_file_version_and_roundtrips(self):
        before = self.resource.file.name
        response = self.client.post(self.url('resource_edit', self.resource.pk), self.data(is_teacher_only='on'))
        self.assertEqual(response.status_code, 302)
        self.resource.refresh_from_db()
        self.assertEqual((self.resource.title, self.resource.description, self.resource.resource_type, self.resource.language,
                          self.resource.level, self.resource.topic, self.resource.course_id, self.resource.is_teacher_only),
                         ('Edited title', 'Real description', 'handout', 'tr', 'a1', 'Speaking', self.course.pk, True))
        self.assertEqual((self.resource.file.name, self.resource.version), (before, 1))

    def test_file_replacement_deletes_old_only_after_commit_and_keeps_links(self):
        link, _ = services.attach_to_lesson(self.lesson, self.resource, actor=self.teacher)
        old_name, storage = self.resource.file.name, self.resource.file.storage
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url('resource_edit', self.resource.pk), self.data(file=pdf_upload('replacement.pdf', PDF_BYTES + b'new')))
            self.assertTrue(storage.exists(old_name))
        self.assertEqual(response.status_code, 302)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.version, 2)
        self.assertEqual(self.resource.original_filename, 'replacement.pdf')
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(self.resource.file.name))
        self.assertEqual(LessonMaterial.objects.get(pk=link.pk).resource_id, self.resource.pk)

    def test_invalid_file_keeps_bound_text_and_saved_sidebar(self):
        bad = SimpleUploadedFile('bad.html', b'<html>not allowed</html>', content_type='text/html')
        response = self.client.post(self.url('resource_edit', self.resource.pk), self.data(file=bad))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Edited title', status_code=400)
        self.assertContains(response, 'deck.pdf', status_code=400)
        self.assertContains(response, 'data-library-unsaved', status_code=400)
        self.resource.refresh_from_db()
        self.assertEqual((self.resource.title, self.resource.version), ('Saved title', 1))

    def test_missing_confirmation_is_no_write(self):
        data = self.data()
        data.pop('confirm_scope')
        response = self.client.post(self.url('resource_edit', self.resource.pk), data)
        self.assertEqual(response.status_code, 400)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'Saved title')

    def test_stale_form_retains_draft_without_overwriting_newer_writer(self):
        data = self.data()
        self.resource.title = 'Newer writer'
        self.resource.save()
        response = self.client.post(self.url('resource_edit', self.resource.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'Edited title', status_code=409)
        self.assertContains(response, 'Newer writer', status_code=409)
        self.assertContains(response, 'disabled', status_code=409)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'Newer writer')

    def test_snapshot_changes_on_aba_tags_and_usage(self):
        original = self.token()['library_revision']
        self.resource.title = 'Temporary title'
        self.resource.save()
        self.resource.title = 'Saved title'
        self.resource.save()
        self.assertNotEqual(original, self.token()['library_revision'])
        current = self.token()['library_revision']
        services.sync_tags(self.resource, 'new-tag')
        self.assertNotEqual(current, self.token()['library_revision'])
        current = self.token()['library_revision']
        services.attach_to_lesson(self.lesson, self.resource)
        self.assertNotEqual(current, self.token()['library_revision'])

    def test_tampered_wrong_action_or_user_token_rejected(self):
        tokens = ['forged', v1.revision(self.other, self.resource, 'save'), v1.revision(self.teacher, self.resource, 'delete')]
        for token in tokens:
            data = self.data()
            data['library_revision'] = token
            self.assertEqual(self.client.post(self.url('resource_edit', self.resource.pk), data).status_code, 409)

    def test_late_v1_post_remains_guarded_after_flag_off(self):
        data = self.data()
        set_flag('frontend_v1_library', enabled=False, reason='In-flight rollback')
        self.resource.title = 'Saved elsewhere'
        self.resource.save()
        response = self.client.post(self.url('resource_edit', self.resource.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertTemplateUsed(response, 'frontend_v1/library/form.html')

    def test_archive_replay_does_not_restore_and_fresh_restore_works(self):
        data = self.token('archive')
        url = self.url('resource_archive', self.resource.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.is_archived)
        self.assertEqual(self.client.post(url, self.token('archive')).status_code, 302)
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.is_archived)

    def test_used_delete_protected_and_unused_delete_cleans_file(self):
        link, _ = services.attach_to_lesson(self.lesson, self.resource)
        url = self.url('resource_delete', self.resource.pk)
        self.assertEqual(self.client.post(url, self.token('delete')).status_code, 302)
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        link.delete()
        name, storage = self.resource.file.name, self.resource.file.storage
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, self.token('delete'))
        self.assertRedirects(response, self.url('resources'))
        self.assertFalse(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        self.assertFalse(storage.exists(name))

    def test_attach_is_scoped_preserves_query_and_replay_has_no_duplicate(self):
        data = dict(self.token('attach', lesson=self.lesson.pk), resource=self.resource.pk,
                    next='picker', querystring='q=Saved&page=2')
        url = self.url('material_attach', self.lesson.pk)
        response = self.client.post(url, data)
        self.assertEqual(response.url, self.url('lesson_picker', self.lesson.pk) + '?q=Saved&page=2')
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(LessonMaterial.objects.filter(lesson=self.lesson).count(), 1)
        self.assertContains(self.client.get(self.url('lesson_picker', self.lesson.pk)), 'Shu darsga biriktirilgan')

    def test_attach_other_lesson_token_archived_or_bad_id_no_write(self):
        data = dict(self.token('attach', lesson=self.foreign_lesson.pk), resource=self.resource.pk)
        url = self.url('material_attach', self.lesson.pk)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        for value in ('oops', '²', '9' * 100, ''):
            self.assertEqual(self.client.post(url, {'resource': value}).status_code, 404)
        self.resource.archive(actor=self.teacher)
        data = dict(self.token('attach', lesson=self.lesson.pk), resource=self.resource.pk)
        self.assertEqual(self.client.post(url, data).status_code, 404)
        self.assertFalse(LessonMaterial.objects.exists())

    def test_teacher_only_attach_uses_canonical_audience(self):
        self.resource.is_teacher_only = True
        self.resource.save()
        data = dict(self.token('attach', lesson=self.lesson.pk), resource=self.resource.pk)
        self.assertEqual(self.client.post(self.url('material_attach', self.lesson.pk), data).status_code, 302)
        self.assertEqual(LessonMaterial.objects.get(resource=self.resource).audience, 'teacher')

    def test_common_library_keeps_foreign_current_course_without_expanding_attach_scope(self):
        self.resource.course = self.foreign
        self.resource.save()
        data = self.data()
        data['course'] = self.foreign.pk
        self.assertEqual(self.client.post(self.url('resource_edit', self.resource.pk), data).status_code, 302)
        for route in ('lesson_picker', 'material_attach'):
            response = self.client.get(self.url(route, self.foreign_lesson.pk)) if route == 'lesson_picker' else self.client.post(self.url(route, self.foreign_lesson.pk), data)
            self.assertEqual(response.status_code, 404)

    def test_anonymous_student_and_csrf_cannot_write_or_read_files(self):
        for user in (None, self.student):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for name, pk in [('resources', None), ('resource_create', None), ('resource_edit', self.resource.pk), ('resource_file', self.resource.pk), ('lesson_picker', self.lesson.pk)]:
                self.assertEqual(self.client.get(self.url(name, pk)).status_code, 302)
            self.assertEqual(self.client.post(self.url('resource_archive', self.resource.pk), self.token('archive')).status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post(self.url('resource_archive', self.resource.pk), self.token('archive')).status_code, 403)

    def test_lifecycle_and_attach_are_post_only(self):
        for route, pk in [('resource_archive', self.resource.pk), ('resource_delete', self.resource.pk), ('material_attach', self.lesson.pk)]:
            self.assertEqual(self.client.get(self.url(route, pk)).status_code, 405)

    def test_filters_do_not_silently_fallback(self):
        for query in ('course=²', 'course=' + '9'*100, 'course=0', 'type=unknown', 'q=a&q=b', 'alien=1', 'page=-1'):
            response = self.client.get(self.url('resources') + '?' + query)
            self.assertContains(response, 'Filtr tanilmadi')
            self.assertNotContains(response, 'data-library-resource=')
        self.assertContains(self.client.get(self.url('resources'), {'q': 'Saved'}), 'Saved title')
        self.assertNotContains(self.client.get(self.url('resources'), {'q': 'not-matching'}), 'Saved title')

    def test_pagination_picker_return_includes_current_page(self):
        for i in range(25):
            LibraryResource.objects.create(title=f'Extra {i}', file=self.resource.file.name)
        response = self.client.get(self.url('lesson_picker', self.lesson.pk), {'page': 2, 'q': 'Extra'})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertIn('page=2', response.context['picker_return_query'])
        self.assertContains(response, 'value="page=2&amp;q=Extra"')

    def test_private_file_and_duplicate_warning_are_real(self):
        duplicate = LibraryResource(title='Duplicate bytes')
        services.apply_upload(duplicate, pdf_upload(), actor=self.teacher)
        duplicate.save()
        self.assertEqual(selectors.used_file_kinds(), ['pdf'])
        self.assertContains(self.client.get(self.url('resource_edit', self.resource.pk)), 'Duplicate bytes')
        response = self.client.get(self.url('resource_file', self.resource.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(b''.join(response.streaming_content), PDF_BYTES)
        # Client's closing_iterator_wrapper already closes safely after consume.
        # Closing twice fires request_finished outside its test-safe wrapper and
        # closes PostgreSQL's class-level TestCase transaction.
        self.assertTrue(response.closed)
        self.assertFalse(connection.closed_in_transaction)
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())
