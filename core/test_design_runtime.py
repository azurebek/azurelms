"""Published design delivery stays public, read-only and separate from drafts."""
from pathlib import Path
import re
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.design_models import DesignDraft, DesignOperation, DesignPreset, DesignState, DesignVersion
from core.design_schema import compile_css, defaults
from core.design_service import execute
from core.flags import set_flag
from frontend.models import SiteSettings


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class DesignRuntimeTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            'runtime-theme-owner', 'runtime-theme-owner@example.test', is_staff=True, is_superuser=True,
        )
        set_flag('backoffice_design_workspace', enabled=True, reason='Synthetic runtime theme test')

    def shell(self, name='frontend_v1/base.html', **context):
        return render_to_string(name, {'site_settings': SiteSettings(), **context})

    def save_draft(self, value, *, revision=0, base_version=0):
        return execute(self.owner, 'save_draft', str(uuid4()), {
            'value': value, 'draft_revision': revision, 'base_version': base_version,
        })

    def publish(self, value):
        saved = self.save_draft(value)
        return execute(self.owner, 'publish', str(uuid4()), {
            'draft_revision': saved['result']['draft_revision'], 'base_version': 0,
            'reason': 'PRIVATE owner publication reason', 'confirmed': True,
        })

    def test_both_shells_load_published_then_role_adapter_after_page_css(self):
        for base, block in (('frontend_v1/base.html', 'extra_head'), ('base.html', 'extra_css')):
            with self.subTest(base=base):
                template = Template('{% extends "' + base + '" %}{% block ' + block + ' %}'
                                    '<style data-page-style>.page { color: inherit; }</style>{% endblock %}')
                html = template.render(Context({'site_settings': SiteSettings()}))
                self.assertLess(html.index('data-page-style'), html.index('data-design-published'))
                self.assertLess(html.index('data-design-published'), html.index('data-design-runtime'))
                self.assertIn(reverse('design_theme_css'), html)
                self.assertIn('backoffice/design-runtime.css', html)
                self.assertEqual(html.count('media="screen"'), 2)

    def test_flag_off_removes_both_links_and_public_projection_without_deleting_state(self):
        value = defaults()
        value['values']['button-radius'] = 20
        self.publish(value)
        set_flag('backoffice_design_workspace', enabled=False, reason='Synthetic rollback')
        for base in ('frontend_v1/base.html', 'base.html'):
            self.assertNotIn('data-design-published', self.shell(base))
            self.assertNotIn('data-design-runtime', self.shell(base))
        response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertEqual(DesignState.objects.get(pk=1).current_version.number, 1)

    def test_flag_read_failure_and_explicit_studio_opt_out_keep_static_shells(self):
        from aicontrol.models import FeatureFlag
        with patch.object(FeatureFlag.objects, 'filter', side_effect=DatabaseError('unavailable')):
            self.assertNotIn('data-design-published', self.shell())
            self.assertEqual(self.client.get(reverse('design_theme_css')).content, b'')
        self.assertNotIn('data-design-published', self.shell(design_theme_disabled=True))

    def test_initial_public_reads_and_template_render_do_not_seed_design_records(self):
        with CaptureQueriesContext(connection) as queries:
            self.shell()
            self.shell('base.html')
            response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), compile_css(defaults()))
        writes = [query['sql'] for query in queries
                  if query['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE'))]
        self.assertEqual(writes, [])
        for model in (DesignState, DesignVersion, DesignDraft, DesignPreset, DesignOperation):
            self.assertFalse(model.objects.exists(), model.__name__)

    def test_public_stylesheet_reads_published_snapshot_never_newer_private_draft(self):
        published = defaults()
        published['values'].update({'button-radius': 20, 'field-radius': 10, 'card-radius': 24})
        self.publish(published)
        draft = defaults()
        draft['values']['button-radius'] = 4
        self.save_draft(draft, revision=1, base_version=1)
        execute(self.owner, 'save_preset', str(uuid4()), {
            'name': 'PRIVATE personal preset', 'value': draft,
        })
        self.client.logout()
        response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.status_code, 200)
        css = response.content.decode()
        self.assertEqual(css, compile_css(published))
        self.assertIn('--dc-button-radius:20px;', css)
        self.assertNotIn('--dc-button-radius:4px;', css)
        for private in ('PRIVATE', self.owner.username, self.owner.email, 'draft', 'operation'):
            self.assertNotIn(private, css)
        self.assertIn('text/css', response['Content-Type'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('no-store', response['Cache-Control'])

    def test_rollback_is_visible_on_next_public_read_and_preserves_brand(self):
        brand = SiteSettings.objects.create(brand_name='Retained brand', logo_mark_text='RB')
        published = defaults()
        published['values']['button-radius'] = 20
        self.publish(published)
        execute(self.owner, 'rollback', str(uuid4()), {
            'target_version': 0, 'base_version': 1,
            'reason': 'Restore readable factory theme', 'confirmed': True,
        })
        response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.content.decode(), compile_css(defaults()))
        self.assertEqual(DesignState.objects.get(pk=1).current_version.number, 2)
        brand.refresh_from_db()
        self.assertEqual((brand.brand_name, brand.logo_mark_text), ('Retained brand', 'RB'))

    def test_missing_theme_tables_fall_back_to_safe_defaults(self):
        with patch.object(DesignState.objects, 'select_related', side_effect=DatabaseError('missing table')):
            response = self.client.get(reverse('design_theme_css'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), compile_css(defaults()))
        self.assertFalse(DesignState.objects.exists())


class DesignRuntimeContractTests(SimpleTestCase):
    def test_independent_component_tokens_do_not_change_other_role_or_user_mode(self):
        value = defaults()
        value['values'].update({'button-radius': 20, 'field-radius': 10, 'card-radius': 24,
                               'bubble-radius': 8, 'text-md': 16})
        css = compile_css(value)
        for declaration in ('--dc-button-radius:20px;', '--dc-field-radius:10px;',
                            '--dc-card-radius:24px;', '--dc-bubble-radius:8px;', '--az-text-md:1rem;'):
            self.assertIn(declaration, css)
        self.assertTrue(css.startswith('@media screen{'))
        self.assertIn(':root:not([data-theme="dark"])', css)
        self.assertIn(':root[data-theme="dark"]', css)
        self.assertNotIn('color-scheme:', css)
        self.assertNotIn('--az-radius-round:', css)

    def test_explicit_text_aliases_reach_workspace_titles_without_replacing_unset_baselines(self):
        base_css = compile_css(defaults())
        for role in ('text-title', 'text-xl', 'text-lg', 'text-md', 'text-sm', 'text-xs'):
            self.assertNotIn(f'--dc-{role}:', base_css)
        value = defaults()
        value['values'].update({'text-title': 36, 'text-xl': 24, 'text-lg': 20,
                               'text-md': 18, 'text-sm': 16, 'text-xs': 14})
        css = compile_css(value)
        for role, size in (('text-title', '2.25'), ('text-xl', '1.5'), ('text-lg', '1.25'),
                           ('text-md', '1.125'), ('text-sm', '1'), ('text-xs', '0.875')):
            self.assertIn(f'--az-{role}:{size}rem;', css)
            self.assertIn(f'--dc-{role}:{size}rem;', css)

        # Literal workspace sizes otherwise hide the public typography tokens.
        # Both main entry titles and the actual lesson prose must be adapters.
        runtime = (Path(__file__).resolve().parent.parent / 'static/backoffice/design-runtime.css').read_text(encoding='utf-8')
        self.assertIn('.ws-page-head h1 { font-size: var(--dc-text-title, clamp(27px, 2.4vw, 34px))', runtime)
        self.assertIn('.ws-page-head h1 { font-size: var(--dc-text-title, 28px)', runtime)
        self.assertIn('.ws-course-heading h1 { font-size: var(--dc-text-title, clamp(22px, 2vw, 29px))', runtime)
        self.assertIn('.ws-section-head h2 { font-size: var(--dc-text-lg, 18px)', runtime)
        self.assertIn('.v1-lesson-prose,.ws-prose', runtime)
        self.assertNotIn('.f-study-content', runtime)
        self.assertIn('.ws-field textarea { min-height: max(160px, var(--dc-field-height, 44px))', runtime)

    def test_projection_is_screen_only_and_has_no_unset_optional_properties_or_vendor_rules(self):
        path = Path(__file__).resolve().parent.parent / 'static/backoffice/design-runtime.css'
        css = path.read_text(encoding='utf-8')
        clean = re.sub(r'/\*.*?\*/', '', css, flags=re.S).strip()
        self.assertTrue(clean.startswith('@media screen {'))
        depth = 0
        for position, character in enumerate(clean):
            if character == '{':
                depth += 1
            elif character == '}':
                depth -= 1
                if depth == 0:
                    self.assertEqual(clean[position + 1:].strip(), '')
        self.assertEqual(depth, 0)
        # An omitted custom property cannot fall through to an earlier CSS
        # declaration: it resets at computed-value time. Always give a fallback.
        self.assertEqual(re.findall(r'var\(--dc-[a-z-]+\)', clean), [])
        self.assertNotIn('!important', clean)
        self.assertNotIn('.ck-editor', clean)
        self.assertNotIn('color-scheme:', clean)
        self.assertIn('--paper: var(--az-canvas,', clean)
        self.assertIn('--azure: var(--az-action,', clean)
