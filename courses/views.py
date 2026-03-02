from django.views.generic import ListView, DetailView
from django.db.models import Q

from .models import Course


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
