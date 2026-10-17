"""Public sirt registri: qaysi route anonimga ochiq va qanday siyosat bilan (PUB1.1a).

Har nomli route uchta guruhdan birida turadi:

* ``PUBLIC_SURFACES`` — anonim yoki tizimga kirmagan odam ocha oladigan sahifa
  va endpoint, har biriga `PublicSurfacePolicy` (method, auditoriya, index,
  canonical, sitemap, cache, rich-content profili);
* ``OPS_ROUTES`` — mahsulot sahifasi emas: health, readiness, upload, webhook,
  runtime CSS. Ular indekslanadigan sahifa hisoblanmaydi;
* ``PRIVATE_ROUTES`` / ``PRIVATE_NAMESPACES`` — anonimga yopiq (login'ga redirect,
  403, 404 yoki 405). Buni `frontend/test_public_route_registry.py` har route'ni
  anonim ochib tekshiradi.

Registry **deklarativ**: view'lar undan qaror olmaydi va biznes qoidani
takrorlamaydi. Bu yerdagi index/cache qiymatlari maqsad; joriy javob bilan
farqi `manage.py audit_public_routes` va snapshot testida dalil sifatida
ko'rinadi, PUB1.1b–d ularni yopadi. Model yoki admin'da route siyosati
yaratilmaydi.

Yangi nomli route qo'shilsa shu yerda tasniflanmaguncha `manage.py check`
xato beradi (`azurelms.E201`).
"""

from dataclasses import dataclass
from enum import Enum

from core.rich_content_policy import PUBLIC_EDITORIAL_V1


class CacheClass(str, Enum):
    SENSITIVE_NO_STORE = "sensitive_no_store"
    STATUS_NO_STORE = "status_no_store"
    PUBLIC_QUERY = "public_query"
    PUBLIC_CONTENT = "public_content"
    IMMUTABLE_ASSET = "immutable_asset"


# Keyinchalik umumiy (shared) cache'ga chiqishi mumkin bo'lgan sinflar.
SHARED_CACHE_CLASSES = frozenset({CacheClass.PUBLIC_CONTENT, CacheClass.IMMUTABLE_ASSET})
ALLOWED_METHODS = frozenset({"GET", "HEAD", "POST"})
AUDIENCES = frozenset({"anonymous", "mixed", "sensitive", "ops"})
INDEX_POLICIES = frozenset({"index", "noindex", "conditional"})
CANONICAL_POLICIES = frozenset({"self", "clean_base", "none", "object"})
SITEMAP_POLICIES = frozenset({"include", "exclude", "object"})
RICH_CONTENT_PROFILES = frozenset({PUBLIC_EDITORIAL_V1})


@dataclass(frozen=True)
class PublicSurfacePolicy:
    route_name: str
    methods: frozenset
    audience: str
    index_policy: str
    canonical_policy: str
    sitemap_policy: str
    cache_class: CacheClass
    rich_content_profile: str | None = None
    telemetry_class: str | None = None
    claim_gate: bool = False


READ = frozenset({"GET", "HEAD"})
FORM = frozenset({"GET", "HEAD", "POST"})
POST_ONLY = frozenset({"POST"})
GET_ONLY = frozenset({"GET"})


def _content(name, *, index="index", canonical="self", sitemap="include", cache=CacheClass.PUBLIC_CONTENT,
             rich=PUBLIC_EDITORIAL_V1, claim_gate=False, telemetry=None):
    return PublicSurfacePolicy(name, READ, "anonymous", index, canonical, sitemap, cache, rich, telemetry, claim_gate)


def _sensitive(name, methods=FORM):
    return PublicSurfacePolicy(name, methods, "sensitive", "noindex", "none", "exclude", CacheClass.SENSITIVE_NO_STORE)


def _status(name):
    return PublicSurfacePolicy(name, READ, "anonymous", "noindex", "none", "exclude", CacheClass.STATUS_NO_STORE)


