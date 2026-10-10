"""Course workspace HTTP contracts with real authoring and private upload services."""

import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cohorts.models import Cohort
from core.backoffice_forms import CourseBackofficeForm
from core.flags import flag_by_slug, set_flag
from courses import authoring_service
from courses.models import Assignment, CohortLessonRelease, Course, Lesson, LessonProgress, Module
from library import services as library_services
from library.models import LessonMaterial, LibraryResource, MaterialAudience


class CourseWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user(
            'workspace-teacher', 'workspace-teacher@example.test', is_staff=True,
        )
        cls.other = User.objects.create_user(
            'workspace-other', 'workspace-other@example.test', is_staff=True,
        )
        cls.student = User.objects.create_user('workspace-student', 'workspace-student@example.test')
        cls.course = Course.objects.create(
            title='Turk tili A1', description='Saved course description', instructor=cls.teacher,
        )
        cls.module = Module.objects.create(course=cls.course, title='Tanishuv', order=1)
        cls.lesson = Lesson.objects.create(
            module=cls.module, title='Saved lesson', content='Saved lesson text', order=1,
        )
        cls.foreign_course = Course.objects.create(title='Private other course', instructor=cls.other)
        cls.foreign_module = Module.objects.create(course=cls.foreign_course, title='Private other module')
        cls.foreign_lesson = Lesson.objects.create(module=cls.foreign_module, title='Private other lesson')
        # A second course owned by the same teacher must also be excluded from
        # the selected course's lesson and module operations.
        cls.second_course = Course.objects.create(title='Own second course', instructor=cls.teacher)
        cls.second_module = Module.objects.create(course=cls.second_course, title='Own second module')
        cls.second_lesson = Lesson.objects.create(module=cls.second_module, title='Own second lesson')
        cls.resource = LibraryResource.objects.create(
            title='Shared synthetic PDF', file='library/synthetic.pdf', file_kind='pdf',
        )

    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='course-workspace-tests-')
        self.addCleanup(scratch.cleanup)
        settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=scratch.name, MEDIA_ROOT=scratch.name,
            GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='',
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.private_root = Path(scratch.name)
        set_flag('backoffice_course_workspace', enabled=True, reason='Isolated workspace regression')
        self.client.force_login(self.teacher)

    def url(self, name='course', obj=None):
        if name in ('course', 'course_edit'):
            obj = obj or self.course
        return reverse('backoffice_workspace_' + name, args=[obj.pk] if obj else [])

    def page(self, *, lesson=None, module=None, new=False):
        query = {}
        if lesson is not None:
            query['lesson'] = lesson.pk
        if module is not None:
            query['module'] = module.pk
        if new:
            query['new'] = '1'
        response = self.client.get(self.url(), query)
        self.assertEqual(response.status_code, 200)
        return response

    def lesson_data(self, *, lesson=True, **extra):
        lesson = self.lesson if lesson is True else lesson
        page = self.page(lesson=lesson) if lesson else self.page(module=self.module, new=True)
        data = {
            'action': 'lesson_save', 'lesson_id': lesson.pk if lesson else '',
            'lesson_revision': page.context['lesson_revision'], 'title': 'Edited lesson',
            'module': self.module.pk, 'video_url': '', 'content': 'Edited lesson text',
            'order': 2, 'xp_reward': 20,
        }
        data.update(extra)
        return data

    def course_data(self, *, course=True, **extra):
        course = self.course if course is True else course
        page = self.client.get(self.url('course_edit', course) if course else self.url('course_create'))
        self.assertEqual(page.status_code, 200)
        data = {name: getattr(self.course, name) for name in CourseBackofficeForm.Meta.fields}
        data.update(instructor=self.teacher.pk, course_revision=page.context['course_revision'])
        data.update(extra)
        return data

    def outline_data(self, action, **extra):
        data = {'action': action, 'outline_revision': self.page().context['outline_revision']}
        data.update(extra)
        return data

    def material_data(self, action='material_attach', **extra):
        data = {
            'action': action, 'lesson_id': self.lesson.pk,
            'material_revision': self.page(lesson=self.lesson).context['material_revision'],
        }
        data.update(extra)
        return data

    def test_private_real_routes_scope_and_no_cache(self):
        for name in ('home', 'courses', 'course_create', 'course_edit', 'course'):
            with self.subTest(route=name):
                response = self.client.get(self.url(name))
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response['Cache-Control'])
                self.assertNotContains(response, 'Private other course')
                self.assertNotContains(response, 'Private other lesson')
                self.assertNotContains(response, '/_preview/')
        response = self.page()
        self.assertIsNone(response.context.get('lesson'))
        self.assertNotContains(response, 'name="lesson_revision"')

    def test_course_create_then_module_and_lesson_end_to_end(self):
        data = self.course_data(course=None, title='Created course', is_active='')
        response = self.client.post(self.url('course_create'), data)
        course = Course.objects.get(title='Created course')
        self.assertRedirects(response, self.url('course', course))
        self.assertFalse(course.is_active)
        self.assertEqual(course.modules.count(), 1)
        self.assertFalse(Lesson.objects.filter(module__course=course).exists())
        page = self.client.get(self.url('course', course))
        response = self.client.post(self.url('course', course), {
            'action': 'module_create', 'title': 'Yangi modul',
            'outline_revision': page.context['outline_revision'],
        })
        self.assertEqual(response.status_code, 302)
        module = course.modules.get(title='Yangi modul')
        page = self.client.get(self.url('course', course), {'module': module.pk, 'new': '1'})
        response = self.client.post(self.url('course', course), {
            'action': 'lesson_save', 'lesson_id': '', 'title': 'Yangi dars',
            'module': module.pk, 'content': 'Merhaba!', 'video_url': '',
            'order': 1, 'xp_reward': 10, 'lesson_revision': page.context['lesson_revision'],
        })
        lesson = Lesson.objects.get(module=module, title='Yangi dars')
        self.assertRedirects(response, self.url('course', course) + f'?lesson={lesson.pk}')
        self.assertEqual(lesson.content, 'Merhaba!')
        self.assertFalse(CohortLessonRelease.objects.exists())
        self.assertFalse(LessonProgress.objects.exists())

    def test_course_creation_replay_does_not_duplicate(self):
        data = self.course_data(course=None, title='Create once')
        self.assertEqual(self.client.post(self.url('course_create'), data).status_code, 302)
        self.assertEqual(self.client.post(self.url('course_create'), data).status_code, 409)
        self.assertEqual(Course.objects.filter(title='Create once').count(), 1)

    def test_course_edit_preserves_all_fields_and_rejects_stale_write(self):
        data = self.course_data(
            title='Changed course', price='250000.00', gradient_cover_title='Cover title',
            certificate_min_attendance_percent=70, certificate_min_lesson_completion_percent=80,
        )
        self.assertEqual(self.client.post(self.url('course_edit'), data).status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Changed course')
        self.assertEqual(self.course.gradient_cover_title, 'Cover title')
        self.assertEqual(self.course.certificate_min_attendance_percent, 70)
        self.assertEqual(self.course.certificate_min_lesson_completion_percent, 80)
        data['title'] = 'Stale course draft'
        response = self.client.post(self.url('course_edit'), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['form']['title'].value(), 'Stale course draft')
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Changed course')

    def test_cannot_assign_own_course_to_another_instructor(self):
        data = self.course_data(instructor=self.other.pk)
        response = self.client.post(self.url('course_edit'), data)
        self.assertEqual(response.status_code, 400)
        self.course.refresh_from_db()
        self.assertEqual(self.course.instructor_id, self.teacher.pk)

    def test_module_create_rename_move_and_stale_replay(self):
        data = self.outline_data('module_create', title='Ikkinchi modul')
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        module = self.course.modules.get(title='Ikkinchi modul')
        self.assertEqual(self.client.post(self.url(), data).status_code, 409)
        self.assertEqual(self.course.modules.count(), 2)
        data = self.outline_data('module_update', module_id=module.pk, title='Renamed module')
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        module.refresh_from_db()
        self.assertEqual(module.title, 'Renamed module')
        data = self.outline_data('module_move', module_id=module.pk, direction='up')
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        self.assertEqual(list(self.course.modules.order_by('order', 'pk').values_list('pk', flat=True)),
                         [module.pk, self.module.pk])
        self.assertEqual(self.client.post(self.url(), data).status_code, 409)

    def test_new_lesson_never_overwrites_first_lesson_and_replay_is_rejected(self):
        data = self.lesson_data(lesson=None, title='A second lesson')
        response = self.client.post(self.url(), data)
        created = Lesson.objects.get(module=self.module, title='A second lesson')
        self.assertRedirects(response, self.url() + f'?lesson={created.pk}')
        self.assertEqual(self.client.post(self.url(), data).status_code, 409)
        self.assertEqual(self.module.lessons.count(), 2)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_new_lesson_changed_module_preserves_original_draft_scope_until_save(self):
        destination = Module.objects.create(course=self.course, title='Destination module', order=2)
        source_url = self.url() + f'?module={self.module.pk}&new=1'
        initial_page = self.client.get(source_url)
        self.assertEqual(initial_page.status_code, 200)
        source_scope = initial_page.context['draft_scope']
        nonce = 'lesson-moved-before-first-save'
        data = {
            'action': 'lesson_save', 'lesson_id': '', 'title': 'New lesson moved before save',
            'module': destination.pk, 'content': 'Text started in the first module',
            'video_url': '', 'order': 1, 'xp_reward': 10,
            'lesson_revision': initial_page.context['lesson_revision'], 'draft_submission_id': nonce,
        }
        for changes, expected_status in (
            ({'action': 'lesson_preview'}, 200),
            ({'order': 'invalid'}, 400),
            ({'lesson_revision': 'stale'}, 409),
        ):
            with self.subTest(changes=changes):
                response = self.client.post(source_url, {**data, **changes})
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.context['draft_scope'], source_scope)
                self.assertEqual(str(response.context['lesson_form']['module'].value()), str(destination.pk))
                self.assertEqual(response.context['saved_scope'], '')
                self.assertFalse(Lesson.objects.filter(title=data['title']).exists())
        response = self.client.post(source_url, data)
        self.assertEqual(response.status_code, 302)
        created = Lesson.objects.get(title=data['title'])
        self.assertEqual(created.module_id, destination.pk)
        self.assertEqual(self.module.lessons.count(), 1)
        self.assertEqual(destination.lessons.count(), 1)
        self.assertEqual(self.client.session['workspace_saved'], {
            'scope': source_scope, 'submission_id': nonce,
        })
        saved_page = self.client.get(response['Location'])
        self.assertEqual(saved_page.status_code, 200)
        self.assertEqual(saved_page.context['lesson'].pk, created.pk)
        self.assertEqual(saved_page.context['saved_scope'], source_scope)
        self.assertEqual(saved_page.context['saved_submission_id'], nonce)

    def test_lesson_edit_keeps_assignments_materials_and_no_release_or_progress(self):
        assignment = Assignment.objects.create(lesson=self.lesson, title='Existing assignment')
        material, _ = library_services.attach_to_lesson(self.lesson, self.resource)
        response = self.client.post(self.url(), self.lesson_data())
        self.assertRedirects(response, self.url() + f'?lesson={self.lesson.pk}')
        self.lesson.refresh_from_db()
        self.assertEqual((self.lesson.title, self.lesson.content, self.lesson.xp_reward),
                         ('Edited lesson', 'Edited lesson text', 20))
        self.assertTrue(self.lesson.assignments.filter(pk=assignment.pk).exists())
        self.assertTrue(self.lesson.materials.filter(pk=material.pk).exists())
        self.assertFalse(CohortLessonRelease.objects.exists())
        self.assertFalse(LessonProgress.objects.exists())

    def test_stale_lesson_preserves_submitted_draft_without_overwriting(self):
        data = self.lesson_data(title='Unsaved draft', content='My unsaved content')
        Lesson.objects.filter(pk=self.lesson.pk).update(content='Saved from another window')
        response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['lesson_form']['title'].value(), 'Unsaved draft')
        self.assertEqual(response.context['lesson_form']['content'].value(), 'My unsaved content')
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.content, 'Saved from another window')

    def test_preview_escapes_untrusted_markup_and_does_not_save(self):
        attack = '<script id="workspace-xss">alert(1)</script><img src=x onerror="alert(2)">'
        data = self.lesson_data(action='lesson_preview', title='Only a preview', content=attack)
        before = (Lesson.objects.count(), Module.objects.count())
        response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only a preview')
        self.assertNotContains(response, '<script id="workspace-xss">')
        self.assertNotContains(response, '<img src=x onerror=')
        self.lesson.refresh_from_db()
        self.assertEqual((self.lesson.title, self.lesson.content), ('Saved lesson', 'Saved lesson text'))
        self.assertEqual(before, (Lesson.objects.count(), Module.objects.count()))
        self.assertFalse(CohortLessonRelease.objects.exists())
        self.assertFalse(LessonProgress.objects.exists())

    def test_invalid_lesson_preserves_form_and_never_changes_saved_row(self):
        data = self.lesson_data(order='wrong', title='Keep this draft')
        response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['lesson_form']['title'].value(), 'Keep this draft')
        self.assertIn('order', response.context['lesson_form'].errors)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_foreign_course_and_cross_course_selection_are_not_found(self):
        for method in (self.client.get, self.client.post):
            for name in ('course', 'course_edit'):
                with self.subTest(method=method.__name__, route=name):
                    self.assertEqual(method(self.url(name, self.foreign_course)).status_code, 404)
        for obj in (self.foreign_lesson, self.second_lesson):
            self.assertEqual(self.client.get(self.url(), {'lesson': obj.pk}).status_code, 404)
        for obj in (self.foreign_module, self.second_module):
            self.assertEqual(self.client.get(self.url(), {'module': obj.pk, 'new': '1'}).status_code, 404)

    def test_cross_course_module_cannot_receive_an_existing_lesson(self):
        for module in (self.foreign_module, self.second_module):
            with self.subTest(module=module.pk):
                response = self.client.post(self.url(), self.lesson_data(module=module.pk))
                self.assertEqual(response.status_code, 400)
                self.assertIn('module', response.context['lesson_form'].errors)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.module_id, self.module.pk)

    def test_foreign_lesson_and_module_post_are_not_found(self):
        for lesson in (self.foreign_lesson, self.second_lesson):
            data = self.lesson_data(lesson_id=lesson.pk)
            self.assertEqual(self.client.post(self.url(), data).status_code, 404)
        for module in (self.foreign_module, self.second_module):
            data = self.outline_data('module_update', module_id=module.pk, title='Forged title')
            self.assertEqual(self.client.post(self.url(), data).status_code, 404)
        self.foreign_lesson.refresh_from_db()
        self.second_lesson.refresh_from_db()
        self.assertEqual(self.foreign_lesson.title, 'Private other lesson')
        self.assertEqual(self.second_lesson.title, 'Own second lesson')

    def test_signed_revisions_bind_actor_action_and_object(self):
        data = self.lesson_data()
        for revision in (
            '', 'tampered', authoring_service.lesson_revision(self.other, self.lesson),
            authoring_service.lesson_revision(self.teacher, self.second_lesson),
            authoring_service.outline_revision(self.teacher, self.course),
        ):
            with self.subTest(revision=revision):
                data['lesson_revision'] = revision
                self.assertEqual(self.client.post(self.url(), data).status_code, 409)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_upload_uses_library_services_and_private_file_access(self):
        payload = b'%PDF-1.4\n' + b'test-only-content ' * 30
        data = self.material_data(
            'material_upload', title='Teacher preparation', is_teacher_only='on',
            file=SimpleUploadedFile('preparation.pdf', payload, content_type='application/pdf'),
        )
        with (
            patch.object(library_services, 'apply_upload', wraps=library_services.apply_upload) as upload,
            patch.object(library_services, 'attach_to_lesson', wraps=library_services.attach_to_lesson) as attach,
        ):
            response = self.client.post(self.url(), data)
        self.assertRedirects(response, self.url() + f'?lesson={self.lesson.pk}#materials')
        upload.assert_called_once()
        attach.assert_called_once()
        resource = LibraryResource.objects.get(title='Teacher preparation')
        material = LessonMaterial.objects.get(lesson=self.lesson, resource=resource)
        self.assertEqual(resource.file_kind, 'pdf')
        self.assertEqual(resource.file_size, len(payload))
        self.assertEqual(resource.created_by_id, self.teacher.pk)
        self.assertTrue(resource.is_teacher_only)
        self.assertEqual(material.audience, MaterialAudience.TEACHER)
        self.assertTrue(Path(resource.file.path).is_relative_to(self.private_root))
        self.assertEqual(Path(resource.file.path).read_bytes(), payload)
        with self.assertRaises(ValueError):
            _ = resource.file.url
        file_url = reverse('library:material_file', args=[material.pk])
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), payload)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(file_url).status_code, 404)

    def test_attach_reuses_file_and_rejects_stale_material_form(self):
        data = self.material_data(resource_id=self.resource.pk)
        before_resources = LibraryResource.objects.count()
        with patch.object(library_services, 'attach_to_lesson', wraps=library_services.attach_to_lesson) as attach:
            response = self.client.post(self.url(), data)
        self.assertRedirects(response, self.url() + f'?lesson={self.lesson.pk}#materials')
        attach.assert_called_once()
        self.assertEqual(self.client.post(self.url(), data).status_code, 409)
        self.assertEqual(LibraryResource.objects.count(), before_resources)
        self.assertEqual(LessonMaterial.objects.filter(lesson=self.lesson, resource=self.resource).count(), 1)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.file.name, 'library/synthetic.pdf')

    def test_invalid_upload_and_archived_resource_do_not_create_material(self):
        data = self.material_data(
            'material_upload', title='Rejected file',
            file=SimpleUploadedFile('bad.html', b'<script>bad</script>', content_type='text/html'),
        )
        response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LibraryResource.objects.filter(title='Rejected file').exists())
        self.assertFalse(LessonMaterial.objects.exists())
        self.assertFalse(any(path.is_file() for path in self.private_root.rglob('*')))
        self.resource.is_archived = True
        self.resource.save()
        response = self.client.post(self.url(), self.material_data(resource_id=self.resource.pk))
        self.assertIn(response.status_code, (400, 404))
        self.assertFalse(LessonMaterial.objects.exists())

    def test_failed_attachment_rolls_back_uploaded_resource_and_private_file(self):
        data = self.material_data(
            'material_upload', title='Rolled back upload',
            file=SimpleUploadedFile('rollback.pdf', b'%PDF-1.4\n' + b'x' * 400,
                                    content_type='application/pdf'),
        )
        with patch.object(library_services, 'attach_to_lesson', side_effect=ValidationError('Attachment rejected')):
            response = self.client.post(self.url(), data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LibraryResource.objects.filter(title='Rolled back upload').exists())
        self.assertFalse(LessonMaterial.objects.exists())
        self.assertFalse(any(path.is_file() for path in self.private_root.rglob('*')))

    def test_resource_insert_failure_cleans_file_written_before_insert(self):
        payload = b'%PDF-1.4\n' + b'insert-failure-only ' * 30
        data = self.material_data(
            'material_upload', title='Failed database insert',
            file=SimpleUploadedFile('insert-failure.pdf', payload, content_type='application/pdf'),
        )
        inserted_files = []
        insert_prefix = 'INSERT INTO ' + connection.ops.quote_name(LibraryResource._meta.db_table)

        def reject_resource_insert(execute, sql, params, many, context):
            if sql.lstrip().startswith(insert_prefix):
                # The actual FileField pre_save has already committed its
                # bytes by the time Django sends the INSERT to the database.
                inserted_files.extend(path for path in self.private_root.rglob('*') if path.is_file())
                self.assertEqual(len(inserted_files), 1)
                self.assertEqual(inserted_files[0].read_bytes(), payload)
                raise DatabaseError('Synthetic resource INSERT failure')
            return execute(sql, params, many, context)

        with connection.execute_wrapper(reject_resource_insert):
            with self.assertRaisesMessage(DatabaseError, 'Synthetic resource INSERT failure'):
                self.client.post(self.url(), data)
        self.assertEqual(len(inserted_files), 1)
        self.assertFalse(inserted_files[0].exists())
        self.assertFalse(LibraryResource.objects.filter(title='Failed database insert').exists())
        self.assertFalse(LessonMaterial.objects.exists())
        self.assertFalse(any(path.is_file() for path in self.private_root.rglob('*')))

    def test_resource_search_keeps_selected_lesson_and_filters_library(self):
        LibraryResource.objects.create(title='Workbook to exclude', file='library/other.pdf')
        response = self.client.get(self.url(), {'lesson': self.lesson.pk, 'resource_q': 'Shared synthetic'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['lesson'].pk, self.lesson.pk)
        self.assertContains(response, 'name="resource_q"')
        self.assertContains(response, 'Shared synthetic PDF')
        self.assertNotContains(response, 'Workbook to exclude')
        self.assertContains(response, 'id="materials"')

    def test_material_post_cannot_target_lesson_in_another_course(self):
        for lesson in (self.foreign_lesson, self.second_lesson):
            data = self.material_data(lesson_id=lesson.pk, resource_id=self.resource.pk)
            self.assertEqual(self.client.post(self.url(), data).status_code, 404)
        self.assertFalse(LessonMaterial.objects.exists())

    def test_csrf_and_nonstaff_requests_are_denied(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post(self.url(), self.lesson_data()).status_code, 403)
        self.client.force_login(self.student)
        for name in ('home', 'courses', 'course_create', 'course_edit', 'course'):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(self.url(name)).status_code, 403)
                self.assertEqual(self.client.post(self.url(name), {}).status_code, 403)
        self.assertFalse(Lesson.objects.filter(title='Edited lesson').exists())

    def test_flag_off_hides_new_routes_and_blocks_inflight_writes(self):
        self.assertFalse(flag_by_slug('backoffice_course_workspace').default)
        lesson_data = self.lesson_data()
        course_data = self.course_data()
        set_flag('backoffice_course_workspace', enabled=False, reason='Workspace rollback')
        for name in ('home', 'courses', 'course_create', 'course_edit', 'course'):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(self.url(name)).status_code, 404)
        self.assertEqual(self.client.post(self.url(), lesson_data).status_code, 409)
        self.assertEqual(self.client.post(self.url('course_edit'), course_data).status_code, 409)
        self.lesson.refresh_from_db()
        self.course.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')
        self.assertEqual(self.course.title, 'Turk tili A1')

    def test_unreadable_flag_fails_closed(self):
        from aicontrol.models import FeatureFlag

        with patch.object(FeatureFlag.objects, 'filter', side_effect=DatabaseError('flag unavailable')):
            self.assertEqual(self.client.get(self.url()).status_code, 404)
            self.assertEqual(self.client.post(self.url(), {'action': 'module_create', 'title': 'Forbidden'}).status_code, 409)
        self.assertFalse(Module.objects.filter(title='Forbidden').exists())

    def test_legacy_entry_gets_route_to_workspace_and_rollback_keeps_old_renderers(self):
        self.assertRedirects(self.client.get(reverse('backoffice_dashboard')), self.url('home'))
        self.assertRedirects(self.client.get(reverse('backoffice_courses'), {'q': 'Turk'}),
                             self.url('courses') + '?q=Turk')
        set_flag('backoffice_course_workspace', enabled=False, reason='Entry rollback')
        set_flag('frontend_v1_editors', enabled=False, reason='Legacy renderer regression')
        response = self.client.get(reverse('backoffice_courses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'backoffice/courses.html')
        set_flag('frontend_v1_editors', enabled=True, reason='Existing V1 renderer regression')
        response = self.client.get(reverse('backoffice_courses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'frontend_v1/editors/list.html')

    def test_duplicate_selection_and_unknown_actions_never_mutate(self):
        response = self.client.get(self.url() + f'?lesson={self.lesson.pk}&lesson={self.second_lesson.pk}')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(self.url(), {'action': ['lesson_save', 'lesson_preview'], 'title': 'Ambiguous'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(self.url(), {'action': 'delete_everything'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.module.lessons.count(), 1)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_post_lesson_cannot_disagree_with_selected_url(self):
        data = self.lesson_data()
        response = self.client.post(self.url() + f'?lesson={self.second_lesson.pk}', data)
        self.assertEqual(response.status_code, 400)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_course_status_filter_combines_search_scope_and_pagination(self):
        draft = Course.objects.create(title='Turk tili draft', instructor=self.teacher, is_active=False)
        Course.objects.create(title='Unrelated draft', instructor=self.teacher, is_active=False)
        Course.objects.create(title='Turk tili foreign draft', instructor=self.other, is_active=False)
        for status, expected in (('draft', [draft.pk]), ('active', [self.course.pk])):
            with self.subTest(status=status):
                response = self.client.get(self.url('courses'), {'q': 'Turk tili', 'status': status})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['status_filter'], status)
                self.assertEqual([row.pk for row in response.context['page_obj']], expected)
        for index in range(12):
            Course.objects.create(title=f'Turk tili draft {index}', instructor=self.teacher, is_active=False)
        response = self.client.get(self.url('courses'), {'q': 'Turk tili', 'status': 'draft', 'page': '2'})
        self.assertEqual(response.context['page_obj'].paginator.count, 13)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual([row.pk for row in response.context['page_obj']], [draft.pk])
        self.assertEqual(self.client.get(self.url('courses'), {'status': 'unknown'}).status_code, 400)

    def test_successful_lesson_write_issues_one_time_server_scoped_draft_receipt(self):
        page = self.page(lesson=self.lesson)
        expected_scope = page.context['draft_scope']
        nonce = 'lesson-save-attempt-123'
        response = self.client.post(self.url(), self.lesson_data(draft_submission_id=nonce))
        self.assertEqual(response.status_code, 302)
        receipt = self.client.session['workspace_saved']
        self.assertEqual(receipt, {'scope': expected_scope, 'submission_id': nonce})
        saved_page = self.client.get(response['Location'])
        self.assertEqual(saved_page.context['saved_scope'], expected_scope)
        self.assertEqual(saved_page.context['saved_submission_id'], nonce)
        self.assertContains(saved_page, f'data-saved-scope="{expected_scope}"')
        self.assertContains(saved_page, f'data-saved-submission-id="{nonce}"')
        self.assertNotIn('workspace_saved', self.client.session)
        reloaded_page = self.page(lesson=self.lesson)
        self.assertEqual(reloaded_page.context['saved_scope'], '')
        self.assertEqual(reloaded_page.context['saved_submission_id'], '')

    def test_course_creation_receipt_acknowledges_original_new_course_scope(self):
        page = self.client.get(self.url('course_create'))
        initial_scope = page.context['draft_scope']
        nonce = 'new-course-submit-456'
        data = self.course_data(course=None, title='Receipt course', draft_submission_id=nonce)
        response = self.client.post(self.url('course_create'), data)
        self.assertEqual(response.status_code, 302)
        saved_page = self.client.get(response['Location'])
        self.assertEqual(saved_page.context['saved_scope'], initial_scope)
        self.assertEqual(saved_page.context['saved_submission_id'], nonce)
        # The redirected course overview has a different draft identity. The
        # receipt must name the original new-course form to clear that draft.
        self.assertNotEqual(saved_page.context['draft_scope'], initial_scope)

    def test_forged_query_or_unsuccessful_submission_cannot_acknowledge_draft(self):
        page = self.page(lesson=self.lesson)
        scope = page.context['draft_scope']
        response = self.client.get(self.url(), {
            'lesson': self.lesson.pk, 'saved_scope': scope,
            'saved_submission_id': 'forged', 'draft_submission_id': 'forged',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['saved_scope'], '')
        self.assertEqual(response.context['saved_submission_id'], '')
        self.assertNotContains(response, 'data-workspace-saved')
        for changes, expected_status in (
            ({'action': 'lesson_preview'}, 200),
            ({'order': 'invalid'}, 400),
            ({'lesson_revision': 'stale'}, 409),
        ):
            with self.subTest(changes=changes):
                data = self.lesson_data(draft_submission_id='unsaved-attempt', **changes)
                response = self.client.post(self.url(), data)
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.context['saved_scope'], '')
                self.assertEqual(response.context['saved_submission_id'], '')
                self.assertNotIn('workspace_saved', self.client.session)

    def test_existing_active_cohort_renders_scoped_lesson_release_link(self):
        cohort = Cohort.objects.create(
            course=self.course, name='A1 evening group', start_date=date(2026, 10, 1),
        )
        Cohort.objects.create(
            course=self.course, name='Inactive group hidden', start_date=date(2026, 9, 1), is_active=False,
        )
        Cohort.objects.create(
            course=self.foreign_course, name='Foreign group hidden', start_date=date(2026, 10, 1),
        )
        Cohort.objects.create(
            course=self.second_course, name='Other own course group hidden', start_date=date(2026, 10, 1),
        )
        response = self.page(lesson=self.lesson)
        self.assertContains(response, cohort.name)
        self.assertNotContains(response, 'Inactive group hidden')
        self.assertNotContains(response, 'Foreign group hidden')
        self.assertNotContains(response, 'Other own course group hidden')
        self.assertEqual([row.pk for row in response.context['cohorts']], [cohort.pk])
        release_url = response.context['cohorts'][0].release_url
        parsed = urlsplit(release_url)
        self.assertEqual(parsed.path, reverse('teacher_release'))
        self.assertEqual(parse_qs(parsed.query), {
            'cohort': [str(cohort.pk)], 'lesson': [str(self.lesson.pk)], 'action': ['release'],
        })
        self.assertContains(response, f'href="{release_url.replace("&", "&amp;")}"')
        # Opening the link selects the intended confirmation; it does not
        # change learner access until the existing release POST is confirmed.
        set_flag('frontend_v1_teacher', enabled=True, reason='Release handoff regression')
        release_page = self.client.get(release_url)
        self.assertEqual(release_page.status_code, 200)
        self.assertEqual(release_page.context['cohort'].pk, cohort.pk)
        self.assertEqual(release_page.context['release_target'].pk, self.lesson.pk)
        self.assertEqual(release_page.context['release_action'], 'release')
        self.assertFalse(CohortLessonRelease.objects.exists())
