from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Course, Batch

def course_list(request):
    query = request.GET.get('q')
    courses = Course.objects.all()

    if query:
        courses = courses.filter(title__icontains=query)

    return render(request, "courses/course_list.html", {"courses": courses, "query": query})

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    # ENROLLING yoki ACTIVE bo'lgan guruhlarni chiqaramiz
    batches = Batch.objects.filter(course=course).exclude(status=Batch.CLOSED).order_by('start_date')
    
    return render(request, "courses/course_detail.html", {
        "course": course,
        "batches": batches
    })
