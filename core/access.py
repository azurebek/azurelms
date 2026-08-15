def is_backoffice_user(user):
    return user.is_staff or user.is_superuser


def is_control_center_owner(user):
    return user.is_active and user.is_superuser


def teacher_course_queryset(user):
    """O'qituvchi ko'ra oladigan kurslar — barcha adapterlar uchun yagona scope.

    Default-deny (`launch-plan/05-launch-ops.md` permission matritsasi,
    backlog `A0b`): superuser hammasini ko'radi, qolgan har kim faqat o'ziga
    instructor sifatida biriktirilgan kurslarni. Biriktirilmagan bo'lsa
    natija bo'sh. Nofaol yoki anonim foydalanuvchi hech nima ko'rmaydi.

    Bu qoida web teacher paneli va Telegram bot adapterida alohida-alohida
    yozilgan edi va ikkalasi ham default-allow tomonga og'gan edi (web:
    biriktirilmagan staff barcha kurslarni ko'rardi; bot: har qanday active
    staff barcha guruhlarni ko'rardi). Endi ikkala adapter shu funksiyani
    iste'mol qiladi; scope o'zgarishi bir joyda bo'ladi.
    """
    from courses.models import Course

    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Course.objects.none()
    if user.is_superuser:
        return Course.objects.all()
    return Course.objects.filter(instructor=user)


def teacher_cohort_queryset(user):
    """`teacher_course_queryset()` dan kelib chiqadigan guruh scope'i."""
    from cohorts.models import Cohort

    return Cohort.objects.filter(course__in=teacher_course_queryset(user))
