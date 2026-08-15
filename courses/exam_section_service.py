"""Generic (non-reading) exam section runtime engine.

Reading bo'limlari uchun boy section-state `reading_service` da. Bu modul aynan
shu funksionallikni listening / grammar_quiz (Question+Choice, avto-baholash) va
writing / speaking (StudentAnswer matn/audio, qo'lda) uchun beradi — saqlab-borish,
per-savol holat (question_map/counts), review-flag. `build_section_payload`
dispatcher ikkalasini birlashtiradi.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Choice, StudentAnswer
from .reading_service import build_reading_section_payload, ensure_exam_section_state

# Writing javobi uchun xavfsizlik chegarasi (text-bomb himoyasi). ~60k belgi ≈ 10k so'z.
MAX_ANSWER_TEXT_CHARS = 60_000


def _word_count(value):
    return len([token for token in (value or "").strip().split() if token])


def word_count_status(question, word_count):
    """Writing so'z talabi holati: ok / too_short / too_long; chegara yo'q bo'lsa None."""
    min_words = question.min_word_count or 0
    max_words = question.max_word_count or 0
    if not min_words and not max_words:
        return None
    if min_words and word_count < min_words:
        return "too_short"
    if max_words and word_count > max_words:
        return "too_long"
    return "ok"


def _serialize_choice(choice):
    return {"id": choice.id, "text": choice.text}


def _serialize_student_answer(answer, question):
    if not answer:
        return {
            "selected_choice_id": None,
            "answer_text": "",
            "audio_url": "",
            "is_flagged_for_review": False,
            "awarded_score": 0,
            "is_graded": False,
            "grader_feedback": "",
            "word_count": 0,
            "word_count_status": word_count_status(question, 0),
        }
    word_count = answer.word_count
    return {
        "selected_choice_id": answer.selected_choice_id,
        "answer_text": answer.answer_text or "",
        "audio_url": answer.audio_playback_url,
        "is_flagged_for_review": answer.is_flagged_for_review,
        "awarded_score": float(answer.awarded_score),
        "is_graded": answer.is_graded,
        "grader_feedback": answer.grader_feedback or "",
        "word_count": word_count,
        "word_count_status": word_count_status(question, word_count),
    }


def _build_status_counts(question_map):
    counts = {"done": 0, "review": 0, "pending": 0, "current": 0}
    for item in question_map:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    counts["answered"] = counts["done"] + counts["review"]
    return counts


def build_question_section_payload(*, attempt, section):
    """Listening/grammar/writing/speaking uchun reading bilan bir xil shakldagi payload."""
    if section.exam_id != attempt.exam_id:
        raise ValidationError("Section ushbu attempt imtihoniga tegishli emas.")

    state = ensure_exam_section_state(attempt=attempt, section=section)
    questions = list(section.questions.prefetch_related("choices").order_by("id"))
    answers = {
        answer.question_id: answer
        for answer in attempt.answers.filter(question__exam_section=section).select_related("selected_choice")
    }

    question_ids = {question.id for question in questions}
    current_question_id = state.state.get("current_question_id")
    if current_question_id not in question_ids:
        current_question_id = questions[0].id if questions else None
        if current_question_id:
            state.state["current_question_id"] = current_question_id
            state.save(update_fields=["state", "updated_at"])

    question_map = []
    serialized_questions = []
    for index, question in enumerate(questions, start=1):
        answer = answers.get(question.id)
        status = "pending"
        if answer and answer.is_flagged_for_review:
            status = "review"
        elif answer and answer.is_answered:
            status = "done"
        elif question.id == current_question_id:
            status = "current"
        question_map.append({"question_id": question.id, "label": str(index), "status": status})
        serialized_questions.append(
            {
                "id": question.id,
                "text": str(question.text or ""),
                "points": question.points,
                "min_word_count": question.min_word_count,
                "max_word_count": question.max_word_count,
                "choices": [_serialize_choice(choice) for choice in question.choices.all()],
                "response": _serialize_student_answer(answer, question),
            }
        )

    return {
        "section": {
            "id": section.id,
            "title": section.title,
            "section_type": section.section_type,
            "instructions": section.instructions or "",
            "media_url": section.media_url or "",
            "time_limit_minutes": section.time_limit_minutes,
            "audio_play_limit": section.audio_play_limit,
            "plays_used": int(state.state.get("plays_used", 0)),
            "plays_left": (max(section.audio_play_limit - int(state.state.get("plays_used", 0)), 0) if section.audio_play_limit else None),
        },
        "state": {
            "current_question_id": current_question_id,
            "question_map": question_map,
            "counts": _build_status_counts(question_map),
        },
        "questions": serialized_questions,
    }


