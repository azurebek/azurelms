from django.shortcuts import redirect
from django.urls import reverse

class CheckOnboardingMiddleware:
    """
    Agar user login bo'lib turib, onboarding tugallanmagan bo'lsa
    har doim onboarding wizardga yuboradi.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and not profile.is_onboarded:
                onboarding_url = reverse("users:onboarding")
                allowed = {
                    onboarding_url,
                    reverse("users:logout"),
                }
                # onboardingning ichidagi htmx postlar ham shu URLga tushadi
                if request.path not in allowed and not request.path.startswith("/legal/"):
                    return redirect("users:onboarding")

        return self.get_response(request)
