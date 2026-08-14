import json
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.views.generic import ListView, DetailView, View
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import Http404, JsonResponse
from django.utils import timezone

from core.upload_validation import validate_upload

from .models import (
    Assignment,
    AssignmentSubmission,
    Certificate,
    CohortLessonRelease,
    Course,
    Exam,
    ExamSection,
    LessonProgress,
    Lesson,
    Question,
    Choice,
    ReadingItem,
    StudentAnswer,
    ExamAttempt,
    Quiz,
    QuizAnswer,
    QuizAttempt,
)
from cohorts.models import Enrollment, enrollment_active_access_q
from .exam_service import (
    ExamAttemptStartBlocked,
    expire_attempt_if_time_limit_reached,
    get_in_progress_exam_attempt,
    get_latest_exam_attempt,
    get_latest_exam_attempt_for_exam_id,
    start_exam_attempt,
)
from .policy_service import check_exam_entry_policy
from .reading_service import (
    build_reading_section_payload,
    save_reading_response,
    toggle_reading_review_flag,
)
from .exam_section_service import (
    word_count_status,
    build_question_section_payload,
    build_section_payload,
    register_audio_play,
    save_question_answer,
    toggle_question_review_flag,
)


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _requested_cohort_id(request):
    return _safe_int(request.GET.get("cohort"))


def _build_url_with_query(base_url, **params):
    query = {key: value for key, value in params.items() if value not in (None, "", [], ())}
    if not query:
        return base_url
    return f"{base_url}?{urlencode(query)}"


def _get_active_enrollment_for_course(user, course, cohort_id=None):
    queryset = (
        Enrollment.objects.filter(
            enrollment_active_access_q(),
            student=user,
            cohort__course=course,
        )
        .select_related("cohort")
        .order_by("-joined_at", "-id")
    )
    if cohort_id:
        selected = queryset.filter(cohort_id=cohort_id).first()
        if selected:
            return selected
    return queryset.first()


def _build_lesson_access_bundle(course, user, enrollment):
    lessons = list(
        Lesson.objects.filter(module__course=course)
        .select_related("module")
        .prefetch_related("assignments")
        .order_by("module__order", "order")
    )
    lesson_access_map = {}
    first_accessible_lesson = None

    drip_enabled = False
    released_lesson_ids = set()
    if enrollment:
        release_qs = CohortLessonRelease.objects.filter(
            cohort=enrollment.cohort,
            lesson__module__course=course,
        )
        drip_enabled = release_qs.exists()
        released_lesson_ids = set(
            release_qs.filter(is_released=True).values_list("lesson_id", flat=True)
        )

    approved_assignment_ids = set()
    if user and user.is_authenticated:
        approved_assignment_ids = set(
            AssignmentSubmission.objects.filter(
                student=user,
                assignment__lesson__module__course=course,
                status=AssignmentSubmission.STATUS_APPROVED,
            ).values_list("assignment_id", flat=True)
        )

    assignment_ids_by_lesson = {
        lesson.id: [assignment.id for assignment in lesson.assignments.all()]
        for lesson in lessons
    }

    for index, lesson in enumerate(lessons):
        state = {
            "is_accessible": True,
            "is_released": True,
            "lock_reason": "",
        }

        if not enrollment:
            state["is_accessible"] = False
            state["lock_reason"] = "Kursga faol obuna kerak."
        else:
            if drip_enabled and lesson.id not in released_lesson_ids:
                state["is_accessible"] = False
                state["is_released"] = False
                state["lock_reason"] = "Bu dars hali o'qituvchi tomonidan ochilmagan."

            if state["is_accessible"] and index > 0:
                previous_lesson = lessons[index - 1]
                previous_assignment_ids = assignment_ids_by_lesson.get(previous_lesson.id, [])
                if previous_assignment_ids and any(
                    assignment_id not in approved_assignment_ids
                    for assignment_id in previous_assignment_ids
                ):
                    state["is_accessible"] = False
                    state["lock_reason"] = (
                        "Oldingi dars vazifasi tekshirilib tasdiqlanmaguncha keyingi dars ochilmaydi."
                    )

        lesson_access_map[lesson.id] = state
        if state["is_accessible"] and first_accessible_lesson is None:
            first_accessible_lesson = lesson

    return {
        "lessons": lessons,
        "lesson_access_map": lesson_access_map,
        "first_accessible_lesson": first_accessible_lesson,
        "drip_enabled": drip_enabled,
    }


