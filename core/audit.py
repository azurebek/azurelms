"""Audit ledgeriga yozishning yagona nuqtasi (A2).

Chaqiruvchilar `SystemAuditEvent` ni to'g'ridan-to'g'ri yaratmaydi: shu funksiya
request'dan actor, IP, user-agent va release SHA'ni bir xil tarzda oladi va
maxfiy maydonlarni tozalaydi. Aks holda har yuzada boshqacha to'ldirilgan
yozuvlar paydo bo'lardi.

**Ataylab tranzaksiya ichida chaqiriladi va xatoni yutmaydi.** Agar audit
yozilmasa, o'zgarishning o'zi ham qaytarilishi kerak — "amal bajarildi, lekin
kim qilgani noma'lum" holati audit ledgerining maqsadini yo'qqa chiqaradi.
"""

from aicontrol.models import SystemAuditEvent

# Before/after snapshotlarida hech qachon chiqmasligi kerak bo'lgan kalitlar.
REDACTED_KEYS = frozenset({
    "password", "password1", "password2", "token", "secret", "api_key",
    "apikey", "authorization", "csrfmiddlewaretoken", "session", "cookie",
})
REDACTED_PLACEHOLDER = "***"
MAX_VALUE_CHARS = 300


def redact(payload):
    """Maxfiy kalitlarni maskalaydi va qiymatlarni cheklab qo'yadi."""
    if not payload:
        return {}
    cleaned = {}
    for key, value in payload.items():
        name = str(key)
        if name.lower() in REDACTED_KEYS:
            cleaned[name] = REDACTED_PLACEHOLDER
            continue
        if isinstance(value, dict):
            cleaned[name] = redact(value)
            continue
        text = value if isinstance(value, (int, float, bool)) or value is None else str(value)
        if isinstance(text, str) and len(text) > MAX_VALUE_CHARS:
            text = text[:MAX_VALUE_CHARS] + "…"
        cleaned[name] = text
    return cleaned


def _client_ip(request):
    if request is None:
        return None
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or None


def record_audit_event(
    *,
    action,
    request=None,
    actor=None,
    source=SystemAuditEvent.SOURCE_WEB,
    outcome=SystemAuditEvent.OUTCOME_SUCCESS,
    target=None,
    target_label="",
    reason="",
    before=None,
    after=None,
    error="",
    idempotency_key="",
):
    """Bitta audit yozuvini yozadi va uni qaytaradi."""
    from core.control_center.snapshot import _release_sha

    if actor is None and request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            actor = candidate

    target_type = target_id = ""
    if target is not None:
        target_type = target.__class__.__name__
        target_id = str(getattr(target, "pk", "") or "")
        if not target_label:
            target_label = str(target)[:200]

    return SystemAuditEvent.objects.create(
        action=action,
        source=source,
        outcome=outcome,
        actor=actor if getattr(actor, "pk", None) else None,
        actor_label=(getattr(actor, "username", "") or "")[:150],
        target_type=target_type[:80],
        target_id=target_id[:80],
        target_label=(target_label or "")[:200],
        reason=(reason or "")[:240],
        before=redact(before),
        after=redact(after),
        error=(error or "")[:300],
        request_id=(getattr(request, "audit_request_id", "") or "")[:64],
        idempotency_key=(idempotency_key or "")[:120],
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:300],
        release_sha=_release_sha()[:40],
    )


def audit_trail_for(target, *, limit=8):
    """Berilgan obyekt bo'yicha oxirgi yozuvlar (sahifadagi tarix uchun)."""
    return SystemAuditEvent.objects.filter(
        target_type=target.__class__.__name__,
        target_id=str(target.pk),
    ).select_related("actor")[:limit]
