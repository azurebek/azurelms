"""Vazifa va quiz topshirish servislari — sayt view'lari va Telegram bot ulashadi.

Mantiq avval `courses/views.py` ichida edi (SubmitAssignmentView / SubmitQuizView);
bot ham xuddi shu qoidalar bilan ishlashi uchun shu yerga chiqarildi.
View'lar endi shu funksiyalarni chaqiradi — bitta manba, bitta xatti-harakat.
"""

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from cohorts.models import Enrollment, enrollment_active_access_q
from core.upload_validation import validate_upload
from courses.models import (
    AssignmentSubmission,
    Choice,
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


def has_course_access(user, course_id):
    return Enrollment.objects.filter(
        enrollment_active_access_q(), student=user, cohort__course_id=course_id
    ).exists()


def submit_assignment(*, user, assignment, answer_text="", attachment=None):
    """Vazifa javobini saqlash (yangi yoki qayta topshirish).

    Qayta topshirilganda holat pending'ga qaytadi va oldingi baho/izoh tozalanadi.
    """
    course_id = assignment.lesson.module.course_id
    if not has_course_access(user, course_id):
        return SubmissionResult(
            ok=False, code="no_access", message="Vazifa yuborish uchun faol obuna kerak."
        )

    if attachment is not None:
        # Baytlar bo'yicha tekshiruv — model field validatori `save()` yo'lida
        # ishlamaydi, shuning uchun gate shu canonical servisda turadi va uni
        # web view ham, Telegram bot ham ulashadi (A0b).
        try:
            validate_upload(attachment, profile="document", field_label="Biriktirma")
        except ValidationError as exc:
            return SubmissionResult(ok=False, code="invalid_attachment", message=exc.messages[0])

    submission, _ = AssignmentSubmission.objects.get_or_create(
        assignment=assignment, student=user
    )
    answer_text = (answer_text or "").strip()
    if not answer_text and not attachment and not submission.attachment:
        return SubmissionResult(
            ok=False, code="empty", message="Kamida matn yoki fayl yuborishingiz kerak."
        )

    if answer_text:
        submission.answer_text = answer_text
    if attachment:
        submission.attachment = attachment

    submission.status = AssignmentSubmission.STATUS_PENDING
    submission.teacher_feedback = ""
    submission.reviewed_by = None
    submission.reviewed_at = None
    submission.awarded_xp = 0
    submission.save()

    # Malakali kunlik faollik — o'quv seriyasini oshiradi.
    from users.streak import record_activity
    record_activity(user)

    return SubmissionResult(
        ok=True,
        code="submitted",
        message="Vazifa yuborildi — o'qituvchi tekshiruvini kuting.",
        submission=submission,
    )


def grade_quiz(*, user, quiz, answers):
    """Quiz javoblarini baholash. `answers`: {question_id(str|int): choice_id}.

    XP: eng yaxshi urinishdan oshgan qismigina beriladi (qayta yechish
    XP'ni takror bermaydi).
    """
    course_id = quiz.lesson.module.course_id if quiz.lesson_id else None
    if course_id and not has_course_access(user, course_id):
        return QuizGradeResult(ok=False, code="no_access", message="Kursga obuna bo'lmagansiz.")
    if not answers:
        return QuizGradeResult(ok=False, code="empty", message="Javoblar bo'sh.")

    questions = list(quiz.questions.prefetch_related("choices").all())
    total_questions = len(questions)
    if total_questions == 0:
        return QuizGradeResult(ok=False, code="no_questions", message="Quizda savollar yo'q.")

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
        selected_choice_id = answers.get(str(question.id), answers.get(question.id))
        correct_choice = next((c for c in question.choices.all() if c.is_correct), None)
        is_correct = False
        selected_choice = None

        if selected_choice_id:
            try:
                selected_choice = question.choices.get(id=int(selected_choice_id))
                is_correct = selected_choice.is_correct
            except (Choice.DoesNotExist, ValueError, TypeError):
                selected_choice = None

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
                "selected_choice_id": int(selected_choice_id) if selected_choice_id else None,
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
        user.total_xp += awarded_xp
        user.save(update_fields=["total_xp"])

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
    )
