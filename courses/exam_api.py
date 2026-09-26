"""HTTP adapters for the canonical attempt-access policy (all renderers)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.db import transaction
from django.utils.cache import patch_cache_control

from .exam_service import ExamAttemptAccessBlocked, get_accessible_exam_attempt


class ExamAPIResponseMixin:
    def dispatch(self, request, *args, **kwargs):
        try:
            response = super().dispatch(request, *args, **kwargs)
        except Http404:
            response = JsonResponse({'error': 'Imtihon yoki topshiriq topilmadi.'}, status=404)
        patch_cache_control(response, private=True, no_store=True)
        return response


class ExamRuntimeAccessMixin(ExamAPIResponseMixin, LoginRequiredMixin):
    @transaction.atomic
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                self.exam_attempt = get_accessible_exam_attempt(
                    student=request.user,
                    course_id=kwargs['course_id'],
                    exam_id=kwargs['exam_id'],
                )
                from .models import ExamAttempt
                self.exam_attempt = ExamAttempt.objects.select_for_update().get(pk=self.exam_attempt.pk)
                if self.exam_attempt.is_completed:
                    raise ExamAttemptAccessBlocked('Faol imtihon urinishi topilmadi.', code='no_attempt')
            except ExamAttemptAccessBlocked as exc:
                response = JsonResponse(
                    {'error': str(exc), 'code': exc.code},
                    status=403 if exc.code == 'not_enrolled' else 404,
                )
                patch_cache_control(response, private=True, no_store=True)
                return response
        return super().dispatch(request, *args, **kwargs)