@transaction.atomic
def save_question_answer(*, attempt, question, payload):
    """StudentAnswer'ni upsert qiladi, choice'ni avto-baholaydi, section-state'ni yangilaydi."""
    if question.exam_section_id and question.exam_section.exam_id != attempt.exam_id:
        raise ValidationError("Savol ushbu imtihon urinishiga tegishli emas.")

    answer, _ = StudentAnswer.objects.select_for_update().get_or_create(attempt=attempt, question=question)

    choice_id = payload.get("choice_id")
    answer_text = payload.get("answer_text")
    audio_key = payload.get("audio_key")

    if choice_id not in (None, ""):
        choice = Choice.objects.filter(id=int(choice_id), question=question).first()
        if not choice:
            raise ValidationError("Tanlangan variant savolga tegishli emas.")
        answer.selected_choice = choice
        answer.awarded_score = question.points if choice.is_correct else 0
        answer.is_graded = True
    elif "choice_id" in payload:  # bo'sh choice_id — javobni tozalash
        answer.selected_choice = None
        answer.awarded_score = 0
        answer.is_graded = False

    if answer_text is not None:
        # So'z soni bo'yicha bloklamaymiz (autosave xavfsizligi) — faqat mutlaq belgi chegarasi.
        if len(answer_text) > MAX_ANSWER_TEXT_CHARS:
            raise ValidationError(
                f"Javob matni juda uzun ({len(answer_text)} belgi). Chegara: {MAX_ANSWER_TEXT_CHARS} belgi."
            )
        answer.answer_text = answer_text
    if audio_key is not None:
        # Private storage kaliti; havola `audio_playback_url` orqali quriladi (A0b).
        answer.audio_key = audio_key
    if "flag_for_review" in payload:
        answer.is_flagged_for_review = bool(payload.get("flag_for_review"))

    answer.save()

    section = question.exam_section
    if section:
        state = ensure_exam_section_state(attempt=attempt, section=section)
        current_question_id = payload.get("current_question_id")
        try:
            current_question_id = int(current_question_id) if current_question_id not in (None, "") else question.id
        except (TypeError, ValueError):
            current_question_id = question.id
        state.state["current_question_id"] = current_question_id
        state.save(update_fields=["state", "updated_at"])
    return answer


@transaction.atomic
def toggle_question_review_flag(*, attempt, question, flagged=None):
    answer, _ = StudentAnswer.objects.select_for_update().get_or_create(attempt=attempt, question=question)
    answer.is_flagged_for_review = (not answer.is_flagged_for_review) if flagged is None else bool(flagged)
    answer.save(update_fields=["is_flagged_for_review", "updated_at"])
    section = question.exam_section
    if section:
        state = ensure_exam_section_state(attempt=attempt, section=section)
        state.state["current_question_id"] = question.id
        state.save(update_fields=["state", "updated_at"])
    return answer


def build_section_payload(*, attempt, section):
    """Dispatcher: ReadingTask'li section → boy task engine; qolganlari → question engine.

    Engine section TURI bo'yicha emas, balki STRUKTURA bo'yicha tanlanadi: agar section'da
    ReadingTask bo'lsa (reading yoki rich listening), boy engine (8 task turi, to'liq
    avto-baholash); aks holda oddiy Question/Choice engine (MCQ avto, matn qo'lda).
    Ikki payload bir xil 'section' + 'state{question_map, counts}' shaklida — frontend
    ularni bir xil section-rail bilan ishlata oladi.
    """
    if section.reading_tasks.exists():
        return build_reading_section_payload(attempt=attempt, section=section)
    return build_question_section_payload(attempt=attempt, section=section)


@transaction.atomic
def register_audio_play(*, attempt, section):
    """Listening audiosi tinglanishini qayd qiladi va limitni SERVER tomonda majburlaydi.

    Holat ExamSectionAttemptState.state['plays_used'] da. Limit tugagan bo'lsa allowed=False
    va hisob oshmaydi (frontend soxta qila olmaydi).
    Returns: {allowed, plays_used, plays_left, limit}.
    """
    if section.exam_id != attempt.exam_id:
        raise ValidationError("Section ushbu attempt imtihoniga tegishli emas.")
    state = ensure_exam_section_state(attempt=attempt, section=section)
    limit = section.audio_play_limit or 0
    used = int(state.state.get("plays_used", 0))
    if limit and used >= limit:
        return {"allowed": False, "plays_used": used, "plays_left": 0, "limit": limit}
    used += 1
    state.state["plays_used"] = used
    state.save(update_fields=["state", "updated_at"])
    return {
        "allowed": True,
        "plays_used": used,
        "plays_left": (max(limit - used, 0) if limit else None),
        "limit": limit,
    }
