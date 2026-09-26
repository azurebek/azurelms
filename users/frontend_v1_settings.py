"""Settings presentation and V1 form snapshots, not AI or quota policy."""

import json

from django.db import transaction
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac

from core.flags import flag_enabled
from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from .models import CustomUser


PREFERENCES = (
    ('ai_tone', 'Javob uslubi', 'update_ai_tone', lambda: CustomUser.AI_TONE_CHOICES),
    ('ai_model', 'AI modeli', 'update_ai_model', CustomUser.effective_ai_model_choices),
    ('ai_web_search_effort', 'Web qidiruv', 'update_ai_web_search_effort', CustomUser.effective_ai_web_search_effort_choices),
)


def _sign_revision(user, action, fact_id, state):
    return salted_hmac('frontend-v1-settings', json.dumps(
        [user.pk, action, fact_id, state], default=str, ensure_ascii=False,
    ), algorithm='sha256').hexdigest()


def settings_revision(user, action, fact_id=None, *, lock=False, snapshot=None):
    """Opaque, per-user/action snapshot; no private fact text in HTML tokens."""
    from messenger.models import AIMemoryFact, AILongTermMemory

    if action.startswith('ai_'):
        state = [getattr(user, action), user.ai_preferences_version]
    else:
        facts = AIMemoryFact.objects.filter(user=user, status=AIMemoryFact.STATUS_ACTIVE)
        if lock:
            facts = facts.select_for_update()
        if fact_id is not None:
            facts = facts.filter(pk=fact_id)
        state = list(facts.order_by('pk').values_list('pk', 'value', 'updated_at'))
        if action == 'clear':
            legacy = AILongTermMemory.objects.filter(user=user)
            if lock:
                legacy = legacy.select_for_update()
            legacy_row = legacy.values_list('pk', 'learned_facts').first()
            if snapshot is not None:
                snapshot.update(fact_ids=[row[0] for row in state], legacy_ids=[legacy_row[0]] if legacy_row else [])
            state.append((legacy_row[1] or '').strip() if legacy_row else '')
    return _sign_revision(user, action, fact_id, state)


def settings_navigation(section):
    account_on = flag_enabled('frontend_v1_account')
    settings_on = flag_enabled('frontend_v1_settings')
    return [dict(url=reverse(name), label=label, active=key == section, legacy=not enabled)
            for key, name, label, enabled in (
                ('profile', 'profile', 'Profil', account_on),
                ('account', 'settings_account', 'Hisob', account_on),
                ('privacy', 'settings_privacy', 'Maxfiylik', settings_on),
                ('billing', 'settings_billing', 'To‘lov', settings_on),
                ('capabilities', 'settings_capabilities', 'Imkoniyatlar', settings_on),
            )]


class SettingsV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = 'frontend_v1_settings'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.frontend_v1_enabled:
            return context
        if self.request.user.is_staff and flag_enabled('frontend_v1_teacher'):
            context.update(teacher_v1_navigation('teacher_dashboard'))
            context['frontend_v1_title'] = self.frontend_v1_title
        context['settings_tabs'] = settings_navigation(self.settings_section)
        user = self.request.user
        if self.settings_section == 'capabilities':
            context['preferences'] = [dict(
                name=name, label=label, url=reverse(url_name), choices=choices(),
                value=getattr(user, name), saved=getattr(user, name),
                saved_label=dict(choices()).get(getattr(user, name), 'Hozir ruxsat etilmagan tanlov'),
                revision=settings_revision(user, name),
                available=getattr(user, name) in dict(choices()),
            ) for name, label, url_name, choices in PREFERENCES]
        return context

    def render_to_response(self, context, **kwargs):
        # Privacy's canonical view builds/maintains facts after super context.
        if self.frontend_v1_enabled and self.settings_section == 'privacy':
            user = self.request.user
            context['toggle_revision'] = settings_revision(user, 'ai_memory_enabled')
            # Sign exactly the displayed snapshot, not a later DB reread. Also
            # avoids two queries per fact on long privacy pages.
            facts = context['memory_revision_facts']
            state = [(fact.pk, fact.value, fact.updated_at) for fact in sorted(facts, key=lambda item: item.pk)]
            context['clear_revision'] = _sign_revision(user, 'clear', None, [*state, context['legacy_memory_text']])
            for group in context['memory_groups']:
                for fact in group['facts']:
                    state = [(fact.pk, fact.value, fact.updated_at)]
                    fact.archive_revision = _sign_revision(user, 'archive', fact.pk, state)
                    fact.reject_revision = _sign_revision(user, 'reject', fact.pk, state)
        return super().render_to_response(context, **kwargs)


class SettingsWriteGuard:
    """Opt-in V1 browser form guard; existing JSON/legacy clients stay compatible.

    This serializes V1 forms, not every AI/legacy writer. Canonical endpoint
    validation and field-only saves remain authoritative after this check.
    """
    settings_action = None

    def dispatch(self, request, *args, **kwargs):
        revision = request.POST.get('settings_revision', '')
        if request.method != 'POST' or (not revision and request.POST.get('frontend_v1_settings') != '1'):
            return super().dispatch(request, *args, **kwargs)
        action = self.settings_action
        with transaction.atomic():
            request.user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            error = None
            status = 409
            snapshot = {}
            if not constant_time_compare(revision, settings_revision(request.user, action, kwargs.get('fact_id'), lock=True, snapshot=snapshot)):
                error = 'Ma’lumot boshqa oynada o‘zgargan yoki forma eskirgan. Holatni yangilang; bu amal bajarilmadi.'
            elif action in ('archive', 'reject', 'clear') and request.POST.get('confirm_change') != 'yes':
                error, status = 'Amalni bajarish uchun tasdiq belgisini qo‘ying. Hech narsa o‘zgarmadi.', 400
            else:
                for name, _, _, choices in PREFERENCES:
                    if action == name and request.POST.get(name, '').strip() not in dict(choices()):
                        error, status = 'Bu tanlov hozir ruxsat etilmagan. Holatni yangilab, mavjud variantni tanlang.', 400
            if error:
                from .views import AIMemoryListView, SettingsCapabilitiesView
                is_preference = action in {item[0] for item in PREFERENCES}
                view = SettingsCapabilitiesView() if is_preference else AIMemoryListView()
                view.setup(request)
                # A submitted V1 form remains intelligible after renderer rollback.
                view.frontend_v1_enabled = True
                context = view.get_context_data()
                context.update(settings_error=error, settings_refresh_url=reverse(
                    'settings_capabilities' if is_preference else 'settings_privacy'))
                if is_preference:
                    for pref in context['preferences']:
                        if pref['name'] == action:
                            pref.update(value=request.POST.get(action, ''), revision=revision, unsaved=True)
                return view.render_to_response(context, status=status)
            if action == 'clear':
                request._settings_memory_snapshot = snapshot
            return super().dispatch(request, *args, **kwargs)
