from dataclasses import dataclass, field

from cohorts.models import Attendance, Enrollment

from .models import Assignment, AssignmentSubmission, ExamAttempt, Lesson, LessonProgress


def _safe_percent(done, total):
    if total <= 0:
        return 100
    return int(round((done / total) * 100))


@dataclass
class CourseProgressMetrics:
    total_lessons: int = 0
    completed_lessons: int = 0
    lesson_completion_percent: int = 100
    total_assignments: int = 0
    approved_assignments: int = 0
    assignment_completion_percent: int = 100
    total_attendance_records: int = 0
    attended_records: int = 0
    attendance_percent: int = 100


@dataclass
class PolicyCheckResult:
    is_allowed: bool
    code: str = ""
    message: str = ""
    metrics: CourseProgressMetrics | None = None
    reasons: list[str] = field(default_factory=list)


def build_course_progress_metrics(*, student, course):
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = (
        LessonProgress.objects.filter(
            enrollment__student=student,
            enrollment__cohort__course=course,
            is_completed=True,
        )
        .values("lesson_id")
        .distinct()
        .count()
    )

    total_assignments = Assignment.objects.filter(lesson__module__course=course).count()
    approved_assignments = (
        AssignmentSubmission.objects.filter(
            student=student,
            assignment__lesson__module__course=course,
            status=AssignmentSubmission.STATUS_APPROVED,
        )
        .values("assignment_id")
        .distinct()
        .count()
    )

    total_attendance_records = Attendance.objects.filter(
        enrollment__student=student,
        enrollment__cohort__course=course,
    ).count()
    attended_records = Attendance.objects.filter(
        enrollment__student=student,
        enrollment__cohort__course=course,
        status__in={Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL},
    ).count()

    return CourseProgressMetrics(
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        lesson_completion_percent=_safe_percent(completed_lessons, total_lessons),
        total_assignments=total_assignments,
        approved_assignments=approved_assignments,
        assignment_completion_percent=_safe_percent(approved_assignments, total_assignments),
        total_attendance_records=total_attendance_records,
        attended_records=attended_records,
        attendance_percent=_safe_percent(attended_records, total_attendance_records),
    )


def check_exam_entry_policy(*, student, exam):
    active_enrollment = (
        Enrollment.objects.with_active_access()
        .filter(student=student, cohort__course=exam.course)
        .select_related("cohort")
        .order_by("-joined_at", "-id")
        .first()
    )
    if not active_enrollment:
        return PolicyCheckResult(
            is_allowed=False,
            code="not_enrolled",
            message="Siz ushbu kursga faol obuna bilan biriktirilmagansiz.",
        )

    if exam.prerequisite_exam_id:
        prerequisite_passed = ExamAttempt.objects.filter(
            student=student,
            exam=exam.prerequisite_exam,
            passed=True,
            is_reviewed=True,
        ).exists()
        if not prerequisite_passed:
            return PolicyCheckResult(
                is_allowed=False,
                code="prerequisite_exam",
                message=(
                    f"Avval {exam.prerequisite_exam.title} imtihonidan muvaffaqiyatli o'tishingiz kerak."
                ),
            )

    needs_metrics = any(
        [
            exam.requires_all_assignments_approved,
            exam.minimum_lesson_completion_percent,
            exam.minimum_attendance_percent,
        ]
    )
    metrics = build_course_progress_metrics(student=student, course=exam.course) if needs_metrics else None

    if exam.requires_all_assignments_approved and metrics and metrics.approved_assignments < metrics.total_assignments:
        return PolicyCheckResult(
            is_allowed=False,
            code="assignment_prerequisite",
            message="Imtihonni boshlashdan oldin kurs assignmentlari tasdiqlanishi kerak.",
            metrics=metrics,
        )

    if exam.minimum_lesson_completion_percent and metrics:
        if metrics.lesson_completion_percent < exam.minimum_lesson_completion_percent:
            return PolicyCheckResult(
                is_allowed=False,
                code="lesson_completion_prerequisite",
                message=(
                    f"Imtihon uchun kamida {exam.minimum_lesson_completion_percent}% lesson completion talab qilinadi."
                ),
                metrics=metrics,
            )

    if exam.minimum_attendance_percent and metrics:
        if metrics.attendance_percent < exam.minimum_attendance_percent:
            return PolicyCheckResult(
                is_allowed=False,
                code="attendance_prerequisite",
                message=(
                    f"Imtihon uchun kamida {exam.minimum_attendance_percent}% attendance talab qilinadi."
                ),
                metrics=metrics,
            )

    return PolicyCheckResult(is_allowed=True, metrics=metrics)


def check_certificate_policy(*, student, course):
    metrics = build_course_progress_metrics(student=student, course=course)
    reasons = []

    if course.certificate_requires_all_assignments_approved and (
        metrics.approved_assignments < metrics.total_assignments
    ):
        reasons.append("Barcha assignmentlar hali tasdiqlanmagan.")

    if (
        course.certificate_min_lesson_completion_percent
        and metrics.lesson_completion_percent < course.certificate_min_lesson_completion_percent
    ):
        reasons.append(
            f"Lesson completion kamida {course.certificate_min_lesson_completion_percent}% bo'lishi kerak."
        )

    if course.certificate_min_attendance_percent and (
        metrics.attendance_percent < course.certificate_min_attendance_percent
    ):
        reasons.append(
            f"Attendance kamida {course.certificate_min_attendance_percent}% bo'lishi kerak."
        )

    return PolicyCheckResult(
        is_allowed=not reasons,
        code="certificate_policy" if reasons else "",
        metrics=metrics,
        reasons=reasons,
        message=" ".join(reasons),
    )
