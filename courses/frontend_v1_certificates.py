"""Public, read-only V1 documents; issuance and publication stay canonical."""
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from core.flags import flag_enabled


class CertificateV1Mixin:
    @cached_property
    def certificate_v1_enabled(self):
        return flag_enabled('frontend_v1_certificates')

    def get_template_names(self):
        if self.certificate_v1_enabled:
            return [self.certificate_v1_template]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.certificate_v1_enabled:
            context['frontend_v1_title'] = 'Sertifikat · ' + self.object.certificate_id
        return context

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if self.certificate_v1_enabled:
            patch_cache_control(response, private=True, no_store=True)
        return response
