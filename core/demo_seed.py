"""QA va demo uchun ma'lumot to'plami (A5 / R4).

Lokal bazada kurs, dars va imtihon yo'q, ya'ni mobil QA faqat bo'sh ekranlarni
ko'radi. A5 esa dars sarlavhasi, imtihon landscape, checkout va davomat
sahifalarini talab qiladi; R4 esa "fresh demo account" so'raydi.

Ikkita qoida butun modulni belgilaydi:

1. **Faqat lokal.** Chaqiruvchi buyruq `settings.IS_LOCAL` ni tekshiradi va
   aks holda ishlamaydi. Demo ma'lumot haqiqiy bazaga tushsa, u yerdagi
   hisobotlar va to'lovlar bilan aralashib ketadi.
2. **Qaytarib olinadi.** Hamma narsa `DEMO_MARK` yoki `demo-` prefiksi bilan
   belgilanadi va `wipe_demo_data()` faqat o'shalarni oladi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import Assignment, Course, Lesson, Module
from subscriptions.models import Plan

#: Demo yozuvlarini haqiqiy yozuvlardan ajratadigan belgi.
DEMO_MARK = "[demo]"
DEMO_USER_PREFIX = "demo-"

#: Mobil layoutni haqiqatan sinash uchun matn yetarlicha uzun bo'lishi kerak —
#: bir qatorlik dars overflow yoki uzun so'z muammosini ko'rsatmaydi.
LESSON_BODY = (
    "<p>Turk tilida <b>gelmek</b> fe'li kelmoq ma'nosini beradi. Hozirgi zamon "
    "uchun <i>-iyor</i> qo'shimchasi ishlatiladi: <code>geliyorum</code>, "
    "<code>geliyorsun</code>, <code>geliyor</code>.</p>"
    "<p>Diqqat qiling: unli uyg'unligi qoidasi qo'shimchaning shaklini "
    "o'zgartiradi. Masalan <b>bakmak</b> fe'lida <code>bakiyorum</code> emas, "
    "<code>bakıyorum</code> bo'ladi — chunki oxirgi unli orqa qatorli.</p>"
    "<p>Mashq: quyidagi gaplarni tarjima qiling va har birida fe'lning "
    "shaxs-son qo'shimchasini ajratib ko'rsating. Uzun so'zlar ham bo'lsin: "
    "<b>muvaffaqiyatsizlashtirilganlardanmisiz</b>.</p>"
)


def _lesson_titles():
    return [
        ("1-modul: Asoslar", [
            "Alifbo va talaffuz",
            "Salomlashish va tanishuv",
            "Unli uyg'unligi qoidasi",
        ]),
        ("2-modul: Hozirgi zamon", [
            "Hozirgi zamon -iyor",
            "Inkor va so'roq shakllari",
        ]),
    ]


@transaction.atomic
def seed_demo_data():
    """Yurib chiqiladigan kurs, guruh va faol o'quvchi yaratadi. Idempotent."""
    User = get_user_model()

    teacher, _ = User.objects.get_or_create(
        username=f"{DEMO_USER_PREFIX}teacher",
        defaults={"email": "demo-teacher@example.com", "is_staff": True,
                  "first_name": "Demo", "last_name": "O'qituvchi"},
    )
    student, created_student = User.objects.get_or_create(
        username=f"{DEMO_USER_PREFIX}student",
        defaults={"email": "demo-student@example.com",
                  "first_name": "Demo", "last_name": "O'quvchi"},
    )
    if created_student:
        student.set_password("demo12345")
        student.save(update_fields=["password"])

    course, _ = Course.objects.get_or_create(
        title=f"{DEMO_MARK} Turk tili A1",
        defaults={
            "description": "QA uchun demo kurs. Haqiqiy kontent emas.",
            "instructor": teacher,
            "level": "beginner",
        },
    )

    for module_index, (module_title, lesson_titles) in enumerate(_lesson_titles(), start=1):
        module, _ = Module.objects.get_or_create(
            course=course, title=module_title, defaults={"order": module_index}
        )
        for lesson_index, lesson_title in enumerate(lesson_titles, start=1):
            lesson, _ = Lesson.objects.get_or_create(
                module=module,
                title=lesson_title,
                defaults={"content": LESSON_BODY, "order": lesson_index, "xp_reward": 20},
            )
            if lesson_index == 1:
                Assignment.objects.get_or_create(
                    lesson=lesson,
                    title=f"{lesson_title} — yozma mashq",
                    defaults={
                        "description": "Darsda ko'rilgan qoidaga besh dona misol yozing.",
                        "max_xp": 40,
                    },
                )

    cohort, _ = Cohort.objects.get_or_create(
        name=f"{DEMO_MARK} Kechki guruh",
        course=course,
        defaults={"start_date": timezone.localdate(), "is_active": True,
                  "is_checkout_default": True},
    )

    plan = Plan.objects.order_by("order", "id").first()
    Enrollment.objects.get_or_create(
        student=student,
        cohort=cohort,
        defaults={
            "status": Enrollment.STATUS_ACTIVE,
            "plan": plan,
            "next_payment_deadline": timezone.localdate() + datetime.timedelta(days=30),
        },
    )
    return {"course": course, "cohort": cohort, "teacher": teacher, "student": student}


@transaction.atomic
def wipe_demo_data():
    """Faqat demo belgisi bor yozuvlarni oladi; qolganiga tegmaydi."""
    User = get_user_model()

    # Tartib muhim: `Cohort.course` PROTECT bilan bog'langan, ya'ni kursni
    # undan oldin o'chirib bo'lmaydi.
    Cohort.objects.filter(name__startswith=DEMO_MARK).delete()
    Course.objects.filter(title__startswith=DEMO_MARK).delete()
    User.objects.filter(username__startswith=DEMO_USER_PREFIX).delete()
