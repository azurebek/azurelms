"""Owner: ochiq sayt reliz tayyorligi va tasdiq (PUB1.8b).

Sahifa `frontend/release_readiness.py` selectorini ko'rsatadi — Control Center va
`manage.py public_release_gate` bilan ayni natija. Tasdiq faqat majburiy bandlarning
hammasi yashil bo'lganda (server qayta tekshiradi), sabab va tasdiq belgisi bilan; natija
audit yozuvi (`public.release.signoff`) — holatlar xeshi bilan qaror kvitansiyasi.
Qizil bandni saytdan yashirish tasdiq uchun yetarli emas.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from aicontrol.models import SystemAuditEvent
from core.access import is_control_center_owner
from frontend import release_readiness as gate


class SignOffForm(forms.Form):
    digest = forms.CharField(widget=forms.HiddenInput, max_length=32)
    reason = forms.CharField(label="Sabab va izoh", max_length=240,
                             widget=forms.Textarea(attrs={"rows": 2, "class": "lc-input"}))
    confirm = forms.BooleanField(label="Majburiy bandlarni o‘zim tekshirdim; ochiq sahifalarni pilotga ochishga roziman",
                                 required=True)


@login_required
@user_passes_test(is_control_center_owner)
def release_readiness_view(request):
    errors = None
    if request.method == "POST":
        form = SignOffForm(request.POST)
        if form.is_valid():
            current = gate.release_readiness()
            if form.cleaned_data["digest"] != current.digest():
                errors = ["Holat sahifa ochilgandan beri o‘zgardi — yangilangan ro‘yxatni ko‘rib, qayta tasdiqlang."]
            else:
                try:
                    readiness = gate.sign_off(actor=request.user, reason=form.cleaned_data["reason"], request=request)
                    messages.success(request, f"Tasdiq yozildi (holat izi {readiness.digest()}).")
                    return redirect("backoffice_release_readiness")
                except gate.NotReady as exc:
                    errors = [f"Majburiy bandlar hali yashil emas: {exc}."]
        else:
            errors = [message for field_errors in form.errors.values() for message in field_errors]
    readiness = gate.release_readiness()
    context = {
        "active_nav": "backoffice",
        "bo_active": "settings",
        "counts": {},
        "readiness": readiness,
        "required_items": [item for item in readiness.items if item.required],
        "optional_items": [item for item in readiness.items if not item.required],
        "last_sign_off": gate.last_sign_off(),
        "sign_offs": SystemAuditEvent.objects.filter(action=gate.SIGNOFF_ACTION).select_related("actor").order_by("-id")[:5],
        "errors": errors,
    }
    return render(request, "backoffice/release_readiness.html", context, status=400 if errors else 200)
