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
    if not created and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(update_fields=["is_completed", "completed_at", "last_accessed_at"])


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

        submission, _ = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=request.user,
        )
        answer_text = (request.POST.get("answer_text") or "").strip()
        attachment = request.FILES.get("attachment")

        if not answer_text and not attachment and not submission.attachment:
            messages.error(request, "Kamida matn yoki fayl yuborishingiz kerak.")
            return redirect(redirect_url)

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

        messages.success(
            request,
            "Vazifa yuborildi. O'qituvchi tekshiruvigacha keyingi dars yopiq qoladi.",
        )
        return redirect(redirect_url)

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
        if section.section_type != "reading":
            return JsonResponse(
                {'error': 'Section state endpoint hozircha faqat reading section uchun ishlaydi.'},
                status=400,
            )

        payload = build_reading_section_payload(attempt=attempt, section=section)
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

            question_id = data.get('question_id')
            answer_text = data.get('answer_text')
            choice_id = data.get('choice_id')
            audio_url = data.get('audio_url')

            question = get_object_or_404(Question, id=question_id)

            # Security: Ensure question actually belongs to this exam
            if question.exam_section and question.exam_section.exam_id != attempt.exam_id:
                return JsonResponse({'error': 'Xatolik: Bu savol ushbu imtihonga tegishli emas.'}, status=400)

            # Upsert student answer
            ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)

            if choice_id:
                choice = get_object_or_404(Choice, id=choice_id, question=question)
                ans.selected_choice = choice
                ans.awarded_score = question.points if choice.is_correct else 0
                ans.is_graded = True
            if answer_text is not None:
                ans.answer_text = answer_text
            if audio_url:
                ans.audio_file_url = audio_url

            ans.save()
            return JsonResponse({'status': 'success'})
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
        if reading_item_id in (None, ""):
            return JsonResponse({'error': "reading_item_id yuborilishi shart."}, status=400)

        try:
            item = ReadingItem.objects.select_related('task__section').get(id=reading_item_id)
            if item.task.section.exam_id != attempt.exam_id:
                raise Http404("Reading item topilmadi.")
            response = toggle_reading_review_flag(
                attempt=attempt,
                item=item,
                flagged=data.get("flagged"),
            )
            payload = build_reading_section_payload(attempt=attempt, section=item.task.section)
            return JsonResponse(
                {
                    'status': 'success',
                    'is_flagged_for_review': response.is_flagged_for_review,
                    'section_state': payload['state'],
                }
            )
        except Http404 as exc:
            return JsonResponse({'error': str(exc)}, status=404)
        except (ReadingItem.DoesNotExist, ValidationError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) and exc.messages else str(exc)
            return JsonResponse({'error': message}, status=400)

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
        
        return JsonResponse({'status': 'success', 'pending_review': True})

class SubmitQuizView(LoginRequiredMixin, View):
    """Dars ichidagi quiz javoblarni qabul qilish va natija hisoblash."""
    def post(self, request, course_id, lesson_id, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, lesson_id=lesson_id, lesson__module__course_id=course_id)
        
        # Enrollment tekshiruvi
        if not Enrollment.objects.filter(
            enrollment_active_access_q(),
            student=request.user,
            cohort__course_id=course_id,
        ).exists():
            return JsonResponse({'error': 'Kursga obuna bo\'lmagansiz.'}, status=403)
        
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})  # {question_id: choice_id}
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Noto\'g\'ri ma\'lumot formati.'}, status=400)
        
        if not answers:
            return JsonResponse({'error': 'Javoblar bo\'sh.'}, status=400)
        
        # Barcha savollarni olish
        questions = quiz.questions.prefetch_related('choices').all()
        total_questions = questions.count()
        
        if total_questions == 0:
            return JsonResponse({'error': 'Quizda savollar yo\'q.'}, status=400)
        
        # Javoblarni tekshirish
        total_correct = 0
        results = []  # Har bir savol natijasi
        
        # QuizAttempt yaratish
        previous_best_xp = (
            QuizAttempt.objects.filter(student=request.user, quiz=quiz)
            .aggregate(best_xp=Max('xp_earned'))
            .get('best_xp')
            or 0
        )
        attempt = QuizAttempt.objects.create(
            student=request.user,
            quiz=quiz,
            total_questions=total_questions,
        )
        
        for question in questions:
            q_id_str = str(question.id)
            selected_choice_id = answers.get(q_id_str)
            
            correct_choice = question.choices.filter(is_correct=True).first()
            is_correct = False
            selected_choice = None
            
            if selected_choice_id:
                try:
                    selected_choice = question.choices.get(id=int(selected_choice_id))
                    is_correct = selected_choice.is_correct
                except (Choice.DoesNotExist, ValueError):
                    pass
            
            if is_correct:
                total_correct += 1
            
            # Javobni saqlash
            if selected_choice:
                QuizAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected_choice,
                    is_correct=is_correct,
                )
            
            results.append({
                'question_id': question.id,
                'selected_choice_id': int(selected_choice_id) if selected_choice_id else None,
                'correct_choice_id': correct_choice.id if correct_choice else None,
                'is_correct': is_correct,
            })
        
        # Ball hisoblash
        score = round((total_correct / total_questions) * 100, 1)
        
        # XP hisoblash — to'g'ri javoblar nisbatiga qarab
        attempt_xp = round(quiz.xp_reward * (total_correct / total_questions))
        awarded_xp = max(0, attempt_xp - previous_best_xp)
        
        # Attempt yangilash
        attempt.score = score
        attempt.total_correct = total_correct
        attempt.xp_earned = attempt_xp
        attempt.save()
        
        # Foydalanuvchiga XP qo'shish
        if awarded_xp > 0:
            request.user.total_xp += awarded_xp
            request.user.save(update_fields=['total_xp'])
        
        return JsonResponse({
            'status': 'success',
            'score': score,
            'total_correct': total_correct,
            'total_questions': total_questions,
            'xp_earned': awarded_xp,
            'attempt_xp': attempt_xp,
            'results': results,
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
