from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    ExamSectionAttemptState,
    READING_TASK_OPTION_TYPES,
    READING_TASK_SHARED_OPTION_TYPES,
    READING_TASK_TEXT_TYPES,
    ReadingItem,
    ReadingOption,
    ReadingResponse,
    normalize_reading_value,
)


def ensure_exam_section_state(*, attempt, section):
    state, _ = ExamSectionAttemptState.objects.get_or_create(
        attempt=attempt,
        section=section,
        defaults={"state": {}},
    )
    return state


def _word_count(value):
    return len([token for token in (value or "").strip().split() if token])


def _serialize_option(option):
    return {
        "id": option.id,
        "label": option.label,
        "text": option.text,
        "key": option.option_key or option.normalized_key,
    }


def _serialize_response(response):
    if not response:
        return {
            "selected_option_id": None,
            "selected_option_ids": [],
            "text_answer": "",
            "is_flagged_for_review": False,
            "awarded_score": 0,
            "is_graded": False,
        }
    return {
        "selected_option_id": response.selected_option_id,
        "selected_option_ids": response.selected_option_ids or [],
        "text_answer": response.text_answer or "",
        "is_flagged_for_review": response.is_flagged_for_review,
        "awarded_score": float(response.awarded_score),
        "is_graded": response.is_graded,
    }


def _build_status_counts(question_map):
    counts = {"done": 0, "review": 0, "pending": 0, "current": 0}
    for item in question_map:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    counts["answered"] = counts["done"] + counts["review"]
    return counts


def build_reading_section_payload(*, attempt, section):
    # Bu "boy task engine" — reading uchun ishlab chiqilgan, lekin ReadingTask'lar
    # asosida har qanday section (masalan listening) uchun ham ishlaydi.
    if section.exam_id != attempt.exam_id:
        raise ValidationError("Section ushbu attempt imtihoniga tegishli emas.")

    state = ensure_exam_section_state(attempt=attempt, section=section)
    tasks = list(
        section.reading_tasks.select_related("passage")
        .prefetch_related("shared_options", "items__options", "items__accepted_answers")
        .order_by("order", "id")
    )
    responses = {
        response.item_id: response
        for response in attempt.reading_responses.filter(item__task__section=section).select_related("selected_option")
    }

    all_items = [item for task in tasks for item in task.items.all()]
    current_item_id = state.state.get("current_item_id")
    if current_item_id not in {item.id for item in all_items}:
        current_item_id = all_items[0].id if all_items else None
        if current_item_id:
            state.state["current_item_id"] = current_item_id
            state.save(update_fields=["state", "updated_at"])

    question_map = []
    serialized_tasks = []
    for task in tasks:
        shared_options = [_serialize_option(option) for option in task.shared_options.all()]
        serialized_items = []
        for item in task.items.all():
            response = responses.get(item.id)
            status = "pending"
            if response and response.is_flagged_for_review:
                status = "review"
            elif response and response.is_answered:
                status = "done"
            elif item.id == current_item_id:
                status = "current"
            question_map.append(
                {
                    "item_id": item.id,
                    "label": item.display_label,
                    "status": status,
                    "task_id": task.id,
                }
            )
            serialized_items.append(
                {
                    "id": item.id,
                    "prompt": item.prompt or "",
                    "short_label": item.short_label,
                    "helper_text": item.helper_text,
                    "points": item.points,
                    "options": [_serialize_option(option) for option in item.options.all()],
                    "response": _serialize_response(response),
                }
            )
        serialized_tasks.append(
            {
                "id": task.id,
                "title": task.title,
                "task_type": task.task_type,
                "display_variant": task.display_variant,
                "instructions": task.instructions or "",
                "body": task.body or "",
                "question_from": task.question_from,
                "question_to": task.question_to,
                "max_selections_per_item": task.max_selections_per_item,
                "max_words_per_answer": task.max_words_per_answer,
                "allow_option_reuse": task.allow_option_reuse,
                "allow_review_flag": task.allow_review_flag,
                "passage_id": task.passage_id,
                "shared_options": shared_options,
                "items": serialized_items,
            }
        )

    passages = [
        {
            "id": passage.id,
            "title": passage.title,
            "body": passage.body or "",
            "paragraph_labels": passage.paragraph_labels,
        }
        for passage in section.reading_passages.all().order_by("order", "id")
    ]

    return {
        "section": {
            "id": section.id,
            "title": section.title,
            "section_type": section.section_type,
            "instructions": section.instructions or "",
            "legacy_reading_text": section.reading_text or "",
            "media_url": section.media_url or "",
            "time_limit_minutes": section.time_limit_minutes,
            "audio_play_limit": section.audio_play_limit,
            "plays_used": int(state.state.get("plays_used", 0)),
            "plays_left": (max(section.audio_play_limit - int(state.state.get("plays_used", 0)), 0) if section.audio_play_limit else None),
        },
        "state": {
            "current_item_id": current_item_id,
            "question_map": question_map,
            "counts": _build_status_counts(question_map),
        },
        "passages": passages,
        "tasks": serialized_tasks,
    }


def _normalize_answer_for_task(task, value):
    return normalize_reading_value(
        value,
        case_sensitive=task.case_sensitive_grading,
        punctuation_sensitive=task.punctuation_sensitive,
    )


