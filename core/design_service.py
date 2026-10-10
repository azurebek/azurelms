"""Owner design drafts and publications: one transactional, durable writer."""
from copy import deepcopy
import hashlib
import json
import unicodedata
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.utils import timezone

from core.audit import record_audit_event
from core.design_models import DesignDraft, DesignOperation, DesignPreset, DesignState, DesignVersion
from core.design_schema import DesignValidationError, defaults, validate
from core.flags import flag_enabled


FLAG = "backoffice_design_workspace"
COMMAND_FIELDS = {
    "save_draft": {"value", "draft_revision", "base_version"},
    "publish": {"draft_revision", "base_version", "reason", "confirmed"},
    "rollback": {"target_version", "base_version", "reason", "confirmed"},
    "save_preset": {"name", "value"},
    "delete_preset": {"preset_id"},
}


class DesignError(Exception):
    def __init__(self, message, *, code="invalid", status=400, errors=None):
        self.message, self.code, self.status, self.errors = message, code, status, errors
        super().__init__(message)


def _owner(actor, *, lock=False):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise DesignError("Hisobga kirish kerak.", code="anonymous", status=401)
    users = get_user_model().objects
    if lock:
        users = users.select_for_update()
    current = users.filter(pk=actor.pk).first()
    if current is None or not current.is_active or not current.is_superuser:
        raise DesignError("Bu amal faqat platforma administratoriga ruxsat etilgan.", code="forbidden", status=403)
    return current


def _operation(value):
    try:
        if type(value) is not str or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise DesignError("Amal belgisi mos emas. Sahifani qayta oching.") from None
    return value


def _snapshot(value):
    try:
        return validate(value)
    except DesignValidationError as error:
        details = {"field": error.field, "section": error.section} if error.field or error.section else None
        raise DesignError(str(error), code="validation", errors=details) from error


def _payload(command, payload):
    if (type(command) is not str or command not in COMMAND_FIELDS
            or type(payload) is not dict or set(payload) != COMMAND_FIELDS[command]):
        raise DesignError("So‘rov maydonlari mos emas.")
    # Only value is structured, and its schema validates scalar leaves before
    # copying. Reject malformed nested input without traversing its graph.
    normalized = dict(payload)
    for key in ("base_version", "draft_revision", "target_version", "preset_id"):
        if key in normalized and (type(normalized[key]) is not int or normalized[key] < (1 if key == "preset_id" else 0)
                                  or normalized[key] > 9223372036854775807):
            raise DesignError("Versiya yoki variant raqami mos emas.")
    if "value" in normalized:
        normalized["value"] = _snapshot(normalized["value"])
    if command in {"publish", "rollback"}:
        reason = normalized["reason"]
        if (normalized["confirmed"] is not True or type(reason) is not str
                or not 3 <= len(reason.strip()) <= 240
                or any(unicodedata.category(character) in {"Cc", "Cs"} for character in reason)):
            raise DesignError("3–240 belgili sabab yozing va tatbiqni tasdiqlang.")
        normalized["reason"] = reason.strip()
    if command == "save_preset":
        name = normalized["name"]
        if (type(name) is not str or not 1 <= len(name.strip()) <= 60
                or any(unicodedata.category(character) in {"Cc", "Cs"} for character in name)):
            raise DesignError("Variant nomi 1–60 belgi bo‘lsin.")
        normalized["name"] = name.strip()
    return normalized


def _factory():
    return {"version": 0, "value": defaults(), "reason": "Asl Azure", "created_at": None}


def _published(state):
    version = state.current_version if state is not None else None
    if version is None:
        return _factory()
    return {"version": version.number, "value": _snapshot(version.value), "reason": version.reason,
            "created_at": version.created_at.isoformat()}


def _state(actor, *, operation=None):
    state = DesignState.objects.select_related("current_version").filter(pk=1).first()
    published = _published(state)
    draft = DesignDraft.objects.filter(owner=actor).first()
    draft_data = ({"revision": draft.revision, "base_version": draft.base_version, "value": _snapshot(draft.value)}
                  if draft is not None else
                  {"revision": 0, "base_version": published["version"], "value": deepcopy(published["value"])})
    history = [{"version": item.number, "value": deepcopy(item.value), "reason": item.reason,
                "created_at": item.created_at.isoformat()}
               for item in DesignVersion.objects.order_by("-number")]
    receipt = DesignOperation.objects.filter(actor=actor, operation=operation).first() if operation else None
    return {
        "published": published, "draft": draft_data, "history": history or [_factory()],
        "presets": [{"id": preset.pk, "name": preset.name, "value": deepcopy(preset.value)}
                    for preset in DesignPreset.objects.filter(owner=actor, deleted_at__isnull=True)],
        "receipt": {"operation": str(receipt.operation), "result": deepcopy(receipt.result)} if receipt else None,
    }


def read_state(actor, operation=None):
    """Private projection. A missing draft is virtual; no GET creates rows."""
    actor = _owner(actor)
    if operation is not None:
        operation = _operation(operation)
    return _state(actor, operation=operation)


def read_published():
    """Public-safe read; unavailable storage/flag/schema leaves static defaults."""
    fallback = {"version": 0, "value": defaults()}
    try:
        if not flag_enabled(FLAG):
            return fallback
        state = DesignState.objects.select_related("current_version").filter(pk=1).first()
        published = _published(state)
    except (DatabaseError, DesignError, ValueError, TypeError):
        return fallback
    return {"version": published["version"], "value": published["value"]}


def _audit(actor, request, operation, command, target, before, after, reason):
    record_audit_event(action=f"design.{command}", actor=actor, request=request, target=target,
                       reason=reason, before=before, after=after, idempotency_key=operation)


