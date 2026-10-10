"""Owner boundary, strict input and durable browser reconciliation contracts."""
import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import Client, TestCase
from django.urls import reverse

from core.design_models import DesignDraft, DesignOperation, DesignPreset, DesignState, DesignVersion
from core.design_schema import defaults
from core.flags import set_flag


class DesignViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user('design-owner', 'design-owner@example.test', is_superuser=True, is_staff=True)
        cls.other = users.objects.create_user('design-other', 'design-other@example.test', is_superuser=True, is_staff=True)
        cls.teacher = users.objects.create_user('design-teacher', 'design-teacher@example.test', is_staff=True)
        cls.student = users.objects.create_user('design-student', 'design-student@example.test')

    def setUp(self):
        set_flag('backoffice_design_workspace', enabled=True, reason='Design HTTP regression')
        self.client.force_login(self.owner)

    def post(self, command, payload, operation=None, client=None):
        return (client or self.client).post(reverse('backoffice_design_command'), json.dumps({
            'operation': operation or str(uuid4()), 'command': command, 'payload': payload,
        }), content_type='application/json')

    def save(self, value=None):
        return self.post('save_draft', {'value': value or defaults(), 'draft_revision': 0, 'base_version': 0})

    def counts(self):
        return tuple(model.objects.count() for model in
                     (DesignState, DesignDraft, DesignVersion, DesignPreset, DesignOperation))

    def test_owner_gets_are_private_and_do_not_initialize_design(self):
        before = self.counts()
        for name in ('backoffice_design_state', 'backoffice_design'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertIn('private', response['Cache-Control'])
        self.assertEqual(self.counts(), before)
        state = self.client.get(reverse('backoffice_design_state')).json()
        self.assertEqual(state['draft']['revision'], 0)
        self.assertEqual(state['published']['version'], 0)

    def test_anonymous_staff_student_and_revoked_owner_cannot_read_or_write(self):
        for user in (None, self.teacher, self.student):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('backoffice_design_state')).status_code, 403)
            self.assertEqual(self.save().status_code, 403)
        self.client.force_login(self.owner)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        self.assertEqual(self.save().status_code, 403)
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))

    def test_flag_off_disables_editor_and_in_flight_request(self):
        self.save()
        before = self.counts()
        set_flag('backoffice_design_workspace', enabled=False, reason='Revert design safely')
        for name in ('backoffice_design_state', 'backoffice_design'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 404)
        self.assertEqual(self.post('publish', {'draft_revision': 1, 'base_version': 0,
                                            'confirmed': True, 'reason': 'New look'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('design_theme_css')).content, b'')
        self.assertEqual(self.counts(), before)

    def test_csrf_is_required_even_with_valid_owner_session(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        payload = {'value': defaults(), 'draft_revision': 0, 'base_version': 0}
        self.assertEqual(self.post('save_draft', payload, client=client).status_code, 403)
        response = client.get(reverse('backoffice_design'))
        self.assertEqual(response.status_code, 200)
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('backoffice_design_command'), json.dumps({
            'operation': str(uuid4()), 'command': 'save_draft', 'payload': payload,
        }), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_unsupported_methods_cannot_mutate(self):
        self.assertEqual(self.client.get(reverse('backoffice_design_command')).status_code, 405)
        self.assertEqual(self.client.post(reverse('backoffice_design_state')).status_code, 405)
        self.assertEqual(self.client.post(reverse('backoffice_design')).status_code, 405)
        self.assertEqual(self.client.post(reverse('design_theme_css')).status_code, 405)
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))

    def test_strict_json_rejects_ambiguous_nonfinite_and_large_payloads(self):
        operation = str(uuid4())
        envelope = {'operation': operation, 'command': 'save_draft', 'payload': {
            'value': defaults(), 'draft_revision': 0, 'base_version': 0}}
        raw = json.dumps(envelope)
        malformed = [raw[:-1] + ',"command":"publish"}', raw.replace('"values": {', '"values": {"x":NaN,'),
                     raw.replace('"values": {', '"values": {"x":Infinity,'), '[]', '{}',
                     raw.replace(operation, 'bad'), raw[:-1] + ',"unknown":true}',
                     raw.replace('"draft_revision": 0', '"draft_revision": 0,"draft_revision": 1')]
        malformed.append(json.dumps({'operation': operation, 'command': 'save_preset',
                                     'payload': {'name': chr(0xD800), 'value': defaults()}}))
        nested = json.dumps({'operation': operation, 'command': 'save_draft',
                             'payload': {'value': None, 'draft_revision': 0, 'base_version': 0}})
        malformed.append(nested.replace('"value": null', '"value": ' + '[' * 700 + '0' + ']' * 700))
        for value in malformed:
            with self.subTest(value=value[:75]):
                response = self.client.post(reverse('backoffice_design_command'), value, content_type='application/json')
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(reverse('backoffice_design_command'), 'x' * 40001,
                                         content_type='application/json').status_code, 413)
        self.assertEqual(self.client.post(reverse('backoffice_design_command'), {}).status_code, 400)
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))

    def test_readback_is_owner_private_and_receipt_survives_new_client(self):
        operation = str(uuid4())
        response = self.post('save_draft', {'value': defaults(), 'draft_revision': 0, 'base_version': 0}, operation)
        self.assertEqual(response.status_code, 200)
        client = Client()
        client.force_login(self.owner)
        state = client.get(reverse('backoffice_design_state'), {'operation': operation}).json()
        self.assertEqual(state['receipt']['result'], response.json()['result'])
        self.assertEqual(state['draft']['revision'], 1)
        client.force_login(self.other)
        foreign = client.get(reverse('backoffice_design_state'), {'operation': operation}).json()
        self.assertIsNone(foreign['receipt'])
        self.assertEqual(foreign['draft']['revision'], 0)

    def test_invalid_readback_query_never_returns_private_data(self):
        for query in ('operation=bad', f'operation={uuid4()}&operation={uuid4()}', 'unexpected=1'):
            self.assertEqual(self.client.get(reverse('backoffice_design_state') + '?' + query).status_code, 400)

    def test_successful_draft_does_not_change_public_theme_and_stale_write_keeps_it(self):
        before = self.client.get(reverse('design_theme_css')).content
        value = defaults()
        value['values']['button-radius'] = 22
        saved = self.save(value)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get(reverse('design_theme_css')).content, before)
        self.assertEqual(self.save().status_code, 409)
        self.assertEqual(DesignDraft.objects.get(owner=self.owner).value['values']['button-radius'], 22)
        published = self.post('publish', {'draft_revision': 1, 'base_version': 0,
                                          'reason': 'Rounded controls', 'confirmed': True})
        self.assertEqual(published.status_code, 200)
        css = self.client.get(reverse('design_theme_css'))
        self.assertIn(b'--dc-button-radius:22px;', css.content)
        self.assertNotIn(b'Rounded controls', css.content)
        self.assertNotIn(b'design-owner', css.content)
        self.assertIn('no-store', css['Cache-Control'])

    def test_database_unavailable_theme_falls_back_without_public_error(self):
        with patch('core.design_views.service.read_published', side_effect=DatabaseError('not migrated')):
            response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_workspace_design_entry_changes_only_when_flag_enabled(self):
        set_flag('backoffice_course_workspace', enabled=True, reason='Workspace navigation')
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertContains(home, reverse('backoffice_design'))
        self.assertContains(home, 'Dizaynni ochish')
        set_flag('backoffice_design_workspace', enabled=False, reason='Disable design navigation')
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertContains(home, reverse('backoffice_brand'))
        self.assertNotContains(home, reverse('backoffice_design'))
