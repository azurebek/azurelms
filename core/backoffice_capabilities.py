"""Backoffice capabilities — global ops, moliya va learner PII uchun explicit ruxsat (DASH1.0a).

Ilgari legacy dashboard, `/backoffice/users/`, `/backoffice/chats/`, chek qarori,
boshqa userning chek fayli va Telegram bot admin buyruqlari bitta keng qoidaga
tayanardi: `is_staff OR is_superuser`. Natijada har qanday xodim — biror kursga
ustoz qilib qo'yilgan odam ham — barcha o'quvchilarning shaxsiy ma'lumotini, chat
matnini, tushumni va boshqalarning chekini ko'rar, chekni tasdiqlay olardi.

Endi har global yuza o'z capability'sini so'raydi:

* superuser (platforma egasi) — explicit owner mapping: barcha capability;
* qolgan faol **staff** — faqat unga Django Group/Permission orqali aniq
  berilgan capability (`core.<nom>`); avtomatik global grant yo'q;
* o'qituvchining o'z kurs ishi capability emas: u `core.access.teacher_course_queryset`
  scope'ida qoladi;
* chek egasining o'z chek faylini ko'rishi ham capability emas — ownership tekshiruvi.

Hech bir capability Messenger matni/snippeti yoki participant email qidiruvini
bermaydi: `/backoffice/chats/` Messenger-owned metadata selector paydo bo'lguncha
hamma uchun, jumladan superuser uchun ham yopiq (fail-closed).
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

OPS_GLOBAL_VIEW = "ops_global_view"
PLATFORM_STATS_VIEW = "platform_stats_view"
FINANCE_RECEIPT_REVIEW = "finance_receipt_review"
FINANCE_CROSS_USER_RECEIPT_FILE_VIEW = "finance_cross_user_receipt_file_view"
LEARNER_PII_VIEW = "learner_pii_view"

#: codename → admin panelda ko'rinadigan nom. `core.models.BackofficeCapability`
#: shu ro'yxatdan permission yaratadi; ikkalasi testda solishtiriladi.
CAPABILITIES = {
    OPS_GLOBAL_VIEW: "Global operatsion ko'rinish (e'lon yuborish, hisob holati)",
    PLATFORM_STATS_VIEW: "Platforma statistikasini ko'rish",
    FINANCE_RECEIPT_REVIEW: "To'lov cheklarini ko'rish va tasdiqlash/rad etish",
    FINANCE_CROSS_USER_RECEIPT_FILE_VIEW: "Boshqa o'quvchining chek faylini ochish",
    LEARNER_PII_VIEW: "O'quvchilarning shaxsiy ma'lumotini ko'rish",
}

#: Botda "admin" rolini beradigan global capability'lar. Faqat kurs ustozi
#: bo'lgan xodim botda "teacher" bo'lib qoladi.
GLOBAL_CAPABILITIES = (
    OPS_GLOBAL_VIEW,
    PLATFORM_STATS_VIEW,
    FINANCE_RECEIPT_REVIEW,
    FINANCE_CROSS_USER_RECEIPT_FILE_VIEW,
    LEARNER_PII_VIEW,
)


def has_capability(user, capability):
    """Default-deny: superuser ha; faol staff faqat aniq berilgan permission bilan."""
    if capability not in CAPABILITIES:
        raise ValueError(f"Noma'lum capability: {capability}")
    if user is None or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    return user.has_perm(f"core.{capability}")


def has_any_global_capability(user):
    return any(has_capability(user, capability) for capability in GLOBAL_CAPABILITIES)


def capability_required(*capabilities):
    """View decorator: barcha capability bo'lmasa 403.

    `user_passes_test` ishlatilmaydi: u kirgan, lekin ruxsati yo'q odamni login
    sahifasiga qaytarib, cheksiz login aylanmasini beradi. Kirmagan odamni
    loginga yuborish `login_required` ning ishi — u shu decoratordan oldin turadi.
    """
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise ValueError(f"Noma'lum capability: {capability}")

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not all(has_capability(request.user, capability) for capability in capabilities):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
