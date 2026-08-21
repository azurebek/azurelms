"""Read-only operational snapshot shared by web and CLI adapters."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Mapping

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Max, Min
from django.utils import timezone

from .registry import CAPABILITY_REGISTRY, CapabilityDefinition


STATUS_ORDER = {"green": 0, "amber": 1, "red": 2}


@dataclass(frozen=True)
class CapabilityResult:
    definition: CapabilityDefinition
    status: str
    summary: str
    details: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict:
        return {
            "slug": self.definition.slug,
            "label": self.definition.label,
            "category": self.definition.category,
            "criticality": self.definition.criticality,
            "owner": self.definition.owner,
            "description": self.definition.description,
            "dependencies": list(self.definition.dependencies),
            "runbook": self.definition.runbook,
            "status": self.status,
            "summary": self.summary,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ControlCenterSnapshot:
    generated_at: datetime
    environment: str
    release_sha: str
    overall_status: str
    results: tuple[CapabilityResult, ...]
    effective_config: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def counts(self) -> dict[str, int]:
        counts = {"green": 0, "amber": 0, "red": 0}
        for result in self.results:
            counts[result.status] += 1
        counts["total"] = len(self.results)
        return counts

    @property
    def attention_results(self) -> tuple[CapabilityResult, ...]:
        return tuple(result for result in self.results if result.status != "green")

    def as_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "environment": self.environment,
            "release_sha": self.release_sha,
            "overall_status": self.overall_status,
            "counts": self.counts,
            "effective_config": dict(self.effective_config),
            "capabilities": [result.as_dict() for result in self.results],
        }


def _result(
    definition: CapabilityDefinition,
    status: str,
    summary: str,
    **details,
) -> CapabilityResult:
    normalized = tuple((str(key), str(value)) for key, value in details.items())
    return CapabilityResult(definition=definition, status=status, summary=summary, details=normalized)


def _backend_name(config: dict) -> str:
    return str(config.get("BACKEND", "unknown")).rsplit(".", 1)[-1]


def _release_sha() -> str:
    for name in ("SOURCE_VERSION", "COMMIT_SHA", "GITHUB_SHA"):
        value = os.getenv(name, "").strip()
        if value:
            return value[:12]
    return "unknown"


def _database_probe(definition: CapabilityDefinition) -> CapabilityResult:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return _result(
        definition,
        "green",
        "Database query muvaffaqiyatli.",
        engine=connection.vendor,
        alias=connection.alias,
    )


def _cache_probe(definition: CapabilityDefinition) -> CapabilityResult:
    config = settings.CACHES.get("default", {})
    backend = _backend_name(config)
    cache.get("azurelms:control-center:read-only-probe")
    local_only = "LocMem" in backend
    if local_only and not settings.IS_LOCAL:
        return _result(definition, "red", "Production shared cache ishlatmayapti.", backend=backend)
    return _result(
        definition,
        "green",
        "Local cache faol." if local_only else "Shared cache probe muvaffaqiyatli.",
        backend=backend,
    )


def _realtime_probe(definition: CapabilityDefinition) -> CapabilityResult:
    config = settings.CHANNEL_LAYERS.get("default", {})
    backend = _backend_name(config)
    in_memory = "InMemory" in backend
    if in_memory and not settings.IS_LOCAL:
        return _result(definition, "red", "Production realtime state processlar orasida bo'lishilmaydi.", backend=backend)
    return _result(
        definition,
        "green" if in_memory else "amber",
        "Local in-memory Channels faol." if in_memory else "Shared backend sozlangan; live heartbeat hali yo'q.",
        backend=backend,
    )


def _jobs_probe(definition: CapabilityDefinition) -> CapabilityResult:
    from core.celery import app as celery_app

    broker = str(celery_app.conf.broker_url or "")
    broker_kind = broker.split(":", 1)[0] or "unset"
    eager = bool(celery_app.conf.task_always_eager)
    memory_broker = broker.startswith("memory://")
    if memory_broker and not settings.IS_LOCAL:
        return _result(
            definition,
            "red",
            "Production job broker xotirada; joblar process restartda yo'qoladi.",
            broker=broker_kind,
            eager=eager,
        )
    if settings.IS_LOCAL and memory_broker and eager:
        return _result(definition, "green", "Local eager job rejimi faol.", broker=broker_kind, eager=eager)
    return _result(
        definition,
        "amber",
        "Broker sozlangan; worker/beat heartbeat hali o'lchanmaydi.",
        broker=broker_kind,
        eager=eager,
    )


#: Control Center kutadigan workerlar. Bugun bitta — Telegram outbox.
EXPECTED_WORKERS = ("telegram-outbox",)


def _workers_probe(definition: CapabilityDefinition) -> CapabilityResult:
    """Worker tirikligini navbatdan emas, o'z belgisidan o'qiydi.

    Outbox probe'i sog'liqni navbat yoshidan chiqaradi, ya'ni navbat bo'sh
    bo'lsa o'lik worker ham yashil ko'rinadi. Bu yerda esa jarayonning o'zi
    yozib qoldirgan `WorkerHeartbeat` o'qiladi.
    """
    from aicontrol.models import WorkerHeartbeat

    beats = {beat.name: beat for beat in WorkerHeartbeat.objects.all()}
    missing, stale, alive = [], [], []
    for name in EXPECTED_WORKERS:
        beat = beats.get(name)
        if beat is None:
            missing.append(name)
        elif beat.is_dead():
            stale.append(name)
        elif not beat.is_alive():
            stale.append(name)
        else:
            alive.append(name)

    if stale:
        status = "red"
        summary = f"Worker javob bermayapti: {', '.join(stale)}."
    elif missing:
        # Lokalda bot odatda ishlamaydi — bu nosozlik emas, sozlanmagan holat.
        status = "amber" if settings.IS_LOCAL else "red"
        summary = f"Worker hech qachon belgi qoldirmagan: {', '.join(missing)}."
    else:
        status = "green"
        summary = "Barcha kutilgan workerlar tirik."

    return _result(
        definition,
        status,
        summary,
        expected=len(EXPECTED_WORKERS),
        alive=len(alive),
        stale=len(stale),
        never_seen=len(missing),
    )


def _telegram_probe(definition: CapabilityDefinition) -> CapabilityResult:
    from bot.models import TelegramOutbox

    # Navbat = hali olinmagan (`pending`) + workerga berilgan (`sending`).
    # `sending` ni hisobdan chiqarish ko'r nuqta yaratardi: worker o'lib qolsa
    # qator lease tugagunicha ko'rinmay, navbat sog'lom bo'lib turardi (A1a).
    queued = TelegramOutbox.objects.filter(
        status__in=(TelegramOutbox.STATUS_PENDING, TelegramOutbox.STATUS_SENDING)
    )
    failed_count = TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_FAILED).count()
    in_flight_count = TelegramOutbox.objects.filter(
        status=TelegramOutbox.STATUS_SENDING
    ).count()
    pending_count = queued.count()
    oldest_pending = queued.aggregate(oldest=Min("created_at"))["oldest"]
    last_sent = TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_SENT).aggregate(last=Max("sent_at"))["last"]
    token = str(getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "")
    configured = bool(token and token != "YOUR_BOT_TOKEN_HERE")
    oldest_minutes = 0
    if oldest_pending:
        oldest_minutes = max(0, int((timezone.now() - oldest_pending).total_seconds() // 60))

    status = "green"
    summary = "Outbox navbati sog'lom."
    if not configured:
        status = "amber" if settings.IS_LOCAL else "red"
        summary = "Telegram token sozlanmagan."
    elif pending_count and oldest_minutes >= 60:
        status = "red"
        summary = "Outbox navbatidagi xabar bir soatdan oshgan."
    elif failed_count or (pending_count and oldest_minutes >= 15):
        status = "amber"
        summary = "Outbox operator e'tiborini talab qiladi."

    return _result(
        definition,
        status,
        summary,
        mode=getattr(settings, "TELEGRAM_MODE", "unknown"),
        pending=pending_count,
        in_flight=in_flight_count,
        oldest_pending_minutes=oldest_minutes,
        failed=failed_count,
        last_sent=timezone.localtime(last_sent).isoformat(timespec="minutes") if last_sent else "never",
    )


def _media_probe(definition: CapabilityDefinition) -> CapabilityResult:
    use_s3 = bool(getattr(settings, "USE_S3", False))
    if use_s3 and getattr(settings, "AWS_DEFAULT_ACL", None) == "public-read":
        return _result(
            definition,
            "red",
            "Remote media public-read; private learner fayllari uchun xavfli.",
            backend="S3/Spaces",
            access="public-read",
        )
    if not use_s3 and not settings.IS_LOCAL:
        return _result(
            definition,
            "red",
            "Production media ephemeral local filesystemda.",
            backend="FileSystemStorage",
        )
    return _result(
        definition,
        "green",
        "Local filesystem development rejimida." if not use_s3 else "Remote private storage sozlangan.",
        backend="FileSystemStorage" if not use_s3 else "S3/Spaces",
    )


def _ai_probe(definition: CapabilityDefinition) -> CapabilityResult:
    from aicontrol.models import AISettings
    from aicontrol.supply import supply_snapshot

    provider = str(getattr(settings, "AI_CHAT_PROVIDER", "gemini") or "gemini").lower()
    free_tier_mode = bool(getattr(settings, "AI_FREE_TIER_MODE", False))
    grounding_enabled = (
        not free_tier_mode
        and bool(getattr(settings, "GEMINI_GROUNDING_ENABLED", False))
    )
    digitalocean_allowed = bool(getattr(settings, "AI_ALLOW_DIGITALOCEAN", False))
    supply = supply_snapshot()
    key_name = {
        "gemini": "GEMINI_API_KEY",
        "digitalocean": "DIGITALOCEAN_INFERENCE_API_KEY",
    }.get(provider)
    configured = bool(key_name and getattr(settings, key_name, None))
    policy = AISettings.objects.first() or AISettings()
    candidate_statuses = []
    issues = []

    if not key_name:
        candidate_statuses.append("red")
        issues.append("Noma'lum AI provider tanlangan.")
    elif provider == "digitalocean" and not digitalocean_allowed:
        candidate_statuses.append("red")
        issues.append("DigitalOcean provider owner HOLD holatida.")

    if configured:
        candidate_statuses.append("green")
    else:
        credential_status = "amber" if settings.IS_LOCAL else "red"
        candidate_statuses.append(credential_status)
        issues.append("AI provider credential mavjud emas.")

    # Kill switch — ataylab qilingan operator harakati, nosozlik emas.
    # 05-launch-ops ta'rifi bo'yicha bu AMBER: oltin kurs oqimi ishlaydi,
    # degradatsiya esa aniq va boshqariladigan (A2).
    kill_switch_on = not policy.ai_remote_calls_enabled
    if kill_switch_on:
        candidate_statuses.append("amber")
        issues.append("AI owner tomonidan to'xtatilgan (kill switch).")

    supply_available = bool(supply.get("available", False))
    supply_status = str(supply.get("status", "red"))
    if supply_status not in STATUS_ORDER:
        supply_status = "red"
    candidate_statuses.append(supply_status)
    if not supply_available:
        issues.append("Global AI supply snapshot mavjud emas.")
    elif bool(supply.get("circuit_open")):
        issues.append("Global AI provider circuit cooldown holatida.")
    elif supply_status == "red":
        issues.append("Global AI supply request yoki token capiga yetgan.")
    elif not bool(supply.get("enforcement", True)):
        issues.append("Global AI supply enforcement o'chirilgan.")
    elif supply_status == "amber":
        issues.append("Global AI supply sarfi 80% chegaraga yetgan.")

    status = max(candidate_statuses, key=STATUS_ORDER.get, default="green")
    summary = (
        " ".join(issues)
        if issues
        else "AI credential va global supply budjeti sog'lom."
    )

    def supply_value(name, default="unavailable"):
        return supply.get(name, default) if supply_available else default

    return _result(
        definition,
        status,
        summary,
        provider=provider,
        credential="configured" if configured else "missing",
        digitalocean_admission="allowed" if digitalocean_allowed else "hold",
        free_tier_mode="on" if free_tier_mode else "off",
        api_grounding="enabled" if grounding_enabled else "disabled",
        user_enforcement="on" if policy.enforcement_enabled else "off",
        supply_enforcement=(
            "on" if supply_available and supply.get("enforcement") else "off"
            if supply_available
            else "unavailable"
        ),
        supply_bucket=supply_value("bucket_date"),
        remote_calls_enabled=policy.ai_remote_calls_enabled,
        requests_used=supply_value("requests_used"),
        requests_limit=supply_value("requests_limit"),
        requests_remaining=supply_value("requests_remaining"),
        minute_requests_used=supply_value("minute_requests_used"),
        minute_requests_limit=supply_value("minute_requests_limit"),
        minute_requests_remaining=supply_value("minute_requests_remaining"),
        tokens_used=supply_value("tokens_used"),
        tokens_limit=supply_value("tokens_limit"),
        tokens_remaining=supply_value("tokens_remaining"),
        actual_attempts=supply_value("actual_attempts"),
        reserved=supply_value("reserved"),
        failed=supply_value("failed"),
        rejected=supply_value("rejected"),
        circuit=(
            "open" if supply_available and supply.get("circuit_open") else "closed"
            if supply_available
            else "unavailable"
        ),
        cooldown_until=supply_value("circuit_open_until", "inactive") or "inactive",
        default_5h_tokens=policy.default_5h_token_limit,
        default_weekly_tokens=policy.default_weekly_token_limit,
    )


def _rag_probe(definition: CapabilityDefinition) -> CapabilityResult:
    from messenger.rag import get_rag_index_status

    index = get_rag_index_status()
    eligible = index["eligible_lessons"]
    ready_percent = index["ready_percent"]
    if eligible == 0:
        status = "green"
        summary = "Index talab qiladigan dars kontenti yo'q."
    elif ready_percent == 100:
        status = "green"
        summary = "Barcha eligible darslar indekslangan."
    else:
        status = "amber"
        summary = "RAG index to'liq yoki fresh emas."
    return _result(
        definition,
        status,
        summary,
        ready=f"{index['ready_lessons']}/{eligible}",
        ready_percent=f"{ready_percent}%",
        missing=index["missing_lessons"],
        stale=index["stale_lessons"],
        chunks=index["total_chunks"],
        pgvector="ready" if index["pgvector_ready"] else "fallback",
    )


def _security_probe(definition: CapabilityDefinition) -> CapabilityResult:
    strict = bool(getattr(settings, "SECURITY_STRICT", False))
    debug = bool(settings.DEBUG)
    if not settings.IS_LOCAL and (debug or not strict):
        return _result(
            definition,
            "red",
            "Production security baseline bajarilmagan.",
            security_strict=strict,
            debug=debug,
        )
    return _result(
        definition,
        "green",
        "Local development security profili." if settings.IS_LOCAL else "Strict production security profili faol.",
        security_strict=strict,
        debug=debug,
    )


def _release_probe(definition: CapabilityDefinition) -> CapabilityResult:
    from aicontrol.models import ReleaseRecord
    from core.release_service import migration_state

    sha = _release_sha()
    applied, unapplied = migration_state()
    # O'qish: eng so'nggi yozilgan release va owner qarori. Probe yozmaydi.
    latest = ReleaseRecord.objects.order_by("-last_seen_at").first()
    decision = latest.get_decision_display() if latest else "yozilmagan"

    # Eng jiddiy holat: kod yangi, baza eski. Bu shu loyihada bir marta
    # sodir bo'ldi va sahifa `OperationalError` bilan yiqildi, ammo Control
    # Center hamma narsani yashil deb turdi.
    if unapplied:
        return _result(
            definition,
            "red",
            f"{len(unapplied)} ta migratsiya qo'llanmagan — kod va baza mos emas.",
            source_sha=sha,
            applied=applied,
            pending=", ".join(unapplied[:3]) + ("..." if len(unapplied) > 3 else ""),
        )

    if sha == "unknown" and not settings.IS_LOCAL:
        return _result(
            definition,
            "amber",
            "Running release SHA aniqlanmadi.",
            source_sha=sha,
            applied=applied,
        )

    return _result(
        definition,
        "green",
        "Local source tree." if sha == "unknown" else "Running release identity mavjud.",
        source_sha=sha,
        applied=applied,
    )


#: Zaxira shu muddatdan eski bo'lsa AMBER. Tanlov: bir hafta ichida bo'lgan
#: yo'qotish qabul qilinadigan darajada, undan eskisi esa tiklashda sezilarli
#: ma'lumot yo'qotishni anglatadi.
BACKUP_STALE_AFTER_DAYS = 7

#: Embedding'siz faktlar ulushi shundan oshsa AMBER. Bunday fakt bazada bor,
#: ammo semantik qidiruvda **ko'rinmaydi** — jim degradatsiya.
MEMORY_UNEMBEDDED_AMBER_SHARE = 0.25


def _backup_probe(definition: CapabilityDefinition) -> CapabilityResult:
    """So'nggi zaxiraning yoshi. Zaxira **olmaydi** — faqat qaraydi."""
    root = Path(settings.BASE_DIR) / "backups"
    files = sorted(root.glob("*.sqlite3"), key=lambda item: item.stat().st_mtime, reverse=True) if root.exists() else []

    if not files:
        # Local'da ham yashil emas: "zaxira yo'q" holati aynan e'tibordan
        # chetda qoladigan va kerak bo'lganda kech bilinadigan narsa.
        return _result(
            definition,
            "red" if not settings.IS_LOCAL else "amber",
            "Zaxira topilmadi.",
            directory=str(root),
        )

    newest = files[0]
    age_days = (timezone.now().timestamp() - newest.stat().st_mtime) / 86400
    size_mb = newest.stat().st_size / (1024 * 1024)
    if age_days > BACKUP_STALE_AFTER_DAYS:
        return _result(
            definition,
            "amber",
            f"So'nggi zaxira {age_days:.0f} kunlik.",
            newest=newest.name,
            age_days=f"{age_days:.1f}",
            size_mb=f"{size_mb:.1f}",
        )
    return _result(
        definition,
        "green",
        f"So'nggi zaxira {age_days:.1f} kunlik.",
        newest=newest.name,
        age_days=f"{age_days:.1f}",
        size_mb=f"{size_mb:.1f}",
        count=len(files),
    )