def _mark_lesson_progress_completed(enrollment, lesson):
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={
            "is_completed": True,
            "completed_at": timezone.now(),
        },
    )
    newly_completed = created
    if not created and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(update_fields=["is_completed", "completed_at", "last_accessed_at"])
        newly_completed = True

    # Dars birinchi marta tugatilganda — malakali kunlik faollik.
    if newly_completed:
        from users.streak import record_activity
        record_activity(enrollment.student)


class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 8
    
    def get_queryset(self):
        from django.db.models import Count, Q as Q_obj
        
        queryset = (
            Course.objects.filter(is_active=True)
            .select_related("instructor")
            .annotate(
                annotated_lessons_count=Count('modules__lessons', distinct=True),
                annotated_students_count=Count(
                    'cohorts__members',
                    filter=enrollment_active_access_q(prefix='cohorts__members__'),
                    distinct=True,
                )
            )
        )
        
        # Qidiruv filtering
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | 
                Q(description__icontains=q)
            )
            
        # Daraja (Level) filtering
        levels = self.request.GET.getlist('level')
        if levels:
            queryset = queryset.filter(level__in=levels)
            
        # Saralash (Sorting)
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-annotated_students_count', '-created_at')
        else:
            # Default = newest
            queryset = queryset.order_by('-created_at')
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_levels'] = self.request.GET.getlist('level')
        context['level_choices'] = Course.LEVEL_CHOICES
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        context['active_nav'] = 'courses'
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        return (
            Course.objects.filter(is_active=True)
            .select_related("instructor")
            .prefetch_related("modules__lessons", "exams")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        modules = list(self.object.modules.all())
        preview_lesson = next(
            (
                lesson
                for module in modules
                for lesson in module.lessons.all()
            ),
            None,
        )

        context['modules'] = modules
        context['preview_lesson'] = preview_lesson
        context['course_lessons_count'] = self.object.lessons_count
        context['course_students_count'] = self.object.students_count
        context['active_cohort_count'] = self.object.cohorts.filter(is_active=True).count()
        context['instructor_course_count'] = (
            self.object.instructor.courses.filter(is_active=True).count()
            if self.object.instructor_id
            else 0
        )
        context['course_exam_count'] = self.object.exams.count()
        if self.request.user.is_authenticated:
            context['is_enrolled'] = Enrollment.objects.filter(
                enrollment_active_access_q(),
                student=self.request.user,
                cohort__course=self.object,
            ).exists()
        else:
            context['is_enrolled'] = False
        context['active_nav'] = 'courses'
        return context

class CourseStudyRedirectView(LoginRequiredMixin, View):
    """
    Redirects an enrolled student to their current lesson (or the first lesson) 
    in the interactive study environment.
    """
    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        selected_cohort_id = _requested_cohort_id(request)
        
        # Check active enrollment
        enrollment = _get_active_enrollment_for_course(request.user, course, selected_cohort_id)
        
        if not enrollment:
            messages.warning(request, "Siz ushbu kursga obuna bo'lmagansiz yoki obunangiz faol emas.")
            return redirect('course_detail', pk=course.id)

        access_bundle = _build_lesson_access_bundle(course, request.user, enrollment)
        first_accessible_lesson = access_bundle["first_accessible_lesson"]

        if first_accessible_lesson:
            return redirect(
                _build_url_with_query(
                    reverse('lesson_detail', kwargs={'course_id': course.id, 'lesson_id': first_accessible_lesson.id}),
                    cohort=enrollment.cohort_id,
                )
            )
        else:
            messages.info(request, "Hozircha siz uchun ochiq dars mavjud emas.")
            return redirect('course_detail', pk=course.id)

class LessonDetailView(LoginRequiredMixin, DetailView):
    """
    Renders the tabbed interactive study environment for a specific lesson.
    """
    model = Lesson
    template_name = 'courses/lesson_detail.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'
    
    def dispatch(self, request, *args, **kwargs):
        # Override dispatch to block access before hitting get_context_data
        if request.user.is_authenticated:
            course_id = self.kwargs.get("course_id")
            lesson_id = self.kwargs.get("lesson_id")
            course = get_object_or_404(Course, id=course_id)
            selected_cohort_id = _requested_cohort_id(request)

            enrollment = _get_active_enrollment_for_course(request.user, course, selected_cohort_id)
            if not enrollment:
                messages.error(request, "Siz bu kursning darslarini ko'rish uchun obuna bo'lishingiz kerak.")
                return redirect("course_detail", pk=course_id)
            self._active_enrollment = enrollment
            self._selected_cohort_id = enrollment.cohort_id

            access_bundle = _build_lesson_access_bundle(course, request.user, enrollment)
            self._lesson_access_bundle = access_bundle

            lesson_state = access_bundle["lesson_access_map"].get(lesson_id)
            if lesson_state and not lesson_state["is_accessible"]:
                messages.warning(
                    request,
                    lesson_state["lock_reason"] or "Bu dars hozircha siz uchun yopiq.",
                )
                fallback_lesson = access_bundle["first_accessible_lesson"]
                if fallback_lesson and fallback_lesson.id != lesson_id:
                    return redirect(
                        _build_url_with_query(
                            reverse(
                                "lesson_detail",
                                kwargs={"course_id": course_id, "lesson_id": fallback_lesson.id},
                            ),
                            cohort=enrollment.cohort_id,
                        )
                    )
                return redirect("course_detail", pk=course_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only allow accessing lessons of the specified course
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(module__course_id=course_id).select_related(
            'module',
            'module__course',
            'module__course__instructor',
        )
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.module.course
        user = self.request.user

        enrollment = getattr(self, "_active_enrollment", None)
        if enrollment is None:
            enrollment = _get_active_enrollment_for_course(
                user,
                course,
                getattr(self, "_selected_cohort_id", None) or _requested_cohort_id(self.request),
            )
        active_cohort_id = enrollment.cohort_id if enrollment else getattr(self, "_selected_cohort_id", None)

        if enrollment:
            _mark_lesson_progress_completed(enrollment, self.object)

        access_bundle = getattr(self, "_lesson_access_bundle", None)
        if access_bundle is None:
            access_bundle = _build_lesson_access_bundle(course, user, enrollment)
        lesson_access_map = access_bundle["lesson_access_map"]
        all_lessons = access_bundle["lessons"]

        context['is_enrolled'] = bool(enrollment)
        context['course'] = course
        context['active_enrollment'] = enrollment
        context['active_cohort_id'] = active_cohort_id
        context['cohort_query'] = f"?cohort={active_cohort_id}" if active_cohort_id else ""

        modules = list(course.modules.all().prefetch_related('lessons'))
        course_exams = course.exams.all().order_by('id')
        assignments = list(self.object.assignments.all())
        quizzes = self.object.quizzes.prefetch_related('questions__choices').all()
        current_module = next((module for module in modules if module.id == self.object.module_id), self.object.module)
        module_lessons = list(current_module.lessons.all()) if hasattr(current_module, 'lessons') else [self.object]

        assignment_submissions = {
            submission.assignment_id: submission
            for submission in AssignmentSubmission.objects.filter(
                student=user,
                assignment_id__in=[assignment.id for assignment in assignments],
            ).select_related("reviewed_by")
        }
        for assignment in assignments:
            assignment.current_submission = assignment_submissions.get(assignment.id)

        for module in modules:
            lesson_items = list(module.lessons.all())
            for lesson_item in lesson_items:
                state = lesson_access_map.get(lesson_item.id, {})
                lesson_item.is_locked = not state.get("is_accessible", True)
                lesson_item.lock_reason = state.get("lock_reason", "")
                lesson_item.is_released_for_student = state.get("is_released", True)
            module.lesson_items = lesson_items

        has_video = bool(self.object.video_url)
        has_content = bool((self.object.content or '').strip())
        has_assignments = bool(assignments)
        has_quizzes = quizzes.exists()

        default_tab = None
        if has_video:
            default_tab = 'video'
        elif has_content:
            default_tab = 'text'
        elif has_assignments:
            default_tab = 'homework'
        elif has_quizzes:
            default_tab = 'quiz'

        context['modules'] = modules
        context['course_exams'] = course_exams
        context['assignments'] = assignments
        context['quizzes'] = quizzes
        context['has_video'] = has_video
        context['has_content'] = has_content
        context['has_assignments'] = has_assignments
        context['has_quizzes'] = has_quizzes
        context['has_course_exams'] = course_exams.exists()
        context['first_course_exam'] = course_exams.first()
        context['default_study_tab'] = default_tab
        context['total_lessons'] = len(all_lessons)
        context['course_module_count'] = len(modules)
        context['current_module'] = current_module
        context['module_lesson_count'] = len(module_lessons)
        context['resource_count'] = int(has_video) + int(has_content) + len(assignments) + quizzes.count()
        context['practice_count'] = len(assignments) + quizzes.count()
        context['active_nav'] = 'my_courses'
        context['lesson_sections'] = [
            section
            for section in [
                {
                    'key': 'video',
                    'label': 'Videodars',
                    'meta': 'Asosiy video sessiya',
                    'enabled': has_video,
                },
                {
                    'key': 'text',
                    'label': 'Notelar',
                    'meta': 'Matnli bayon va tushuntirishlar',
                    'enabled': has_content,
                },
                {
                    'key': 'homework',
                    'label': 'Vazifa',
                    'meta': f"{len(assignments)} ta topshiriq",
                    'enabled': has_assignments,
                },
                {
                    'key': 'quiz',
                    'label': 'Quiz',
                    'meta': f"{quizzes.count()} ta test bloki",
                    'enabled': has_quizzes,
                },
            ]
            if section['enabled']
        ]
        requested_tab = self.request.GET.get("tab")
        available_tabs = {section["key"] for section in context["lesson_sections"]}
        if requested_tab in available_tabs:
            context["default_study_tab"] = requested_tab
        context['lesson_section_count'] = len(context['lesson_sections'])
        context["drip_enabled"] = access_bundle["drip_enabled"]
        context["lesson_access_map"] = lesson_access_map
        context["completed_lesson_ids"] = set(
            LessonProgress.objects.filter(
                enrollment=enrollment,
                lesson__module__course=course,
                is_completed=True,
            ).values_list("lesson_id", flat=True)
        ) if enrollment else set()

        # Oldingi quiz urinishlarini yuklash
        quiz_ids = list(quizzes.values_list('id', flat=True))
        context['quiz_attempts'] = {
            a.quiz_id: a for a in QuizAttempt.objects.filter(
                student=user, quiz_id__in=quiz_ids
            ).order_by('-completed_at')
        } if quiz_ids else {}

        # Determine previous and next lessons
        try:
            current_index = all_lessons.index(self.object)
            module_index = module_lessons.index(self.object)

            context['lesson_position'] = current_index + 1
            context['module_lesson_position'] = module_index + 1
            context['course_progress_percent'] = round(((current_index + 1) / max(len(all_lessons), 1)) * 100)
            context['module_progress_percent'] = round(((module_index + 1) / max(len(module_lessons), 1)) * 100)
            
            if current_index > 0:
                previous_lesson = all_lessons[current_index - 1]
                if lesson_access_map.get(previous_lesson.id, {}).get("is_accessible", True):
                    context['prev_lesson'] = previous_lesson
            
            if current_index < len(all_lessons) - 1:
                immediate_next = all_lessons[current_index + 1]
                next_state = lesson_access_map.get(immediate_next.id, {})
                if next_state.get("is_accessible", True):
                    context['next_lesson'] = immediate_next
                else:
                    context["next_lesson_locked"] = True
                    context["next_lesson_lock_reason"] = next_state.get(
                        "lock_reason",
                        "Keyingi dars hozircha yopiq.",
                    )
        except ValueError:
            context['lesson_position'] = 1
            context['module_lesson_position'] = 1
            context['course_progress_percent'] = 100
            context['module_progress_percent'] = 100
            
        return context


class SubmitAssignmentView(LoginRequiredMixin, View):
    def post(self, request, course_id, lesson_id, assignment_id):
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            lesson_id=lesson_id,
            lesson__module__course_id=course_id,
        )
        course = assignment.lesson.module.course
        selected_cohort_id = _requested_cohort_id(request)
        enrollment = _get_active_enrollment_for_course(request.user, course, selected_cohort_id)
        redirect_url = _build_url_with_query(
            reverse('lesson_detail', kwargs={'course_id': course_id, 'lesson_id': lesson_id}),
            tab='homework',
            cohort=enrollment.cohort_id if enrollment else selected_cohort_id,
        )

        if not enrollment:
            messages.error(request, "Vazifa yuborish uchun faol obuna kerak.")
            return redirect("course_detail", pk=course_id)

        # Mantiq courses/submission_service.py da — Telegram bot ham shuni chaqiradi.
        from courses.submission_service import submit_assignment

        result = submit_assignment(
            user=request.user,
            assignment=assignment,
            answer_text=request.POST.get("answer_text") or "",
            attachment=request.FILES.get("attachment"),
        )
        if not result.ok:
            messages.error(request, result.message)
            return redirect(redirect_url)

        messages.success(
            request,
            "Vazifa yuborildi. O'qituvchi tekshiruvigacha keyingi dars yopiq qoladi.",
        )
        return redirect(redirect_url)

class ExamCenterView(LoginRequiredMixin, ListView):
    """O'quvchining faol kurslaridagi imtihonlar markazi (AppShell 'Imtihon').

    Eski stub `exam:` app o'rnini bosadi — haqiqiy courses exam oqimiga ulaydi.
    """
    model = Exam
    template_name = 'courses/exam_center.html'
    context_object_name = 'exams'

    def get_queryset(self):
        from django.db.models import Count
        user = self.request.user
        course_ids = (
            Enrollment.objects.filter(enrollment_active_access_q(), student=user)
            .values_list('cohort__course_id', flat=True)
            .distinct()
        )
        exams = list(
            Exam.objects.filter(course_id__in=course_ids)
            .select_related('course')
            .annotate(
                section_count=Count('sections', distinct=True),
                attempts_used=Count('attempts', filter=Q(attempts__student=user), distinct=True),
            )
            .order_by('course__title', 'exam_type')
        )
        latest_by_exam = {}
        for attempt in ExamAttempt.objects.filter(student=user, exam__in=exams).order_by('exam_id', '-attempt_number'):
            latest_by_exam.setdefault(attempt.exam_id, attempt)
        for exam in exams:
            exam.latest_attempt = latest_by_exam.get(exam.id)
            exam.attempts_left = max(exam.max_attempts - exam.attempts_used, 0)
        return exams

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'exam'
        return context


class ExamDetailView(LoginRequiredMixin, DetailView):
    model = Exam
    template_name = 'courses/exam_detail.html'
    context_object_name = 'exam'
    pk_url_kwarg = 'exam_id'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            course_id = self.kwargs.get('course_id')
            exam_id = self.kwargs.get('exam_id')
            is_enrolled = Enrollment.objects.filter(
                enrollment_active_access_q(),
                student=request.user,
                cohort__course_id=course_id,
            ).exists()
            if not is_enrolled:
                messages.error(request, "Siz bu imtihonni ko'rish uchun kursga obuna bo'lishingiz kerak.")
                return redirect('course_detail', pk=course_id)
                
            attempt = get_latest_exam_attempt_for_exam_id(student=request.user, exam_id=exam_id)
            if attempt and attempt.is_completed:
                return redirect('exam_result', course_id=course_id, exam_id=exam_id)
                
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Exam.objects.filter(course_id=course_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.course
        user = self.request.user
        
        is_enrolled = Enrollment.objects.filter(
            enrollment_active_access_q(),
            student=user,
            cohort__course=course,
        ).exists()
        
        context['is_enrolled'] = is_enrolled
        context['course'] = course
        context['modules'] = course.modules.all().prefetch_related('lessons')
        context['course_exams'] = course.exams.all().order_by('id')
        context['sections'] = self.object.sections.all().order_by('order')
        
        latest_attempt = get_latest_exam_attempt(student=user, exam=self.object)
        context['my_attempt'] = latest_attempt
        if latest_attempt:
            context['remaining_attempts'] = max(self.object.max_attempts - latest_attempt.attempt_number, 0)
        else:
            context['remaining_attempts'] = self.object.max_attempts
        entry_policy = check_exam_entry_policy(student=user, exam=self.object) if is_enrolled else None
        context['exam_entry_policy'] = entry_policy
        context['can_start_exam'] = bool(entry_policy and entry_policy.is_allowed)

        # exam-shell.js uchun runtime konfiguratsiya (json_script orqali xavfsiz uzatiladi)
        from django.middleware.csrf import get_token

        exam = self.object
        sections = list(context['sections'])
        context['exam_config'] = {
            'csrf': get_token(self.request),
            'urls': {
                'start': reverse('api_exam_start', args=[course.id, exam.id]),
                'save': reverse('api_exam_save', args=[course.id, exam.id]),
                'audioUpload': reverse('api_exam_audio_upload', args=[course.id, exam.id]),
                'audioPlay': reverse('api_exam_audio_play', args=[course.id, exam.id]),
                'reviewFlag': reverse('api_exam_review_flag', args=[course.id, exam.id]),
                'blur': reverse('api_exam_blur', args=[course.id, exam.id]),
                'submit': reverse('api_exam_submit', args=[course.id, exam.id]),
                'result': reverse('exam_result', args=[course.id, exam.id]),
                'center': reverse('exam_center'),
                # JS '/0/' ni haqiqiy section id bilan almashtiradi
                'sectionState': reverse('api_exam_section_state', args=[course.id, exam.id, 0]),
            },
            'sections': [
                {
                    'id': section.id,
                    'title': section.title,
                    'type': section.section_type,
                    'typeLabel': section.get_section_type_display(),
                    'timeLimit': section.time_limit_minutes,
                }
                for section in sections
            ],
        }

        return context

class ExamResultView(LoginRequiredMixin, DetailView):
    model = Exam
    template_name = 'courses/exam_result.html'
    context_object_name = 'exam'
    pk_url_kwarg = 'exam_id'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            course_id = self.kwargs.get('course_id')
            exam_id = self.kwargs.get('exam_id')
            is_enrolled = Enrollment.objects.filter(
                enrollment_active_access_q(),
                student=request.user,
                cohort__course_id=course_id,
            ).exists()
            if not is_enrolled:
                messages.error(request, "Iltimos, kursga a'zo bo'ling.")
                return redirect('course_detail', pk=course_id)
                
            attempt = get_latest_exam_attempt_for_exam_id(student=request.user, exam_id=exam_id)
            if not attempt or not attempt.is_completed:
                return redirect('exam_detail', course_id=course_id, exam_id=exam_id)
                
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Exam.objects.filter(course_id=course_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.course
        context['course'] = course
        context['modules'] = course.modules.all().prefetch_related('lessons')
        context['course_exams'] = course.exams.all().order_by('id')
        
        attempt = get_latest_exam_attempt(student=self.request.user, exam=self.object)
        context['attempt'] = attempt
        context['course_certificate'] = None
        if attempt and attempt.is_reviewed and attempt.passed:
            context['course_certificate'] = Certificate.objects.filter(
                student=self.request.user,
                course=course,
            ).first()
        context['remaining_attempts'] = max(
            self.object.max_attempts - (attempt.attempt_number if attempt else 0),
            0,
        )
        context['can_retake'] = bool(
            attempt
            and attempt.is_completed
            and attempt.is_reviewed
            and not attempt.passed
            and attempt.attempt_number < self.object.max_attempts
        )

        context['active_nav'] = 'exam'
        context['section_reviews'] = []
        context['feedback_answers'] = []
        context['duration_minutes'] = None
        if attempt:
            context['section_reviews'] = list(
                attempt.section_reviews.select_related('section').order_by('section__order')
            )
            # per-esse/javob o'qituvchi izohlari (writing/speaking)
            context['feedback_answers'] = list(
                attempt.answers.exclude(grader_feedback="")
                .select_related('question', 'question__exam_section')
                .order_by('question__exam_section__order', 'question_id')
            )
            if attempt.completed_time and attempt.start_time:
                context['duration_minutes'] = max(
                    int((attempt.completed_time - attempt.start_time).total_seconds() // 60), 0
                )
        return context

class StartExamView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        exam = get_object_or_404(Exam, id=exam_id, course_id=course_id)

        try:
            attempt, created = start_exam_attempt(student=request.user, exam=exam)
        except ExamAttemptStartBlocked as exc:
            status_code = 403 if exc.code == "not_enrolled" else 400
            return JsonResponse({'error': str(exc), 'code': exc.code}, status=status_code)

        deadline = attempt.get_deadline()
        return JsonResponse(
            {
                'status': 'success',
                'attempt_id': attempt.id,
                'attempt_number': attempt.attempt_number,
                'start_time': attempt.start_time.isoformat(),
                'created': created,
                'time_limit_minutes': attempt.time_limit_minutes,
                'deadline': deadline.isoformat() if deadline else None,
                'remaining_attempts': max(exam.max_attempts - attempt.attempt_number, 0),
            }
        )

class ExamSectionStateView(LoginRequiredMixin, View):
    def get(self, request, course_id, exam_id, section_id):
        section = get_object_or_404(ExamSection, id=section_id, exam_id=exam_id)
        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )
        payload = build_section_payload(attempt=attempt, section=section)
        return JsonResponse({'status': 'success', **payload})


class SaveExamAnswerView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': "JSON formati noto'g'ri."}, status=400)

        try:
            attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
            if not attempt:
                return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
            if expire_attempt_if_time_limit_reached(attempt):
                return JsonResponse(
                    {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                    status=400,
                )

            reading_item_id = data.get('reading_item_id')
            if reading_item_id not in (None, ""):
                item = ReadingItem.objects.select_related('task__section').filter(id=reading_item_id).first()
                if not item or item.task.section.exam_id != attempt.exam_id:
                    raise Http404("Reading item topilmadi.")
                response = save_reading_response(attempt=attempt, item=item, payload=data)
                payload = build_reading_section_payload(attempt=attempt, section=item.task.section)
                return JsonResponse(
                    {
                        'status': 'success',
                        'section_state': payload['state'],
                        'saved_response': {
                            'item_id': response.item_id,
                            'awarded_score': float(response.awarded_score),
                            'is_graded': response.is_graded,
                            'is_flagged_for_review': response.is_flagged_for_review,
                        },
                    }
                )

            question = get_object_or_404(Question, id=data.get('question_id'))
            answer = save_question_answer(attempt=attempt, question=question, payload=data)
            response_payload = {
                'status': 'success',
                'saved_answer': {
                    'question_id': answer.question_id,
                    'awarded_score': float(answer.awarded_score),
                    'is_graded': answer.is_graded,
                    'is_flagged_for_review': answer.is_flagged_for_review,
                    'word_count': answer.word_count,
                    'word_count_status': word_count_status(question, answer.word_count),
                },
            }
            if question.exam_section_id:
                response_payload['section_state'] = build_question_section_payload(
                    attempt=attempt, section=question.exam_section
                )['state']
            return JsonResponse(response_payload)
        except Http404 as exc:
            return JsonResponse({'error': str(exc)}, status=404)
        except (ValidationError, ValueError) as exc:
            message = exc.message if isinstance(exc, ValidationError) and hasattr(exc, "message") else str(exc)
            if isinstance(exc, ValidationError) and exc.messages:
                message = exc.messages[0]
            return JsonResponse({'error': message}, status=400)


class ToggleExamReviewFlagView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': "JSON formati noto'g'ri."}, status=400)

        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )

        reading_item_id = data.get("reading_item_id")
        question_id = data.get("question_id")

        try:
            if reading_item_id not in (None, ""):
                item = ReadingItem.objects.select_related('task__section').get(id=reading_item_id)
                if item.task.section.exam_id != attempt.exam_id:
                    raise Http404("Reading item topilmadi.")
                response = toggle_reading_review_flag(attempt=attempt, item=item, flagged=data.get("flagged"))
                payload = build_reading_section_payload(attempt=attempt, section=item.task.section)
                return JsonResponse(
                    {
                        'status': 'success',
                        'is_flagged_for_review': response.is_flagged_for_review,
                        'section_state': payload['state'],
                    }
                )
            if question_id not in (None, ""):
                question = get_object_or_404(Question, id=question_id)
                if question.exam_section and question.exam_section.exam_id != attempt.exam_id:
                    raise Http404("Savol topilmadi.")
                answer = toggle_question_review_flag(attempt=attempt, question=question, flagged=data.get("flagged"))
                section_state = {}
                if question.exam_section_id:
                    section_state = build_question_section_payload(attempt=attempt, section=question.exam_section)['state']
                return JsonResponse(
                    {
                        'status': 'success',
                        'is_flagged_for_review': answer.is_flagged_for_review,
                        'section_state': section_state,
                    }
                )
            return JsonResponse({'error': "reading_item_id yoki question_id yuborilishi shart."}, status=400)
        except Http404 as exc:
            return JsonResponse({'error': str(exc)}, status=404)
        except (ReadingItem.DoesNotExist, ValidationError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) and exc.messages else str(exc)
            return JsonResponse({'error': message}, status=400)

class RegisterAudioPlayView(LoginRequiredMixin, View):
    """Listening audiosi tinglanishini qayd qiladi va tinglash limitini server tomonda majburlaydi."""
    def post(self, request, course_id, exam_id):
        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            data = {}
        section = get_object_or_404(ExamSection, id=data.get('section_id'), exam_id=exam_id)
        try:
            result = register_audio_play(attempt=attempt, section=section)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, 'messages', None) else str(exc)
            return JsonResponse({'error': message}, status=400)
        return JsonResponse(
            {'status': 'success' if result['allowed'] else 'limit_reached', **result},
            status=200 if result['allowed'] else 403,
        )


class UploadExamAudioView(LoginRequiredMixin, View):
    """Speaking yozuvini qabul qiladi → storage'ga (S3/Spaces yoki local) saqlaydi →
    StudentAnswer.audio_file_url'ga biriktiradi. Speaking topshirishning yetishmayotgan halqasi.

    Hajm va format chegaralari `core.upload_validation` dagi `audio` profilida."""

    def post(self, request, course_id, exam_id):
        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )

        question = get_object_or_404(Question, id=request.POST.get('question_id'))
        if question.exam_section and question.exam_section.exam_id != attempt.exam_id:
            return JsonResponse({'error': 'Bu savol ushbu imtihonga tegishli emas.'}, status=400)

        upload = request.FILES.get('audio')
        if not upload:
            return JsonResponse({'error': "Audio fayl yuborilmadi."}, status=400)
        # Ilgari bu yerda faqat `upload.content_type` tekshirilardi — u brauzer
        # yuboradigan sarlavha, soxtalashtirilishi mumkin va bo'sh bo'lsa
        # tekshiruv butunlay o'tkazib yuborilardi. Endi konteyner baytlardan
        # aniqlanadi (A0b).
        try:
            validate_upload(upload, profile="audio", field_label="Audio yozuv")
        except ValidationError as exc:
            return JsonResponse({'error': exc.messages[0]}, status=400)

        import os
        import uuid
        from django.core.files.storage import default_storage

        ext = os.path.splitext(upload.name or '')[1].lower()
        if not ext or len(ext) > 8 or '/' in ext or '\\' in ext:
            ext = '.webm'
        key = f"exam_audio/{attempt.id}/{question.id}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(key, upload)
        audio_url = request.build_absolute_uri(default_storage.url(saved_path))

        try:
            answer = save_question_answer(
                attempt=attempt,
                question=question,
                payload={
                    'audio_url': audio_url,
                    'current_question_id': request.POST.get('current_question_id'),
                },
            )
        except (ValidationError, ValueError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) and getattr(exc, 'messages', None) else str(exc)
            return JsonResponse({'error': message}, status=400)

        response_payload = {
            'status': 'success',
            'audio_url': audio_url,
            'saved_answer': {
                'question_id': answer.question_id,
                'audio_url': answer.audio_file_url,
                'is_flagged_for_review': answer.is_flagged_for_review,
            },
        }
        if question.exam_section_id:
            response_payload['section_state'] = build_question_section_payload(
                attempt=attempt, section=question.exam_section
            )['state']
        return JsonResponse(response_payload)


class LogBlurWarningView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )
        attempt.blur_warnings += 1
        attempt.save()
        return JsonResponse({'status': 'logged', 'warnings': attempt.blur_warnings})

