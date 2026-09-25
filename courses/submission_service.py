"""Vazifa va quiz topshirish servislari — sayt view'lari va Telegram bot ulashadi.

Mantiq avval `courses/views.py` ichida edi (SubmitAssignmentView / SubmitQuizView);
bot ham xuddi shu qoidalar bilan ishlashi uchun shu yerga chiqarildi.
View'lar endi shu funksiyalarni chaqiradi — bitta manba, bitta xatti-harakat.
"""

from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from cohorts.models import Enrollment, enrollment_active_access_q
from core.upload_validation import validate_upload
from courses.models import (
    AssignmentSubmission,
    QuizAnswer,
    QuizAttempt,
)


@dataclass
class SubmissionResult:
    ok: bool
    code: str
    message: str
    submission: AssignmentSubmission | None = None


@dataclass
class QuizGradeResult:
    ok: bool
    code: str
    message: str = ""
    score: float = 0.0
    total_correct: int = 0
    total_questions: int = 0
    xp_earned: int = 0
    attempt_xp: int = 0
    results: list = field(default_factory=list)
    attempt_id: int | None = None


def has_course_access(user, course_id):
    return Enrollment.objects.filter(
        enrollment_active_access_q(), student=user, cohort__course_id=course_id
    ).exists()


def _active_submission_enrollment(user, course_id, enrollment):
    """An explicit cohort must never silently fall back to another cohort."""
    qs = Enrollment.objects.filter(
        enrollment_active_access_q(), student=user, cohort__course_id=course_id
    ).select_related('cohort')
    if enrollment is not None:
        qs = qs.filter(pk=enrollment.pk)
    return qs.order_by('-joined_at', '-pk').first()


@transaction.atomic
def submit_assignment(*, user, assignment, answer_text="", attachment=None,
                      enrollment=None, replace_review=False):
    """Vazifa javobini saqlash (yangi yoki qayta topshirish).

    Qayta topshirilganda holat pending'ga qaytadi va oldingi baho/izoh tozalanadi.
    """
    course_id = assignment.lesson.module.course_id
    enrollment = _active_submission_enrollment(user, course_id, enrollment)
    if enrollment is None:
        return SubmissionResult(
            ok=False, code="no_access", message="Vazifa yuborish uchun faol obuna kerak."
        )

    # Obuna — kurs darajasidagi ruxsat; u dars ochilganini bildirmaydi.
    # Ilgari bu tekshiruv faqat sahifa ko'rsatishda bor edi, ya'ni yopiq
    # darsning submit URL'iga to'g'ridan-to'g'ri POST ishlayverardi va bot
    # tomonida `BotPendingAction` qulf o'zgargandan keyin ham amal qilardi.
    from .access_service import check_lesson_access

    access = check_lesson_access(user=user, lesson=assignment.lesson, enrollment=enrollment)
    if not access.is_allowed:
        return SubmissionResult(ok=False, code="locked", message=access.message)

    if attachment is not None:
        # Baytlar bo'yicha tekshiruv — model field validatori `save()` yo'lida
        # ishlamaydi, shuning uchun gate shu canonical servisda turadi va uni
        # web view ham, Telegram bot ham ulashadi (A0b).
        try:
            validate_upload(attachment, profile="document", field_label="Biriktirma")
        except ValidationError as exc:
            return SubmissionResult(ok=False, code="invalid_attachment", message=exc.messages[0])

    # A stable user row serializes creation/resubmission with review, even
    # before a student's first submission exists.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=user).first()
    answer_text = (answer_text or "").strip()
    if not answer_text and not attachment and not (submission and submission.attachment):
        return SubmissionResult(
            ok=False, code="empty", message="Kamida matn yoki fayl yuborishingiz kerak."
        )

    if submission and submission.status != AssignmentSubmission.STATUS_PENDING and not replace_review:
        return SubmissionResult(ok=False, code='confirm_review', message="Qayta yuborish avvalgi baho, XP va izohni tozalashini tasdiqlang.")
    if submission is None:
        submission = AssignmentSubmission(assignment=assignment, student=user)
    elif (submission.status == AssignmentSubmission.STATUS_PENDING and not attachment
          and (not answer_text or answer_text == submission.answer_text)):
        return SubmissionResult(ok=True, code='unchanged', message="Bu javob allaqachon tekshiruvda.", submission=submission)

    if answer_text:
        submission.answer_text = answer_text
    if attachment:
        submission.attachment = attachment

    submission.status = AssignmentSubmission.STATUS_PENDING
    submission.teacher_feedback = ""
    submission.reviewed_by = None
    submission.reviewed_at = None
    previous_xp = submission.awarded_xp
    submission.awarded_xp = 0
    submission.save()
    if previous_xp:
        from users.xp import award_xp
        award_xp(user, -previous_xp)

    # Malakali kunlik faollik — o'quv seriyasini oshiradi.
    from users.streak import record_activity
    record_activity(user)

    return SubmissionResult(
        ok=True,
        code="submitted",
        message="Vazifa yuborildi — o'qituvchi tekshiruvini kuting.",
        submission=submission,
    )