def _email_probe(definition: CapabilityDefinition) -> CapabilityResult:
    """Backend sozlanganmi. Xat **yubormaydi** — probe yon ta'sir qoldirmaydi."""
    path = str(getattr(settings, "EMAIL_BACKEND", ""))
    # Klass nomi hamma backendda `EmailBackend` — farq **modul** qismida
    # (`...backends.console.EmailBackend`), shuning uchun o'sha bo'lak olinadi.
    parts = path.split(".")
    backend = parts[-2] if len(parts) >= 2 else path
    silent = backend in {"console", "dummy", "locmem"}

    if silent:
        if settings.IS_LOCAL:
            return _result(definition, "green", "Local: xatlar konsolga yoziladi.", backend=backend)
        # Production'da bu jim yo'qotish: parol tiklash va bildirishnoma
        # yuborilgandek ko'rinadi, ammo hech kimga yetib bormaydi.
        return _result(definition, "red", "Xatlar hech kimga yuborilmayapti.", backend=backend)

    host = str(getattr(settings, "EMAIL_HOST", "") or "")
    if not host or host == "localhost":
        return _result(definition, "amber", "SMTP host sozlanmagan.", backend=backend, host=host or "-")
    return _result(
        definition, "green", "SMTP backend sozlangan.",
        backend=backend, host=host, tls=str(getattr(settings, "EMAIL_USE_TLS", False)),
    )


