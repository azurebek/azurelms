"""Course context, form recovery and shared-resource safety for B2.1."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from core.flags import set_flag
from courses.models import Course, Lesson, Module
from library import material_authoring
from library.models import LessonMaterial, LibraryResource


class WorkspaceMaterialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = get_user_model().objects.create_user('material-author', is_staff=True)
        cls.course = Course.objects.create(title='Kurs', instructor=cls.teacher)
        cls.lesson = Lesson.objects.create(module=Module.objects.create(course=cls.course, title='Modul'),
                                          title='Dars', content='Saved lesson')
        cls.other_course = Course.objects.create(title='Other own course', instructor=cls.teacher)
        cls.other_lesson = Lesson.objects.create(module=Module.objects.create(course=cls.other_course), title='Other')
        cls.resource = LibraryResource.objects.create(title='Shared file', file='library/test.pdf', file_kind='pdf')
        cls.material = LessonMaterial.objects.create(lesson=cls.lesson, resource=cls.resource, order=1)
        cls.shared_link = LessonMaterial.objects.create(lesson=cls.other_lesson, resource=cls.resource)
        cls.next_material = LessonMaterial.objects.create(lesson=cls.lesson, order=2,
            resource=LibraryResource.objects.create(title='Next file', file='library/next.pdf', file_kind='pdf'))

    def setUp(self):
        set_flag('backoffice_course_workspace', enabled=True, reason='B2.1 isolated test')
        self.client.force_login(self.teacher)
        self.url = reverse('backoffice_workspace_course', args=[self.course.pk]) + f'?lesson={self.lesson.pk}'

    def data(self, action='material_update', **extra):
        data = {'action': action, 'lesson_id': self.lesson.pk, 'material_id': self.material.pk,
                'display_title': 'Lesson file', 'audience': 'student', 'is_visible': 'on',
                'is_downloadable': 'on', 'available_from': '',
                'editor_revision': material_authoring.material_revision(
                    self.teacher, self.material, 'detach' if action == 'material_detach' else 'material')}
        data.update(extra)
        return data

    def test_settings_and_exam_link_are_in_selected_lesson(self):
        page = self.client.get(self.url)
        self.assertContains(page, 'Materialni saqlash')
        self.assertContains(page, f'?course={self.course.pk}&amp;lesson={self.lesson.pk}')
        self.assertContains(page, f'material_{self.material.pk}_available_from')
        self.assertContains(page, f'material_{self.next_material.pk}_available_from')

    def test_invalid_date_retains_value_form_and_draft_scope_without_write(self):
        initial = self.client.get(self.url)
        response = self.client.post(self.url, self.data(available_from='not-a-date'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['lesson'].pk, self.lesson.pk)
        self.assertEqual(response.context['draft_scope'], initial.context['draft_scope'])
        form = response.context['materials'][0].workspace_form
        self.assertTrue(form.errors['available_from'])
        self.assertEqual(form['available_from'].value(), 'not-a-date')
        self.assertContains(response, 'value="not-a-date"', status_code=400)
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, '')
        self.assertFalse(any(message.level == 25 for message in get_messages(response.wsgi_request)))

    def test_update_changes_only_link_and_preview_follows_visibility(self):
        response = self.client.post(self.url, self.data(is_visible=''))
        self.assertRedirects(response, self.url + '#materials')
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, 'Lesson file')
        self.assertFalse(self.material.is_visible)
        self.assertEqual(self.resource.title, 'Shared file')
        self.shared_link.refresh_from_db()
        self.assertTrue(self.shared_link.is_visible)
        preview_ids = [item.pk for item in self.client.get(self.url).context['preview_materials']]
        self.assertNotIn(self.material.pk, preview_ids)
        self.assertIn(self.next_material.pk, preview_ids)

    def test_stale_update_retains_draft_without_save(self):
        data = self.data()
        self.material.display_title = 'Another window'
        self.material.save()
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['materials'][0].workspace_form['display_title'].value(), 'Lesson file')
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, 'Another window')

    def test_detach_keeps_file_resource_other_lesson_and_selected_context(self):
        with patch('core.private_storage.PrivateMediaStorage.delete') as delete:
            response = self.client.post(self.url, self.data('material_detach'))
        self.assertRedirects(response, self.url + '#materials')
        delete.assert_not_called()
        self.assertFalse(LessonMaterial.objects.filter(pk=self.material.pk).exists())
        self.assertTrue(LibraryResource.objects.filter(pk=self.resource.pk).exists())
        self.assertTrue(LessonMaterial.objects.filter(pk=self.shared_link.pk).exists())

    def test_other_lesson_material_cannot_be_changed_even_with_valid_token(self):
        data = self.data(material_id=self.shared_link.pk,
            editor_revision=material_authoring.material_revision(self.teacher, self.shared_link))
        self.assertEqual(self.client.post(self.url, data).status_code, 404)
        self.shared_link.refresh_from_db()
        self.assertEqual(self.shared_link.display_title, '')

    def test_reorder_rejects_bad_positions_and_preserves_them(self):
        data = {'action': 'material_reorder', 'lesson_id': self.lesson.pk,
                'editor_revision': material_authoring.reorder_revision(self.teacher, self.lesson),
                f'order-{self.material.pk}': 'invalid', f'order-{self.next_material.pk}': '1'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'value="invalid"', status_code=400)
        self.material.refresh_from_db()
        self.assertEqual(self.material.order, 1)
        data[f'order-{self.material.pk}'] = '2'
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url + '#materials')
        self.assertEqual(list(self.lesson.materials.order_by('order').values_list('pk', flat=True)),
                         [self.next_material.pk, self.material.pk])
        self.assertEqual(self.client.post(self.url, data).status_code, 409)

    def test_flag_off_rejects_post_and_keeps_content(self):
        data = self.data('material_detach')
        set_flag('backoffice_course_workspace', enabled=False, reason='B2.1 rollback test')
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.assertTrue(LessonMaterial.objects.filter(pk=self.material.pk).exists())

    def test_material_write_never_acknowledges_lesson_draft(self):
        lesson_scope = self.client.get(self.url).context['draft_scope']
        response = self.client.post(self.url, self.data(draft_submission_id='unrelated-lesson-nonce'))
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(self.client.session['workspace_saved']['scope'], lesson_scope)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.content, 'Saved lesson')