def _positive_id(value):
    if type(value) is int:
        return value if 0 < value < 2**63 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 19:
        parsed = int(value)
        return parsed if 0 < parsed < 2**63 else None
    return None


@transaction.atomic
def grade_quiz(*, user, quiz, answers, enrollment=None):
    """Quiz javoblarini baholash. `answers`: {question_id(str|int): choice_id}.

    XP: eng yaxshi urinishdan oshgan qismigina beriladi (qayta yechish
    XP'ni takror bermaydi).
    """
    course_id = quiz.lesson.module.course_id if quiz.lesson_id else None
    if course_id:
        enrollment = _active_submission_enrollment(user, course_id, enrollment)
    if course_id and enrollment is None:
        return QuizGradeResult(ok=False, code="no_access", message="Kursga obuna bo'lmagansiz.")

    # Dars qulfi — `submit_assignment` dagi bilan bir xil sabab. Imtihon
    # bo'limiga tegishli quizda `lesson` yo'q, u alohida attempt lifecycle
    # bilan boshqariladi, shuning uchun bu gate faqat dars quizlariga.
    if quiz.lesson_id:
        from .access_service import check_lesson_access

        access = check_lesson_access(user=user, lesson=quiz.lesson, enrollment=enrollment)
        if not access.is_allowed:
            return QuizGradeResult(ok=False, code="locked", message=access.message)
    if not isinstance(answers, dict):
        return QuizGradeResult(ok=False, code='invalid_answers', message="Javoblar formati noto‘g‘ri.")
    if not answers:
        return QuizGradeResult(ok=False, code="empty", message="Javoblar bo'sh.")

    questions = list(quiz.questions.prefetch_related("choices").order_by('pk'))
    total_questions = len(questions)
    if total_questions == 0:
        return QuizGradeResult(ok=False, code="no_questions", message="Quizda savollar yo'q.")

    # Validate all inputs before creating any attempt/answer/XP.
    choices_by_question = {q.pk: {c.pk: c for c in q.choices.all()} for q in questions}
    selected = {}
    for key, value in answers.items():
        question_id = _positive_id(key)
        choice_id = None if value is None or value == '' else _positive_id(value)
        if (question_id not in choices_by_question or question_id in selected
                or (value is not None and value != '' and choice_id not in choices_by_question[question_id])):
            return QuizGradeResult(ok=False, code='invalid_answers', message="Savol yoki javob varianti ushbu quizga mos emas.")
        selected[question_id] = choices_by_question[question_id].get(choice_id)

    # Read the best XP only after acquiring the per-student lock.
    get_user_model().objects.select_for_update().get(pk=user.pk)

    previous_best_xp = (
        QuizAttempt.objects.filter(student=user, quiz=quiz)
        .aggregate(best_xp=Max("xp_earned"))
        .get("best_xp")
        or 0
    )
    attempt = QuizAttempt.objects.create(
        student=user, quiz=quiz, total_questions=total_questions
    )

    total_correct = 0
    results = []
    for question in questions:
        selected_choice = selected.get(question.pk)
        correct_choice = next((c for c in question.choices.all() if c.is_correct), None)
        is_correct = bool(selected_choice and selected_choice.is_correct)

        if is_correct:
            total_correct += 1
        if selected_choice:
            QuizAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct,
            )
        results.append(
            {
                "question_id": question.id,
                "selected_choice_id": selected_choice.pk if selected_choice else None,
                "correct_choice_id": correct_choice.id if correct_choice else None,
                "is_correct": is_correct,
            }
        )

    score = round((total_correct / total_questions) * 100, 1)
    attempt_xp = round(quiz.xp_reward * (total_correct / total_questions))
    awarded_xp = max(0, attempt_xp - previous_best_xp)

    attempt.score = score
    attempt.total_correct = total_correct
    attempt.xp_earned = attempt_xp
    attempt.save()

    if awarded_xp > 0:
        from users.xp import award_xp

        award_xp(user, awarded_xp)

    # Quizni yechish — malakali kunlik faollik.
    from users.streak import record_activity
    record_activity(user)

    return QuizGradeResult(
        ok=True,
        code="graded",
        score=score,
        total_correct=total_correct,
        total_questions=total_questions,
        xp_earned=awarded_xp,
        attempt_xp=attempt_xp,
        results=results,
        attempt_id=attempt.pk,
    )


