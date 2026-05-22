from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class _ExamBaseView(LoginRequiredMixin, TemplateView):
    active_nav = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_nav"] = self.active_nav
        return context


class ExamCenterView(_ExamBaseView):
    template_name = "exam/center.html"
    active_nav = "exam_center"


class ExamHistoryView(_ExamBaseView):
    template_name = "exam/history.html"
    active_nav = "exam_history"


class ExamListeningView(_ExamBaseView):
    template_name = "exam/listening.html"
    active_nav = "exam_listening"


class ExamWritingView(_ExamBaseView):
    template_name = "exam/writing.html"
    active_nav = "exam_writing"


class ExamSpeakingView(_ExamBaseView):
    template_name = "exam/speaking.html"
    active_nav = "exam_speaking"


class ExamReviewView(_ExamBaseView):
    template_name = "exam/review.html"
    active_nav = "exam_review"
