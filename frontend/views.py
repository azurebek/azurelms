from django.shortcuts import render, redirect
from courses.models import Course
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from .models import (
    LandingAIFeature,
    LandingExamSkill,
    LandingHeroSlide,
    LandingLevelStage,
    LandingPage,
    LandingPortalListItem,
    LandingPortalTab,
    LandingProcessStep,
    Statistic,
    Testimonial,
    AboutPage,
    AboutStatistic,
    TeamMember,
    LegalPage,
)

User = get_user_model()


def _default_hero_slides():
    return [
        {
            "layout_class": "public-billboard-slide--default",
            "gradient_class": "public-billboard-slide--ocean",
            "chart_class": "poster-chart--academic",
            "poster_kicker": "Academic bulletin",
            "poster_year_label": "2026",
            "poster_title": "A1-C1",
            "poster_text": "Tartibli track, lesson workspace va dashboard bitta oqimda.",
            "poster_chip_one": "A1-C1 flow",
            "poster_chip_two": "Sertifikat track",
            "poster_chip_three": "Live support",
            "side_label": "TR",
            "side_title": "A1-C1",
            "side_text": "Turk tili, dashboard va exam flow yagona tizimda.",
            "kicker": "Turk tili platformasi",
            "title": "Akademik ruhdagi, lekin amaliy o'quv portali",
            "subtitle": "Kurs katalogi, sertifikat yo'li va o'quv muhitini bitta landing ichida tartibli ko'rsatish.",
            "primary_label": "Kurslarni ko'rish",
            "primary_url": "/courses/",
            "secondary_label": "Platforma haqida",
            "secondary_url": "/about/",
            "metric_items": [
                {"value": "6 track", "label": "A1 dan C1 gacha"},
                {"value": "10 hafta", "label": "Lesson, exam va chat"},
                {"value": "Doimiy support", "label": "Telegram va dashboard"},
            ],
        },
        {
            "layout_class": "public-billboard-slide--reverse",
            "gradient_class": "public-billboard-slide--graphite",
            "chart_class": "poster-chart--catalog",
            "poster_kicker": "Course catalog",
            "poster_year_label": "2026",
            "poster_title": "Modul",
            "poster_text": "Har modul uchun aniq lesson ritmi, material va progress oqimi.",
            "poster_chip_one": "Modul katalogi",
            "poster_chip_two": "Weekly rhythm",
            "poster_chip_three": "Study roadmap",
            "side_label": "B2",
            "side_title": "Track",
            "side_text": "Katalog, lesson plan va student dashboard bir-biriga bog'langan.",
            "kicker": "Kurs arxitekturasi",
            "title": "Katalogdan lesson workspacegacha bir xil tartib",
            "subtitle": "Kurs preview, modul ritmi va qaysi yo'l bilan sertifikatga borish aniq ko'rinadi.",
            "primary_label": "Katalogni ochish",
            "primary_url": "/courses/",
            "secondary_label": "Yo'l xaritasi",
            "secondary_url": "/about/",
            "metric_items": [
                {"value": "18-24 dars", "label": "Har kurs uchun aniq ritm"},
                {"value": "Weekly plan", "label": "Modul va homework oqimi"},
                {"value": "Lesson workspace", "label": "Video, chat va exam"},
            ],
        },
        {
            "layout_class": "public-billboard-slide--default",
            "gradient_class": "public-billboard-slide--ruby",
            "chart_class": "poster-chart--certification",
            "poster_kicker": "Certification flow",
            "poster_year_label": "2026",
            "poster_title": "Final",
            "poster_text": "Imtihon, tasdiqlash va sertifikat chiqarish bitta aniq yo'lda.",
            "poster_chip_one": "Exam workspace",
            "poster_chip_two": "Certificate ready",
            "poster_chip_three": "Admin review",
            "side_label": "Live",
            "side_title": "Support",
            "side_text": "Telegram, mentor va help center bilan doimiy aloqa mavjud.",
            "kicker": "Sertifikat yo'li",
            "title": "Imtihon va sertifikatni bir tizimda yuritish",
            "subtitle": "Exam workspace, verification va final certificate status bitta tizimda yuradi.",
            "primary_label": "Sertifikat yo'li",
            "primary_url": "/users/register/",
            "secondary_label": "Yordam markazi",
            "secondary_url": "/faq/",
            "metric_items": [
                {"value": "Exam flow", "label": "Secure workspace"},
                {"value": "Verification", "label": "Admin va status"},
                {"value": "Ready output", "label": "Certificate va history"},
            ],
        },
    ]


def _default_portal_tabs():
    return [
        {"label": "Lisans", "url": "/courses/", "is_active": True},
        {"label": "Yuqori daraja", "url": "/courses/", "is_active": False},
        {"label": "Sertifikat", "url": "/about/", "is_active": False},
    ]


def _default_portal_items():
    return [
        {"text": "Mashhur kurslar va modul ritmi"},
        {"text": "Qanday ishlaydi (4 qadam)"},
        {"text": "O'quvchilar fikri va statistika"},
        {"text": "Sertifikat va qabul yo'li"},
    ]

def home_view(request):
    """
    Renders the landing page for guests.
    Redirects authenticated users straight to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    page_content = LandingPage.load()
    statistics = Statistic.objects.filter(is_active=True)
    level_stages = list(LandingLevelStage.objects.filter(is_visible=True).order_by("order", "id"))
    ai_features = list(LandingAIFeature.objects.filter(is_visible=True).order_by("order", "id"))
    exam_skills = list(LandingExamSkill.objects.filter(is_visible=True).order_by("order", "id"))
    hero_slides = list(
        LandingHeroSlide.objects.filter(is_active=True)
        .prefetch_related("metrics")
        .order_by("order", "id")
    )
    if not hero_slides:
        hero_slides = _default_hero_slides()

    portal_tabs = list(LandingPortalTab.objects.filter(is_visible=True).order_by("order", "id"))
    if not portal_tabs:
        portal_tabs = _default_portal_tabs()

    portal_items = list(LandingPortalListItem.objects.filter(is_visible=True).order_by("order", "id"))
    if not portal_items:
        portal_items = _default_portal_items()
    
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
    how_it_works_steps = list(LandingProcessStep.objects.filter(is_visible=True).order_by("order", "id"))
    if not how_it_works_steps:
        how_it_works_steps = [
            {
                "number": 1,
                "title": page_content.how_it_works_step_one_title,
                "description": page_content.how_it_works_step_one_description,
                "icon_class": "bi bi-person-plus",
                "color_class": "",
            },
            {
                "number": 2,
                "title": page_content.how_it_works_step_two_title,
                "description": page_content.how_it_works_step_two_description,
                "icon_class": "bi bi-signpost-split",
                "color_class": "step-number--secondary",
            },
            {
                "number": 3,
                "title": page_content.how_it_works_step_three_title,
                "description": page_content.how_it_works_step_three_description,
                "icon_class": "bi bi-play-circle",
                "color_class": "step-number--success",
            },
            {
                "number": 4,
                "title": page_content.how_it_works_step_four_title,
                "description": page_content.how_it_works_step_four_description,
                "icon_class": "bi bi-patch-check",
                "color_class": "step-number--danger",
            },
        ]
    
    context = {
        'page': page_content,
        'hero_slides': hero_slides,
        'portal_tabs': portal_tabs,
        'portal_items': portal_items,
        'statistics': statistics,
        'level_stages': level_stages,
        'ai_features': ai_features,
        'exam_skills': exam_skills,
        'testimonials': testimonials,
        'popular_courses': popular_courses,
        'recent_students': recent_students,
        'how_it_works_steps': how_it_works_steps,
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
