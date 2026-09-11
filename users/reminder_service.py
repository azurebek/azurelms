"""Oldinga qaragan eslatmalar — canonical servis (T2).

**Nima uchun kerak edi.** Audit ko'rsatdi: platformada 11 ta bildirishnoma
triggeri bor va **hammasi reaktiv** — chek tasdiqlandi, dars ochildi, vazifa
baholandi. Ya'ni bot hech qachon birinchi gapirmaydi. Jonli kurs uchun eng
qimmatli xabar esa hodisadan **oldin** keladigani.

**Nima qurildi va nima qurilmadi.** Reja uchta eslatmani nomlagan edi, ammo
ikkitasi ma'lumot modelida umuman yo'q:

* «Darsingiz bir soatdan keyin» — hech qayerda **rejalashtirilgan dars vaqti
  saqlanmaydi**. `Cohort.start_date` kurs boshlanishi, `attendance_date` esa
  o'tgan darsning yozuvi; jonli dars o'qituvchining `/dars N` amali bilan
  ad-hoc boshlanadi. Jadval modeli — mahsulot qarori (haftalik takrorlanuvchi
  jadvalmi yoki har sessiya alohidami), shuning uchun bu yerda taxmin
  qilinmadi.
* «Vazifa muddati ertaga» — `Assignment` da muddat maydoni **yo'q** (faqat
  lesson, title, description, max_xp).

Shu sabab T2 ning qurilgan qismi ikkita: **to'lov muddati** eslatmasi (u
allaqachon bor edi, lekin oynalari kodda qotib turardi — qarang
`users/notification_service.py`) va **o'qituvchi navbati** eslatmasi, quyida.

**Nega digest, har topshiriq uchun alohida emas.** Har kutayotgan topshiriq
uchun bitta xabar yuborilsa, o'n topshiriq o'n bildirishnoma bo'lardi va
ular o'qituvchining haqiqiy ishidan ko'ra ko'proq shovqin yasardi. Kuniga
bitta yig'ma xabar navbat bo'shaguncha takrorlanadi va bo'shagach o'z-o'zidan
to'xtaydi.
"""

import logging
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

FLAG_TEACHER_REVIEW = "reminder_teacher_review"


def _teacher_candidates():
    """Eslatma olishi mumkin bo'lgan foydalanuvchilar.

    Nomzodlar ro'yxati keng olinadi (staff yoki biror kursning instructori),
    haqiqiy ko'rinish esa har biri uchun canonical scope bilan hisoblanadi
    (`core/access.py::teacher_course_queryset`). Ya'ni "kim qaysi kursni
    ko'radi" qoidasi bu yerda **qayta yozilmaydi** — A0b/1 aynan shu
    nusxalanish sababli tuzatilgan edi (bot adapterida qoida teskari yozilib,
    har qanday faol staff barcha guruhlarni ko'rardi).

    Nofaol hisob ro'yxatga kirmaydi; `teacher_course_queryset` ham uni bo'sh
    natija bilan rad etadi, ya'ni himoya ikki qatlamda.
    """
    from django.db.models import Q

    from users.models import CustomUser

    return (
        CustomUser.objects.filter(is_active=True)
        .filter(Q(is_staff=True) | Q(courses__isnull=False))
        .distinct()
    )


def pending_review_summary(user, *, older_than_days, now=None):
    """`user` scope'idagi uzoq kutayotgan topshiriqlar: `(soni, eng eskisi)`."""
    from core.access import teacher_course_queryset
    from courses.models import AssignmentSubmission

    now = now or timezone.now()
    cutoff = now - timedelta(days=older_than_days)
    courses = teacher_course_queryset(user)
    queryset = AssignmentSubmission.objects.filter(
        status=AssignmentSubmission.STATUS_PENDING,
        submitted_at__lte=cutoff,
        assignment__lesson__module__course__in=courses,
    )
    oldest = queryset.order_by("submitted_at").values_list("submitted_at", flat=True).first()
    return queryset.count(), oldest


def _review_message(count, oldest, now):
    days = (now - oldest).days if oldest else 0
    if count == 1:
        head = "1 ta topshiriq tekshiruvni kutmoqda."
    else:
        head = f"{count} ta topshiriq tekshiruvni kutmoqda."
    if days >= 1:
        head += f" Eng eskisi {days} kundan beri."
    return head + " Navbatni ochish uchun bosing."


def send_teacher_review_reminders(*, now=None):
    """Uzoq tekshirilmagan topshiriqlar haqida kunlik yig'ma eslatma.

    Yuborilgan xabarlar sonini qaytaradi. Idempotent: `external_key` da sana
    bor, ya'ni beat kuniga bir necha marta yugursa ham o'qituvchi bitta
    eslatma oladi.
    """
    from core.flags import flag_enabled
    from users.models import Notification
    from users.notification_service import create_notification
    from users.reminder_settings import current_policy

    if not flag_enabled(FLAG_TEACHER_REVIEW):
        return 0

    now = now or timezone.now()
    policy = current_policy()
    today = timezone.localdate()
    url = reverse("teacher_grading")

    sent = 0
    for user in _teacher_candidates():
        count, oldest = pending_review_summary(
            user, older_than_days=policy.teacher_review_after_days, now=now
        )
        if not count:
            # Navbat bo'sh — eslatma ham yo'q. Shu sabab "hammasi
            # tekshirilgan" holati o'z-o'zidan jim bo'ladi.
            continue
        _, created = create_notification(
            recipient=user,
            title="Tekshiruv navbati",
            message=_review_message(count, oldest, now),
            icon="inbox",
            url=url,
            category=Notification.CATEGORY_REMINDER,
            external_key=f"reminder-review-{user.id}-{today.isoformat()}",
        )
        if created:
            sent += 1
    return sent
