"""Project-wide AI supply budget, idempotency ledger, and circuit breaker.

User token allowances answer "who may use AI".  This module answers the
separate question "may this project spend another remote-provider request".
Every admitted logical call is reserved before network I/O and reconciled
afterwards.  Database failures are fail-closed so a broken ledger cannot turn
into an unbounded Gemini bill/quota fan-out.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import AISettings, AISupplyEvent, AISupplyState


class SupplyError(RuntimeError):
    """Base class for a call stopped before remote-provider execution."""

    code = "supply_error"

    def __init__(self, message: str, *, event: AISupplyEvent | None = None):
        super().__init__(message)
        self.event = event


class SupplyDenied(SupplyError):
    code = "supply_denied"


class SupplyDuplicate(SupplyError):
    code = "duplicate"


class SupplyUnavailable(SupplyError):
    code = "ledger_unavailable"


@dataclass(frozen=True)
class SupplyReservation:
    event_id: int
    request_key: str
    reserved_requests: int
    reserved_tokens: int


def normalize_request_key(value: str | None, *, prefix: str = "ai") -> str:
    """Return a bounded unique key without leaking full prompt/user content."""
    raw = str(value or "").strip() or f"{prefix}:{uuid.uuid4().hex}"
    if len(raw) <= 180:
        return raw
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{raw[:110]}:{digest}"


def fingerprint_request(prefix: str, *parts: Any, daily: bool = False) -> str:
    payload = "\x1f".join(str(part or "") for part in parts)
    if daily:
        payload = f"{timezone.localdate().isoformat()}\x1f{payload}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return normalize_request_key(f"{prefix}:{digest}")


def estimate_tokens(prompt: str | None, *, max_output_tokens: int = 0) -> int:
    """Conservative pre-call estimate when provider usage is not available yet."""
    prompt_estimate = math.ceil(len(str(prompt or "")) / 4)
    return max(1, prompt_estimate + max(0, int(max_output_tokens or 0)))


def classify_supply_error(error: BaseException | str | None) -> str:
    text = str(error or "").lower()
    if any(
        marker in text
        for marker in (
            "resource_exhausted",
            "rate limit",
            "rate_limit",
            "ratelimit",
            "quota",
            "billing",
            "prepayment credits",
            "status 429",
            "status_code=429",
            "code=429",
        )
    ):
        return "quota"
    if "timeout" in text or "deadline" in text:
        return "timeout"
    return "provider_error"


def _provider_attempt_count(provider, *, default: int = 1) -> int:
    value = getattr(provider, "last_attempt_count", None)
    if value is None:
        return default
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _provider_error_kind(provider, error=None) -> str:
    value = getattr(provider, "last_error_kind", "")
    if isinstance(value, str) and value:
        return value[:40]
    return classify_supply_error(error) if error else ""


def reserve_supply(
    *,
    request_key: str,
    call_type: str,
    provider: str = "gemini",
    model_name: str = "",
    user=None,
    reserved_requests: int = 1,
    reserved_tokens: int | None = None,
    metadata: dict | None = None,
) -> SupplyReservation:
    """Atomically reserve daily project capacity before any network request."""
    key = normalize_request_key(request_key)
    request_count = max(1, min(int(reserved_requests or 1), 2))
    denied_reason = ""
    event = None
    try:
        # Ensure singleton rows exist before locking them.  Their unique singleton
        # keys make a concurrent creator safe; the outer IntegrityError path then
        # resolves a duplicate request without performing network I/O.
        AISettings.load()
        AISupplyState.load()
        with transaction.atomic():
            policy = AISettings.objects.select_for_update().get(singleton=True)
            state = AISupplyState.objects.select_for_update().get(singleton=True)
            existing = AISupplyEvent.objects.filter(request_key=key).first()
            if existing is not None:
                raise SupplyDuplicate("Bu AI request avval ledgerga yozilgan.", event=existing)

            now = timezone.now()
            if state.circuit_open_until and state.circuit_open_until <= now:
                state.circuit_open_until = None
                state.circuit_reason = ""
                state.opened_at = None
                state.save(
                    update_fields=["circuit_open_until", "circuit_reason", "opened_at", "updated_at"]
                )

            token_reservation = int(
                reserved_tokens
                if reserved_tokens is not None
                else policy.supply_default_reservation_tokens
            )
            token_reservation = max(1, token_reservation)
            bucket = timezone.localdate()
            user_value = user if getattr(user, "pk", None) else None

            if policy.supply_enforcement_enabled and state.circuit_open_until:
                denied_reason = "circuit_open"
            elif policy.supply_enforcement_enabled:
                totals = AISupplyEvent.objects.filter(bucket_date=bucket).aggregate(
                    requests=Sum("accounted_requests"),
                    tokens=Sum("accounted_tokens"),
                )
                minute_requests = int(
                    AISupplyEvent.objects.filter(
                        reserved_at__gte=now - timedelta(minutes=1),
                    ).aggregate(total=Sum("accounted_requests"))["total"]
                    or 0
                )
                used_requests = int(totals["requests"] or 0)
                used_tokens = int(totals["tokens"] or 0)
                if minute_requests + request_count > policy.supply_minute_request_limit:
                    denied_reason = "minute_request_limit"
                elif used_requests + request_count > policy.supply_daily_request_limit:
                    denied_reason = "daily_request_limit"
                elif used_tokens + token_reservation > policy.supply_daily_token_limit:
                    denied_reason = "daily_token_limit"

            rejected = bool(denied_reason)
            event = AISupplyEvent.objects.create(
                request_key=key,
                bucket_date=bucket,
                call_type=call_type,
                provider=provider,
                model_name=model_name,
                user=user_value,
                status=(
                    AISupplyEvent.STATUS_REJECTED
                    if rejected
                    else AISupplyEvent.STATUS_RESERVED
                ),
                reserved_requests=request_count,
                reserved_tokens=token_reservation,
                accounted_requests=0 if rejected else request_count,
                accounted_tokens=0 if rejected else token_reservation,
                error_kind=denied_reason,
                error_message=(
                    "Global AI supply policy remote callni providerdan oldin to'xtatdi."
                    if rejected
                    else ""
                ),
                metadata=metadata or {},
                completed_at=now if rejected else None,
            )
    except SupplyDuplicate:
        raise
    except IntegrityError as exc:
        # The most likely integrity race is another worker reserving the same
        # idempotency key.  It is still a hard no-call decision.
        try:
            existing = AISupplyEvent.objects.filter(request_key=key).first()
        except DatabaseError:
            existing = None
        if existing is not None:
            raise SupplyDuplicate("Bu AI request parallel workerda avval yozilgan.", event=existing) from exc
        raise SupplyUnavailable("AI supply ledger yozuvi yaratilmadi; call xavfsiz to'xtatildi.") from exc
    except DatabaseError as exc:
        raise SupplyUnavailable("AI supply ledger mavjud emas; call xavfsiz to'xtatildi.") from exc

    if denied_reason:
        messages = {
            "circuit_open": "AI provider quota cooldown holatida.",
            "minute_request_limit": "Global AI bir daqiqalik request budjeti tugadi.",
            "daily_request_limit": "Bugungi global AI request budjeti tugadi.",
            "daily_token_limit": "Bugungi global AI token budjeti tugadi.",
        }
        raise SupplyDenied(messages.get(denied_reason, "Global AI supply budjeti callni to'xtatdi."), event=event)

    return SupplyReservation(
        event_id=event.pk,
        request_key=key,
        reserved_requests=event.reserved_requests,
        reserved_tokens=event.reserved_tokens,
    )


def reconcile_supply(
    reservation: SupplyReservation,
    *,
    succeeded: bool,
    actual_requests: int | None = None,
    usage: dict | None = None,
    model_name: str = "",
    error: BaseException | str | None = None,
    error_kind: str = "",
) -> AISupplyEvent:
    """Replace a conservative reservation with observed provider usage."""
    try:
        with transaction.atomic():
            event = AISupplyEvent.objects.select_for_update().get(pk=reservation.event_id)
            attempts = (
                max(0, int(actual_requests))
                if actual_requests is not None
                else event.reserved_requests
            )
            usage = usage or {}
            prompt_tokens = max(0, int(usage.get("prompt_tokens", 0) or 0))
            completion_tokens = max(0, int(usage.get("completion_tokens", 0) or 0))
            total_tokens = max(
                0,
                int(usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)),
            )
            kind = error_kind or (classify_supply_error(error) if error else "")

            event.status = (
                AISupplyEvent.STATUS_SUCCEEDED if succeeded else AISupplyEvent.STATUS_FAILED
            )
            event.actual_requests = attempts
            event.prompt_tokens = prompt_tokens
            event.completion_tokens = completion_tokens
            event.total_tokens = total_tokens
            event.accounted_requests = attempts
            event.accounted_tokens = (
                total_tokens
                if total_tokens
                else (event.reserved_tokens if attempts > 0 else 0)
            )
            event.model_name = model_name or event.model_name
            event.error_kind = kind
            # Raw SDK errors can contain request URLs or provider details. The
            # operational ledger stores only a bounded taxonomy, never secrets,
            # prompts, or full remote error payloads.
            event.error_message = f"Remote AI call failed: {kind}" if error else ""
            event.completed_at = timezone.now()
            event.save()

            policy = AISettings.objects.select_for_update().get(singleton=True)
            bucket_totals = AISupplyEvent.objects.filter(
                bucket_date=event.bucket_date
            ).aggregate(
                requests=Sum("accounted_requests"),
                tokens=Sum("accounted_tokens"),
            )
            project_overrun = (
                int(bucket_totals["requests"] or 0) > policy.supply_daily_request_limit
                or int(bucket_totals["tokens"] or 0) > policy.supply_daily_token_limit
            )
            reservation_overrun = (
                event.accounted_requests > event.reserved_requests
                or event.accounted_tokens > event.reserved_tokens
            )
            if kind == "quota" or project_overrun or reservation_overrun:
                state = AISupplyState.objects.select_for_update().get(singleton=True)
                opened_at = timezone.now()
                state.opened_at = opened_at
                if kind == "quota":
                    state.circuit_open_until = opened_at + timedelta(
                        seconds=max(1, int(policy.supply_cooldown_seconds or 1))
                    )
                    state.circuit_reason = "quota"
                else:
                    state.circuit_open_until = opened_at + timedelta(minutes=15)
                    state.circuit_reason = (
                        "project_cap_overrun" if project_overrun else "reservation_overrun"
                    )
                state.save()
            return event
    except DatabaseError as exc:
        raise SupplyUnavailable("AI supply reconciliation yozilmadi; ledger tekshirilsin.") from exc


def set_reservation_call_type(reservation: SupplyReservation, call_type: str) -> None:
    """Refine a pre-reserved main call once routing (chat vs grounding) is known."""
    try:
        updated = AISupplyEvent.objects.filter(
            pk=reservation.event_id,
            status=AISupplyEvent.STATUS_RESERVED,
        ).update(call_type=call_type)
    except DatabaseError as exc:
        raise SupplyUnavailable("AI supply route ledgerga yozilmadi.") from exc
    if updated != 1:
        raise SupplyUnavailable("AI supply reservation remote call oldidan yaroqsiz bo'ldi.")


def execute_provider_call(
    provider,
    *,
    request_key: str,
    call_type: str,
    prompt: str,
    user=None,
    max_requests: int = 2,
    reserved_tokens: int | None = None,
    metadata: dict | None = None,
    **provider_kwargs,
):
    """Reserve, execute exactly once, then reconcile a provider.generate call."""
    provider_name = provider.__class__.__name__.replace("Provider", "").lower() or "unknown"
    max_output = int(provider_kwargs.pop("_max_output_tokens", 0) or 0)
    reservation = reserve_supply(
        request_key=request_key,
        call_type=call_type,
        provider=provider_name,
        model_name=str(provider_kwargs.get("selected_model") or ""),
        user=user,
        reserved_requests=max_requests,
        reserved_tokens=(
            reserved_tokens
            if reserved_tokens is not None
            else (
                estimate_tokens(prompt, max_output_tokens=max_output)
                if max_output
                else None
            )
        ),
        metadata=metadata,
    )
    return execute_reserved_provider_call(
        reservation,
        provider,
        prompt=prompt,
        **provider_kwargs,
    )


def execute_reserved_provider_call(
    reservation: SupplyReservation,
    provider,
    *,
    prompt: str,
    **provider_kwargs,
):
    """Execute a call whose capacity was reserved by the outer task.

    Reserving the main reply before SmartForm/RAG/memory work prevents an
    auxiliary best-effort call from consuming the final daily slot and leaving
    the learner without the primary response.
    """
    try:
        # A reservation may have waited behind auxiliary work while another
        # request opened the global quota circuit. Re-check immediately before
        # network I/O so already-reserved work also fails closed.
        state = AISupplyState.load()
        if state.circuit_open_until and state.circuit_open_until > timezone.now():
            error = SupplyDenied("AI provider quota cooldown holatida.")
            reconcile_supply(
                reservation,
                succeeded=False,
                actual_requests=0,
                error=error,
                error_kind="circuit_open",
            )
            raise error
    except (SupplyDenied, SupplyUnavailable):
        raise
    except DatabaseError as exc:
        unavailable = SupplyUnavailable(
            "AI supply circuit holati o'qilmadi; call xavfsiz to'xtatildi."
        )
        try:
            reconcile_supply(
                reservation,
                succeeded=False,
                actual_requests=0,
                error=unavailable,
                error_kind="ledger_unavailable",
            )
        except SupplyUnavailable:
            pass
        raise unavailable from exc

    try:
        response = provider.generate(prompt=prompt, **provider_kwargs)
    except Exception as exc:
        attempts = _provider_attempt_count(provider)
        kind = _provider_error_kind(provider, exc)
        reconcile_supply(
            reservation,
            succeeded=False,
            actual_requests=attempts,
            error=exc,
            error_kind=kind,
        )
        raise

    attempts = _provider_attempt_count(provider)
    reconcile_supply(
        reservation,
        succeeded=True,
        actual_requests=attempts,
        usage=getattr(response, "usage", None),
        model_name=str(getattr(response, "model_name", "") or ""),
        error_kind=_provider_error_kind(provider),
    )
    return response


def supply_snapshot() -> dict:
    """Read-only daily budget/circuit summary for Control Center and tests."""
    try:
        policy = AISettings.load()
        state = AISupplyState.load()
        bucket = timezone.localdate()
        rows = AISupplyEvent.objects.filter(bucket_date=bucket)
        totals = rows.aggregate(
            requests=Sum("accounted_requests"),
            tokens=Sum("accounted_tokens"),
            actual_requests=Sum("actual_requests"),
        )
        requests = int(totals["requests"] or 0)
        tokens = int(totals["tokens"] or 0)
        now = timezone.now()
        minute_requests = int(
            AISupplyEvent.objects.filter(
                reserved_at__gte=now - timedelta(minutes=1),
            ).aggregate(total=Sum("accounted_requests"))["total"]
            or 0
        )
        circuit_open = bool(state.circuit_open_until and state.circuit_open_until > now)
        request_limit = int(policy.supply_daily_request_limit)
        token_limit = int(policy.supply_daily_token_limit)
        ratio = max(
            requests / request_limit if request_limit else 1,
            tokens / token_limit if token_limit else 1,
            minute_requests / int(policy.supply_minute_request_limit)
            if policy.supply_minute_request_limit
            else 1,
        )
        if (
            circuit_open
            or requests >= request_limit
            or tokens >= token_limit
            or minute_requests >= int(policy.supply_minute_request_limit)
        ):
            status = "red"
        elif not policy.supply_enforcement_enabled or ratio >= 0.8:
            status = "amber"
        else:
            status = "green"
        return {
            "status": status,
            "available": True,
            "enforcement": policy.supply_enforcement_enabled,
            "bucket_date": bucket.isoformat(),
            "requests_used": requests,
            "requests_limit": request_limit,
            "requests_remaining": max(request_limit - requests, 0),
            "minute_requests_used": minute_requests,
            "minute_requests_limit": int(policy.supply_minute_request_limit),
            "minute_requests_remaining": max(
                int(policy.supply_minute_request_limit) - minute_requests,
                0,
            ),
            "tokens_used": tokens,
            "tokens_limit": token_limit,
            "tokens_remaining": max(token_limit - tokens, 0),
            "actual_attempts": int(totals["actual_requests"] or 0),
            "reserved": rows.filter(status=AISupplyEvent.STATUS_RESERVED).count(),
            "failed": rows.filter(status=AISupplyEvent.STATUS_FAILED).count(),
            "rejected": rows.filter(status=AISupplyEvent.STATUS_REJECTED).count(),
            "circuit_open": circuit_open,
            "circuit_reason": state.circuit_reason if circuit_open else "",
            "circuit_open_until": (
                state.circuit_open_until.isoformat() if circuit_open else ""
            ),
        }
    except DatabaseError as exc:
        return {
            "status": "red",
            "available": False,
            "enforcement": True,
            "error_type": type(exc).__name__,
        }