PUBLIC_SURFACES = (
    # Kontent sahifalari (§5.3 matritsasi). PUBLIC_CONTENT avval
    # `max-age=0, must-revalidate`; shared cache faqat isbotdan keyin.
    _content("home", claim_gate=True),
    _content("about", claim_gate=True),
    _content("privacy_policy"),
    _content("terms_of_service"),
    _content("faq_page"),
    _content("courses", index="conditional", canonical="clean_base", cache=CacheClass.PUBLIC_QUERY, rich=None),
    _content("course_detail", canonical="object", sitemap="object", claim_gate=True),
    _content("subscriptions:pricing", index="conditional", sitemap="object", rich=None, claim_gate=True),
    _content("blog:list", index="conditional", canonical="clean_base", cache=CacheClass.PUBLIC_QUERY, rich=None),
    _content("blog:detail", index="conditional", canonical="object", sitemap="object", telemetry="blog_read"),
    _content("sit:home", index="conditional", sitemap="object"),
    _content("sit:university_list", index="conditional", canonical="clean_base", cache=CacheClass.PUBLIC_QUERY, rich=None),
    _content("sit:university_detail", index="conditional", canonical="object", sitemap="object"),
    _content("sit:knowledge_detail", index="conditional", canonical="object", sitemap="object"),
    # Auth va token yuzalari: indekslanmaydi, saqlanmaydi.
    _sensitive("login"),
    _sensitive("register"),
    _sensitive("password_reset"),
    _sensitive("password_reset_done", READ),
    _sensitive("password_reset_confirm"),
    _sensitive("password_reset_complete", READ),
    _sensitive("telegram_auth_init", POST_ONLY),
    _sensitive("telegram_auth_status", GET_ONLY),
    _sensitive("telegram_auth_consume", POST_ONLY),
    _sensitive("telegram_auth_cancel", POST_ONLY),
    # Sertifikat aniq ID bilan ochiladi — token kabi: noindex, saqlanmaydi.
    _sensitive("certificate_detail", READ),
    _sensitive("certificate_appendix", READ),
    # Telegram Mini App kirish qobig'i va initData tekshiruvi.
    _sensitive("bot:miniapp_entry", READ),
    _sensitive("bot:miniapp_auth", POST_ONLY),
    # Holat sahifalari.
    _status("maintenance"),
    _status("offline"),
)

# Mahsulot sahifasi emas. Indekslanmaydi va sitemap'ga kirmaydi.
OPS_ROUTES = {
    "healthz": "Liveness — process tirikmi (bazaga tegmaydi).",
    "readyz": "Readiness — critical capability'lar.",
    "design_theme_css": "Runtime dizayn token CSS'i (asset).",
    "ck_editor_5_upload_file": "CKEditor rasm upload'i (faqat xodim).",
    "bot:telegram_webhook": "Telegram webhook (secret token bilan).",
    "robots_txt": "Crawler uchun sitemap ko'rsatkichi (sahifa emas).",
    "sitemap_xml": "Faqat e'lon qilingan canonical URL'lar (frontend/public_sitemap.py).",
}
# Faqat sozlama yoqilganda mount bo'ladigan ops route'lar.
OPTIONAL_OPS_ROUTES = {
    "prometheus-django-metrics": "PROMETHEUS_ENABLED bo'lsa metrikalar.",
}

# Bu namespace'lardagi hamma route anonimga yopiq.
PRIVATE_NAMESPACES = frozenset({
    "admin", "messenger", "classbook", "cohorts", "library", "library_backoffice", "sit_backoffice",
})