class SubmitExamView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        attempt = get_in_progress_exam_attempt(student=request.user, exam_id=exam_id)
        if not attempt:
            return JsonResponse({'error': 'Faol imtihon urinishi topilmadi.'}, status=404)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse(
                {'error': 'Imtihon vaqti tugadi. Urinish tekshiruvga yuborildi.'},
                status=400,
            )
        attempt.submit_for_review()

        # Imtihonni topshirish — malakali kunlik faollik.
        from users.streak import record_activity
        record_activity(request.user)

        return JsonResponse({'status': 'success', 'pending_review': True})

class SubmitQuizView(LoginRequiredMixin, View):
    """Dars ichidagi quiz javoblarni qabul qilish va natija hisoblash.

    Baholash mantig'i courses/submission_service.grade_quiz da — Telegram bot
    ham xuddi shu servisni chaqiradi (bitta qoida, bitta XP hisobi).
    """
    def post(self, request, course_id, lesson_id, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, lesson_id=lesson_id, lesson__module__course_id=course_id)

        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})  # {question_id: choice_id}
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': "Noto'g'ri ma'lumot formati."}, status=400)

        from courses.submission_service import grade_quiz

        result = grade_quiz(user=request.user, quiz=quiz, answers=answers)
        if not result.ok:
            status = 403 if result.code == 'no_access' else 400
            return JsonResponse({'error': result.message}, status=status)

        return JsonResponse({
            'status': 'success',
            'score': result.score,
            'total_correct': result.total_correct,
            'total_questions': result.total_questions,
            'xp_earned': result.xp_earned,
            'attempt_xp': result.attempt_xp,
            'results': result.results,
        })

