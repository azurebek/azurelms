"""Canonical capability inventory for the Azure Control Center.

The registry describes ownership and dependencies only. Runtime state belongs to
``snapshot.py`` so the web page and management command cannot drift apart.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDefinition:
    slug: str
    label: str
    category: str
    criticality: str
    owner: str
    description: str
    dependencies: tuple[str, ...] = ()
    runbook: str = ""


CAPABILITY_REGISTRY = (
    CapabilityDefinition(
        slug="database",
        label="Ma'lumotlar bazasi",
        category="Core",
        criticality="critical",
        owner="Azurbek",
        description="Canonical product state and transactional records.",
        runbook="Database connectivity, migrations and restore pointni tekshiring.",
    ),
    CapabilityDefinition(
        slug="cache",
        label="Cache",
        category="Runtime",
        criticality="high",
        owner="Azurbek",
        description="Shared cache used by production web processes.",
        dependencies=("database",),
        runbook="Redis/Valkey URL, TLS va service availabilityni tekshiring.",
    ),
    CapabilityDefinition(
        slug="realtime",
        label="Realtime / Channels",
        category="Runtime",
        criticality="high",
        owner="Azurbek",
        description="Messenger WebSocket fan-out and shared channel state.",
        dependencies=("cache",),
        runbook="Channel backend va Redis/Valkey ulanishini tekshiring.",
    ),
    CapabilityDefinition(
        slug="jobs",
        label="Jobs / Celery",
        category="Runtime",
        criticality="critical",
        owner="Azurbek",
        description="Background AI, lifecycle and notification execution.",
        dependencies=("database", "cache"),
        runbook="Broker URL, worker va beat processlarini tekshiring.",
    ),
    CapabilityDefinition(
        slug="telegram_outbox",
        label="Telegram outbox",
        category="Integrations",
        criticality="high",
        owner="Azurbek",
        description="Platform notifications queued for Telegram delivery.",
        dependencies=("database", "jobs"),
        runbook="telegram_outbox worker, token va failed yozuvlarni tekshiring.",
    ),
    CapabilityDefinition(
        slug="media_storage",
        label="Media storage",
        category="Storage",
        criticality="critical",
        owner="Azurbek",
        description="Learner uploads, receipts and course media storage policy.",
        dependencies=("database",),
        runbook="Storage credentials, privacy policy va object accessni tekshiring.",
    ),
    CapabilityDefinition(
        slug="ai_provider",
        label="AI provider",
        category="AI",
        criticality="high",
        owner="Azurbek",
        description="Selected chat provider and effective token policy.",
        dependencies=("database", "jobs"),
        runbook="Provider tanlovi, API key va AI limit enforcementni tekshiring.",
    ),
    CapabilityDefinition(
        slug="rag",
        label="RAG index",
        category="AI",
        criticality="medium",
        owner="Azurbek",
        description="Lesson-grounded retrieval coverage and index freshness.",
        dependencies=("database", "ai_provider"),
        runbook="python manage.py reindex_rag --force",
    ),
    CapabilityDefinition(
        slug="security",
        label="Security posture",
        category="Governance",
        criticality="critical",
        owner="Azurbek",
        description="Environment-aware debug and transport security posture.",
        dependencies=("database",),
        runbook="SECURITY_STRICT, DEBUG, secure cookie va deploy checkni tekshiring.",
    ),
    CapabilityDefinition(
        slug="workers",
        label="Fon workerlari",
        category="Runtime",
        criticality="high",
        owner="Azurbek",
        description="Background workers reporting a live heartbeat.",
        dependencies=("database",),
        runbook="Worker jarayonini qayta ishga tushiring: `python manage.py runbot` yoki `telegram_outbox`.",
    ),
    CapabilityDefinition(
        slug="release",
        label="Release identity",
        category="Governance",
        criticality="high",
        owner="Azurbek",
        description="Currently running source revision and rollback identity.",
        dependencies=("database",),
        runbook="Deploy source SHA va rollback targetni tasdiqlang.",
    ),
)


def capability_by_slug(slug: str) -> CapabilityDefinition:
    for capability in CAPABILITY_REGISTRY:
        if capability.slug == slug:
            return capability
    raise KeyError(f"Unknown capability: {slug}")