PRIVATE_ROUTES = frozenset({
    # Hisob, sozlamalar va onboarding.
    "onboarding_choice", "start_smart_onboarding", "logout", "profile", "settings", "settings_account",
    "settings_privacy", "settings_billing", "settings_capabilities", "update_avatar", "update_password",
    "update_ai_tone", "update_ai_model", "update_ai_skill", "update_ai_web_search_effort", "ai_memory",
    "ai_memory_toggle", "ai_memory_clear", "ai_memory_archive", "ai_memory_reject",
    # O'quvchi kabineti.
    "dashboard", "my_courses", "leaderboard", "notifications", "notification_open", "notifications_read_all",
    "attendance_calendar", "attendance_manage", "subscriptions", "certificates", "help_center",
    # O'qish, imtihon va private media.
    "exam_center", "course_study", "lesson_detail", "lesson_completion", "assignment_submit", "api_quiz_submit",
    "exam_detail", "exam_result", "api_exam_v1", "api_exam_start", "api_exam_section_state", "api_exam_save",
    "api_exam_audio_upload", "api_exam_audio_play", "api_exam_review_flag", "api_exam_blur", "api_exam_submit",
    "submission_file", "exam_answer_audio",
    # Blog studiyasi va interaktivlik (kirish kerak).
    "blog:studio", "blog:studio_create", "blog:studio_edit", "blog:clap", "blog:comment_create",
    "blog:comment_like",
    # Mini App ichki sahifalari.
    "bot:miniapp_home", "bot:miniapp_courses", "bot:miniapp_ai", "bot:miniapp_profile",
    # Backoffice.
    "backoffice_ai_kill_switch", "backoffice_ai_circuit_reset", "backoffice_feature_flags",
    "backoffice_runtime_settings", "backoffice_ai_cost", "backoffice_dead_letter", "backoffice_brand",
    "backoffice_design", "backoffice_design_state", "backoffice_design_command", "backoffice_landing",
    "backoffice_receipts", "backoffice_catalog", "backoffice_plan_edit", "backoffice_cohort_create",
    "backoffice_cohort_edit", "backoffice_cohort_members", "backoffice_control", "backoffice_dashboard",
    "backoffice_workspace_home", "backoffice_workspace_search", "backoffice_workspace_payments",
    "backoffice_workspace_plans", "backoffice_workspace_site", "backoffice_workspace_settings",
    "backoffice_workspace_groups", "backoffice_workspace_students", "backoffice_workspace_student",
    "backoffice_workspace_courses", "backoffice_workspace_course_create", "backoffice_workspace_course_edit",
    "backoffice_workspace_course", "backoffice_workspace_assignment_new", "backoffice_workspace_assignment_edit",
    "backoffice_workspace_quiz_new", "backoffice_workspace_quiz_edit", "backoffice_users", "backoffice_chats",
    "backoffice_courses", "backoffice_course_create", "backoffice_course_edit", "backoffice_lessons",
    "backoffice_lesson_edit", "backoffice_exams", "backoffice_exam_edit", "backoffice_ai_control",
    # O'qituvchi paneli.
    "teacher_dashboard", "teacher_cohorts", "teacher_students", "teacher_courses", "teacher_grading",
    "teacher_grade_exam", "teacher_grade_assignment", "teacher_attendance", "teacher_release",
})

PUBLIC = "public"
OPS = "ops"
PRIVATE = "private"


def surface_by_name(surfaces=PUBLIC_SURFACES):
    return {policy.route_name: policy for policy in surfaces}


def route_inventory(resolver=None):
    """Nomli route'lar: ``[(nom, pattern, converter_nomlari), ...]`` (namespace bilan)."""
    from django.urls import URLResolver, get_resolver

    rows = []

    def walk(patterns, namespace=None, prefix=""):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                inner = pattern.namespace
                full_ns = f"{namespace}:{inner}" if (namespace and inner) else (inner or namespace)
                walk(pattern.url_patterns, full_ns, prefix + str(pattern.pattern))
            elif pattern.name:
                name = f"{namespace}:{pattern.name}" if namespace else pattern.name
                rows.append((name, prefix + str(pattern.pattern), tuple(pattern.pattern.converters)))

    walk((resolver or get_resolver()).url_patterns)
    return rows


