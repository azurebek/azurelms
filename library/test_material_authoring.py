"""Material commands retain input and use the same policy in every renderer."""
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.http import QueryDict
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from core import frontend_v1_editors as editor
from core.flags import set_flag
from courses.models import Course, Lesson, Module
from library import material_authoring as authoring
from library.models import LessonMaterial, LibraryResource


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class MaterialAuthoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = get_user_model().objects.create_user(
            'material-author', 'material-author@example.test', is_staff=True)
        cls.course = Course.objects.create(title='Material kursi', description='Test',
            instructor=cls.teacher, level='beginner', duration=10)
        cls.module = Module.objects.create(course=cls.course, title='Bo‘lim', order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title='Dars', order=1)
        cls.resource = LibraryResource.objects.create(title='Umumiy material', file='material.pdf')
        cls.material = LessonMaterial.objects.create(lesson=cls.lesson, resource=cls.resource, order=1)

    def setUp(self):
        self.client.force_login(self.teacher)

    def material_data(self, **changes):
        data = {'display_title': 'Saqlanmagan nom', 'audience': 'student',
                'is_visible': 'on', 'is_downloadable': 'on', 'available_from': '',
                'editor_revision': editor.material_revision(self.teacher, self.material, 'material'),
                'confirm_scope': 'yes'}
        data.update(changes)
        return data

    def test_legacy_invalid_material_keeps_bound_values_and_error(self):
        response = self.client.post(reverse('library_backoffice:material_update', args=[self.material.pk]),
            self.material_data(available_from='not-a-date'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['form']['display_title'].value(), 'Saqlanmagan nom')
        self.assertEqual(response.context['form']['available_from'].value(), 'not-a-date')
        self.assertIn('available_from', response.context['form'].errors)
        self.assertContains(response, 'value="not-a-date"', status_code=400)
        self.assertEqual(response.context['form'].fields['available_from'].widget.input_type, 'text')
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, '')

    def test_legacy_invalid_reorder_is_rejected_without_normalizing(self):
        self.material.order = 7
        self.material.save(update_fields=['order'])
        response = self.client.post(reverse('library_backoffice:material_reorder', args=[self.lesson.pk]),
            {'editor_revision': editor.reorder_revision(self.teacher, self.lesson),
             'confirm_scope': 'yes', f'order-{self.material.pk}': 'not-a-number'})
        self.assertEqual(response.status_code, 400)
        self.material.refresh_from_db()
        self.assertEqual(self.material.order, 7)

    def test_renderers_reject_each_invalid_order_and_preserve_input(self):
        second = LessonMaterial.objects.create(lesson=self.lesson,
            resource=LibraryResource.objects.create(title='Ikkinchi material', file='second.pdf'), order=2)
        for enabled in (False, True):
            set_flag('frontend_v1_editors', enabled=enabled, reason='Isolated renderer parity')
            for bad in ('-1', '1.5', '١', '²', '2147483648', '', '9' * 80):
                with self.subTest(enabled=enabled, bad=bad):
                    data = {'editor_revision': authoring.reorder_revision(self.teacher, self.lesson),
                        'confirm_scope': 'yes', f'order-{self.material.pk}': bad, f'order-{second.pk}': '0'}
                    response = self.client.post(reverse('library_backoffice:material_reorder', args=[self.lesson.pk]), data)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.context['materials'][0].posted_order, bad)
                    self.assertEqual(list(self.lesson.materials.values_list('order', flat=True)), [1, 2])
        self.assertFalse(SystemAuditEvent.objects.filter(action='library.material.reorder').exists())

    def test_partial_extra_and_duplicate_positions_are_rejected_by_service(self):
        for values in ({}, {f'order-{self.material.pk}': '1', 'order-999': '2'},
                       {f'order-{self.material.pk}': ['1', '2']}):
            positions = QueryDict('', mutable=True)
            for key, value in values.items():
                positions.setlist(key, value if isinstance(value, list) else [value])
            with self.subTest(values=values), self.assertRaises(ValidationError):
                authoring.reorder_materials(actor=self.teacher, lesson_id=self.lesson.pk,
                    positions=positions, expected_revision=authoring.reorder_revision(self.teacher, self.lesson))
        self.material.refresh_from_db()
        self.assertEqual(self.material.order, 1)

    def test_equal_numbers_keep_previous_order_and_reorder_audit_is_atomic(self):
        second = LessonMaterial.objects.create(lesson=self.lesson,
            resource=LibraryResource.objects.create(title='Ikkinchi material', file='second.pdf'), order=0)
        positions = {f'order-{self.material.pk}': '4', f'order-{second.pk}': '4'}
        revision = authoring.reorder_revision(self.teacher, self.lesson)
        with patch('library.material_authoring.record_audit_event', side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                authoring.reorder_materials(actor=self.teacher, lesson_id=self.lesson.pk,
                    positions=positions, expected_revision=revision)
        self.assertEqual(list(self.lesson.materials.values_list('pk', 'order')), [(second.pk, 0), (self.material.pk, 1)])
        self.assertTrue(authoring.reorder_materials(actor=self.teacher, lesson_id=self.lesson.pk,
            positions=positions, expected_revision=revision))
        self.assertEqual(list(self.lesson.materials.values_list('pk', 'order')), [(second.pk, 1), (self.material.pk, 2)])
        self.assertEqual(SystemAuditEvent.objects.filter(action='library.material.reorder').count(), 1)
        self.assertFalse(authoring.reorder_materials(actor=self.teacher, lesson_id=self.lesson.pk,
            positions=positions, expected_revision=authoring.reorder_revision(self.teacher, self.lesson)))
        self.assertEqual(SystemAuditEvent.objects.filter(action='library.material.reorder').count(), 1)

    def test_update_audit_noop_and_stale_revision(self):
        revision = authoring.material_revision(self.teacher, self.material)
        material, changed = authoring.update_material(actor=self.teacher, material_id=self.material.pk,
            data=self.material_data(), expected_revision=revision)
        self.assertTrue(changed)
        self.assertEqual(material.display_title, 'Saqlanmagan nom')
        with self.assertRaises(authoring.MaterialConflict):
            authoring.update_material(actor=self.teacher, material_id=self.material.pk,
                data=self.material_data(), expected_revision=revision)
        _, changed = authoring.update_material(actor=self.teacher, material_id=self.material.pk,
            data=self.material_data(), expected_revision=authoring.material_revision(self.teacher, material))
        self.assertFalse(changed)
        self.assertEqual(SystemAuditEvent.objects.filter(action='library.material.update').count(), 1)

    def test_audit_failure_rolls_back_update_and_detach(self):
        with patch('library.material_authoring.record_audit_event', side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                authoring.update_material(actor=self.teacher, material_id=self.material.pk,
                    data=self.material_data(), expected_revision=authoring.material_revision(self.teacher, self.material))
            with self.assertRaises(RuntimeError):
                authoring.detach_material(actor=self.teacher, material_id=self.material.pk,
                    expected_revision=authoring.material_revision(self.teacher, self.material, 'detach'))
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, '')

    def test_detach_keeps_shared_resource_and_other_lesson_link(self):
        other_lesson = Lesson.objects.create(module=self.module, title='Yana bir dars', order=2)
        other_link = LessonMaterial.objects.create(lesson=other_lesson, resource=self.resource, order=1)
        result = authoring.detach_material(actor=self.teacher, material_id=self.material.pk,
            expected_revision=authoring.material_revision(self.teacher, self.material, 'detach'))
        self.assertEqual(result, self.lesson.pk)
        self.assertFalse(LessonMaterial.objects.filter(pk=self.material.pk).exists())
        self.assertTrue(LessonMaterial.objects.filter(pk=other_link.pk).exists())
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.file.name, 'material.pdf')
        self.assertEqual(SystemAuditEvent.objects.filter(action='library.material.detach').count(), 1)

    def test_service_rechecks_actor_and_parent_scope(self):
        other = get_user_model().objects.create_user('other-material', 'other-material@example.test', is_staff=True)
        with self.assertRaises(Lesson.DoesNotExist):
            authoring.update_material(actor=other, material_id=self.material.pk, data=self.material_data(),
                expected_revision=authoring.material_revision(other, self.material))
        with self.assertRaises(LessonMaterial.DoesNotExist):
            authoring.detach_material(actor=self.teacher, material_id=self.material.pk, lesson_id=self.lesson.pk + 1,
                expected_revision=authoring.material_revision(self.teacher, self.material, 'detach'))
        with self.assertRaises(Lesson.DoesNotExist):
            authoring.reorder_materials(actor=self.teacher, lesson_id=self.lesson.pk, course_id=self.course.pk + 1,
                positions={f'order-{self.material.pk}': '1'}, expected_revision=authoring.reorder_revision(self.teacher, self.lesson))
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            authoring.update_material(actor=self.teacher, material_id=self.material.pk, data=self.material_data(),
                expected_revision=authoring.material_revision(self.teacher, self.material))

    def test_resource_policy_changes_reject_stale_or_unsafe_update(self):
        revision = authoring.material_revision(self.teacher, self.material)
        self.resource.is_teacher_only = True
        self.resource.save()
        with self.assertRaises(authoring.MaterialConflict):
            authoring.update_material(actor=self.teacher, material_id=self.material.pk,
                data=self.material_data(), expected_revision=revision)
        self.material.refresh_from_db()
        with self.assertRaises(ValidationError) as raised:
            authoring.update_material(actor=self.teacher, material_id=self.material.pk,
                data=self.material_data(), expected_revision=authoring.material_revision(self.teacher, self.material))
        self.assertIn('audience', raised.exception.error_dict)

    def test_legacy_forms_have_tokens_and_missing_stale_or_duplicate_posts_do_not_write(self):
        response = self.client.get(reverse('backoffice_lesson_edit', args=[self.lesson.pk]))
        self.assertContains(response, authoring.material_revision(self.teacher, self.material))
        self.assertContains(response, authoring.material_revision(self.teacher, self.material, 'detach'))
        self.assertContains(response, authoring.reorder_revision(self.teacher, self.lesson))
        url = reverse('library_backoffice:material_update', args=[self.material.pk])
        for revision in ('', 'stale'):
            self.assertEqual(self.client.post(url, self.material_data(editor_revision=revision)).status_code, 409)
        self.assertEqual(self.client.post(url, self.material_data(display_title=['one', 'two'])).status_code, 400)
        self.material.refresh_from_db()
        self.assertEqual(self.material.display_title, '')
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post(url, self.material_data()).status_code, 403)


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class MaterialConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_actors_updating_same_snapshot_commit_once(self):
        teacher = get_user_model().objects.create_user('material-race', 'material-race@example.test', is_staff=True)
        owner = get_user_model().objects.create_user('material-owner-race', 'material-owner-race@example.test',
            is_staff=True, is_superuser=True)
        course = Course.objects.create(title='Race', instructor=teacher)
        module = Module.objects.create(course=course, title='Module', order=1)
        lesson = Lesson.objects.create(module=module, title='Lesson', order=1)
        resource = LibraryResource.objects.create(title='File', file='race.pdf')
        material = LessonMaterial.objects.create(lesson=lesson, resource=resource, order=1)
        revisions = {actor.pk: authoring.material_revision(actor, material) for actor in (teacher, owner)}
        barrier = Barrier(2)

        def save(actor_id):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=actor_id)
                barrier.wait(timeout=10)
                try:
                    authoring.update_material(actor=actor, material_id=material.pk,
                        data={'display_title': str(actor_id), 'audience': 'student', 'is_visible': 'on',
                              'is_downloadable': 'on', 'available_from': ''}, expected_revision=revisions[actor_id])
                    return 'saved'
                except authoring.MaterialConflict:
                    return 'stale'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(save, actor.pk) for actor in (teacher, owner)]
            results = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(results, ['saved', 'stale'])
        self.assertEqual(SystemAuditEvent.objects.filter(action='library.material.update').count(), 1)
