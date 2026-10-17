"""Owner: public da'volar dalili va o'quvchi fikrlari roziligi (PUB1.2a).

Bosh sahifa va "Biz haqimizda" statistikasi dalil bilan tasdiqlanmaguncha
saytda chiqmaydi; fikr esa egasining roziligisiz chiqmaydi. Bu sahifa holatni
ko'rsatadi va tasdiqlash/qaytarishni sabab, tasdiq va audit bilan bajaradi.
Qaror `frontend/public_claims.py`da — bu yerda faqat forma.
"""

from datetime import datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from core.access import is_control_center_owner
from frontend import public_claims
from frontend.models import Testimonial

AUDIT_ACTIONS = ("public_claim.approve", "public_claim.revoke",
                 "public_testimonial.consent", "public_testimonial.revoke")


class _ReasonForm(forms.Form):
    reason = forms.CharField(label="Sabab", max_length=240, widget=forms.Textarea(attrs={"rows": 2, "class": "lc-input"}))
    confirm = forms.BooleanField(label="Saytdagi o‘zgarishni tasdiqlayman", required=True)


class ApproveClaimForm(_ReasonForm):
    claim_key = forms.CharField(widget=forms.HiddenInput)
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    expires_on = forms.DateField(label="Qachongacha amal qiladi", widget=forms.DateInput(attrs={"type": "date", "class": "lc-input"}))
    source_url = forms.URLField(label="Manba havolasi (ixtiyoriy, https)", required=False, max_length=500,
                                widget=forms.URLInput(attrs={"class": "lc-input"}))
    evidence_note = forms.CharField(label="Dalil izohi (saytga chiqmaydi)", required=False, max_length=1000,
                                    widget=forms.Textarea(attrs={"rows": 2, "class": "lc-input"}))

    def clean_expires_on(self):
        value = self.cleaned_data["expires_on"]
        if value <= timezone.localdate():
            raise forms.ValidationError("Muddat bugundan keyin bo‘lishi kerak.")
        return value


class RevokeClaimForm(_ReasonForm):
    claim_key = forms.CharField(widget=forms.HiddenInput)
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=1)


class ConsentForm(_ReasonForm):
    testimonial_id = forms.IntegerField(widget=forms.HiddenInput)
    display_name = forms.CharField(label="Saytda ko‘rinadigan ism", required=False, max_length=100,
                                   widget=forms.TextInput(attrs={"class": "lc-input"}))
    source_reference = forms.CharField(label="Rozilik qayerda olingan", max_length=240,
                                       widget=forms.TextInput(attrs={"class": "lc-input"}))


class ConsentRevokeForm(_ReasonForm):
    testimonial_id = forms.IntegerField(widget=forms.HiddenInput)


FORMS = {
    "approve": ApproveClaimForm,
    "revoke": RevokeClaimForm,
    "consent": ConsentForm,
    "consent_revoke": ConsentRevokeForm,
}


def _apply(request, action, data):
    if action == "approve":
        expires_at = timezone.make_aware(datetime.combine(data["expires_on"], time.max))
        public_claims.approve(
            data["claim_key"], actor=request.user, reason=data["reason"], expires_at=expires_at,
            expected_revision=data["revision"], source_url=data["source_url"],
            evidence_note=data["evidence_note"], request=request,
        )
        return "Da’vo tasdiqlandi va saytda ko‘rinadi."
    if action == "revoke":
        public_claims.revoke(data["claim_key"], actor=request.user, reason=data["reason"],
                             expected_revision=data["revision"], request=request)
        return "Da’vo qaytarib olindi — saytda ko‘rinmaydi."
    testimonial = get_object_or_404(Testimonial, pk=data["testimonial_id"])
    confirmed = action == "consent"
    public_claims.set_testimonial_consent(
        testimonial, actor=request.user, confirmed=confirmed, reason=data["reason"],
        display_name=data.get("display_name", ""), source_reference=data.get("source_reference", ""),
        request=request,
    )
    return "Rozilik qayd etildi — fikr saytda ko‘rinadi." if confirmed else "Rozilik qaytarildi — fikr saytdan olindi."


@login_required
@user_passes_test(is_control_center_owner)
def claim_evidence(request):
    errors = None
    if request.method == "POST":
        action = request.POST.get("action", "")
        form_class = FORMS.get(action)
        form = form_class(request.POST) if form_class else None
        if form is not None and form.is_valid():
            try:
                messages.success(request, _apply(request, action, form.cleaned_data))
                return redirect("backoffice_claim_evidence")
            except public_claims.ClaimConflict as exc:
                errors = [str(exc)]
            except (ValueError, LookupError) as exc:
                errors = [str(exc)]
        else:
            errors = [message for field_errors in (form.errors.values() if form else [["Noma’lum amal."]])
                      for message in field_errors]
    context = {
        "active_nav": "backoffice",
        "bo_active": "site",
        "counts": {},
        "claims": public_claims.all_claims(),
        "testimonials": list(Testimonial.objects.order_by("order", "id")),
        "default_expiry": timezone.localdate() + timedelta(days=90),
        "errors": errors,
        "recent_changes": SystemAuditEvent.objects.filter(action__in=AUDIT_ACTIONS).select_related("actor")[:8],
    }
    return render(request, "backoffice/claim_evidence.html", context, status=400 if errors else 200)