def _stale(message="Boshqa oynada ko‘rinish yangilangan. Joriy holatni o‘qib, farqni qayta tekshiring."):
    raise DesignError(message, code="stale", status=409)


def execute(actor, command, operation, payload, request=None):
    """Apply once, or return the original receipt for the same normalized input."""
    actor = _owner(actor)
    operation = _operation(operation)
    payload = _payload(command, payload)
    fingerprint = hashlib.sha256(json.dumps([command, payload], sort_keys=True, ensure_ascii=False,
                                           separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    with transaction.atomic():
        actor = _owner(actor, lock=True)
        if not flag_enabled(FLAG):
            raise DesignError("Dizayn boshqaruvi hozir o‘chirilgan. O‘zgarish saqlanmadi.", code="disabled", status=409)
        # Owner locking serializes the same actor's operation keys, including
        # first draft/preset creation. Global pointer locking handles other owners.
        receipt = DesignOperation.objects.filter(actor=actor, operation=operation).first()
        if receipt is not None:
            if receipt.fingerprint != fingerprint:
                raise DesignError("Bu amal belgisi boshqa so‘rov uchun ishlatilgan.", code="idempotency_conflict", status=409)
            return {"result": deepcopy(receipt.result), "state": _state(actor, operation=operation)}
        DesignState.objects.get_or_create(pk=1)
        state = DesignState.objects.select_for_update().get(pk=1)
        published = _published(state)
        version = published["version"]
        draft = DesignDraft.objects.select_for_update().filter(owner=actor).first()
        result = {"operation": operation, "command": command, "kind": "noop", "version": version, "changed": False}
        if "base_version" in payload and payload["base_version"] != version:
            _stale()
        if command == "save_draft":
            if payload["draft_revision"] != (draft.revision if draft else 0):
                _stale("Qoralama boshqa oynada yangilangan. O‘zingizdagi o‘zgarishni saqlab, holatni qayta o‘qing.")
            if draft is None or draft.value != payload["value"] or draft.base_version != version:
                previous = draft.revision if draft else 0
                if draft is None:
                    draft = DesignDraft(owner=actor)
                draft.value, draft.base_version, draft.revision = payload["value"], version, previous + 1
                draft.save()
                _audit(actor, request, operation, command, draft, {"revision": previous},
                       {"revision": draft.revision, "base_version": version}, "Dizayn qoralamasi saqlandi.")
                result.update(kind="saved", changed=True)
            result["draft_revision"] = draft.revision
        elif command in {"publish", "rollback"}:
            target = None
            if command == "publish":
                if draft is None:
                    raise DesignError("Avval qoralamani saqlang, keyin tatbiq qiling.", code="draft_required", status=409)
                if draft.revision != payload["draft_revision"] or draft.base_version != version:
                    _stale("Qoralama yoki joriy ko‘rinish o‘zgargan. Farqni ko‘rib, qoralamani qayta saqlang.")
                value = _snapshot(draft.value)
            else:
                target = DesignVersion.objects.filter(number=payload["target_version"]).first()
                if target is None and payload["target_version"] != 0:
                    raise DesignError("Tarixdagi ko‘rinish topilmadi.", code="not_found", status=404)
                value = _snapshot(target.value if target is not None else defaults())
            if value != published["value"]:
                # Freeze the initial default on first publication. Future factory
                # defaults can never rewrite the rollback target of this history.
                if state.current_version_id is None:
                    baseline = DesignVersion.objects.create(number=0, value=published["value"], kind="factory", reason="Asl Azure")
                    if command == "rollback" and payload["target_version"] == 0:
                        target = baseline
                new_version = DesignVersion.objects.create(
                    number=version + 1, value=value, kind=command, reason=payload["reason"],
                    actor=actor, actor_label=actor.username, source_version=target)
                state.current_version = new_version
                state.save(update_fields=["current_version"])
                _audit(actor, request, operation, command, new_version, {"version": version},
                       {"version": new_version.number, "source_version": target.number if target else None}, payload["reason"])
                result.update(kind="published" if command == "publish" else "rolled_back",
                              version=new_version.number, changed=True)
        elif command == "save_preset":
            name_key = payload["name"].casefold()
            preset = DesignPreset.objects.filter(owner=actor, name_key=name_key, deleted_at__isnull=True).first()
            if preset is not None and preset.value != payload["value"]:
                raise DesignError("Bu nomli variant bor. Boshqa nom yozing.", code="name_conflict", status=409)
            if preset is None:
                preset = DesignPreset.objects.create(owner=actor, name=payload["name"], name_key=name_key, value=payload["value"])
                _audit(actor, request, operation, command, preset, {}, {"name": preset.name}, "Dizayn varianti saqlandi.")
                result.update(kind="preset_saved", changed=True)
            result["preset_id"] = preset.pk
        else:
            preset = DesignPreset.objects.filter(owner=actor, pk=payload["preset_id"]).first()
            if preset is None:
                raise DesignError("Variant topilmadi.", code="not_found", status=404)
            if preset.deleted_at is None:
                preset.deleted_at = timezone.now()
                preset.save(update_fields=["deleted_at"])
                _audit(actor, request, operation, command, preset, {"name": preset.name}, {"deleted": True}, "Dizayn varianti o‘chirildi.")
                result.update(kind="preset_deleted", changed=True)
            result["preset_id"] = preset.pk
        DesignOperation.objects.create(actor=actor, actor_label=actor.username, operation=operation,
                                       fingerprint=fingerprint, command=command, result=result)
        return {"result": result, "state": _state(actor, operation=operation)}
