from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .models import Course, Lesson, Certificate, Exam, Quiz, QuizAttempt, QuizAnswer
from cohorts.models import Enrollment


class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 8
    
    def get_queryset(self):
        from django.db.models import Count, Q as Q_obj
        
        queryset = Course.objects.filter(is_active=True).annotate(
            annotated_lessons_count=Count('modules__lessons', distinct=True),
            annotated_students_count=Count('cohorts__members', filter=Q_obj(cohorts__members__status='active'), distinct=True)
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
            # Har bir kursning studentlar sonini hisoblash mumkin, 
            # ammo oddiylik uchun hozircha default newest. 
            # Keyinroq annotation qo'shsa bo'ladi: annotate(num_students=Count('cohorts__members')).order_by('-num_students')
            queryset = queryset.order_by('-created_at')
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['is_enrolled'] = Enrollment.objects.filter(
                student=self.request.user,
                cohort__course=self.object,
                status='active'
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
        
        # Check active enrollment
        enrollment = Enrollment.objects.filter(
            student=request.user,
            cohort__course=course,
            status='active'
        ).first()
        
        if not enrollment:
            messages.warning(request, "Siz ushbu kursga obuna bo'lmagansiz yoki obunangiz faol emas.")
            return redirect('course_detail', pk=course.id)
            
        # Get the first lesson to start with (can be improved to save last watched lesson later)
        first_lesson = Lesson.objects.filter(module__course=course).order_by('module__order', 'order').first()
        
        if first_lesson:
            return redirect('lesson_detail', course_id=course.id, lesson_id=first_lesson.id)
        else:
            messages.info(request, "Ushbu kursda hali darslar mavjud emas.")
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
            course_id = self.kwargs.get('course_id')
            is_enrolled = Enrollment.objects.filter(
                student=request.user,
                cohort__course_id=course_id,
                status='active'
            ).exists()
            if not is_enrolled:
                messages.error(request, "Siz bu kursning darslarini ko'rish uchun obuna bo'lishingiz kerak.")
                return redirect('course_detail', pk=course_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only allow accessing lessons of the specified course
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(module__course_id=course_id)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.module.course
        user = self.request.user
        
        # Security: Strictly verify active enrollment. Kick out if unauthorized.
        is_enrolled = Enrollment.objects.filter(
            student=user,
            cohort__course=course,
            status='active'
        ).exists()
        
        context['is_enrolled'] = is_enrolled
        context['course'] = course
        
        # Load all modules and lessons for the sidebar Accordion ToC
        context['modules'] = course.modules.all().prefetch_related('lessons')
        context['course_exams'] = course.exams.all().order_by('id')
        
        # Load any assignments or quizzes attached to this lesson
        context['assignments'] = self.object.assignments.all()
        context['quizzes'] = self.object.quizzes.prefetch_related('questions__choices').all()
        
        # Oldingi quiz urinishlarini yuklash
        quiz_ids = list(self.object.quizzes.values_list('id', flat=True))
        context['quiz_attempts'] = {
            a.quiz_id: a for a in QuizAttempt.objects.filter(
                student=user, quiz_id__in=quiz_ids
            ).order_by('-completed_at')
        } if quiz_ids else {}
        
        # Determine previous and next lessons
        all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
        
        try:
            current_index = all_lessons.index(self.object)
            
            if current_index > 0:
                context['prev_lesson'] = all_lessons[current_index - 1]
            
            if current_index < len(all_lessons) - 1:
                context['next_lesson'] = all_lessons[current_index + 1]
        except ValueError:
            pass # Lesson somehow not in list (e.g., drafted or mismatched module)
            
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
                student=request.user,
                cohort__course_id=course_id,
                status='active'
            ).exists()
            if not is_enrolled:
                messages.error(request, "Siz bu imtihonni ko'rish uchun kursga obuna bo'lishingiz kerak.")
                return redirect('course_detail', pk=course_id)
                
            from .models import ExamAttempt
            attempt = ExamAttempt.objects.filter(student=request.user, exam_id=exam_id).first()
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
            student=user,
            cohort__course=course,
            status='active'
        ).exists()
        
        context['is_enrolled'] = is_enrolled
        context['course'] = course
        context['modules'] = course.modules.all().prefetch_related('lessons')
        context['course_exams'] = course.exams.all().order_by('id')
        context['sections'] = self.object.sections.all().order_by('order')
        
        from .models import ExamAttempt
        context['my_attempt'] = ExamAttempt.objects.filter(student=user, exam=self.object).first()
        
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
            is_enrolled = Enrollment.objects.filter(student=request.user, cohort__course_id=course_id, status='active').exists()
            if not is_enrolled:
                messages.error(request, "Iltimos, kursga a'zo bo'ling.")
                return redirect('course_detail', pk=course_id)
                
            from .models import ExamAttempt
            attempt = ExamAttempt.objects.filter(student=request.user, exam_id=exam_id).first()
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
        
        from .models import ExamAttempt
        attempt = ExamAttempt.objects.filter(student=self.request.user, exam=self.object).first()
        context['attempt'] = attempt
        context['course_certificate'] = None
        if attempt and attempt.is_reviewed and attempt.passed:
            context['course_certificate'] = Certificate.objects.filter(
                student=self.request.user,
                course=course,
            ).first()
        return context

import json
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from .models import ExamAttempt, StudentAnswer, Question, Choice

class StartExamView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        exam = get_object_or_404(Exam, id=exam_id, course_id=course_id)
        
        # Check active enrollment
        if not Enrollment.objects.filter(student=request.user, cohort__course=exam.course, status='active').exists():
            return JsonResponse({'error': 'Siz ushbu kursga a\'zo emassiz.'}, status=403)
            
        from django.db import IntegrityError
        try:
            attempt, created = ExamAttempt.objects.get_or_create(
                student=request.user, 
                exam=exam
            )
        except IntegrityError:
            attempt = ExamAttempt.objects.get(student=request.user, exam=exam)
            created = False
        
        if not created and attempt.is_completed:
             return JsonResponse({'error': 'Siz bu imtihonni avval topshirgansiz.'}, status=400)

        attempt.ensure_section_reviews()
             
        return JsonResponse({'status': 'success', 'attempt_id': attempt.id, 'start_time': attempt.start_time.isoformat()})

class SaveExamAnswerView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        try:
            data = json.loads(request.body)
            question_id = data.get('question_id')
            answer_text = data.get('answer_text')
            choice_id = data.get('choice_id')
            audio_url = data.get('audio_url')
            
            attempt = get_object_or_404(ExamAttempt, student=request.user, exam_id=exam_id)
            if attempt.is_completed:
                return JsonResponse({'error': 'Imtihon yakunlangan, javob qabul qilinmaydi.'}, status=400)
                
            question = get_object_or_404(Question, id=question_id)
            
            # Security: Ensure question actually belongs to this exam
            if question.exam_section and question.exam_section.exam_id != attempt.exam_id:
                return JsonResponse({'error': 'Xatolik: Bu savol ushbu imtihonga tegishli emas.'}, status=400)
            
            # Upsert student answer
            ans, created = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)
            
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
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class LogBlurWarningView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        attempt = get_object_or_404(ExamAttempt, student=request.user, exam_id=exam_id, is_completed=False)
        attempt.blur_warnings += 1
        attempt.save()
        return JsonResponse({'status': 'logged', 'warnings': attempt.blur_warnings})

