"""Scoped course authoring shared by backoffice adapters.

Every mutation checks a signed snapshot under a stable row lock, validates the
current parent scope, and commits its audit record in the same transaction.
Snapshots deliberately follow the existing editor contract: replayed creates
are rejected, but they are not durable operation receipts or revision counters.
An external writer changing values and restoring them (ABA) is not detected.
Saving lesson content never creates a release or a private draft.
"""

import hashlib
import json
from html import unescape

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.html import strip_tags

from core.access import teacher_course_queryset
from core.audit import record_audit_event
from courses.models import (
    Assignment, AssignmentSubmission, Choice, Course, Lesson, Module,
    Question, Quiz, QuizAnswer, QuizAttempt, StudentAnswer,
)


LESSON_FIELDS = ("title", "module", "video_url", "content", "order", "xp_reward")


class AuthoringConflict(ValidationError):
    def __init__(self):
        super().__init__(
            "Ma’lumot boshqa oynada o‘zgargan. Yozganlaringizni olib, so‘nggi holatni oching.",
            code="stale",
        )


def _sign(actor, action, state):
    return salted_hmac(
        "course-authoring", json.dumps([actor.pk, action, state], default=str),
        algorithm="sha256",
    ).hexdigest()


def outline_revision(actor, course):
    return _sign(actor, "outline", [
        course.pk,
        list(Module.objects.filter(course=course).order_by("order", "pk")
             .values_list("pk", "title", "order")),
        list(Lesson.objects.filter(module__course=course).order_by("pk")
             .values_list("pk", "module_id", "title", "order")),
    ])


def lesson_revision(actor, lesson):
    return _sign(actor, "lesson", [
        lesson.pk,
        [str(lesson._meta.get_field(name).value_from_object(lesson)) for name in LESSON_FIELDS],
    ])


def _course_value(course, name):
    field = course._meta.get_field(name)
    value = field.value_from_object(course)
    if field.get_internal_type() == "DecimalField" and value is not None:
        value = f"{field.to_python(value):.{field.decimal_places}f}"
    return str(value)


def course_revision(actor, course=None):
    from core.backoffice_forms import CourseBackofficeForm

    state = (
        [course.pk, [_course_value(course, name)
                     for name in CourseBackofficeForm.Meta.fields]]
        if course is not None else
        list(teacher_course_queryset(actor).order_by("pk").values_list("pk", flat=True))
    )
    return _sign(actor, "course" if course is not None else "new-course", state)


def _check_revision(expected, current):
    if not isinstance(expected, str) or not constant_time_compare(expected, current):
        raise AuthoringConflict()


