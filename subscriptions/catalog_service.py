"""Owner mutations: validation, serialization and audit stay together."""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from aicontrol.models import SystemAuditEvent
from core.access import is_control_center_owner
from core.audit import record_audit_event
from cohorts.models import Cohort
from courses.models import Course
from .catalog_forms import CatalogPlanForm, DeliveryCohortForm
from .models import Plan, PlanFeature


def require_owner(actor, *, request=None):
    if not actor or not is_control_center_owner(actor):
        record_audit_event(action="catalog.edit", actor=actor, request=request,
                           outcome=SystemAuditEvent.OUTCOME_DENIED, error="Owner ruxsati kerak.")
        raise PermissionDenied


def _snapshot(instance, fields):
    return {name: getattr(instance, instance._meta.get_field(name).attname) for name in fields}


def update_plan(*, actor, plan_id, data, request=None):
    require_owner(actor, request=request)
    with transaction.atomic():
        plan = Plan.objects.select_for_update().get(pk=plan_id)
        before = _snapshot(plan, CatalogPlanForm.Meta.fields)
        before["features"] = list(plan.features.values_list("name", "is_included", "order"))
        form = CatalogPlanForm(data, instance=plan)
        if not form.is_valid():
            return form
        form.save(commit=False).save(update_fields=CatalogPlanForm.Meta.fields)
        lines = form.cleaned_data["features_text"].splitlines()
        existing = list(plan.features.order_by("order", "id"))
        for index, line in enumerate(lines):
            feature = existing[index] if index < len(existing) else PlanFeature(plan=plan)
            feature.name = line.removeprefix("- ")
            feature.is_included = not line.startswith("- ")
            feature.order = index
            feature.save()
        # Only the owner-submitted marketing rows; no historical plan deletion.
        PlanFeature.objects.filter(pk__in=[f.pk for f in existing[len(lines):]]).delete()
        after = _snapshot(plan, CatalogPlanForm.Meta.fields)
        after["features"] = list(plan.features.values_list("name", "is_included", "order"))
        record_audit_event(action="catalog.plan.update", actor=actor, request=request,
                           target=plan, reason=form.cleaned_data["change_reason"], before=before, after=after)
        return form


def save_cohort(*, actor, cohort_id=None, data, request=None):
    require_owner(actor, request=request)
    instance = Cohort.objects.get(pk=cohort_id) if cohort_id else Cohort()
    form = DeliveryCohortForm(data, instance=instance)
    if not form.is_valid():
        return form
    with transaction.atomic():
        course_ids = {form.cleaned_data["course"].pk}
        if cohort_id:
            course_ids.add(Cohort.objects.values_list("course_id", flat=True).get(pk=cohort_id))
        list(Course.objects.select_for_update().filter(pk__in=course_ids).order_by("pk"))
        instance = Cohort.objects.select_for_update().get(pk=cohort_id) if cohort_id else Cohort()
        before = _snapshot(instance, DeliveryCohortForm.Meta.fields) if cohort_id else {}
        form = DeliveryCohortForm(data, instance=instance)
        if not form.is_valid():
            return form
        cohort = form.save(commit=False)
        cohort.save(update_fields=DeliveryCohortForm.Meta.fields if cohort_id else None)
        record_audit_event(action="catalog.cohort.save", actor=actor, request=request,
                           target=cohort, reason=form.cleaned_data["change_reason"], before=before,
                           after=_snapshot(cohort, DeliveryCohortForm.Meta.fields))
        return form