def _resolve_selected_option_ids(item, raw_option_ids):
    option_ids = []
    for value in raw_option_ids or []:
        try:
            option_ids.append(int(value))
        except (TypeError, ValueError):
            raise ValidationError("Option IDlar ro'yxati noto'g'ri formatda keldi.")
    option_ids = sorted(set(option_ids))
    valid_ids = set(item.options.values_list("id", flat=True))
    invalid_ids = [option_id for option_id in option_ids if option_id not in valid_ids]
    if invalid_ids:
        raise ValidationError("Selected optionlar itemga tegishli emas.")
    return option_ids


def _grade_response_for_item(*, item, selected_option=None, selected_option_ids=None, text_answer=""):
    task = item.task

    if task.task_type == "single_choice":
        correct_option = item.options.filter(is_correct=True).first()
        is_correct = bool(correct_option and selected_option and selected_option.id == correct_option.id)
        return item.points if is_correct else 0, True

    if task.task_type == "multiple_choice":
        correct_ids = sorted(item.options.filter(is_correct=True).values_list("id", flat=True))
        is_correct = selected_option_ids == correct_ids and bool(correct_ids)
        return item.points if is_correct else 0, True

    if task.task_type in READING_TASK_SHARED_OPTION_TYPES:
        accepted_values = {
            _normalize_answer_for_task(task, accepted.value)
            for accepted in item.accepted_answers.all()
        }
        selected_value = selected_option.option_key or selected_option.label or selected_option.text if selected_option else ""
        is_correct = bool(selected_option and _normalize_answer_for_task(task, selected_value) in accepted_values)
        return item.points if is_correct else 0, True

    if task.task_type in READING_TASK_TEXT_TYPES:
        if task.max_words_per_answer and _word_count(text_answer) > task.max_words_per_answer:
            raise ValidationError(
                f"Javob {task.max_words_per_answer} ta so'zdan oshmasligi kerak."
            )
        normalized_answer = _normalize_answer_for_task(task, text_answer)
        accepted_values = {
            _normalize_answer_for_task(task, accepted.value)
            for accepted in item.accepted_answers.all()
        }
        if not accepted_values:
            return 0, False
        is_correct = normalized_answer in accepted_values
        return item.points if is_correct else 0, True

    raise ValidationError("Ushbu reading task turi hali qo'llab-quvvatlanmaydi.")


@transaction.atomic
def save_reading_response(*, attempt, item, payload):
    if item.task.section.exam_id != attempt.exam_id:
        raise ValidationError("Reading item ushbu imtihon urinishiga tegishli emas.")

    response, _ = ReadingResponse.objects.select_for_update().get_or_create(
        attempt=attempt,
        item=item,
    )
    task = item.task

    selected_option = None
    selected_option_ids = []
    text_answer = (payload.get("text_answer") or "").strip()

    if task.task_type == "single_choice":
        option_id = payload.get("option_id")
        if option_id in (None, ""):
            response.selected_option = None
            response.selected_option_ids = []
            response.text_answer = ""
            response.awarded_score = 0
            response.is_graded = False
            response.is_flagged_for_review = bool(payload.get("flag_for_review", response.is_flagged_for_review))
            response.full_clean()
            response.save()
            return response
        selected_option = ReadingOption.objects.filter(id=int(option_id), item=item).first()
        if not selected_option:
            raise ValidationError("Tanlangan option itemga tegishli emas.")

    elif task.task_type == "multiple_choice":
        selected_option_ids = _resolve_selected_option_ids(item, payload.get("option_ids"))

    elif task.task_type in READING_TASK_SHARED_OPTION_TYPES:
        option_id = payload.get("option_id")
        if option_id in (None, ""):
            response.selected_option = None
            response.selected_option_ids = []
            response.text_answer = ""
            response.awarded_score = 0
            response.is_graded = False
            response.is_flagged_for_review = bool(payload.get("flag_for_review", response.is_flagged_for_review))
            response.full_clean()
            response.save()
            return response
        selected_option = ReadingOption.objects.filter(id=int(option_id), task=task).first()
        if not selected_option:
            raise ValidationError("Tanlangan option taskga tegishli emas.")

    elif task.task_type in READING_TASK_TEXT_TYPES:
        selected_option = None
    else:
        raise ValidationError("Ushbu reading task turi hali qo'llab-quvvatlanmaydi.")

    awarded_score, is_graded = _grade_response_for_item(
        item=item,
        selected_option=selected_option,
        selected_option_ids=selected_option_ids,
        text_answer=text_answer,
    )
    response.selected_option = selected_option
    response.selected_option_ids = selected_option_ids
    response.text_answer = text_answer
    response.awarded_score = awarded_score
    response.is_graded = is_graded
    response.is_flagged_for_review = bool(payload.get("flag_for_review", response.is_flagged_for_review))
    response.full_clean()
    response.save()

    state = ensure_exam_section_state(attempt=attempt, section=task.section)
    current_item_id = payload.get("current_item_id")
    try:
        current_item_id = int(current_item_id) if current_item_id not in (None, "") else item.id
    except (TypeError, ValueError):
        current_item_id = item.id
    state.state["current_item_id"] = current_item_id
    state.save(update_fields=["state", "updated_at"])
    return response


@transaction.atomic
def toggle_reading_review_flag(*, attempt, item, flagged=None):
    response, _ = ReadingResponse.objects.select_for_update().get_or_create(
        attempt=attempt,
        item=item,
    )
    response.is_flagged_for_review = (not response.is_flagged_for_review) if flagged is None else bool(flagged)
    response.full_clean()
    response.save(update_fields=["is_flagged_for_review", "updated_at"])

    state = ensure_exam_section_state(attempt=attempt, section=item.task.section)
    state.state["current_item_id"] = item.id
    state.save(update_fields=["state", "updated_at"])
    return response
