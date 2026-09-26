"""Real settings integration, isolated DB and no external provider calls."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.flags import flag_by_slug, set_flag
from messenger.models import AIMemoryFact, AIMemoryTrace, AILongTermMemory
from .frontend_v1_settings import settings_revision

User = get_user_model()
ROUTES = ('settings_privacy', 'settings_billing', 'settings_capabilities')


class SettingsV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('settings-v1', 'settings-v1@example.test', 'Local-only-test-43', total_xp=34)
        cls.other = User.objects.create_user('settings-other', 'settings-other@example.test', 'Local-only-test-43', is_staff=True)
        cls.fact = AIMemoryFact.objects.create(user=cls.user, value='Turk tilini o‘rganaman.', confidence=0.9)
        cls.foreign = AIMemoryFact.objects.create(user=cls.other, value='OTHER PRIVATE FACT', confidence=0.9)

    def setUp(self):
        set_flag('frontend_v1_settings', enabled=True, reason='I5c regression')
        self.client.force_login(self.user)

    def payload(self, action, fact=None, **extra):
        self.user.refresh_from_db()
        return dict(frontend_v1_settings='1', settings_revision=settings_revision(self.user, action, fact), **extra)

    def test_three_routes_select_private_renderer_without_demo_or_legacy_assets(self):
        for name in ROUTES:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f'frontend_v1/{name}.html')
                self.assertIn('no-store', response['Cache-Control'])
                for target in ('profile', 'settings_account', *ROUTES):
                    self.assertContains(response, f'href="{reverse(target)}"')
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, 'static/js/app.js')
                self.assertNotContains(response, '/static/css/settings.css')

    def test_independent_default_off_and_rollback_preserve_data(self):
        self.assertFalse(flag_by_slug('frontend_v1_settings').default)
        set_flag('frontend_v1_settings', enabled=False, reason='Rollback')
        set_flag('frontend_v1_account', enabled=True, reason='Independent account')
        for name in ROUTES:
            self.assertTemplateUsed(self.client.get(reverse(name)), f'users/settings/{name.removeprefix("settings_")}.html')
        self.assertTemplateUsed(self.client.get(reverse('settings_account')), 'frontend_v1/settings_account.html')
        self.fact.refresh_from_db()
        self.assertEqual(self.fact.status, 'active')

    def test_shared_tabs_mark_current_and_only_legacy_destinations(self):
        for enabled in (False, True):
            set_flag('frontend_v1_account', enabled=enabled, reason='Tabs test')
            response = self.client.get(reverse('settings_capabilities'))
            tabs = response.context['settings_tabs']
            self.assertEqual([tab['label'] for tab in tabs if tab['active']], ['Imkoniyatlar'])
            self.assertEqual([tab['label'] for tab in tabs if tab['legacy']], [] if enabled else ['Profil', 'Hisob'])
        self.assertNotContains(self.client.get(reverse('settings_account')), 'Maxfiylik, To‘lov va Imkoniyatlar hozircha')

    def test_staff_navigation_and_canonical_unlimited_not_fake_access(self):
        set_flag('frontend_v1_teacher', enabled=True, reason='Role test')
        self.client.force_login(self.other)
        for name in ROUTES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.context['frontend_v1_workspace'], 'Ustoz maydoni')
            self.assertEqual(response.context['frontend_v1_home'], reverse('teacher_dashboard'))
        self.assertContains(response, 'Imkoniyatlar')
        self.assertContains(self.client.get(reverse('settings_billing')), 'umumiy xizmat va ta’minot cheklovlari')

    def test_auth_csrf_and_get_write_denial(self):
        self.client.logout()
        for name in ROUTES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        endpoints = [('update_ai_tone', {}), ('ai_memory_toggle', {}), ('ai_memory_clear', {}),
                     ('ai_memory_archive', {'fact_id': self.fact.pk}), ('ai_memory_reject', {'fact_id': self.fact.pk})]
        for name, args in endpoints:
            self.assertEqual(client.get(reverse(name, kwargs=args)).status_code, 405)
            self.assertEqual(client.post(reverse(name, kwargs=args), {}).status_code, 403)

    def test_three_preference_posts_are_field_only_and_return_to_same_section(self):
        for action, endpoint, value in (
            ('ai_tone', 'update_ai_tone', 'formal'),
            ('ai_model', 'update_ai_model', User.effective_ai_model_choices()[-1][0]),
            ('ai_web_search_effort', 'update_ai_web_search_effort', 'medium'),
        ):
            response = self.client.post(reverse(endpoint), self.payload(action, **{action: value, 'total_xp': 900, 'is_staff': 'true'}), follow=True)
            self.assertEqual(response.redirect_chain, [(reverse('settings_capabilities'), 302)])
            self.user.refresh_from_db()
            self.assertEqual(getattr(self.user, action), value)
            self.assertEqual(self.user.total_xp, 34)
            self.assertFalse(self.user.is_staff)
        self.other.refresh_from_db()
        self.assertEqual(self.other.ai_tone, 'friendly')

    @override_settings(AI_FREE_TIER_MODE=True, GEMINI_FREE_MODEL_ALLOWLIST=('gemini-3.1-flash-lite',))
    def test_policy_choices_and_invalid_saved_selection_are_honest(self):
        User.objects.filter(pk=self.user.pk).update(ai_model='retired-model')
        response = self.client.get(reverse('settings_capabilities'))
        self.assertContains(response, 'Oldingi tanlov hozirgi ruxsatli variantlar orasida yo‘q')
        self.assertNotContains(response, 'value="retired-model"')
        self.assertNotContains(response, 'value="heavy"')
        self.assertContains(response, 'qidiruv xizmatini yoqmaydi')
        response = self.client.post(reverse('update_ai_model'), self.payload('ai_model', ai_model='retired-model'))
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'frontend_v1/settings_capabilities.html')
        self.assertContains(response, 'data-settings-unsaved', status_code=400)

    def test_stale_preference_bound_value_no_success_and_rollback_guard(self):
        payload = self.payload('ai_tone', ai_tone='brief')
        User.objects.filter(pk=self.user.pk).update(ai_tone='formal')
        set_flag('frontend_v1_settings', enabled=False, reason='In-flight rollback')
        response = self.client.post(reverse('update_ai_tone'), payload)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'value="brief" selected', status_code=409)
        self.assertContains(response, 'data-settings-unsaved', status_code=409)
        self.assertNotContains(response, 'uslubi yangilandi', status_code=409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_tone, 'formal')

    def test_missing_tampered_cross_user_cross_action_tokens_rejected(self):
        for token in ('', 'bad', settings_revision(self.other, 'ai_tone'), settings_revision(self.user, 'ai_model')):
            response = self.client.post(reverse('update_ai_tone'), dict(frontend_v1_settings='1', settings_revision=token, ai_tone='formal'))
            self.assertEqual(response.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_tone, 'friendly')

    def test_legacy_and_json_clients_keep_existing_contract(self):
        response = self.client.post(reverse('update_ai_tone'), {'ai_tone': 'formal'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json()['ai_tone'], 'formal')
        self.assertRedirects(self.client.post(reverse('ai_memory_toggle'), {'ai_memory_enabled': '0'}), reverse('settings_privacy'))

    def test_privacy_scoped_and_fact_text_escaped(self):
        self.fact.value = '<script>not trusted</script>'
        self.fact.save()
        response = self.client.get(reverse('settings_privacy'))
        self.assertContains(response, '&lt;script&gt;not trusted&lt;/script&gt;')
        self.assertNotContains(response, 'OTHER PRIVATE FACT')
        self.assertContains(response, 'name="confirm_change" value="yes" required')
        self.assertNotContains(response, self.fact.value)

    def test_toggle_preserves_facts_and_stale_toggle_cannot_reverse_new_choice(self):
        payload = self.payload('ai_memory_enabled', ai_memory_enabled='0')
        self.assertRedirects(self.client.post(reverse('ai_memory_toggle'), payload), reverse('settings_privacy'))
        response = self.client.post(reverse('ai_memory_toggle'), {**payload, 'ai_memory_enabled': '1'})
        self.assertEqual(response.status_code, 409)
        self.fact.refresh_from_db(); self.user.refresh_from_db()
        self.assertEqual(self.fact.status, 'active')
        self.assertFalse(self.user.ai_memory_enabled)

    def test_rendered_privacy_revisions_match_displayed_snapshot_and_submit(self):
        AILongTermMemory.objects.create(user=self.user, learned_facts='  Eski xotira  ')
        response = self.client.get(reverse('settings_privacy'))
        self.user.refresh_from_db()
        shown = response.context['memory_groups'][0]['facts'][0]
        for action in ('archive', 'reject'):
            self.assertEqual(getattr(shown, action + '_revision'), settings_revision(self.user, action, shown.pk))
        self.assertEqual(response.context['toggle_revision'], settings_revision(self.user, 'ai_memory_enabled'))
        self.assertEqual(response.context['clear_revision'], settings_revision(self.user, 'clear'))
        # Use the revision actually emitted by the view, not a test-only token.
        result = self.client.post(reverse('ai_memory_clear'), {
            'frontend_v1_settings': '1', 'settings_revision': response.context['clear_revision'],
            'confirm_change': 'yes',
        })
        self.assertRedirects(result, reverse('settings_privacy'))
        self.fact.refresh_from_db()
        self.assertEqual(self.fact.status, 'archived')

    def test_archive_and_reject_require_confirmation_and_use_repository_trace(self):
        for action in ('archive', 'reject'):
            fact = AIMemoryFact.objects.create(user=self.user, value=action, fingerprint=action, confidence=0.9)
            url = reverse('ai_memory_' + action, args=[fact.pk])
            payload = self.payload(action, fact.pk)
            self.assertEqual(self.client.post(url, payload).status_code, 400)
            fact.refresh_from_db(); self.assertEqual(fact.status, 'active')
            self.assertRedirects(self.client.post(url, {**payload, 'confirm_change': 'yes'}), reverse('settings_privacy'))
            fact.refresh_from_db()
            self.assertEqual(fact.status, 'archived' if action == 'archive' else 'rejected')
            self.assertTrue(AIMemoryTrace.objects.filter(user=self.user, fact=fact, metadata__action='user_' + action).exists())
            self.assertEqual(self.client.post(url, {**payload, 'confirm_change': 'yes'}).status_code, 409)

    def test_fact_revision_cannot_move_to_other_fact_or_other_user(self):
        payload = self.payload('archive', self.fact.pk, confirm_change='yes')
        for pk in (self.foreign.pk, 999999):
            self.assertEqual(self.client.post(reverse('ai_memory_archive', args=[pk]), payload).status_code, 409)
        self.foreign.refresh_from_db(); self.assertEqual(self.foreign.status, 'active')

    def test_changed_fact_rejected_before_archive(self):
        payload = self.payload('archive', self.fact.pk, confirm_change='yes')
        AIMemoryFact.objects.filter(pk=self.fact.pk).update(value='Yangi ma’lumot')
        self.assertEqual(self.client.post(reverse('ai_memory_archive', args=[self.fact.pk]), payload).status_code, 409)
        self.fact.refresh_from_db(); self.assertEqual(self.fact.status, 'active')

    def test_clear_archives_own_active_and_clears_legacy_not_toggle_or_others(self):
        legacy = AILongTermMemory.objects.create(user=self.user, learned_facts='Eski matn')
        response = self.client.post(reverse('ai_memory_clear'), self.payload('clear', confirm_change='yes'))
        self.assertRedirects(response, reverse('settings_privacy'))
        self.fact.refresh_from_db(); legacy.refresh_from_db(); self.foreign.refresh_from_db(); self.user.refresh_from_db()
        self.assertEqual(self.fact.status, 'archived')
        self.assertEqual(legacy.learned_facts, '')
        self.assertEqual(self.foreign.status, 'active')
        self.assertTrue(self.user.ai_memory_enabled)

    def test_clear_checks_confirmation_and_new_fact_snapshot(self):
        payload = self.payload('clear')
        self.assertEqual(self.client.post(reverse('ai_memory_clear'), payload).status_code, 400)
        new = AIMemoryFact.objects.create(user=self.user, value='Keyin kelgan fakt', fingerprint='new-fact', confidence=0.9)
        self.assertEqual(self.client.post(reverse('ai_memory_clear'), {**payload, 'confirm_change': 'yes'}).status_code, 409)
        new.refresh_from_db(); self.assertEqual(new.status, 'active')

    def test_clear_legacy_only_is_not_disabled_and_legacy_change_stales_it(self):
        self.fact.delete()
        legacy = AILongTermMemory.objects.create(user=self.user, learned_facts='Faqat eski xotira')
        response = self.client.get(reverse('settings_privacy'))
        self.assertNotContains(response, 'disabled')
        payload = self.payload('clear', confirm_change='yes')
        legacy.learned_facts = 'Yangi eski matn'; legacy.save()
        self.assertEqual(self.client.post(reverse('ai_memory_clear'), payload).status_code, 409)

    def test_billing_canonical_values_not_recomputed_and_no_writing_controls(self):
        panel = dict(blocked=False, unlimited=False, session=dict(used=73, limit=211, percent=35, remaining=138, reset_at=None), weekly=dict(used=201, limit=999, percent=20, remaining=798, reset_at=None))
        with patch('aicontrol.service.build_usage_panel', return_value=panel) as service:
            response = self.client.get(reverse('settings_billing'))
        service.assert_called_once_with(self.user)
        self.assertContains(response, 'value="35"')
        self.assertContains(response, '138 token qoldi')
        self.assertNotContains(response, 'data-settings-form')
        self.assertContains(response, 'Tiklanish vaqti hali belgilanmagan')

    def test_billing_blocked_unavailable_and_zero_are_distinct(self):
        for panel, text in ((None, 'Ko‘rsatkich hozir mavjud emas'), (dict(blocked=True), 'vaqtincha to‘xtatilgan'), (dict(unlimited=True), 'token limiti qo‘llanmaydi')):
            with patch('aicontrol.service.build_usage_panel', return_value=panel):
                response = self.client.get(reverse('settings_billing'))
            self.assertContains(response, text)
            self.assertNotContains(response, '<progress')
        with patch('aicontrol.service.build_usage_panel', return_value=dict(blocked=False, unlimited=False, session={}, weekly={})):
            response = self.client.get(reverse('settings_billing'))
        self.assertNotContains(response, '<progress')

    def test_real_blocked_allowance_and_staff_exemption(self):
        from aicontrol.models import AIUserAllowance
        AIUserAllowance.objects.create(user=self.user, is_blocked=True)
        self.assertContains(self.client.get(reverse('settings_billing')), 'vaqtincha to‘xtatilgan')
        self.client.force_login(self.other)
        self.assertContains(self.client.get(reverse('settings_billing')), 'token limiti qo‘llanmaydi')
