"""Bounded, read-only learning records for the existing learner support card.

This does not grade work, recalculate progress, open learner views, or create
review rows. Course scope and learner lookup use the same support policies as
the access diagnosis; exam scores come only from the canonical publication.
"""

from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Subquery
from django.urls import reverse

from core.access import teacher_course_queryset
from core.flags import flag_enabled
from core.student_support_service import _actor, _students
from courses.exam_publication import learner_result
from courses.models import Assignment, AssignmentSubmission, ExamAttempt, Lesson, QuizAttempt


# A presentation page size, not a limit on attempts or an operational policy.
PAGE_SIZE = 6


def _assignment_row(assignment):
    submission = next(iter(assignment.support_submissions), None)
    row = {
        'id': assignment.pk, 'title': assignment.title,
        'lesson_title': assignment.lesson.title, 'score': None,
        'awarded_xp': None, 'updated_at': None, 'action_url': '', 'action_label': '',
        'status': 'empty', 'status_label': 'Yuborilmagan',
        'detail': 'Bu topshiriq uchun yuborilgan ish qaydi yo‘q.',
        'learner_label': 'Tekshiruv natijasi hali yo‘q.',
    }
    if submission is None:
        return row
    row.update(
        submission_id=submission.pk, updated_at=submission.updated_at,
        action_url=reverse('teacher_grade_assignment', kwargs={'submission_id': submission.pk}),
        action_label='Ishni ko‘rib chiqish',
    )
    if submission.status == AssignmentSubmission.STATUS_APPROVED:
        row.update(status='approved', status_label='Tasdiqlangan',
                   detail='Ustoz ishni tekshirib, tasdiqlagan.',
                   learner_label='Tasdiqlangan holat va ustoz izohi o‘quvchi uchun saqlangan.',
                   awarded_xp=submission.awarded_xp)
    elif submission.status == AssignmentSubmission.STATUS_NEEDS_REVISION:
        row.update(status='revision', status_label='Qayta ishlash kerak',
                   detail='Ustoz ishni to‘ldirish uchun qaytargan.',
                   learner_label='Qayta ishlash talabi va ustoz izohi o‘quvchi uchun saqlangan.')
    else:
        row.update(status='pending', status_label='Tekshiruv kutilmoqda',
                   detail='Ish yuborilgan. Ustozning yakuniy qarori hali yo‘q.',
                   learner_label='Yuborilgan ish holati ko‘rinadi; tasdiqlangan natija hali yo‘q.')
    return row


def _quiz_row(attempt):
    is_latest = attempt.pk == attempt.support_latest_id
    return {
        'id': attempt.pk, 'title': attempt.quiz.title,
        'lesson_title': attempt.quiz.lesson.title, 'status': 'recorded',
        'status_label': 'Natija saqlangan', 'score': attempt.score,
        'total_correct': attempt.total_correct, 'total_questions': attempt.total_questions,
        'updated_at': attempt.completed_at, 'is_latest': is_latest,
        'detail': 'Bu oddiy testning saqlangan natijasi; ustoz tasdig‘ini kutmaydi.',
        'learner_label': ('O‘quvchi darsida ko‘rsatiladigan oxirgi natija.' if is_latest else
                          'Oldingi urinish. O‘quvchi darsida yangiroq natija ko‘rsatiladi.'),
        'action_url': '', 'action_label': '',
    }


def _exam_row(attempt, *, review_enabled):
    result = learner_result(attempt)
    is_latest = attempt.pk == attempt.support_latest_id
    reviewed = result['is_reviewed']
    row = {
        'id': attempt.pk, 'title': attempt.exam.title,
        'attempt_number': attempt.attempt_number, 'is_latest': is_latest,
        'status': 'in_progress', 'status_label': 'Hali yakunlanmagan',
        'detail': 'Imtihon urinishi boshlangan, lekin yakunlangan qayd yo‘q.',
        'learner_label': 'Tasdiqlangan natija hali yo‘q.', 'score': None,
        'updated_at': attempt.completed_time or attempt.start_time,
        'result_visible': False, 'details_unavailable': result['details_unavailable'],
        'action_url': '', 'action_label': '',
        'action_note': '',
    }
    if attempt.is_completed:
        row.update(
            status='pending', status_label='Tekshiruv kutilmoqda',
            detail='Imtihon topshirilgan. Baholash qoralamasi yakuniy natija emas.',
            learner_label='Yakuniy natija o‘quvchiga hali ochilmagan.',
        )
        if review_enabled:
            row.update(action_url=reverse('teacher_grade_exam', kwargs={'attempt_id': attempt.pk}),
                       action_label='Imtihonni ko‘rib chiqish')
        else:
            row['action_note'] = 'Batafsil ko‘rib chiqish sahifasi hozir yoqilmagan.'
    if reviewed:
        row.update(
            status='approved', status_label='Natija tasdiqlangan',
            score=result['score'], result_visible=is_latest,
            updated_at=result['reviewed_at'] or row['updated_at'],
            detail='O‘tgan.' if result['passed'] else 'O‘tish bali yetmagan.',
            learner_label=('O‘quvchi uchun ochilgan oxirgi natija.' if is_latest else
                           'Oldingi urinishning tasdiqlangan natijasi. O‘quvchi sahifasida oxirgi urinish ko‘rsatiladi.'),
        )
        if result['details_unavailable']:
            row['detail'] += ' Eski natija: faqat tasdiqlangan umumiy ball saqlangan.'
    return row


