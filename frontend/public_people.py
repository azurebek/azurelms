"""Ochiq sahifalarda odam nomi (PUB1.6a).

Hisobdagi to'liq ism; bo'lmasa umumiy nom. Login (username) ochiq sahifada,
meta'da va JSON-LD'da hech qachon chiqmaydi — u kirish identifikatori. Blog
izohi formasidagi ogohlantirish ham "hisobingizdagi ism" deydi.
"""

PUBLIC_PERSON_FALLBACK = {"author": "Platforma muallifi", "teacher": "Platforma o‘qituvchisi", "user": "Foydalanuvchi"}


def real_name(user):
    """Hisobdagi to'liq ism yoki ``""``."""
    return (user.get_full_name() if user is not None else "").strip()


def public_person_name(user, role="user"):
    return real_name(user) or PUBLIC_PERSON_FALLBACK.get(role, PUBLIC_PERSON_FALLBACK["user"])