class CertificateDetailView(DetailView):
    """
    Renders the professional certificate for printing/downloading.
    Publicly accessible to verify the certificate if one has the exact ID.
    """
    model = Certificate
    template_name = 'courses/certificate.html'
    context_object_name = 'certificate'
    
    def get_object(self, queryset=None):
        certificate_id = self.kwargs.get('certificate_id')
        return get_object_or_404(Certificate, certificate_id=certificate_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['auto_print'] = self.request.GET.get('download') == '1'
        return context


class CertificateAppendixView(DetailView):
    model = Certificate
    template_name = 'courses/certificate_appendix.html'
    context_object_name = 'certificate'

    def get_object(self, queryset=None):
        certificate_id = self.kwargs.get('certificate_id')
        return get_object_or_404(Certificate, certificate_id=certificate_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.object
        from .models import ExamAttempt

        reviewed_attempts = (
            ExamAttempt.objects
            .filter(
                student=certificate.student,
                exam__course=certificate.course,
                is_reviewed=True,
            )
            .select_related('exam')
            .prefetch_related('section_reviews__section')
            .order_by('exam__exam_type', 'exam__title')
        )
        context['reviewed_attempts'] = reviewed_attempts
        context['auto_print'] = self.request.GET.get('download') == '1'
        return context
