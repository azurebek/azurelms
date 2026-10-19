"""Owner: maxfiylik siyosati va foydalanish shartlari versiyalari (PUB1.5a).

Matnni owner yoki yurist beradi. Bu sahifa jarayonni ko'rsatadi: qoralama →
tasdiqlash → nashr (hozir yoki belgilangan vaqtda) → kerak bo'lsa bekor qilish,
amaldagisi bekor qilinsa oldingi nashr qaytadi. Har amal sabab, tasdiq va
audit bilan; nashr/bekor qilish CAS bilan. Qaror `frontend/legal_revisions.py`da.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_GET

from aicontrol.models import SystemAuditEvent
from core.access import is_control_center_owner
from core.workspace_forms import rich_widget
from frontend import legal_revisions
from frontend.models import LegalDocument, LegalRevision


class DraftForm(forms.Form):
    version_label = forms.CharField(label="Versiya (masalan, 1.0)", max_length=40,
                                    widget=forms.TextInput(attrs={"class": "lc-input"}))
    title = forms.CharField(label="Sarlavha", max_length=150, widget=forms.TextInput(attrs={"class": "lc-input"}))
    content = forms.CharField(label="Matn", widget=forms.Textarea)
    reason = forms.CharField(label="Izoh (ixtiyoriy, saytga chiqmaydi)", required=False, max_length=240,
                             widget=forms.TextInput(attrs={"class": "lc-input"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = rich_widget()


class _DecisionForm(forms.Form):
    revision_id = forms.IntegerField(widget=forms.HiddenInput)
    reason = forms.CharField(label="Sabab", max_length=240, widget=forms.Textarea(attrs={"rows": 2, "class": "lc-input"}))
    confirm = forms.BooleanField(label="Saytdagi huquqiy matnga ta’sirini tushunaman", required=True)


class ApproveForm(_DecisionForm):
    pass


class PublishForm(_DecisionForm):
    document_revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    effective_at = forms.DateTimeField(
        label="Kuchga kirish vaqti", input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "lc-input"}, format="%Y-%m-%dT%H:%M"),
    )


class ArchiveForm(_DecisionForm):
    document_revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)


class BackfillForm(forms.Form):
    kind = forms.ChoiceField(choices=LegalDocument.KIND_CHOICES, widget=forms.HiddenInput)
    confirm = forms.BooleanField(required=True)


FORMS = {"approve": ApproveForm, "publish": PublishForm, "archive": ArchiveForm, "backfill": BackfillForm}


def _apply(request, action, data):
    if action == "backfill":
        rows = legal_revisions.backfill_from_legacy(apply=True, actor=request.user, kinds=(data["kind"],))
        if rows[0].action != "created":
            raise ValueError("Eski matndan qoralama allaqachon bor yoki eski matn bo‘sh.")
        return "Eski matndan qoralama yaratildi. U tasdiqlanmagan — o‘qib chiqing va kerak bo‘lsa tahrirlang."
    revision = get_object_or_404(LegalRevision.objects.select_related("document"), pk=data["revision_id"])
    if action == "approve":
        legal_revisions.approve(revision, actor=request.user, reason=data["reason"], request=request)
        return f"«{revision.version_label}» tasdiqlandi. Endi uni nashr qilishingiz mumkin."
    if action == "publish":
        row = legal_revisions.publish(
            revision, actor=request.user, reason=data["reason"], effective_at=data["effective_at"],
            expected_document_revision=data["document_revision"], request=request,
        )
        if row.effective_at > timezone.now():
            return f"«{row.version_label}» nashr qilindi va {timezone.localtime(row.effective_at):%d.%m.%Y %H:%M} da kuchga kiradi."
        return f"«{row.version_label}» nashr qilindi — saytda amal qilmoqda."
    legal_revisions.archive(revision, actor=request.user, reason=data["reason"],
                            expected_document_revision=data["document_revision"], request=request)
    return f"«{revision.version_label}» bekor qilindi."


def _owner(view):
    return login_required(user_passes_test(is_control_center_owner)(view))


@_owner
def legal_documents(request):
    errors = None
    if request.method == "POST":
        action = request.POST.get("action", "")
        form_class = FORMS.get(action)
        form = form_class(request.POST) if form_class else None
        if form is not None and form.is_valid():
            try:
                messages.success(request, _apply(request, action, form.cleaned_data))
                return redirect("backoffice_legal_documents")
            except (legal_revisions.LegalConflict, ValueError) as exc:
                errors = [str(exc)]
        else:
            errors = [message for field_errors in (form.errors.values() if form else [["Noma’lum amal."]])
                      for message in field_errors]
    context = {
        "active_nav": "backoffice",
        "bo_active": "site",
        "counts": {},
        "documents": legal_revisions.document_states(),
        "now_local": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        "errors": errors,
        "recent_changes": SystemAuditEvent.objects.filter(
            action__in=legal_revisions.AUDIT_ACTIONS).select_related("actor")[:10],
    }
    return render(request, "backoffice/legal_documents.html", context, status=400 if errors else 200)


@_owner
def legal_edit(request, kind=None, pk=None):
    """Yangi qoralama (`kind`) yoki mavjud qoralamani tahrirlash (`pk`)."""
    revision = None
    if pk is not None:
        revision = get_object_or_404(LegalRevision.objects.select_related("document"), pk=pk)
        kind = revision.document.kind
        if revision.status != LegalRevision.STATUS_DRAFT:
            messages.error(request, "Tasdiqlangan matn o‘zgarmaydi — yangi qoralama yarating.")
            return redirect("backoffice_legal_documents")
    elif kind not in legal_revisions.KINDS:
        raise Http404
    errors = None
    if request.method == "POST":
        form = DraftForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                if revision is None:
                    legal_revisions.create_draft(kind, title=data["title"], version_label=data["version_label"],
                                                 content=data["content"], actor=request.user, reason=data["reason"],
                                                 request=request)
                else:
                    legal_revisions.update_draft(revision, title=data["title"], version_label=data["version_label"],
                                                 content=data["content"], actor=request.user, reason=data["reason"],
                                                 request=request)
                messages.success(request, "Qoralama saqlandi. Saytda ko‘rinmaydi — tasdiqlab, nashr qiling.")
                return redirect("backoffice_legal_documents")
            except (legal_revisions.LegalConflict, ValueError) as exc:
                errors = [str(exc)]
    else:
        initial = {"title": dict(LegalDocument.KIND_CHOICES)[kind]}
        if revision is not None:
            initial = {"version_label": revision.version_label, "title": revision.title, "content": revision.content}
        form = DraftForm(initial=initial)
    context = {
        "active_nav": "backoffice", "bo_active": "site", "counts": {},
        "form": form, "revision": revision, "kind_label": dict(LegalDocument.KIND_CHOICES)[kind], "errors": errors,
    }
    return render(request, "backoffice/legal_edit.html", context, status=400 if errors or form.errors else 200)


@require_GET
@_owner
def legal_preview(request, pk):
    """Saytdagidek ko'rinish, lekin yopiq: indekslanmaydi, keshlanmaydi, hech narsa yozmaydi."""
    revision = get_object_or_404(LegalRevision.objects.select_related("document"), pk=pk)
    response = render(request, "backoffice/legal_preview.html", {"revision": revision})
    response["X-Robots-Tag"] = "noindex, nofollow"
    patch_cache_control(response, private=True, no_store=True)
    return response
