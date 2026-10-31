"""Bosh sahifa va "Biz haqimizda" uchun deterministik read projection (PUB1.2b).

Har renderer (legacy yoki V1) faqat o'zi chizadigan ma'lumotni oladi:
ishlatilmaydigan so'rov yo'q, foydalanuvchi PII'si (masalan, oxirgi
ro'yxatdan o'tganlar) umuman o'qilmaydi. Har ro'yxat aniq, to'liq tartibda
(oxirida `id`) — bir xil ma'lumot doim bir xil HTML beradi, random tanlov yo'q.

Statistika va fikrlar `frontend/public_claims.py` selektoridan (dalil va
rozilik bilan). Bo'sh bo'lsa bo'sh qoladi — o'rniga soxta "fallback" da'vo
qo'yilmaydi. "Qanday ishlaydi" qadamlari qatori bo'lmasa bosh sahifa
matnidagi owner kiritgan qadamlar ishlatiladi (bu da'vo emas, jarayon tavsifi).
"""

from django.db.models import Count, Q

from core.flags import flags_enabled
from frontend.models import (
    AboutPage,
    LandingAIFeature,
    LandingExamSkill,
    LandingLevelStage,
    LandingPage,
    LandingProcessStep,
    TeamMember,
)
from frontend.public_claims import public_testimonials, verified_about_statistics, verified_landing_statistics

LEGACY = "legacy"
V1 = "v1"
# PUBLIC-02: V1 ma'lumoti, editorial ramka/shablon. Proyeksiyalar uni V1 kabi o'qiydi (faqat LEGACY farq qiladi).
EDITORIAL = "editorial"
HOME_COURSE_LIMIT = 3
TESTIMONIAL_LIMIT = 3
# Editorial bosh sahifa bandlari: Journal (1 tanlangan + 3), Turkiyada o'qish (3 universitet).
HOME_JOURNAL_LIMIT = 4
HOME_SIT_LIMIT = 3


def current_renderer():
    """`render_public` bilan ayni qaror: qaysi shablon chiziladi.

    Ikkala flag bitta so'rovda o'qiladi — editorial qarori ochiq sahifalarning qulflangan so'rov byudjetiga
    yangi so'rov qo'shmaydi. Editorial faqat V1 ustida ishlaydi: `frontend_v1_public` o'chiq bo'lsa legacy.
    """
    flags = flags_enabled("frontend_v1_public", "public_editorial_v1")
    if not flags["frontend_v1_public"]:
        return LEGACY
    return EDITORIAL if flags["public_editorial_v1"] else V1


def _visible(model):
    return list(model.objects.filter(is_visible=True).order_by("order", "id"))


def _how_it_works(page):
    steps = _visible(LandingProcessStep)
    if steps:
        return steps
    texts = (
        (page.how_it_works_step_one_title, page.how_it_works_step_one_description, "bi bi-person-plus", ""),
        (page.how_it_works_step_two_title, page.how_it_works_step_two_description, "bi bi-signpost-split",
         "step-number--secondary"),
        (page.how_it_works_step_three_title, page.how_it_works_step_three_description, "bi bi-play-circle",
         "step-number--success"),
        (page.how_it_works_step_four_title, page.how_it_works_step_four_description, "bi bi-patch-check",
         "step-number--danger"),
    )
    return [
        {"number": number, "title": title, "description": description, "icon_class": icon, "color_class": color}
        for number, (title, description, icon, color) in enumerate(texts, start=1)
    ]


def home_courses():
    """Faol kurslar: ko'p faol o'quvchili oldin, teng bo'lsa yangisi, so'ng `id` — doim bir xil."""
    from courses.models import Course

    return list(
        Course.objects.filter(is_active=True)
        .select_related("instructor")
        # Kartada faqat o'qituvchi nomi: email, telefon, parol xeshi va
        # Telegram ID xotiraga ham o'qilmaydi.
        .only("id", "title", "description", "level", "created_at", "instructor__id",
              "instructor__first_name", "instructor__last_name", "instructor__username")
        .annotate(
            annotated_lessons_count=Count("modules__lessons", distinct=True),
            annotated_students_count=Count(
                "cohorts__members", filter=Q(cohorts__members__status="active"), distinct=True,
            ),
        )
        .order_by("-annotated_students_count", "-created_at", "-id")[:HOME_COURSE_LIMIT]
    )


def home_projection(renderer=None):
    renderer = renderer or current_renderer()
    page = LandingPage.current()
    data = {
        "page": page,
        "statistics": verified_landing_statistics(),
        "how_it_works_steps": _how_it_works(page),
    }
    if renderer == LEGACY:
        data.update(
            level_stages=_visible(LandingLevelStage),
            ai_features=_visible(LandingAIFeature),
            exam_skills=_visible(LandingExamSkill),
        )
    else:
        data.update(
            popular_courses=home_courses(),
            testimonials=public_testimonials(TESTIMONIAL_LIMIT),
        )
    if renderer == EDITORIAL:
        # Editorial bosh sahifaning qo'shimcha bandlari — faqat o'z domen adapterlaridan (yangi qoida yo'q).
        from blog.listing import latest_posts
        from sit.selectors import featured_open_universities

        data.update(
            journal_posts=latest_posts(HOME_JOURNAL_LIMIT),
            sit_universities=featured_open_universities(HOME_SIT_LIMIT),
            course_levels=course_levels(),
        )
    return data


def course_levels():
    """Daraja tanlash bandi uchun — katalog filtrining o'zi qabul qiladigan qiymatlar (`Course.LEVEL_CHOICES`)."""
    from courses.models import Course

    return Course.LEVEL_CHOICES


def about_projection(renderer=None):
    renderer = renderer or current_renderer()
    statistics = verified_about_statistics()
    team = list(TeamMember.objects.order_by("order", "id"))
    data = {"page": AboutPage.current(), "statistics": statistics, "team": team}
    if renderer == LEGACY:
        data.update(
            highlighted_statistics=statistics[:3],
            featured_member=team[0] if team else None,
            team_members=team[1:],
            testimonials=public_testimonials(TESTIMONIAL_LIMIT),
        )
    if renderer == EDITORIAL:
        data["course_levels"] = course_levels()
    return data