def build_student_results(*, actor, student_id, course_id, lesson_id=None,
                          assignment_page=1, quiz_page=1, exam_page=1):
    """Return three independent pages; do not trust previously loaded objects.

    The view resolves its normal course/lesson selection first. No selection
    produces empty pages; an explicit mismatched parent raises DoesNotExist.
    Exam history is course-wide because exams are not children of a lesson.
    """
    actor = _actor(actor)
    student = _students(actor).only('pk').get(pk=student_id)
    course = teacher_course_queryset(actor).only('pk', 'title').get(pk=course_id) if course_id is not None else None
    lesson = None
    if lesson_id is not None:
        if course is None:
            raise Lesson.DoesNotExist
        lesson = Lesson.objects.only('pk', 'title').get(pk=lesson_id, module__course=course)

    assignments = Assignment.objects.none()
    quizzes = QuizAttempt.objects.none()
    exams = ExamAttempt.objects.none()
    if course is not None:
        submissions = AssignmentSubmission.objects.filter(student=student).only(
            'pk', 'assignment_id', 'status', 'awarded_xp', 'updated_at')
        assignments = Assignment.objects.filter(lesson__module__course=course).select_related('lesson').only(
            'pk', 'title', 'lesson_id', 'lesson__title').prefetch_related(
                Prefetch('submissions', queryset=submissions, to_attr='support_submissions')
            ).order_by('lesson__module__order', 'lesson__module_id', 'lesson__order', 'lesson_id', 'pk')
        # An imported quiz with both parent fields is ambiguous. Do not let its
        # lesson relationship expose an exam-bound record from another scope.
        quizzes = QuizAttempt.objects.filter(
            student=student, quiz__lesson__module__course=course, quiz__exam_section__isnull=True,
        ).select_related('quiz__lesson').only(
            'pk', 'quiz_id', 'score', 'total_correct', 'total_questions', 'completed_at',
            'quiz__title', 'quiz__lesson_id', 'quiz__lesson__title',
        ).annotate(support_latest_id=Subquery(
            QuizAttempt.objects.filter(student=student, quiz_id=OuterRef('quiz_id'))
            .order_by('-completed_at', '-pk').values('pk')[:1]
        )).order_by('-completed_at', '-pk')
        if lesson is not None:
            assignments = assignments.filter(lesson=lesson)
            quizzes = quizzes.filter(quiz__lesson=lesson)
        exams = ExamAttempt.objects.filter(student=student, exam__course=course).select_related(
            'exam', 'result_publication',
        ).only(
            'pk', 'exam_id', 'attempt_number', 'start_time', 'completed_time',
            'is_completed', 'is_reviewed', 'score', 'passed', 'reviewed_at',
            'exam__title', 'result_publication__attempt_id', 'result_publication__payload',
        ).annotate(support_latest_id=Subquery(
            ExamAttempt.objects.filter(student=student, exam_id=OuterRef('exam_id'))
            .order_by('-attempt_number', '-pk').values('pk')[:1]
        )).order_by('-start_time', '-pk')

    assignment_page_obj = Paginator(assignments, PAGE_SIZE).get_page(assignment_page)
    quiz_page_obj = Paginator(quizzes, PAGE_SIZE).get_page(quiz_page)
    exam_page_obj = Paginator(exams, PAGE_SIZE).get_page(exam_page)
    review_enabled = flag_enabled('frontend_v1_exam_review')
    assignment_rows = [_assignment_row(item) for item in assignment_page_obj]
    quiz_rows = [_quiz_row(item) for item in quiz_page_obj]
    exam_rows = [_exam_row(item, review_enabled=review_enabled) for item in exam_page_obj]
    # Templates receive summaries only, including when they iterate a pager.
    # Never leave model instances or publication payloads in the page context.
    for page, rows in ((assignment_page_obj, assignment_rows),
                       (quiz_page_obj, quiz_rows), (exam_page_obj, exam_rows)):
        page.object_list = rows
    return {
        'selected_course': course, 'selected_lesson': lesson,
        'scope_label': lesson.title if lesson else course.title if course else 'Kurs tanlanmagan',
        'exam_scope_label': f'{course.title} kursidagi imtihonlar' if course else 'Kurs tanlanmagan',
        'assignment_rows': assignment_rows,
        'assignment_page_obj': assignment_page_obj,
        'quiz_rows': quiz_rows, 'quiz_page_obj': quiz_page_obj,
        'exam_rows': exam_rows, 'exam_page_obj': exam_page_obj,
    }
