"""Testlar uchun: xodimga aniq boshqaruv ruxsatini berish (DASH1.0a).

Production'da ruxsat admin panelidan guruh yoki foydalanuvchi ruxsati sifatida
beriladi. Testlar ham xuddi shu yo'ldan yuradi: oddiy Django `Permission`,
hech qanday maxsus bayroq yo'q.
"""
from django.contrib.auth.models import Permission

from core.backoffice_capabilities import CAPABILITIES


def grant_capabilities(user, *capabilities):
    unknown = set(capabilities) - set(CAPABILITIES)
    if unknown:
        raise ValueError(f"Noma'lum capability: {sorted(unknown)}")
    permissions = list(Permission.objects.filter(
        content_type__app_label="core", codename__in=capabilities,
    ))
    if len(permissions) != len(set(capabilities)):
        raise LookupError("Capability permission bazada yo'q: migratsiyani tekshiring.")
    user.user_permissions.add(*permissions)
    # Django foydalanuvchi obyektida ruxsatlarni keshlaydi.
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


def grant_all_capabilities(user):
    return grant_capabilities(user, *CAPABILITIES)
