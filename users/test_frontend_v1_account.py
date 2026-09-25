"""Real ACC-01 views/forms, no demo state or live provider calls."""

from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.flags import flag_by_slug, set_flag
from .frontend_v1_account import profile_revision


class AccountV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            'account-student', 'account-student@example.test', 'Local-test-secret-49',
            first_name='O‘quvchi', bio='Haqiqiy bio', total_xp=32,
        )
        cls.other = get_user_model().objects.create_user(
            'account-other', 'account-other@example.test', 'Local-test-secret-49', is_staff=True,
        )

    def setUp(self):
        set_flag('frontend_v1_account', enabled=True, reason='ACC-01 regression')
        self.client.force_login(self.user)

    def data(self, **overrides):
        return dict(first_name='Yangi', last_name='Familiya', phone_number='+998901234567',
                    bio='Yangi bio', profile_revision=profile_revision(self.user), **overrides)

    def test_default_off_and_explicit_rollback_preserve_legacy(self):
        self.assertFalse(flag_by_slug('frontend_v1_account').default)
        set_flag('frontend_v1_account', enabled=False, reason='Rollback regression')
        for name, template in [('profile', 'users/profile.html'), ('settings_account', 'users/settings/account.html')]:
            self.assertTemplateUsed(self.client.get(reverse(name)), template)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Haqiqiy bio')

    def test_on_selects_private_shared_forms_without_legacy_assets(self):
        for name in ('profile', 'settings_account'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertTemplateUsed(response, f'frontend_v1/{name}.html')
                self.assertTemplateUsed(response, 'frontend_v1/profile_fields.html')
                self.assertTemplateUsed(response, 'frontend_v1/avatar_editor.html')
                self.assertEqual(response.context['profile_revision'], profile_revision(self.user))
                self.assertContains(response, 'account-student@example.test')
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, 'css/settings.css')
                self.assertNotContains(response, 'static/js/app.js')
                self.assertIn('no-store', response['Cache-Control'])

    def test_native_success_both_routes_stays_on_exact_surface(self):
        for name in ('profile', 'settings_account'):
            self.user.refresh_from_db()
            response = self.client.post(reverse(name), self.data(), follow=True)
            self.assertEqual(response.redirect_chain, [(reverse(name), 302)])
            self.assertContains(response, 'Yangi bio')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Yangi')

    def test_invalid_form_retains_input_and_opens_disclosure(self):
        data = self.data()
        data.update(first_name='x' * 151, bio='<script>bound input</script>')
        response = self.client.post(reverse('profile'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'v1-profile-editor" open')
        self.assertContains(response, '&lt;script&gt;bound input&lt;/script&gt;')
        self.assertContains(response, 'data-form-errors')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'O‘quvchi')

    def test_identity_role_xp_and_preferences_cannot_be_overwritten(self):
        response = self.client.post(reverse('settings_account'), self.data(
            email='attacker@example.test', username='attacker', total_xp=9999,
            is_staff=True, ai_memory_enabled=False, id=self.other.pk,
        ))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'account-student@example.test')
        self.assertEqual(self.user.username, 'account-student')
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.total_xp, 32)
        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, '')

    def test_cross_surface_stale_save_409_and_no_false_success(self):
        first = self.data()
        self.client.post(reverse('profile'), first)
        # Drain the success flash from the earlier, genuinely successful save.
        self.client.get(reverse('profile'))
        response = self.client.post(reverse('settings_account'), {**first, 'bio': 'Stale matn'})
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'Stale matn', status_code=409)
        self.assertContains(response, 'boshqa oynada', status_code=409)
        self.assertNotContains(response, 'muvaffaqiyatli yangilandi', status_code=409)
        self.assertEqual(response.context['profile_revision'], first['profile_revision'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Yangi bio')

    def test_missing_tampered_and_foreign_revision_fail_closed(self):
        for revision in ('', 'tampered', profile_revision(self.other)):
            response = self.client.post(reverse('profile'), {**self.data(), 'profile_revision': revision})
            self.assertEqual(response.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Haqiqiy bio')

    def test_non_profile_change_does_not_stale_or_overwrite(self):
        data = self.data()
        get_user_model().objects.filter(pk=self.user.pk).update(total_xp=450, ai_tone='formal')
        self.assertEqual(self.client.post(reverse('profile'), data).status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 450)
        self.assertEqual(self.user.ai_tone, 'formal')

    def test_loaded_v1_form_still_checks_revision_after_rollback(self):
        data = self.data()
        get_user_model().objects.filter(pk=self.user.pk).update(bio='Boshqa oyna')
        set_flag('frontend_v1_account', enabled=False, reason='Rollback regression')
        response = self.client.post(reverse('profile'), data)
        self.assertEqual(response.status_code, 409)
        self.assertTemplateUsed(response, 'users/profile.html')
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Boshqa oyna')

    def test_staff_keeps_teacher_workspace_and_account_title(self):
        set_flag('frontend_v1_teacher', enabled=True, reason='Teacher scope')
        self.client.force_login(self.other)
        for name, title in [('profile', 'Profil'), ('settings_account', 'Hisob')]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.context['frontend_v1_workspace'], 'Ustoz maydoni')
            self.assertEqual(response.context['frontend_v1_title'], title)
            self.assertEqual(response.context['frontend_v1_home'], reverse('teacher_dashboard'))
            self.assertNotContains(response, 'href="/users/my-courses/"')

    def test_auth_and_csrf_still_required(self):
        strict = Client(enforce_csrf_checks=True)
        for name in ('profile', 'settings_account'):
            self.assertEqual(strict.get(reverse(name)).status_code, 302)
        strict.force_login(self.user)
        for name in ('profile', 'settings_account', 'update_avatar', 'update_password'):
            self.assertEqual(strict.post(reverse(name), self.data()).status_code, 403)

    def test_safe_next_and_unchanged_settings_destinations(self):
        response = self.client.get(reverse('settings_account'))
        for name in ('profile', 'settings_privacy', 'settings_billing', 'settings_capabilities'):
            self.assertContains(response, f'href="{reverse(name)}"')
        response = self.client.post(reverse('settings_account'), self.data(next='https://elsewhere.example/'))
        self.assertRedirects(response, reverse('settings_account'))
        self.assertTemplateUsed(self.client.get(reverse('settings_capabilities')), 'users/settings/capabilities.html')

    def test_avatar_uses_canonical_validation_and_return_url(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            image = BytesIO()
            Image.new('RGB', (2, 2), 'blue').save(image, format='PNG')
            response = self.client.post(reverse('update_avatar'), {
                'avatar': SimpleUploadedFile('sample.png', image.getvalue(), content_type='image/png'),
                'next': reverse('profile'),
            })
            self.assertRedirects(response, reverse('profile'))
            self.user.refresh_from_db()
            saved = self.user.avatar.name
            self.assertTrue(saved)
            response = self.client.post(reverse('update_avatar'), {
                'avatar': SimpleUploadedFile('bad.png', b'<script>bad</script>', content_type='image/png'),
            }, follow=True)
            self.assertTemplateUsed(response, 'frontend_v1/settings_account.html')
            self.user.refresh_from_db()
            self.assertEqual(self.user.avatar.name, saved)

    def test_password_validation_and_session_survive_canonical_post(self):
        for old, new, confirm in [('wrong', 'Another-local-secret-28', 'Another-local-secret-28'),
                                  ('Local-test-secret-49', '123', '123'),
                                  ('Local-test-secret-49', 'Another-local-secret-28', 'mismatch')]:
            self.client.post(reverse('update_password'), dict(old_password=old, new_password1=new, new_password2=confirm))
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password('Local-test-secret-49'))
        response = self.client.post(reverse('update_password'), dict(
            old_password='Local-test-secret-49', new_password1='Another-local-secret-28', new_password2='Another-local-secret-28',
        ), follow=True)
        self.assertTemplateUsed(response, 'frontend_v1/settings_account.html')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Another-local-secret-28'))
        self.assertEqual(str(self.user.pk), self.client.session[SESSION_KEY])
        self.assertEqual(self.user.total_xp, 32)
        self.assertNotContains(response, 'Another-local-secret-28')