class SubmitExamView(LoginRequiredMixin, View):
    def post(self, request, course_id, exam_id):
        attempt = get_object_or_404(ExamAttempt, student=request.user, exam_id=exam_id, is_completed=False)
        attempt.is_completed = True
        attempt.completed_time = timezone.now()
        attempt.is_reviewed = False
        attempt.reviewed_at = None
        attempt.reviewed_by = None
        attempt.passed = False
        attempt.score = 0
        attempt.save(update_fields=['is_completed', 'completed_time', 'is_reviewed', 'reviewed_at', 'reviewed_by', 'passed', 'score'])

        # Prepare section-level scores so the instructor can review and approve them.
        attempt.ensure_section_reviews()
        attempt.prefill_section_scores_from_answers()
        
        return JsonResponse({'status': 'success', 'pending_review': True})

class SubmitQuizView(LoginRequiredMixin, View):
    """Dars ichidagi quiz javoblarni qabul qilish va natija hisoblash."""
    def post(self, request, course_id, lesson_id, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, lesson_id=lesson_id, lesson__module__course_id=course_id)
        
        # Enrollment tekshiruvi
        if not Enrollment.objects.filter(student=request.user, cohort__course_id=course_id, status='active').exists():
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
        xp_earned = round(quiz.xp_reward * (total_correct / total_questions))
        
        # Attempt yangilash
        attempt.score = score
        attempt.total_correct = total_correct
        attempt.xp_earned = xp_earned
        attempt.save()
        
        # Foydalanuvchiga XP qo'shish
        if xp_earned > 0:
            request.user.total_xp += xp_earned
            request.user.save(update_fields=['total_xp'])
        
        return JsonResponse({
            'status': 'success',
            'score': score,
            'total_correct': total_correct,
            'total_questions': total_questions,
            'xp_earned': xp_earned,
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
