"""Scoped, atomic exam metadata/first-section authoring.

Signed state snapshots follow course authoring: stale/replayed creates fail,
but they are not durable revision counters and do not detect external ABA.
The exam row is shared with start_exam_attempt's first-attempt lock. Content
with any attempt is read-only; no question builder or versioning is implied.
"""
import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.crypto import salted_hmac

from core.audit import record_audit_event
from core.backoffice_forms import ExamBackofficeForm, ExamSectionBackofficeForm
from courses.authoring_service import _actor, _check_revision, _course
from courses.models import Exam, ExamSection


class ExamAuthoringInvalid(Exception):
    def __init__(self, exam_form, section_form):
        self.exam_form, self.section_form = exam_form, section_form


class ExamInUse(ValidationError):
    def __init__(self):
        super().__init__("Bu imtihonni o‘quvchilar boshlagan. Ularning ishlarini saqlash uchun tahrirlash yopilgan.", code="in_use")


def _values(obj, fields):
    values = {name: obj._meta.get_field(name).value_from_object(obj) for name in fields}
    for name in ("reading_text", "media_url"):
        if name in values:
            values[name] = values[name] or ""
    return values


def _section_state(section):
    return {"pk": section.pk, **_values(section, ExamSectionBackofficeForm.Meta.fields),
            "audio_play_limit": section.audio_play_limit}


def _state(exam):
    return {
        "exam": _values(exam, ExamBackofficeForm.Meta.fields),
        "sections": [_section_state(section) for section in exam.sections.order_by("pk")],
    }


def exam_revision(actor, course, exam=None, section_id=None):
    state = _state(exam) if exam else list(
        Exam.objects.filter(course=course).order_by("pk").values_list("pk", flat=True))
    return salted_hmac("exam-authoring", json.dumps(
        [actor.pk, course.pk, exam.pk if exam else None, section_id, state], default=str,
    ), algorithm="sha256").hexdigest()


def _audit_state(state):
    # Rich section content need not be copied into the operations ledger.
    return {"exam": state["exam"], "sections_sha256": hashlib.sha256(
        json.dumps(state["sections"], default=str, sort_keys=True).encode()).hexdigest()}


@transaction.atomic
def save_exam(*, actor, course_id, data, expected_revision, exam_id=None, section_id=None, request=None):
    actor = _actor(actor)
    course = _course(actor, course_id)
    if hasattr(data, "getlist"):
        controls = (*ExamBackofficeForm.Meta.fields, "section_id", "editor_revision",
                    *("section-" + name for name in ExamSectionBackofficeForm.Meta.fields))
        if any(len(data.getlist(name)) > 1 for name in controls):
            raise ValidationError("Bir maydon bir necha marta yuborilgan. Sahifani yangilab, qayta urinib ko‘ring.")
    exam = Exam.objects.select_for_update().get(pk=exam_id, course=course) if exam_id else None
    section = ExamSection.objects.select_for_update().get(pk=section_id, exam=exam) if section_id else None
    needs_section = section is not None or exam is None or not exam.sections.exists()
    revision = exam_revision(actor, course, exam, section_id)
    before = _state(exam) if exam else None
    # Fail closed for every attempt, including an active, unanswered attempt.
    if exam and exam.attempts.exists():
        raise ExamInUse()
    _check_revision(expected_revision, revision)
    exam_form = ExamBackofficeForm(data, instance=exam, user=actor, initial={"course": course.pk})
    exam_form.fields["course"].queryset = exam_form.fields["course"].queryset.filter(pk=course.pk)
    exam_form.fields["course"].help_text = "Kurs shu sahifa uchun tanlangan. Boshqa kurs imtihonlari uchun ro‘yxatga qayting."
    exam_form.fields["prerequisite_exam"].queryset = exam_form.fields["prerequisite_exam"].queryset.filter(course=course)
    section_form = (ExamSectionBackofficeForm(data, instance=section, prefix="section")
                    if needs_section else None)
    valid = exam_form.is_valid()
    if section_form is not None:
        valid = section_form.is_valid() and valid
    if exam_form.cleaned_data.get("course") != course:
        if not exam_form.errors.get("course"):
            exam_form.add_error("course", "Shu sahifadagi kursni tanlang. Imtihonni boshqa kursga ko‘chirish yopilgan.")
        valid = False
    # An old/stale caller must not silently lose a submitted section edit.
    if not needs_section and any(str(key).startswith("section-") for key in data):
        exam_form.add_error(None, "Avval tahrirlanadigan bo‘limni tanlang.")
        valid = False
    if not valid:
        raise ExamAuthoringInvalid(exam_form, section_form)
    saved = exam_form.save(commit=False)
    saved.full_clean()
    created = saved.pk is None
    if section_form:
        changed_section = section_form.save(commit=False)
        changed_section.exam = saved
        # The unsaved parent is written inside this transaction first.
    else:
        changed_section = None
    exam_changed = created or before["exam"] != _values(saved, ExamBackofficeForm.Meta.fields)
    section_changed = bool(changed_section and (not changed_section.pk or next(
        row for row in before["sections"] if row["pk"] == changed_section.pk
    ) != _section_state(changed_section)))
    if not exam_changed and not section_changed:
        return saved, changed_section, False
    if exam_changed:
        saved.save()
    if changed_section and section_changed:
        changed_section.exam = saved
        changed_section.full_clean()
        changed_section.save()
    record_audit_event(
        action="exam.create" if created else "exam.update", actor=actor, target=saved,
        request=request, reason="Imtihon tayyorlash sahifasida saqlandi.",
        before=_audit_state(before) if before else {}, after=_audit_state(_state(saved)),
    )
    return saved, changed_section, True
