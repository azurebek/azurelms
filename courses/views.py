from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .models import Course, Lesson, Certificate
from cohorts.models import Enrollment


class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 8
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True)
        
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
    
    def get_queryset(self):
        # Only allow accessing lessons of the specified course
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(module__course_id=course_id)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.module.course
        user = self.request.user
        
        # Security: Re-verify active enrollment
        is_enrolled = Enrollment.objects.filter(
            student=user,
            cohort__course=course,
            status='active'
        ).exists()
        
        context['is_enrolled'] = is_enrolled
        context['course'] = course
        
        # Load all modules and lessons for the sidebar Accordion ToC
        context['modules'] = course.modules.all().prefetch_related('lessons')
        
        # Load any assignments or quizzes attached to this lesson
        context['assignments'] = self.object.assignments.all()
        context['quizzes'] = self.object.quizzes.all()
        
        # Determine previous and next lessons
        all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
        current_index = all_lessons.index(self.object)
        
        if current_index > 0:
            context['prev_lesson'] = all_lessons[current_index - 1]
        
        if current_index < len(all_lessons) - 1:
            context['next_lesson'] = all_lessons[current_index + 1]
            
        return context

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
