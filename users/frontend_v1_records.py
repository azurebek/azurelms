"""Frozen records/support presentation; no parallel access/XP/payment rules."""
from urllib.parse import urlencode, urlsplit

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from core.flags import flag_enabled
from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from frontend.models import SiteSettings


RECORD_TABS = (("certificates", "Sertifikatlar"), ("attendance_calendar", "Davomat"),
               ("subscriptions", "Obunalar"), ("leaderboard", "Reyting"))
MONTHS = tuple(enumerate(("Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
                          "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"), 1))


def notification_target(request, value):
    """Only same-site HTTP(S)/relative destinations; never executable URLs."""
    value = (value or '').strip()
    if value and url_has_allowed_host_and_scheme(value, {request.get_host()}, require_https=request.is_secure()):
        return value
    return ''


def notification_return(request, notice_id=None):
    # Only the bounded list page survives a POST. Arbitrary next URLs never do.
    try:
        page = max(1, int(request.POST.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    return reverse('notifications') + '?' + urlencode({'page': page}) + (f'#notice-{notice_id}' if notice_id else '')


class RecordsV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = 'frontend_v1_records'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context['certificate_documents_v1'] = flag_enabled('frontend_v1_certificates')
            context['records_tabs'] = [dict(name=name, label=label, url=reverse(name)) for name, label in RECORD_TABS]
            if self.request.user.is_staff and flag_enabled('frontend_v1_teacher'):
                context.update(teacher_v1_navigation('teacher_dashboard'))
                context['frontend_v1_title'] = self.frontend_v1_title
        return context

    def render_to_response(self, context, **kwargs):
        if self.frontend_v1_enabled:
            route = self.request.resolver_match.url_name
            context['records_has_tabs'] = route in dict(RECORD_TABS)
            if route in ('attendance_calendar', 'leaderboard'):
                attendance = route == 'attendance_calendar'
                context['records_choices'] = context['attendance_cohort_choices' if attendance else 'leaderboard_cohort_choices']
                context['records_cohort'] = context['attendance_cohort' if attendance else 'leaderboard_cohort']
                selected = context['selected_attendance_cohort_id' if attendance else 'selected_leaderboard_cohort_id']
                context['records_selected_cohort'] = selected
                supplied = self.request.GET.get('cohort')
                context['records_filter_notice'] = bool(supplied and str(selected) != supplied) or any(len(self.request.GET.getlist(key)) > 1 for key in ('cohort', 'year', 'month'))
                if attendance:
                    date = context['selected_month']
                    context['records_months'] = MONTHS
                    context['records_month_label'] = dict(MONTHS)[date.month]
                    context['records_filter_notice'] |= any(self.request.GET.get(key) not in (None, str(number)) for key, number in [('year', date.year), ('month', date.month)])
            elif route == 'notifications':
                # Fixed ordering survives marking read; pagination is presentation,
                # not an operational limit on the recipient's inbox.
                page = Paginator(self.request.user.notifications.order_by('-created_at', '-id'), 20).get_page(self.request.GET.get('page'))
                for notice in page:
                    notice.v1_target = notification_target(self.request, notice.url)
                context['notice_page'] = page
            elif route == 'subscriptions':
                # The paid period, not mutable catalog/intent, selects the plan.
                context['record_enrollments'] = [dict(enrollment=item, plan=item.active_plan()) for item in context['enrollments']]
            elif route == 'help_center':
                contact = (SiteSettings.load().telegram_url or '').strip()
                try:
                    parsed = urlsplit(contact)
                    if parsed.scheme in ('http', 'https') and parsed.hostname:
                        context['records_contact_url'] = contact
                except ValueError:
                    pass
        return super().render_to_response(context, **kwargs)