def _actor(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise PermissionDenied
    try:
        current = get_user_model().objects.select_for_update().get(pk=actor.pk)
    except get_user_model().DoesNotExist:
        raise PermissionDenied from None
    if not current.is_active or not (current.is_staff or current.is_superuser):
        raise PermissionDenied
    return current


def _course(actor, course_id):
    return teacher_course_queryset(actor).select_for_update().get(pk=course_id)


def _module_state(module):
    return {"course_id": module.course_id, "title": module.title, "order": module.order}


def _lesson_state(lesson):
    return {
        "module_id": lesson.module_id, "title": lesson.title, "order": lesson.order,
        "xp_reward": lesson.xp_reward, "video_url": lesson.video_url or "",
        "content_sha256": hashlib.sha256((lesson.content or "").encode()).hexdigest(),
    }


def _course_state(course):
    from core.backoffice_forms import CourseBackofficeForm

    state = {
        name: _course_value(course, name)
        for name in CourseBackofficeForm.Meta.fields if name != "description"
    }
    state["description_sha256"] = hashlib.sha256((course.description or "").encode()).hexdigest()
    return state


def _audit(*, actor, action, target, before, after, request):
    record_audit_event(
        action=action, actor=actor, target=target, request=request,
        reason="Kurs va dars ustaxonasida saqlandi.", before=before, after=after,
    )


@transaction.atomic
def save_course(*, actor, data, expected_revision, course_id=None, request=None):
    """Validate the canonical course form again against the locked current row."""
    from core.backoffice_forms import CourseBackofficeForm

    actor = _actor(actor)
    course = _course(actor, course_id) if course_id is not None else None
    _check_revision(expected_revision, course_revision(actor, course))
    before = _course_state(course) if course is not None else {}
    form = CourseBackofficeForm(data, instance=course, user=actor)
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    course = form.save(commit=False)
    if not course.instructor_id:
        course.instructor = actor
    if not actor.is_superuser and course.instructor_id != actor.pk:
        raise PermissionDenied
    course.full_clean()
    after = _course_state(course)
    created = course.pk is None
    if not created and before == after:
        return course, False
    course.save()
    if not course.modules.exists():
        Module.objects.create(course=course, title="1. Boshlanish", order=1)
    _audit(actor=actor, action="course.create" if created else "course.update",
           target=course, before=before, after=after, request=request)
    return course, True


@transaction.atomic
def save_module(*, actor, course_id, title, expected_revision, module_id=None, request=None):
    actor = _actor(actor)
    course = _course(actor, course_id)
    _check_revision(expected_revision, outline_revision(actor, course))
    if not isinstance(title, str):
        raise ValidationError({"title": "Modul nomini kiriting."})
    if module_id is None:
        order = (course.modules.aggregate(last=Max("order"))["last"] or 0) + 1
        module = Module(course=course, order=order)
        before = {}
    else:
        module = Module.objects.select_for_update().get(pk=module_id, course=course)
        before = _module_state(module)
    module.title = title.strip()
    module.full_clean()
    after = _module_state(module)
    created = module.pk is None
    if not created and before == after:
        return module, False
    module.save()
    _audit(actor=actor, action="module.create" if created else "module.update",
           target=module, before=before, after=after, request=request)
    return module, True


@transaction.atomic
def move_module(*, actor, course_id, module_id, direction, expected_revision, request=None):
    """Move one module one step; never trust an arbitrary submitted ID list."""
    actor = _actor(actor)
    course = _course(actor, course_id)
    _check_revision(expected_revision, outline_revision(actor, course))
    if direction not in ("up", "down"):
        raise ValidationError({"direction": "Yuqoriga yoki pastga siljitishni tanlang."})
    modules = list(course.modules.select_for_update().order_by("order", "pk"))
    module = next((item for item in modules if str(item.pk) == str(module_id)), None)
    if module is None:
        raise Module.DoesNotExist
    index = modules.index(module)
    destination = index + (-1 if direction == "up" else 1)
    if not 0 <= destination < len(modules):
        return False
    before = {str(item.pk): item.order for item in modules}
    modules[index], modules[destination] = modules[destination], modules[index]
    for position, item in enumerate(modules, 1):
        item.order = position
    Module.objects.bulk_update(modules, ["order"])
    _audit(actor=actor, action="module.reorder", target=course, before=before,
           after={str(item.pk): item.order for item in modules}, request=request)
    return True


@transaction.atomic
def save_lesson(*, actor, course_id, data, expected_revision, lesson_id=None, request=None):
    actor = _actor(actor)
    course = _course(actor, course_id)
    if lesson_id is None:
        lesson = None
        _check_revision(expected_revision, outline_revision(actor, course))
    else:
        lesson = Lesson.objects.select_for_update().get(pk=lesson_id, module__course=course)
        _check_revision(expected_revision, lesson_revision(actor, lesson))
    before = _lesson_state(lesson) if lesson is not None else {}
    required = ("title", "module") if lesson is None else LESSON_FIELDS
    missing = {name: "Bu maydonni to‘ldiring." for name in required if name not in data}
    if missing:
        raise ValidationError(missing)
    module_value = data["module"]
    module_id = module_value.pk if isinstance(module_value, Module) else module_value
    try:
        module = course.modules.select_for_update().get(pk=module_id)
    except (Module.DoesNotExist, TypeError, ValueError, ValidationError):
        raise ValidationError({"module": "Shu kursdagi modulni tanlang."}) from None
    if lesson is None:
        next_order = (module.lessons.aggregate(last=Max("order"))["last"] or 0) + 1
        lesson = Lesson(module=module, order=next_order)
    lesson.module = module
    for name in LESSON_FIELDS:
        if name != "module" and name in data:
            setattr(lesson, name, data[name])
    if not isinstance(lesson.title, str):
        raise ValidationError({"title": "Dars nomini kiriting."})
    lesson.title = lesson.title.strip()
    lesson.video_url = lesson.video_url or ""
    lesson.content = lesson.content or ""
    lesson.full_clean()
    after = _lesson_state(lesson)
    created = lesson.pk is None
    if not created and before == after:
        return lesson, False
    lesson.save()
    _audit(actor=actor, action="lesson.create" if created else "lesson.update",
           target=lesson, before=before, after=after, request=request)
    return lesson, True


class PracticeUnavailable(ValidationError):
    def __init__(self):
        super().__init__("Topshiriq va test tayyorlash hozir yopilgan.", code="unavailable")


class PracticeInUse(ValidationError):
    def __init__(self, message):
        super().__init__(message, code="in_use")


class PracticeUnsupported(ValidationError):
    def __init__(self, message):
        super().__init__(message, code="unsupported")


def _practice_gate():
    from core.flags import flag_enabled

    if not flag_enabled("backoffice_practice_authoring"):
        raise PracticeUnavailable()


def _practice_id(value, field):
    if type(value) is int and 0 < value < 2**63:
        return value
    if (isinstance(value, str) and value.isascii() and value.isdecimal()
            and len(value) <= 19 and 0 < int(value) < 2**63):
        return int(value)
    raise ValidationError({field: "To‘g‘ri yozuvni tanlang."})


def _practice_parent(actor, course_id, lesson_id):
    course = _course(actor, _practice_id(course_id, "course"))
    return Lesson.objects.select_for_update().get(
        pk=_practice_id(lesson_id, "lesson"), module__course=course,
    )


def _parent_state(lesson):
    return [lesson.pk, lesson.module_id, lesson.module.course_id]


def _assignment_state(assignment):
    return {"id": assignment.pk, "lesson_id": assignment.lesson_id,
            "title": assignment.title, "description": assignment.description,
            "max_xp": assignment.max_xp}


def assignment_revision(actor, lesson, assignment=None):
    state = (_assignment_state(assignment) if assignment else
             list(lesson.assignments.order_by("pk").values_list("pk", flat=True)))
    return _sign(actor, "assignment" if assignment else "new-assignment", [_parent_state(lesson), state])


def _quiz_state(quiz):
    return {
        "id": quiz.pk, "lesson_id": quiz.lesson_id, "exam_section_id": quiz.exam_section_id,
        "title": quiz.title, "xp_reward": quiz.xp_reward,
        "questions": [
            {"id": question.pk, "text": question.text, "points": question.points,
             "exam_section_id": question.exam_section_id,
             "min_word_count": question.min_word_count, "max_word_count": question.max_word_count,
             "choices": list(question.choices.order_by("pk").values("id", "text", "is_correct"))}
            for question in quiz.questions.order_by("pk").prefetch_related("choices")
        ],
    }


def lesson_quiz_revision(actor, lesson, quiz=None):
    state = (_quiz_state(quiz) if quiz else
             list(lesson.quizzes.order_by("pk").values_list("pk", flat=True)))
    return _sign(actor, "lesson-quiz" if quiz else "new-lesson-quiz", [_parent_state(lesson), state])


def assignment_edit_block_reason(assignment):
    if AssignmentSubmission.objects.filter(assignment=assignment).exists():
        return "Bu topshiriqqa javob yuborilgan. Oldingi ish va baholarni saqlash uchun yangi topshiriq yarating."
    return ""


def _quiz_in_use(quiz):
    linked = Q(question__quiz=quiz) | Q(selected_choice__question__quiz=quiz)
    return (QuizAttempt.objects.filter(quiz=quiz).exists()
            or QuizAnswer.objects.filter(linked).exists()
            or StudentAnswer.objects.filter(linked).exists())


def _visible_text(value):
    return isinstance(value, str) and bool(unescape(strip_tags(value)).strip())


def _quiz_supported(quiz):
    if not quiz.lesson_id or quiz.exam_section_id:
        return False
    questions = list(quiz.questions.prefetch_related("choices"))
    if not questions:
        return False
    for question in questions:
        choices = list(question.choices.all())
        if (question.exam_section_id or question.points != 1 or question.min_word_count
                or question.max_word_count or not _visible_text(question.text)
                or len(choices) < 2 or sum(item.is_correct for item in choices) != 1
                or any(not item.text.strip() for item in choices)):
            return False
    return True


def lesson_quiz_edit_block_reason(quiz):
    if _quiz_in_use(quiz):
        return "Bu testda o‘quvchi urinishi yoki javobi bor. Natijalarni saqlash uchun yangi test yarating."
    if not _quiz_supported(quiz):
        return "Bu testning tuzilishi oddiy bir javobli testga mos emas. Asl nusxa saqlanadi; yangi oddiy test yarating."
    return ""


def _practice_fields(data, names):
    if not hasattr(data, "get"):
        raise ValidationError("Maydonlarni to‘ldirib, qayta urinib ko‘ring.")
    errors = {name: "Bu maydonni to‘ldiring." for name in names if name not in data}
    if hasattr(data, "getlist"):
        errors.update({name: "Bu maydon bir necha marta yuborilgan." for name in names
                       if len(data.getlist(name)) > 1})
    if errors:
        raise ValidationError(errors)


def _practice_text(value, field, *, rich=False, max_length=None):
    if not isinstance(value, str) or not (_visible_text(value) if rich else value.strip()):
        raise ValidationError({field: "Matnni kiriting."})
    if max_length and len(value.strip()) > max_length:
        raise ValidationError({field: f"Matn {max_length} belgidan oshmasin."})
    if rich:
        from frontend.templatetags.bleach_tags import sanitize

        # Keep supported formatting through the learner's existing sanitizer.
        return str(sanitize(value))
    return value.strip()


def _practice_xp(value, field):
    if type(value) is int and 0 <= value <= 2147483647:
        return value
    if (isinstance(value, str) and value.isascii() and value.isdecimal()
            and len(value) <= 10 and 0 <= int(value) <= 2147483647):
        return int(value)
    raise ValidationError({field: "0 yoki undan katta butun son kiriting."})


def _practice_audit(*, actor, target, action, before, after, request):
    def digest(state):
        return {"content_sha256": hashlib.sha256(
            json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()} if state else {}

    record_audit_event(action=action, actor=actor, target=target, request=request,
                       reason="Dars topshirig‘i yoki oddiy test tayyorlandi.",
                       before=digest(before), after=digest(after))


def validate_assignment_data(data):
    """Pure content validation for previews; callers still enforce actor scope."""
    _practice_fields(data, ("title", "description", "max_xp"))
    return {"title": _practice_text(data["title"], "title", max_length=200),
            "description": _practice_text(data["description"], "description", rich=True),
            "max_xp": _practice_xp(data["max_xp"], "max_xp")}


@transaction.atomic
def save_assignment(*, actor, course_id, lesson_id, data, expected_revision,
                    assignment_id=None, request=None):
    actor = _actor(actor)
    _practice_gate()
    lesson = _practice_parent(actor, course_id, lesson_id)
    assignment = (Assignment.objects.select_for_update().get(
        pk=_practice_id(assignment_id, "assignment"), lesson=lesson,
    ) if assignment_id is not None else None)
    if assignment and (reason := assignment_edit_block_reason(assignment)):
        raise PracticeInUse(reason)
    _check_revision(expected_revision, assignment_revision(actor, lesson, assignment))
    cleaned = validate_assignment_data(data)
    before = _assignment_state(assignment) if assignment else {}
    assignment = assignment or Assignment(lesson=lesson)
    for name, value in cleaned.items():
        setattr(assignment, name, value)
    assignment.full_clean()
    if before == _assignment_state(assignment):
        return assignment, False
    created = assignment.pk is None
    assignment.save()
    _practice_audit(actor=actor, target=assignment, action="assignment.create" if created else "assignment.update",
                    before=before, after=_assignment_state(assignment), request=request)
    return assignment, True


def _question_payload(questions, existing):
    if not isinstance(questions, list) or not questions:
        raise ValidationError({"questions": "Kamida bitta savol qo‘shing."})
    normalized, seen_questions, seen_choices = [], set(), set()
    for index, row in enumerate(questions):
        prefix = f"questions-{index}"
        if not isinstance(row, dict):
            raise ValidationError({prefix + "-text": "Savolni to‘ldiring."})
        qid = _practice_id(row["id"], prefix + "-id") if row.get("id") not in (None, "") else None
        if qid is not None and (qid not in existing or qid in seen_questions):
            raise ValidationError({prefix + "-id": "Bu savol shu testga tegishli emas yoki takrorlangan."})
        seen_questions.add(qid)
        text = _practice_text(row.get("text"), prefix + "-text", rich=True)
        choices = row.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            raise ValidationError({prefix + "-correct": "Kamida ikkita variant kiriting."})
        old_choices = {choice["id"] for choice in existing[qid]["choices"]} if qid else set()
        cleaned_choices = []
        for number, choice in enumerate(choices):
            key = f"{prefix}-choices-{number}"
            if not isinstance(choice, dict):
                raise ValidationError({key + "-text": "Variantni to‘ldiring."})
            cid = _practice_id(choice["id"], key + "-id") if choice.get("id") not in (None, "") else None
            if cid is not None and (cid not in old_choices or cid in seen_choices):
                raise ValidationError({key + "-id": "Bu variant shu savolga tegishli emas yoki takrorlangan."})
            seen_choices.add(cid)
            if type(choice.get("is_correct")) is not bool:
                raise ValidationError({prefix + "-correct": "Bitta to‘g‘ri javobni tanlang."})
            cleaned_choices.append({"id": cid, "text": _practice_text(choice.get("text"), key + "-text", max_length=200),
                                    "is_correct": choice["is_correct"]})
        if sum(choice["is_correct"] for choice in cleaned_choices) != 1:
            raise ValidationError({prefix + "-correct": "Aynan bitta to‘g‘ri javobni tanlang."})
        normalized.append({"id": qid, "text": text, "choices": cleaned_choices})
    return normalized


def validate_lesson_quiz_data(data, questions, quiz=None):
    """Pure preview validation, using an already scoped quiz for retained IDs."""
    _practice_fields(data, ("title", "xp_reward"))
    cleaned = {"title": _practice_text(data["title"], "title", max_length=200),
               "xp_reward": _practice_xp(data["xp_reward"], "xp_reward")}
    existing = {row["id"]: row for row in _quiz_state(quiz)["questions"]} if quiz else {}
    return cleaned, _question_payload(questions, existing)


@transaction.atomic
def save_lesson_quiz(*, actor, course_id, lesson_id, data, questions,
                     expected_revision, quiz_id=None, request=None):
    actor = _actor(actor)
    _practice_gate()
    lesson = _practice_parent(actor, course_id, lesson_id)
    quiz = (Quiz.objects.select_for_update().get(
        pk=_practice_id(quiz_id, "quiz"), lesson=lesson,
    ) if quiz_id is not None else None)
    if quiz:
        # Lock child rows too; IDs may be retained, removed or appended, never moved.
        list(Question.objects.select_for_update().filter(quiz=quiz).order_by("pk"))
        list(Choice.objects.select_for_update().filter(question__quiz=quiz).order_by("pk"))
        if _quiz_in_use(quiz):
            raise PracticeInUse(lesson_quiz_edit_block_reason(quiz))
        if not _quiz_supported(quiz):
            raise PracticeUnsupported(lesson_quiz_edit_block_reason(quiz))
    _check_revision(expected_revision, lesson_quiz_revision(actor, lesson, quiz))
    before = _quiz_state(quiz) if quiz else {}
    cleaned, normalized = validate_lesson_quiz_data(data, questions, quiz)
    quiz = quiz or Quiz(lesson=lesson)
    quiz.title, quiz.xp_reward = cleaned["title"], cleaned["xp_reward"]
    quiz.full_clean()
    created = quiz.pk is None
    # Save only changes. Child IDs and rich content survive an unchanged save.
    quiz_changed = created or quiz.title != before["title"] or quiz.xp_reward != before["xp_reward"]
    if quiz_changed:
        quiz.save()
    retained_questions = []
    for row in normalized:
        question = Question.objects.get(pk=row["id"], quiz=quiz) if row["id"] else Question(quiz=quiz)
        if not question.pk or question.text != row["text"]:
            question.text = row["text"]
            question.full_clean()
            question.save()
        retained_questions.append(question.pk)
        retained_choices = []
        for item in row["choices"]:
            choice = Choice.objects.get(pk=item["id"], question=question) if item["id"] else Choice(question=question)
            if not choice.pk or choice.text != item["text"] or choice.is_correct != item["is_correct"]:
                choice.text, choice.is_correct = item["text"], item["is_correct"]
                choice.full_clean()
                choice.save()
            retained_choices.append(choice.pk)
        question.choices.exclude(pk__in=retained_choices).delete()
    quiz.questions.exclude(pk__in=retained_questions).delete()
    after = _quiz_state(quiz)
    if before == after:
        return quiz, False
    _practice_audit(actor=actor, target=quiz, action="quiz.create" if created else "quiz.update",
                    before=before, after=after, request=request)
    return quiz, True
