from django.shortcuts import render, redirect
from courses.models import Course
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from .models import (
    LandingPage,
    Statistic,
    Testimonial,
    AboutPage,
    AboutStatistic,
    TeamMember,
    LegalPage,
)

User = get_user_model()

def home_view(request):
    """
    Renders the landing page for guests.
    Redirects authenticated users straight to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    page_content = LandingPage.load()
    statistics = Statistic.objects.all()
    
    # Optimize: Avoid slow SQL `ORDER BY RAND()`/`RANDOM()` which kills performance on large DBs
    import random
    active_testis = list(Testimonial.objects.filter(is_active=True))
    testimonials = random.sample(active_testis, min(len(active_testis), 3)) if active_testis else []
    
    # Try to get top 3 popular courses (for now we can just order by id or published date)
    popular_courses = (
        Course.objects.filter(is_active=True)
        .select_related("instructor")
        .annotate(
            annotated_lessons_count=Count("modules__lessons", distinct=True),
            annotated_students_count=Count(
                "cohorts__members",
                filter=Q(cohorts__members__status="active"),
                distinct=True,
            ),
        )
        .order_by("-annotated_students_count", "-created_at")[:3]
    )
    recent_students = User.objects.filter(is_superuser=False).order_by('-date_joined')[:4]
    
    context = {
        'page': page_content,
        'statistics': statistics,
        'testimonials': testimonials,
        'popular_courses': popular_courses,
        'recent_students': recent_students,
    }
    
    return render(request, 'index.html', context)

def about_view(request):
    page_content = AboutPage.load()
    statistics = list(AboutStatistic.objects.all())
    team = list(TeamMember.objects.all())
    featured_member = team[0] if team else None
    team_members = team[1:] if team else []

    import random

    active_testimonials = list(Testimonial.objects.filter(is_active=True))
    testimonials = random.sample(active_testimonials, min(len(active_testimonials), 3)) if active_testimonials else []
    
    context = {
        'page': page_content,
        'statistics': statistics,
        'highlighted_statistics': statistics[:3],
        'team': team,
        'featured_member': featured_member,
        'team_members': team_members,
        'testimonials': testimonials,
    }
    
    return render(request, 'about.html', context)


def _get_legal_page(page_type):
    defaults = LegalPage.defaults_for(page_type)
    page, _ = LegalPage.objects.get_or_create(
        page_type=page_type,
        defaults=defaults,
    )
    return page


def legal_page_view(request, page_type):
    page = _get_legal_page(page_type)
    return render(
        request,
        "legal_page.html",
        {
            "legal_page": page,
            "active_legal_page": page_type,
        },
    )
