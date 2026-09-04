"""Suhbatdoshning profil kartasi — kim ko'rsa, nimani ko'radi.

Telegram'da profil rasmiga bosilganda o'ngdan ma'lumot paneli ochiladi.
Bu yerda ham shunday, ammo bitta muhim farq bilan: Telegram — kontaktlar
ilovasi, bu esa **o'quv platformasi**. Guruhdagi o'quvchining telefon raqami
va emailini sinfdoshlariga ko'rsatish shaxsiy ma'lumotni tarqatish bo'lardi.

Shuning uchun ikki qatlam:

* **suhbatdoshlar** ismni, rasmni, rolni, bio'ni, darajani va umumiy guruhni
  ko'radi — bularning hammasi platformada allaqachon ochiq (masalan
  reyting jadvalida ism va XP turadi);
* **xodim (staff/owner)** qo'shimcha aloqa ma'lumotlarini ko'radi — u
  buni backoffice foydalanuvchilar sahifasida ham ko'ra oladi, ya'ni yangi
  ruxsat ochilmayapti, mavjudi shu joyga keltirilyapti.

Va yagona gate: **umumiy xonasi bo'lmagan odam** hech narsa ko'rmaydi.
Aks holda istalgan o'quvchi id'ni almashtirib butun bazani o'qib chiqardi.
"""

from django.contrib.auth import get_user_model

from .models import ChatRoom


def shares_a_room(viewer, target):
    """Ikkalasi bitta suhbatda turadimi (o'zini ko'rish ham ruxsat)."""
    if not viewer or not viewer.is_authenticated or not target:
        return False
    if viewer.pk == target.pk:
        return True
    return (
        ChatRoom.objects.filter(participants=viewer)
        .filter(participants=target)
        .exists()
    )


def _role_label(user):
    if user.is_superuser:
        return "Administrator"
    if user.is_staff:
        return "O'qituvchi"
    return "O'quvchi"


def _shared_rooms(viewer, target):
    if viewer.pk == target.pk:
        return []
    rooms = (
        ChatRoom.objects.filter(participants=viewer)
        .filter(participants=target)
        .exclude(room_type="ai")
        .select_related("cohort__course")
        .order_by("id")
    )
    labels = []
    for room in rooms:
        if room.cohort_id:
            labels.append(f"{room.cohort.name} · {room.cohort.course.title}")
        elif room.name:
            labels.append(room.name)
    return labels[:4]


def profile_card(viewer, target_id):
    """Profil kartasi (yoki `None` — ko'rish huquqi yo'q).

    `None` ataylab: "bu odam yo'q" va "sizga ko'rsatilmaydi" farqi
    tashqaridan bilinmasin.
    """
    User = get_user_model()
    target = User.objects.filter(pk=target_id, is_active=True).first()
    if target is None or not shares_a_room(viewer, target):
        return None

    full_name = target.get_full_name().strip() or target.username
    avatar_url = ""
    if getattr(target, "avatar", None):
        try:
            avatar_url = target.avatar.url
        except ValueError:
            avatar_url = ""

    card = {
        "id": target.pk,
        "name": full_name,
        "initial": (full_name[:1] or "?").upper(),
        "avatar_url": avatar_url,
        "role": _role_label(target),
        "bio": (target.bio or "").strip(),
        "total_xp": int(target.total_xp or 0),
        "joined": target.date_joined.strftime("%d.%m.%Y") if target.date_joined else "",
        "shared": _shared_rooms(viewer, target),
        "is_self": viewer.pk == target.pk,
        "contacts": [],
    }

    # Aloqa ma'lumotlari faqat xodimga va odamning o'ziga.
    if viewer.is_staff or viewer.is_superuser or viewer.pk == target.pk:
        for label, value in (
            ("Email", target.email),
            ("Telefon", target.phone_number),
            ("Telegram", f"@{target.telegram_username}" if target.telegram_username else ""),
        ):
            if value:
                card["contacts"].append({"label": label, "value": value})
    return card
