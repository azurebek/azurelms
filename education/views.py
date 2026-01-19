from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from courses.models import Lesson
from .forms import LessonAssignmentForm
from .models import Enrollment, LessonProgress
from .services import get_next_lesson


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = Enrollment.objects.filter(
        user=request.user,
        batch__course=lesson.module.course,
        is_active=True,
    ).first()
    if not enrollment:
        return render(request, "education/lesson_access_denied.html", {"lesson": lesson})

    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
    )
    assignment_form = LessonAssignmentForm(instance=progress)

    if request.method == "POST":
        if "mark_watched" in request.POST:
            progress.is_video_watched = True
            progress.save(update_fields=["is_video_watched"])
            messages.success(request, "Video ko'rildi deb belgilandi.")
            return redirect("education:lesson_detail", lesson_id=lesson.id)

        if "submit_assignment" in request.POST:
            assignment_form = LessonAssignmentForm(
                request.POST,
                request.FILES,
                instance=progress,
            )
            if assignment_form.is_valid():
                progress = assignment_form.save(commit=False)
                progress.assignment_status = LessonProgress.PENDING
                progress.save()
                messages.success(request, "Vazifa yuborildi. Admin tekshiradi.")
                return redirect("education:lesson_detail", lesson_id=lesson.id)

    next_lesson = get_next_lesson(enrollment, lesson)
    return render(
        request,
        "education/lesson_detail.html",
        {
            "lesson": lesson,
            "progress": progress,
            "assignment_form": assignment_form,
            "next_lesson": next_lesson,
        },
    )
