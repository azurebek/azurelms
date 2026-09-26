"""Real auth flow parity with a locmem mailbox; no SMTP or provider calls."""
from datetime import datetime, timedelta
from urllib.parse import quote
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.flags import flag_by_slug, set_flag
from messenger.models import ChatRoom, Message, SmartFormSession
from users.models import UserOnboarding

User = get_user_model()
PASSWORD = 'Local-Olive!River492'
NEXT = '/courses/7/?cohort=3&tab=materials'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('auth-existing', 'existing@example.test', PASSWORD)

    def setUp(self):
        set_flag('frontend_v1_auth', enabled=True, reason='Auth V1 regression')

    def register_payload(self, **extra):
        return dict(first_name='Dilnoza', last_name='Karimova', email='new-auth@example.test',
                    password1=PASSWORD, password2=PASSWORD, **extra)

    def reset_url(self, user=None):
        user = user or self.user
        return reverse('password_reset_confirm', args=[
            urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)])

    def test_default_off_and_all_six_routes_on_off(self):
        self.assertFalse(flag_by_slug('frontend_v1_auth').default)
        paths = [
            ('register', (), 'auth_register', 'register'),
            ('onboarding_choice', (), 'auth_onboarding', 'onboarding_choice'),
            ('password_reset', (), 'auth_reset', 'password_reset_form'),
            ('password_reset_done', (), 'auth_reset_done', 'password_reset_done'),
            ('password_reset_confirm', ('bad', 'bad'), 'auth_reset_confirm', 'password_reset_confirm'),
            ('password_reset_complete', (), 'auth_reset_complete', 'password_reset_complete'),
        ]
        for enabled in (True, False):
            set_flag('frontend_v1_auth', enabled=enabled, reason='Renderer parity')
            for name, args, v1, old in paths:
                with self.subTest(enabled=enabled, route=name):
                    self.client.logout()
                    if name == 'onboarding_choice':
                        self.client.force_login(self.user)
                    response = self.client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, f'frontend_v1/{v1}.html' if enabled else f'registration/{old}.html')
                    if enabled:
                        self.assertIn('no-store', response['Cache-Control'])
                        self.assertNotContains(response, 'Enter the same password')
                        for unwanted in ('/_preview/', 'data-fixture', 'preview-token', 'static/js/app.js', 'base_public.html'):
                            self.assertNotContains(response, unwanted)

    def test_auth_and_learning_flags_select_login_independently(self):
        for auth, learning in ((False, False), (True, False), (False, True), (True, True)):
            set_flag('frontend_v1_auth', enabled=auth, reason='Auth independence')
            set_flag('frontend_v1_learning', enabled=learning, reason='Learning independence')
            self.assertTemplateUsed(self.client.get(reverse('login')),
                                    'frontend_v1/login.html' if auth or learning else 'registration/login.html')

    def test_register_native_success_canonical_identity_and_safe_next(self):
        response = self.client.post(reverse('register'), self.register_payload(
            next=NEXT, is_staff='1', total_xp='999', username='injected'))
        self.assertRedirects(response, reverse('onboarding_choice') + '?next=' + quote(NEXT, safe=''), fetch_redirect_response=False)
        user = User.objects.get(email='new-auth@example.test')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(user.username, 'new-auth')
        self.assertFalse(user.is_staff)
        self.assertEqual(user.total_xp, 0)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertFalse(UserOnboarding.objects.filter(user=user).exists())
        page = self.client.get(response.url)
        self.assertContains(page, '/courses/7/?cohort=3&amp;tab=materials')
        self.assertContains(page, 'data-onboarding-skip')

    def test_register_validation_retains_bound_text_but_not_password(self):
        data = self.register_payload()
        data.update(first_name='<script>alert(1)</script>', password2='different')
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'frontend_v1/auth_register.html')
        self.assertContains(response, 'data-form-errors')
        self.assertContains(response, 'data-auth-unsaved')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, f'value="{PASSWORD}"')
        self.assertNotContains(response, 'value="different"')
        self.assertFalse(User.objects.filter(email=data['email']).exists())

    def test_duplicate_email_and_weak_password_use_canonical_errors(self):
        data = self.register_payload()
        data.update(email='EXISTING@example.test', password1='123', password2='123')
        response = self.client.post(reverse('register'), data)
        self.assertIn('email', response.context['form'].errors)
        self.assertIn('password1', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_closed_get_post_and_authenticated_redirect(self):
        set_flag('public_registration', enabled=False, reason='Closed test')
        for method in (self.client.get, self.client.post):
            response = method(reverse('register'), {'next': NEXT})
            self.assertTemplateUsed(response, 'frontend_v1/auth_register_closed.html')
            self.assertNotContains(response, 'name="password1"')
            self.assertContains(response, '?next=' + quote(NEXT, safe=''))
            self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(User.objects.count(), 1)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post(reverse('register'), self.register_payload()), reverse('dashboard'), fetch_redirect_response=False)

    def test_register_and_onboarding_reject_external_next(self):
        for target in ('https://outside.example/exit', '//outside.example/exit', 'javascript:alert(1)'):
            response = self.client.get(reverse('register'), {'next': target})
            self.assertEqual(response.context['next'], '')
            self.client.force_login(self.user)
            page = self.client.get(reverse('onboarding_choice'), {'next': target})
            self.assertEqual(page.context['next'], '')
            self.assertContains(page, f'href="{reverse("dashboard")}" data-onboarding-skip')
            self.client.logout()

    def test_register_csrf_and_onboarding_auth_post_boundaries(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse('register'), self.register_payload()).status_code, 403)
        self.assertEqual(strict.post(reverse('password_reset'), {'email': 'existing@example.test'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('onboarding_choice')).status_code, 302)
        strict.force_login(self.user)
        self.assertEqual(strict.get(reverse('start_smart_onboarding')).status_code, 405)
        self.assertEqual(strict.post(reverse('start_smart_onboarding')).status_code, 403)
        self.assertEqual(ChatRoom.objects.count(), 0)

    def test_onboarding_get_is_read_only_and_context_claim_is_conditional(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('onboarding_choice'))
        self.assertContains(response, 'AI misol va izohlarda')
        self.assertContains(response, reverse('start_smart_onboarding'))
        self.assertFalse(UserOnboarding.objects.filter(user=self.user).exists())
        self.assertEqual(SmartFormSession.objects.count(), 0)
        User.objects.filter(pk=self.user.pk).update(ai_memory_enabled=False)
        self.assertNotContains(self.client.get(reverse('onboarding_choice')), 'AI misol va izohlarda')

    def test_onboarding_explicit_post_uses_and_reuses_canonical_room(self):
        self.client.force_login(self.user)
        first = self.client.post(reverse('start_smart_onboarding'))
        second = self.client.post(reverse('start_smart_onboarding'))
        self.assertEqual(first.url, second.url)
        self.assertEqual(SmartFormSession.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertTrue(Message.objects.get().is_ai_response)
        self.assertEqual(list(ChatRoom.objects.get().participants.all()), [self.user])

    def test_reset_request_known_unknown_inactive_unusable_have_same_receipt(self):
        User.objects.create_user('inactive', 'inactive@example.test', PASSWORD, is_active=False)
        User.objects.create_user('unusable', 'unusable@example.test', None)
        for email in ('existing@example.test', 'unknown@example.test', 'inactive@example.test', 'unusable@example.test'):
            response = self.client.post(reverse('password_reset'), {'email': email}, follow=True)
            self.assertEqual(response.redirect_chain, [(reverse('password_reset_done'), 302)])
            self.assertContains(response, 'Bu sahifa xat yetib borganini tasdiqlamaydi.')
            self.assertNotContains(response, email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['existing@example.test'])
        self.assertIn('/users/password-reset-confirm/', mail.outbox[0].body)

    def test_reset_invalid_email_stays_bound_and_no_mail(self):
        response = self.client.post(reverse('password_reset'), {'email': 'not-email'})
        self.assertContains(response, 'value="not-email"')
        self.assertContains(response, 'data-form-errors')
        self.assertContains(response, 'data-auth-unsaved')
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_keeps_django_anti_enumeration_and_no_delivery_claim(self):
        with patch('django.core.mail.EmailMultiAlternatives.send', side_effect=OSError('Synthetic offline SMTP')):
            response = self.client.post(reverse('password_reset'), {'email': self.user.email}, follow=True)
        self.assertEqual(response.redirect_chain, [(reverse('password_reset_done'), 302)])
        self.assertContains(response, 'xat yetib borganini tasdiqlamaydi')
        self.assertNotContains(response, 'Havola yuborildi')

    def test_reset_token_round_trip_password_change_and_one_use_receipt(self):
        link = self.reset_url()
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/set-password/', response.url)
        page = self.client.get(response.url)
        self.assertTrue(page.context['validlink'])
        self.assertTemplateUsed(page, 'frontend_v1/auth_reset_confirm.html')
        self.assertNotContains(page, 'Enter the same password')
        changed = self.client.post(response.url, {'new_password1': PASSWORD + '!next', 'new_password2': PASSWORD + '!next'}, follow=True)
        self.assertContains(changed, 'Parolingiz yangilandi.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD + '!next'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertNotIn('_password_reset_token', self.client.session)
        self.assertNotContains(self.client.get(reverse('password_reset_complete')), 'Parolingiz yangilandi.')
        reused = self.client.get(link)
        self.assertFalse(reused.context['validlink'])
        self.assertNotContains(reused, 'name="new_password1"')

    def test_reset_weak_mismatched_values_do_not_change_password_or_echo_it(self):
        response = self.client.get(self.reset_url())
        for one, two, error_field in (('123', '123', 'new_password1'), (PASSWORD, 'different', 'new_password2')):
            page = self.client.post(response.url, {'new_password1': one, 'new_password2': two})
            self.assertIn(error_field, page.context['form'].errors)
            self.assertNotContains(page, f'value="{one}"')
            self.assertContains(page, 'data-form-errors')
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password(PASSWORD))

    def test_invalid_expired_and_foreign_session_tokens_have_no_form(self):
        link = self.reset_url()
        masked = self.client.get(link).url
        self.assertFalse(Client().get(masked).context['validlink'])
        for args in (('bad', 'bad'), (urlsafe_base64_encode(force_bytes(999999)), 'bad')):
            page = self.client.get(reverse('password_reset_confirm', args=args))
            self.assertFalse(page.context['validlink'])
            self.assertNotContains(page, 'name="new_password1"')
        with override_settings(PASSWORD_RESET_TIMEOUT=1), patch.object(default_token_generator, '_now', return_value=datetime.now() + timedelta(seconds=20)):
            self.assertFalse(self.client.get(link).context['validlink'])

    def test_reset_csrf_and_renderer_rollback_preserve_token_flow(self):
        strict = Client(enforce_csrf_checks=True)
        masked = strict.get(self.reset_url()).url
        self.assertEqual(strict.post(masked, {'new_password1': PASSWORD, 'new_password2': PASSWORD}).status_code, 403)
        set_flag('frontend_v1_auth', enabled=False, reason='In-flight rollback')
        page = strict.get(masked)
        self.assertTemplateUsed(page, 'registration/password_reset_confirm.html')
        self.assertTrue(page.context['validlink'])

    def test_direct_completion_get_never_claims_a_password_change(self):
        response = self.client.get(reverse('password_reset_complete'))
        self.assertContains(response, 'Bu sahifani ochish parolni o‘zgartirmaydi.')
        self.assertNotContains(response, 'Parol yangilandi')

    def test_registration_telegram_reuses_real_transport_and_safe_return(self):
        response = self.client.get(reverse('register'), {'next': NEXT})
        self.assertContains(response, 'data-telegram-auth')
        self.assertContains(response, '/static/frontend_v1/js/login.js')
        self.assertContains(response, '?next=' + quote(NEXT, safe=''))
        self.assertNotContains(response, 'setInterval')
