"""Release holati: qaysi kod ishlayapti va bazasi unga mos keladimi (A2).

Bo'linish ataylab:

* `migration_state()` — **faqat o'qish**. Control Center probe'i shuni
  ishlatadi, ya'ni snapshot ko'rish hech narsa yozmaydi.
* `record_current_release()` — aniq buyruq bilan chaqiriladi (deploy bosqichi).
* `decide_release()` — owner qarori, audit ledgeriga tushadi.

Nega migratsiya holati eng muhim qismi: shu sessiyaning o'zida kill switch
sahifasi `OperationalError` bilan yiqildi, chunki beshta migratsiya haqiqiy
bazaga qo'llanmagan edi. Kod yangi, baza eski — va Control Center o'nta
capability'ni yashil deb turardi.
"""

from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from aicontrol.models import ReleaseRecord


class ReleaseNotRecorded(Exception):
    """Bu SHA hali yozilmagan — qaror qabul qilishga narsa yo'q."""


def migration_state(*, alias="default"):
    """`(qo'llangan_soni, ["app.nom", ...])` — hech narsa yozmaydi."""
    connection = connections[alias]
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)

    unapplied = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]
    return len(executor.loader.applied_migrations), unapplied


def record_current_release(*, commit_sha, gate_results=None, now=None):
    """Ishlab turgan release'ni yozadi (deploy bosqichida chaqiriladi)."""
    applied, unapplied = migration_state()
    defaults = {
        "last_seen_at": now or timezone.now(),
        "migrations_applied": applied,
        "unapplied_migrations": unapplied,
    }
    if gate_results is not None:
        defaults["gate_results"] = gate_results

    record, _created = ReleaseRecord.objects.update_or_create(
        commit_sha=commit_sha,
        defaults=defaults,
    )
    return record


def decide_release(*, commit_sha, decision, actor, note="", request=None):
    """Owner qarorini yozadi. Qaror o'zgarmasa hech narsa yozilmaydi."""
    from core.audit import record_audit_event

    record = ReleaseRecord.objects.filter(commit_sha=commit_sha).first()
    if record is None:
        raise ReleaseNotRecorded(
            f"{commit_sha} yozilmagan. Avval `manage.py record_release` ni yugurting."
        )

    previous = record.decision
    if previous == decision and record.note == note:
        return record

    record.decision = decision
    record.decided_by = actor
    record.decided_at = timezone.now()
    record.note = note
    record.save(update_fields=["decision", "decided_by", "decided_at", "note"])

    record_audit_event(
        action="release.decision",
        request=request,
        actor=actor,
        target=record,
        target_label=f"Release {commit_sha[:12]}",
        reason=note,
        before={"decision": previous},
        after={"decision": decision, "unapplied_migrations": len(record.unapplied_migrations)},
    )
    return record
