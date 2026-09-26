"""V1 editor integration: real forms/services, scoped rows, no external calls."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core import frontend_v1_editors as v1
from core.backoffice_forms import CourseBackofficeForm, LessonBackofficeForm
from core.flags import flag_by_slug, set_flag
from courses.models import Assignment, Course, Lesson, Module
from library import services
from library.models import LessonMaterial, LibraryResource


class EditorV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('editor-teacher', 'editor-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('editor-other', 'editor-other@example.test', is_staff=True)
        cls.student = User.objects.create_user('editor-student', 'editor-student@example.test')
        cls.course = Course.objects.create(title='Turk tili', description='Saved description', instructor=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title='Birinchi modul')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Saved lesson', content='Saved text')
        cls.foreign = Course.objects.create(title='Foreign course', instructor=cls.other)
        cls.foreign_module = Module.objects.create(course=cls.foreign, title='Foreign module')
        cls.foreign_lesson = Lesson.objects.create(module=cls.foreign_module, title='Foreign lesson')
        cls.resource = LibraryResource.objects.create(title='Shared PDF', file='synthetic.pdf', file_kind='pdf')
        cls.material, _ = services.attach_to_lesson(cls.lesson, cls.resource)
        cls.resource2 = LibraryResource.objects.create(title='Second PDF', file='synthetic2.pdf', file_kind='pdf')
        cls.material2, _ = services.attach_to_lesson(cls.lesson, cls.resource2)

    def setUp(self):
        set_flag('frontend_v1_editors', enabled=True, reason='Isolated editor test')
        self.client.force_login(self.teacher)

    def url(self, name, pk=None):
        return reverse(name, args=[pk] if pk else [])

    def token(self, obj, action):
        if obj is not None:
            obj.refresh_from_db()
        if action in ('material', 'detach'):
            rev = v1.material_revision(self.teacher, obj, action)
        elif action == 'reorder':
            rev = v1.reorder_revision(self.teacher, obj)
        else:
            rev = v1.revision(self.teacher, obj, action)
        return dict(frontend_v1_editors='1', confirm_scope='yes', editor_revision=rev)

    def course_data(self, obj=True, **extra):
        obj = self.course if obj is True else obj
        data = {name: getattr(self.course, name) for name in CourseBackofficeForm.Meta.fields}
        data['instructor'] = self.teacher.pk
        data.update(self.token(obj, 'course'))
        data.update(extra)
        return data

    def lesson_data(self, **extra):
        return dict(self.token(self.lesson, 'lesson'), title='Updated lesson', module=self.module.pk,
                    video_url='', content='Changed text', order=2, xp_reward=30, **extra)

    def material_data(self, **extra):
        data = dict(self.token(self.material, 'material'), display_title='Darsdagi nom',
                    audience='student', is_visible='on', is_downloadable='on', available_from='')
        data.update(extra)
        return data

    def test_five_routes_real_private_no_demo(self):
        for name, pk, page in [('backoffice_courses', None, 'list'), ('backoffice_course_create', None, 'course'),
                              ('backoffice_course_edit', self.course.pk, 'course'), ('backoffice_lessons', None, 'index'),
                              ('backoffice_lesson_edit', self.lesson.pk, 'lesson')]:
            with self.subTest(page=page):
                response = self.client.get(self.url(name, pk))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f'frontend_v1/editors/{page}.html')
                self.assertIn('no-store', response['Cache-Control'])
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, 'Foreign lesson')

    def test_all_fields_and_unique_material_ids(self):
        for name, obj, fields in [('backoffice_course_edit', self.course, CourseBackofficeForm.Meta.fields),
                                  ('backoffice_lesson_edit', self.lesson, LessonBackofficeForm.Meta.fields)]:
            response = self.client.get(self.url(name, obj.pk))
            for field in fields:
                self.assertContains(response, f'name="{field}"')
        for material in (self.material, self.material2):
            self.assertContains(response, f'id="material_{material.pk}_display_title"', count=1)
        self.assertContains(response, 'frontend_v1/js/library.js')
        self.assertEqual(response.context['form'].fields['content'].label, 'Dars matni')

    def test_flag_off_retains_legacy_and_first_lesson(self):
        self.assertFalse(flag_by_slug('frontend_v1_editors').default)
        set_flag('frontend_v1_editors', enabled=False, reason='Rollback')
        response = self.client.get(self.url('backoffice_lessons'))
        self.assertTemplateUsed(response, 'backoffice/lesson_form.html')
        self.assertEqual(response.context['lesson'], self.lesson)
        response = self.client.get(self.url('backoffice_courses'))
        self.assertTemplateUsed(response, 'backoffice/courses.html')

    def test_filters_scope_and_pagination(self):
        for i in range(13):
            Course.objects.create(title=f'Draft {i}', instructor=self.teacher, is_active=False)
        response = self.client.get(self.url('backoffice_courses'), {'q': 'Draft', 'status': 'draft', 'page': '2'})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(response.context['page_obj'].paginator.count, 13)
        self.assertContains(response, 'q=Draft&amp;status=draft')
        self.assertNotContains(response, 'Foreign course')

    def test_invalid_filters_never_open_another_selection(self):
        for route, suffix in [('backoffice_courses', '?status=oops'), ('backoffice_courses', '?page=2&page=1'),
                              ('backoffice_lessons', '?course=１'), ('backoffice_lessons', '?course=1&course=2'),
                              ('backoffice_lessons', '?unknown=yes')]:
            response = self.client.get(self.url(route) + suffix)
            self.assertContains(response, 'Manzil tanlovi tanilmadi')
            self.assertNotContains(response, 'Tarkibni ko‘rish')
        response = self.client.get(self.url('backoffice_lessons'), {'course': self.foreign.pk})
        self.assertEqual(response.status_code, 404)

    def test_index_never_saves_first_lesson(self):
        response = self.client.get(self.url('backoffice_lessons'))
        self.assertNotIn('lesson', response.context)
        self.assertContains(response, self.url('backoffice_lesson_edit', self.lesson.pk))
        response = self.client.post(self.url('backoffice_lessons'), self.lesson_data())
        self.assertEqual(response.status_code, 409)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Saved lesson')

    def test_first_lesson_create_when_scope_has_no_lessons(self):
        # Preserve the original empty-editor create contract without selecting a different lesson.
        self.client.force_login(self.other)
        self.foreign_lesson.delete()
        response = self.client.get(self.url('backoffice_lessons'))
        self.assertContains(response, 'Birinchi dars')
        data = dict(frontend_v1_editors='1', confirm_scope='yes', editor_revision=response.context['editor_revision'],
                    module=self.foreign_module.pk, title='First lesson', order=1, xp_reward=10, video_url='', content='')
        response = self.client.post(self.url('backoffice_lessons'), data)
        created = Lesson.objects.get(title='First lesson')
        self.assertRedirects(response, self.url('backoffice_lesson_edit', created.pk))

    def test_course_create_and_draft_prg_default_module(self):
        response = self.client.post(self.url('backoffice_course_create'), self.course_data(None, title='New course', save_draft='1'))
        course = Course.objects.get(title='New course')
        self.assertRedirects(response, self.url('backoffice_course_edit', course.pk))
        self.assertFalse(course.is_active)
        self.assertEqual(course.modules.count(), 1)
        self.assertFalse(Lesson.objects.filter(module__course=course).exists())

    def test_course_save_preserves_all_fields_and_scope(self):
        response = self.client.post(self.url('backoffice_course_edit', self.course.pk), self.course_data(
            title='Edited course', price='250000.00', gradient_cover_title='Cover',
            certificate_min_attendance_percent=70, certificate_min_lesson_completion_percent=80))
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Edited course')
        self.assertEqual(self.course.certificate_min_attendance_percent, 70)
        self.assertEqual(self.course.gradient_cover_title, 'Cover')
        self.assertEqual(self.course.modules.count(), 1)

    def test_stale_course_draft_preserved_no_write(self):
        data = self.course_data(title='Unsaved draft')
        Course.objects.filter(pk=self.course.pk).update(title='Other window')
        response = self.client.post(self.url('backoffice_course_edit', self.course.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['form']['title'].value(), 'Unsaved draft')
        self.assertContains(response, 'Other window', status_code=409)
        self.assertContains(response, ' disabled', status_code=409)
        self.assertContains(response, 'data-library-unsaved', status_code=409)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Other window')

    def test_invalid_course_preserves_bound_data(self):
        response = self.client.post(self.url('backoffice_course_edit', self.course.pk), self.course_data(title='Draft title', duration='wrong'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['form']['title'].value(), 'Draft title')
        self.assertIn('duration', response.context['form'].errors)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Turk tili')

    def test_lesson_save_preserves_links_and_makes_no_progress(self):
        assignment = Assignment.objects.create(lesson=self.lesson, title='Assignment')
        response = self.client.post(self.url('backoffice_lesson_edit', self.lesson.pk), self.lesson_data())
        self.assertRedirects(response, self.url('backoffice_lesson_edit', self.lesson.pk))
        self.lesson.refresh_from_db()
        self.assertEqual((self.lesson.title, self.lesson.xp_reward), ('Updated lesson', 30))
        self.assertTrue(self.lesson.assignments.filter(pk=assignment.pk).exists())
        self.assertEqual(self.lesson.materials.count(), 2)

    def test_stale_lesson_rejects_replay(self):
        data = self.lesson_data()
        url = self.url('backoffice_lesson_edit', self.lesson.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_invalid_lesson_and_foreign_module_preserve_draft(self):
        data = self.lesson_data()
        data.update(module=self.foreign_module.pk)
        response = self.client.post(self.url('backoffice_lesson_edit', self.lesson.pk), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('module', response.context['form'].errors)
        self.assertEqual(response.context['form']['title'].value(), 'Updated lesson')
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.module_id, self.module.pk)

    def test_confirmation_user_action_and_object_binding(self):
        url = self.url('backoffice_lesson_edit', self.lesson.pk)
        data = self.lesson_data()
        data.pop('confirm_scope')
        self.assertEqual(self.client.post(url, data).status_code, 400)
        data['confirm_scope'] = 'yes'
        data['editor_revision'] = v1.revision(self.other, self.lesson, 'lesson')
        self.assertEqual(self.client.post(url, data).status_code, 409)
        data['editor_revision'] = v1.revision(self.teacher, self.course, 'course')
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_csrf_roles_and_foreign_rows(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post(self.url('backoffice_course_edit', self.course.pk), self.course_data()).status_code, 403)
        for name, obj in [('backoffice_course_edit', self.foreign), ('backoffice_lesson_edit', self.foreign_lesson)]:
            self.assertEqual(self.client.get(self.url(name, obj.pk)).status_code, 404)
            self.assertEqual(self.client.post(self.url(name, obj.pk), {}).status_code, 404)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url('backoffice_courses')).status_code, 302)

    def test_late_v1_form_keeps_guard_when_flag_off(self):
        data = self.lesson_data()
        set_flag('frontend_v1_editors', enabled=False, reason='Rollback')
        Lesson.objects.filter(pk=self.lesson.pk).update(content='Other window')
        response = self.client.post(self.url('backoffice_lesson_edit', self.lesson.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertTemplateUsed(response, 'frontend_v1/editors/lesson.html')

    def test_material_settings_real_prg_no_resource_mutation(self):
        response = self.client.post(self.url('library_backoffice:material_update', self.material.pk), self.material_data(is_required='on'))
        self.assertRedirects(response, self.url('backoffice_lesson_edit', self.lesson.pk))
        self.material.refresh_from_db()
        self.resource.refresh_from_db()
        self.assertEqual(self.material.display_title, 'Darsdagi nom')
        self.assertTrue(self.material.is_required)
        self.assertEqual(self.resource.title, 'Shared PDF')

    def test_invalid_material_draft_no_write(self):
        response = self.client.post(self.url('library_backoffice:material_update', self.material.pk), self.material_data(available_from='not-date'))
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'frontend_v1/editors/material.html')
        self.assertEqual(response.context['form']['display_title'].value(), 'Darsdagi nom')
        self.assertEqual(response.context['form']['available_from'].value(), 'not-date')
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, '')

    def test_stale_material_and_changed_resource_policy_rejected(self):
        data = self.material_data()
        self.resource.is_teacher_only = True
        self.resource.save()
        response = self.client.post(self.url('library_backoffice:material_update', self.material.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['form']['display_title'].value(), 'Darsdagi nom')
        fresh = self.material_data()
        response = self.client.post(self.url('library_backoffice:material_update', self.material.pk), fresh)
        self.assertEqual(response.status_code, 400)
        self.assertIn('audience', response.context['form'].errors)

    def test_detach_only_scoped_link_and_requires_confirmation(self):
        data = self.token(self.material, 'detach')
        data.pop('confirm_scope')
        url = self.url('library_backoffice:material_detach', self.material.pk)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        data['confirm_scope'] = 'yes'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(LessonMaterial.objects.filter(pk=self.material.pk).exists())
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        self.assertTrue(LessonMaterial.objects.filter(pk=self.material2.pk).exists())

    def test_reorder_canonical_order_and_stale_replay(self):
        data = dict(self.token(self.lesson, 'reorder'), **{f'order-{self.material.pk}': '2', f'order-{self.material2.pk}': '1'})
        url = self.url('library_backoffice:material_reorder', self.lesson.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.material.refresh_from_db()
        self.material2.refresh_from_db()
        self.assertEqual((self.material.order, self.material2.order), (2, 1))
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_reorder_invalid_partial_or_extra_never_normalizes_silently(self):
        url = self.url('library_backoffice:material_reorder', self.lesson.pk)
        for orders in [{f'order-{self.material.pk}': '1'}, {f'order-{self.material.pk}': 'n/a', f'order-{self.material2.pk}': '2'},
                       {f'order-{self.material.pk}': '1', f'order-{self.material2.pk}': '2', 'order-999': '3'},
                       {f'order-{self.material.pk}': ['1', '2'], f'order-{self.material2.pk}': '2'}]:
            response = self.client.post(url, dict(self.token(self.lesson, 'reorder'), **orders))
            self.assertEqual(response.status_code, 400)
            self.assertTemplateUsed(response, 'frontend_v1/editors/reorder.html')
        self.material.refresh_from_db()
        self.assertEqual(self.material.order, 1)

    def test_attach_invalidates_old_reorder(self):
        data = dict(self.token(self.lesson, 'reorder'), **{f'order-{self.material.pk}': '1', f'order-{self.material2.pk}': '2'})
        resource = LibraryResource.objects.create(title='Third PDF', file='third.pdf')
        services.attach_to_lesson(self.lesson, resource)
        response = self.client.post(self.url('library_backoffice:material_reorder', self.lesson.pk), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.lesson.materials.count(), 3)

    def test_foreign_material_actions_are_denied(self):
        link, _ = services.attach_to_lesson(self.foreign_lesson, self.resource)
        for action in ('material_update', 'material_detach'):
            response = self.client.post(self.url('library_backoffice:' + action, link.pk), {})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(self.url('library_backoffice:material_reorder', self.foreign_lesson.pk), {}).status_code, 404)

    def test_query_on_editor_post_cannot_write(self):
        response = self.client.post(self.url('backoffice_course_edit', self.course.pk) + '?unknown=yes', self.course_data(title='Wrong'))
        self.assertEqual(response.status_code, 400)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Turk tili')

    def test_empty_post_is_bound_and_keeps_guard(self):
        response = self.client.post(self.url('backoffice_course_edit', self.course.pk), {})
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.context['form'].is_bound)
        self.assertIn('title', response.context['form'].errors)

    def test_create_get_starts_as_draft_without_changing_model_default(self):
        response = self.client.get(self.url('backoffice_course_create'))
        self.assertFalse(response.context['form']['is_active'].value())
        self.assertTrue(Course._meta.get_field('is_active').default)
