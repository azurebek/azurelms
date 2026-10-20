"""SIT ochiq sahifalari uchun ruxsat qoidasi (PUB1.6b).

Qoralama (nashr etilmagan universitet yoki qo'llanma) `?preview=1` bilan faqat
shu qoida ruxsat bergan foydalanuvchiga ochiladi; boshqalarga oddiy 404. Hozirgi
qoida — faol xodim yoki superuser; SIT1.0a uni toraytiradi (masalan, faqat owner),
lekin chaqiruvchilar o'zgarmaydi.
"""


def can_preview(user):
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )


def preview_requested(request):
    return request.GET.get("preview") == "1" and can_preview(request.user)
