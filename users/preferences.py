"""Canonical preference persistence shared by settings and messenger endpoints."""
from django.db import transaction

from .models import CustomUser


def save_ai_preference(user, field, value):
    """Record a mutation even if a later request restores the old value (ABA).

    Views own choice validation. Raw admin/ORM writes are not revision-aware.
    A single monotonic counter conservatively stales all AI preference forms.
    """
    if field not in {'ai_tone', 'ai_model', 'ai_web_search_effort', 'ai_memory_enabled'}:
        raise ValueError('Unsupported AI preference field')
    with transaction.atomic():
        current = CustomUser.objects.select_for_update().get(pk=user.pk)
        changed = getattr(current, field) != value
        if changed:
            setattr(current, field, value)
            current.ai_preferences_version += 1
            current.save(update_fields=[field, 'ai_preferences_version'])
        setattr(user, field, getattr(current, field))
        user.ai_preferences_version = current.ai_preferences_version
        return changed
