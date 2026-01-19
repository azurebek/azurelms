from django.shortcuts import render, get_object_or_404
from .models import Course, Batch

def course_list(request):
    courses = Course.objects.all()
    # Aktiv batchlarni ham olish mumkin agar kerak bo'lsa
    return render(request, "courses/course_list.html", {"courses": courses})

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    batches = Batch.objects.filter(course=course, status=Batch.ENROLLING) # Faqat yozilish mumkin bo'lganlari
    return render(request, "courses/course_detail.html", {
        "course": course,
        "batches": batches
    })
