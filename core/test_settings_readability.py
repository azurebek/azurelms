"""Unified settings disclosures keep the existing forms usable and unchanged."""

from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.models import OperationalSettings
from subscriptions.models import Plan


class SettingsHTML(HTMLParser):
    """Collect submitted controls and disclosure ancestry from rendered HTML."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.details = []
        self.detail_stack = []
        self.forms = []
        self.form = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details':
            detail = {'attrs': attrs, 'controls': [], 'text': []}
            self.details.append(detail)
            self.detail_stack.append(detail)
        if tag == 'form' and attrs.get('method', '').lower() == 'post':
            self.form = {'action': attrs.get('action', ''), 'controls': []}
            self.forms.append(self.form)
        if tag in {'input', 'textarea', 'select'} and attrs.get('name') != 'csrfmiddlewaretoken':
            control = (tag, attrs.get('name'), attrs.get('type'), attrs.get('value'),
                       'required' in attrs, attrs.get('min'), attrs.get('max'))
            if self.form is not None:
                self.form['controls'].append(control)
            for detail in self.detail_stack:
                detail['controls'].append(control)

    def handle_endtag(self, tag):
        if tag == 'details':
            self.detail_stack.pop()
        if tag == 'form':
            self.form = None

    def handle_data(self, data):
        for detail in self.detail_stack:
            detail['text'].append(data)


class SettingsReadabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_superuser(
            'settings-readable', 'settings-readable@example.test', 'testpass',
        )
        Plan.objects.create(name='Sinov tarifi', code='settings-test', price=100000, description='Sinov')

    def setUp(self):
        self.client.force_login(self.owner)

    def set_unified(self, enabled):
        FeatureFlag.objects.update_or_create(
            slug='backoffice_unified_navigation', defaults={'enabled': enabled},
        )

    def page(self, name):
        response = self.client.get(reverse(name))
        self.assertEqual(response.status_code, 200)
        return response, SettingsHTML(response.content.decode())

    def test_unified_settings_preserve_original_post_controls(self):
        for name in (
            'backoffice_runtime_settings', 'backoffice_ai_cost',
            'backoffice_ai_control', 'backoffice_ai_kill_switch',
            'backoffice_ai_circuit_reset', 'backoffice_dead_letter',
        ):
            with self.subTest(name=name):
                self.set_unified(False)
                _, legacy = self.page(name)
                self.set_unified(True)
                _, unified = self.page(name)
                self.assertEqual(legacy.forms, unified.forms)

    def test_runtime_starts_with_seven_closed_independent_tasks(self):
        self.set_unified(True)
        response, page = self.page('backoffice_runtime_settings')
        tasks = [d for d in page.details if d['attrs'].get('id', '').startswith('settings-')]
        self.assertEqual(len(tasks), 7)
        for detail in tasks:
            self.assertNotIn('open', detail['attrs'])
            names = [control[1] for control in detail['controls']]
            self.assertEqual(names.count('form_name'), 1)
            self.assertEqual(names.count('change_reason'), 1)
            self.assertEqual(names.count('confirm_change'), 1)
        self.assertContains(response, reverse('backoffice_workspace_settings'))

    def test_invalid_runtime_task_reopens_with_errors_and_keeps_state(self):
        self.set_unified(True)
        response = self.client.post(reverse('backoffice_runtime_settings'), {
            'form_name': 'checkout', 'checkout_quote_minutes': '0',
            'change_reason': '',
        })
        self.assertEqual(response.status_code, 200)
        page = SettingsHTML(response.content.decode())
        tasks = [d for d in page.details if d['attrs'].get('id', '').startswith('settings-')]
        self.assertEqual([d['attrs']['id'] for d in tasks if 'open' in d['attrs']], ['settings-checkout'])
        checkout = next(d for d in tasks if d['attrs']['id'] == 'settings-checkout')
        self.assertTrue(response.context['checkout_form'].errors)
        for errors in response.context['checkout_form'].errors.values():
            for error in errors:
                self.assertIn(str(error), ''.join(checkout['text']))
        self.assertEqual(OperationalSettings.load().checkout_quote_minutes, 30)
        self.assertFalse(SystemAuditEvent.objects.filter(action='settings.checkout.update').exists())

    def test_price_validation_reopens_its_form(self):
        self.set_unified(True)
        response = self.client.post(reverse('backoffice_ai_cost'), {})
        self.assertEqual(response.status_code, 200)
        page = SettingsHTML(response.content.decode())
        price_detail = next(d for d in page.details if any(c[1] == 'effective_from' for c in d['controls']))
        self.assertIn('open', price_detail['attrs'])
        self.assertTrue(response.context['form'].errors)
        for errors in response.context['form'].errors.values():
            for error in errors:
                self.assertIn(str(error), ''.join(price_detail['text']))

    def test_flag_failed_submission_reopens_affected_service(self):
        self.set_unified(True)
        response = self.client.post(reverse('backoffice_feature_flags'), {
            'slug': 'backoffice_design_workspace', 'enabled': 'on',
        })
        self.assertEqual(response.status_code, 200)
        page = SettingsHTML(response.content.decode())
        service = next(d for d in page.details if any(c[1] == 'slug' and c[3] == 'backoffice_design_workspace' for c in d['controls']))
        self.assertIn('open', service['attrs'])
        self.assertFalse(FeatureFlag.objects.filter(slug='backoffice_design_workspace', enabled=True).exists())

    def test_health_diagnostics_stay_available_inside_details(self):
        self.set_unified(True)
        response, page = self.page('backoffice_control')
        self.assertContains(response, 'Xizmatlar qanday ishlayapti?')
        self.assertTrue(any('Amaldagi texnik qiymatlar' in ''.join(d['text']) for d in page.details))
        self.assertTrue(any('Texnik tafsilotlar' in ''.join(d['text']) for d in page.details))
        self.assertFalse([form for form in page.forms if form['action'] != reverse('logout')])
