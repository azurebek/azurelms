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
from courses.models import (
    Assignment, Choice, Course, Exam, ExamSection, Lesson, Module, Question,
)
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

    _seed_demo_exam(course)

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


#: Har bo'lim turi imtihon UIda boshqacha render qilinadi (variant tanlash,
#: uzun o'qish matni, so'z hisoblagichli maydon, audio pleyer, mikrofon yozuvi).
#: Bittasini qoldirish qolgan yuzalarni sinovsiz qoldiradi — shuning uchun
#: beshalasi ham seed qilinadi. Landscape (568x320) eng tor holat.
DEMO_EXAM_SECTIONS = (
    {
        "section_type": "grammar_quiz",
        "title": "Grammatika va lug'at",
        "instructions": "Har savol uchun bitta to'g'ri javobni tanlang.",
        "max_score": 20,
        "time_limit_minutes": 10,
        "questions": [
            {
                "text": "Quyidagilardan qaysi biri <b>gelmek</b> fe'lining hozirgi zamon shakli?",
                "choices": [("geliyorum", True), ("geldim", False), ("gelecegim", False)],
            },
            {
                "text": "Unli uyg'unligi qoidasiga ko'ra <b>bakmak</b> fe'li qanday bo'ladi?",
                "choices": [("bakiyorum", False), ("bakiyorum (orqa qatorli)", True), ("bakmisim", False)],
            },
        ],
    },
    {
        "section_type": "reading",
        "title": "O'qish",
        "instructions": "Matnni o'qing va savolga javob bering.",
        "reading_text": (
            "Ankara Turkiyaning poytaxti bo'lib, mamlakatning markaziy qismida joylashgan. "
            "Shahar 1923-yilda poytaxt maqomini olgan. Bugungi kunda u davlat idoralari, "
            "universitetlar va yirik kutubxonalari bilan tanilgan. Ankarada yashovchilar "
            "qishda sovuq, yozda esa quruq iqlimga o'rganib qolishgan."
        ),
        "max_score": 20,
        "time_limit_minutes": 15,
        "questions": [
            {
                "text": "Ankara qachon poytaxt bo'lgan?",
                "choices": [("1923-yilda", True), ("1908-yilda", False), ("1945-yilda", False)],
            },
        ],
    },
    {
        "section_type": "writing",
        "title": "Yozish",
        "instructions": "Berilgan mavzuda qisqa matn yozing.",
        "max_score": 25,
        "time_limit_minutes": 20,
        "questions": [
            {
                "text": "O'z shahringiz haqida yozing: iqlim, odamlar va sizga yoqadigan joy.",
                "min_word_count": 40,
                "max_word_count": 120,
            },
        ],
    },
    {
        "section_type": "listening",
        "title": "Eshitish",
        "instructions": "Audioni tinglang va savolga javob bering. Audio cheklangan marta ijro etiladi.",
        "media_url": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Example.ogg",
        "audio_play_limit": 2,
        "max_score": 20,
        "time_limit_minutes": 10,
        "questions": [
            {
                "text": "Audioda nima haqida gapirilyapti?",
                "choices": [("Ob-havo", True), ("Sport", False), ("Musiqa", False)],
            },
        ],
    },
    {
        "section_type": "speaking",
        "title": "Gapirish",
        "instructions": (
            "Savolni o'qing va ovozingizni yozib javob bering. "
            "Mikrofon faqat xavfsiz ulanishda (HTTPS yoki localhost) ishlaydi."
        ),
        "max_score": 15,
        "time_limit_minutes": 10,
        "questions": [
            {"text": "O'zingiz haqingizda qisqacha gapiring: ism, kasb va turk tilini nima uchun o'rganyapsiz."},
        ],
    },
)


def _seed_demo_exam(course):
    """Imtihon yuzasini sinash mumkin bo'lishi uchun demo imtihon.

    Bu yerda bo'lmaganda A5 ning imtihon bandi na avtomatik probe bilan, na
    owner tomonidan qurilmada sinalishi mumkin edi — sinaydigan narsaning
    o'zi yo'q edi. Speaking bo'limi mikrofon oqimi uchun majburiy.
    """
    exam, _ = Exam.objects.get_or_create(
        course=course,
        title=f"{DEMO_MARK} A1 yakuniy imtihon",
        defaults={
            "exam_type": "final",
            "weight_percentage": 40,
            "passing_score": 60,
            "max_attempts": 3,
        },
    )

    for order, spec in enumerate(DEMO_EXAM_SECTIONS, start=1):
        section, _ = ExamSection.objects.get_or_create(
            exam=exam,
            section_type=spec["section_type"],
            defaults={
                "title": spec["title"],
                "instructions": spec["instructions"],
                "reading_text": spec.get("reading_text", ""),
                "media_url": spec.get("media_url", ""),
                "audio_play_limit": spec.get("audio_play_limit", 0),
                "max_score": spec["max_score"],
                "time_limit_minutes": spec["time_limit_minutes"],
                "order": order,
            },
        )
        for question_spec in spec["questions"]:
            question, _ = Question.objects.get_or_create(
                exam_section=section,
                text=question_spec["text"],
                defaults={
                    "points": 5,
                    "min_word_count": question_spec.get("min_word_count", 0),
                    "max_word_count": question_spec.get("max_word_count", 0),
                },
            )
            for choice_text, is_correct in question_spec.get("choices", []):
                Choice.objects.get_or_create(
                    question=question, text=choice_text, defaults={"is_correct": is_correct}
                )

    return exam


@transaction.atomic
def wipe_demo_data():
    """Faqat demo belgisi bor yozuvlarni oladi; qolganiga tegmaydi."""
    User = get_user_model()

    # Tartib muhim: `Cohort.course` PROTECT bilan bog'langan, ya'ni kursni
    # undan oldin o'chirib bo'lmaydi.
    Cohort.objects.filter(name__startswith=DEMO_MARK).delete()
    Course.objects.filter(title__startswith=DEMO_MARK).delete()
    User.objects.filter(username__startswith=DEMO_USER_PREFIX).delete()
