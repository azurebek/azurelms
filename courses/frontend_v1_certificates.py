"""Public, read-only V1 documents; issuance and publication stay canonical."""
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from core.flags import flags_enabled
from core.frontend_v1 import PLATFORM_CALM_FLAG, calm_template_names


class CertificateV1Mixin:
    @cached_property
    def certificate_renderer_flags(self):
        return flags_enabled('frontend_v1_certificates', PLATFORM_CALM_FLAG)

    @property
    def certificate_v1_enabled(self):
        return self.certificate_renderer_flags['frontend_v1_certificates']

    @property
    def platform_calm_enabled(self):
        return self.certificate_renderer_flags[PLATFORM_CALM_FLAG]

    def get_template_names(self):
        if self.certificate_v1_enabled:
            return calm_template_names(self.certificate_v1_template, enabled=self.platform_calm_enabled)
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.certificate_v1_enabled:
            context['frontend_v1_title'] = 'Sertifikat · ' + self.object.certificate_id
            context['platform_calm_v1'] = self.platform_calm_enabled
        return context

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if self.certificate_v1_enabled:
            patch_cache_control(response, private=True, no_store=True)
        return response