def classify(name, *, surfaces=PUBLIC_SURFACES, ops=None, private=PRIVATE_ROUTES):
    ops = OPS_ROUTES | OPTIONAL_OPS_ROUTES if ops is None else ops
    if name in surface_by_name(surfaces):
        return PUBLIC
    if name in ops:
        return OPS
    if name in private or (":" in name and name.split(":", 1)[0] in PRIVATE_NAMESPACES):
        return PRIVATE
    return None


def registry_errors(*, surfaces=PUBLIC_SURFACES, ops=None, private=PRIVATE_ROUTES, route_names=None):
    """Registry va URL inventarining nomuvofiqliklari (bo'sh ro'yxat — hammasi joyida)."""
    ops = OPS_ROUTES if ops is None else ops
    if route_names is None:
        route_names = [name for name, _pattern, _converters in route_inventory()]
    known = set(route_names)
    errors = []

    seen = set()
    for policy in surfaces:
        name = policy.route_name
        if name in seen:
            errors.append(f"{name}: registryda ikki marta.")
        seen.add(name)
        if name not in known:
            errors.append(f"{name}: URL inventarida bunday nomli route yo'q.")
        if not policy.methods or not set(policy.methods) <= ALLOWED_METHODS:
            errors.append(f"{name}: noto'g'ri method to'plami {sorted(policy.methods)}.")
        for field, allowed in (("audience", AUDIENCES), ("index_policy", INDEX_POLICIES),
                               ("canonical_policy", CANONICAL_POLICIES), ("sitemap_policy", SITEMAP_POLICIES)):
            if getattr(policy, field) not in allowed:
                errors.append(f"{name}: {field}={getattr(policy, field)!r} ruxsat etilmagan.")
        if not isinstance(policy.cache_class, CacheClass):
            errors.append(f"{name}: cache_class CacheClass emas.")
        if policy.audience == "sensitive":
            if policy.index_policy != "noindex":
                errors.append(f"{name}: sensitive yuza indekslanmaydi (noindex bo'lishi shart).")
            if policy.cache_class != CacheClass.SENSITIVE_NO_STORE:
                errors.append(f"{name}: sensitive yuza faqat SENSITIVE_NO_STORE bo'ladi.")
        if policy.audience in {"mixed", "sensitive"} and policy.cache_class in SHARED_CACHE_CLASSES:
            errors.append(f"{name}: shaxsiy/aralash javob shared cache'ga tushmaydi.")
        if policy.sitemap_policy != "exclude" and policy.canonical_policy == "none":
            errors.append(f"{name}: canonical'siz route sitemap'ga kirmaydi.")
        if policy.index_policy == "index" and policy.audience != "anonymous":
            errors.append(f"{name}: faqat anonim kontent indekslanadi.")
        if policy.rich_content_profile is not None and policy.rich_content_profile not in RICH_CONTENT_PROFILES:
            errors.append(f"{name}: noma'lum rich-content profili {policy.rich_content_profile!r}.")

    for name in ops:
        if name not in known:
            errors.append(f"{name}: ops allowlist'dagi route URL inventarida yo'q.")
    for name in private:
        if name not in known:
            errors.append(f"{name}: private ro'yxatdagi route URL inventarida yo'q.")

    groups = (set(seen), set(ops) | set(OPTIONAL_OPS_ROUTES), set(private))
    for index, left in enumerate(groups):
        for right in groups[index + 1:]:
            for name in sorted(left & right):
                errors.append(f"{name}: bir vaqtda ikki guruhda tasniflangan.")

    for name in route_names:
        if classify(name, surfaces=surfaces, ops=set(ops) | set(OPTIONAL_OPS_ROUTES), private=private) is None:
            errors.append(
                f"{name}: tasniflanmagan route — frontend/public_policy.py'da public, ops yoki private deb belgilang."
            )
    return errors