@transaction.atomic
def review_assignment_submission(
    *,
    submission,
    approved,
    reviewer,
    feedback=None,
    awarded_xp=None,
    request=None,
    expected_revision=None,
):
    """Vazifani baholaydi: hukm, XP va o'quvchiga xabar — bitta joyda.

    XP **farq** bo'yicha hisoblanadi (`upsert_attendance_and_xp` bilan bir xil
    naqsh): qayta baholash ikki marta bermaydi, bahoni pasaytirish esa
    balansdan ayiradi. Ilgari `awarded_xp` faqat `AssignmentSubmission`
    qatoriga yozilardi va `user.total_xp` ga hech qachon qo'shilmasdi — ya'ni
    o'qituvchi bergan XP o'quvchiga yetib bormasdi.

    Xabar faqat hukm o'zgarganda yuboriladi: bir xil bahoni qayta saqlash
    o'quvchining telefonini ikkinchi marta chalmaydi.
    """
    from core.audit import record_audit_event

    # Refresh under the same lock used by resubmission; the caller may hold
    # a stale instance from another tab or bot interaction.
    get_user_model().objects.select_for_update().get(pk=submission.student_id)
    submission.refresh_from_db()
    if expected_revision is not None and expected_revision != submission.updated_at.isoformat():
        raise ValidationError(
            'Ish siz ochganingizdan keyin yangilangan. Qaror saqlanmadi. Joriy javobni qayta o‘qing va tasdiqlang.',
            code='stale_review',
        )

    new_status = (
        AssignmentSubmission.STATUS_APPROVED
        if approved
        else AssignmentSubmission.STATUS_NEEDS_REVISION
    )
    previous_status = submission.status
    previous_xp = submission.awarded_xp

    if awarded_xp is None:
        new_xp = previous_xp
    else:
        new_xp = max(0, min(int(awarded_xp), submission.assignment.max_xp))
    # Qayta ishlashga qaytarilgan ish uchun XP saqlanmaydi.
    if not approved:
        new_xp = 0

    with transaction.atomic():
        if feedback is not None:
            submission.teacher_feedback = feedback
        submission.status = new_status
        submission.awarded_xp = new_xp
        submission.reviewed_by = reviewer
        submission.reviewed_at = timezone.now()
        submission.save()

        xp_diff = new_xp - previous_xp
        if xp_diff:
            from users.xp import award_xp

            award_xp(submission.student, xp_diff)

        record_audit_event(
            action="assignment.review",
            request=request,
            actor=reviewer,
            target=submission,
            target_label=f"{submission.assignment.title} — {submission.student.username}",
            before={"status": previous_status, "awarded_xp": previous_xp},
            after={"status": new_status, "awarded_xp": new_xp},
        )

        if new_status != previous_status:
            _notify_reviewed(submission=submission, approved=approved)

    return submission


def _notify_reviewed(*, submission, approved):
    from users.notification_service import create_notification

    lesson = submission.assignment.lesson
    title = "Vazifangiz tasdiqlandi" if approved else "Vazifa qayta ishlashga qaytarildi"
    if approved:
        message = f"\"{submission.assignment.title}\" vazifangiz tasdiqlandi."
        if submission.awarded_xp:
            message += f" {submission.awarded_xp} XP qo'shildi."
    else:
        message = (
            f"\"{submission.assignment.title}\" vazifangiz qayta ishlashga qaytarildi. "
            "O'qituvchi izohini o'qib, qaytadan yuboring."
        )

    create_notification(
        recipient=submission.student,
        title=title,
        message=message,
        icon="check2-circle" if approved else "arrow-counterclockwise",
        url=f"/courses/{lesson.module.course_id}/lesson/{lesson.id}/",
        external_key=f"assignment-review-{submission.id}-{submission.reviewed_at.isoformat()}",
    )