def _memory_probe(definition: CapabilityDefinition) -> CapabilityResult:
    """Faol xotira faktlari va ularning embedding qamrovi."""
    from messenger.models import AIMemoryFact

    active = AIMemoryFact.objects.filter(status=AIMemoryFact.STATUS_ACTIVE)
    total = active.count()
    if not total:
        return _result(definition, "green", "Faol xotira fakti yo'q.", active="0")

    # `embedding` — `JSONField(default=list)`, ya'ni NOT NULL: "yo'q" holati
    # bo'sh ro'yxat. JSON bo'shligini so'rash backendga bog'liq, `embedding_dim`
    # esa integer va SQLite/PostgreSQL da bir xil ishlaydi.
    unembedded = active.filter(embedding_dim=0).count()
    share = unembedded / total
    if share >= MEMORY_UNEMBEDDED_AMBER_SHARE:
        return _result(
            definition,
            "amber",
            f"{unembedded}/{total} fakt embedding'siz.",
            active=str(total),
            unembedded=str(unembedded),
        )
    return _result(
        definition, "green", f"{total} faol fakt, embedding qamrovi to'liq.",
        active=str(total), unembedded=str(unembedded),
    )


PROBE_FUNCTIONS: dict[str, Callable[[CapabilityDefinition], CapabilityResult]] = {
    "database": _database_probe,
    "cache": _cache_probe,
    "realtime": _realtime_probe,
    "jobs": _jobs_probe,
    "telegram_outbox": _telegram_probe,
    "workers": _workers_probe,
    "media_storage": _media_probe,
    "ai_provider": _ai_probe,
    "rag": _rag_probe,
    "security": _security_probe,
    "backup": _backup_probe,
    "email": _email_probe,
    "memory": _memory_probe,
    "release": _release_probe,
}


def _effective_config(release_sha: str) -> tuple[tuple[str, str], ...]:
    cache_backend = _backend_name(settings.CACHES.get("default", {}))
    channel_backend = _backend_name(settings.CHANNEL_LAYERS.get("default", {}))
    return (
        ("Environment", str(settings.APP_ENV)),
        ("Release", release_sha),
        ("AI provider", str(getattr(settings, "AI_CHAT_PROVIDER", "gemini"))),
        ("Telegram mode", str(getattr(settings, "TELEGRAM_MODE", "unknown"))),
        ("Cache", cache_backend),
        ("Channels", channel_backend),
        ("Media", "S3/Spaces" if getattr(settings, "USE_S3", False) else "Local filesystem"),
        ("Security strict", "on" if getattr(settings, "SECURITY_STRICT", False) else "off"),
    )


def build_control_center_snapshot(
    *,
    probe_functions: Mapping[str, Callable[[CapabilityDefinition], CapabilityResult]] | None = None,
) -> ControlCenterSnapshot:
    """Build one safe snapshot; a broken probe never hides other capabilities."""

    probes = dict(PROBE_FUNCTIONS)
    if probe_functions:
        probes.update(probe_functions)

    results = []
    for definition in CAPABILITY_REGISTRY:
        try:
            result = probes[definition.slug](definition)
            if result.status not in STATUS_ORDER:
                raise ValueError(f"Invalid status: {result.status}")
        except Exception as exc:  # A health page must survive partial infrastructure failure.
            result = _result(
                definition,
                "red",
                "Probe xavfsiz tarzda xatoga tushdi.",
                error_type=type(exc).__name__,
            )
        results.append(result)

    overall = max((item.status for item in results), key=STATUS_ORDER.get, default="green")
    release_sha = _release_sha()
    return ControlCenterSnapshot(
        generated_at=timezone.now(),
        environment=str(settings.APP_ENV),
        release_sha=release_sha,
        overall_status=overall,
        results=tuple(results),
        effective_config=_effective_config(release_sha),
    )
