"""Brauzerda saqlanadigan narsalar va uchinchi tomon manbalari ro'yxati (PUBLIC-01 · PUB1.5b).

Bu ro'yxat — dalil: sayt qaysi cookie va brauzer xotirasini (localStorage,
sessionStorage) nima uchun, qancha muddatga va qaysi kod orqali yozadi,
qaysi tashqi manba yuklanadi. `manage.py privacy_inventory --write` undan
`nuclear-program/frontend-v1/PUBLIC-COOKIE-INVENTORY.md`ni yaratadi; testlar
ikki tomondan qo'riqlaydi:

* **koddan**: brauzer xotirasiga yoki cookie'ga tegadigan har fayl shu yerda
  qayd etilgan bo'lishi shart (`uncovered_files()` bo'sh);
* **javobdan**: public va auth sahifalari qo'ygan har cookie, sahifa
  yuklaydigan har tashqi manba shu ro'yxatda; kuzatuv xizmati yo'q.

Hozir hamma narsa **zarur** — xizmat ishlashi yoki foydalanuvchi o'zi so'ragan
sozlama (mavzu). Analitika yoki marketing cookie'si yo'q (PUB-D6 qaroriga qadar
o'chiq), shuning uchun rozilik banneri ham yo'q: bezak uchun banner qo'yilmaydi.
Ixtiyoriy maqsad qabul qilinsa — avval shu ro'yxatga, keyin rozilik mexanizmi.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

COOKIE = "cookie"
LOCAL = "localStorage"
SESSION = "sessionStorage"

ACTIVE = "active"
REMOVED = "removed"  # endi yozilmaydi; eski brauzerdan faqat o'chiriladi

ZARUR = "Zarur — xizmat ishlashi uchun"
ZARUR_SOZLAMA = "Zarur — foydalanuvchining o'zi tanlagan sozlama"


@dataclass(frozen=True)
class StorageItem:
    name: str
    kind: str
    set_by: str
    purpose: str
    basis: str
    expiry: str
    clearing: str
    code_paths: tuple
    status: str = ACTIVE


@dataclass(frozen=True)
class ThirdPartyResource:
    origin: str
    purpose: str
    loaded_on: str
    data_seen: str
    note: str = ""


ITEMS = (
    StorageItem(
        name=settings.SESSION_COOKIE_NAME, kind=COOKIE, set_by="server (Django sessiyasi)",
        purpose="Kirgan holatni, Telegram orqali kirish oqimini va forma xabarlarini saqlash. Anonim public sahifa uni qo'ymaydi.",
        basis=ZARUR, expiry=f"{settings.SESSION_COOKIE_AGE // 86400} kun (chiqishda o'chadi)",
        clearing="Chiqish (logout) yoki muddat tugashi; HttpOnly, SameSite=Lax",
        code_paths=("core/settings.py", "users/telegram_auth_service.py"),
    ),
    StorageItem(
        name=settings.CSRF_COOKIE_NAME, kind=COOKIE, set_by="server (Django CSRF)",
        purpose="Forma va so'rovlarni boshqa saytdan soxtalashtirishdan (CSRF) himoya qilish; formali sahifada qo'yiladi.",
        basis=ZARUR, expiry=f"{settings.CSRF_COOKIE_AGE // 86400} kun",
        clearing="Muddat tugashi yoki brauzerda tozalash; JS faqat o'qiydi (so'rov sarlavhasi uchun)",
        code_paths=("core/settings.py", "static/admin/js/landing_nav_sort.js", "static/classbook/live-activity.js",
                    "static/js/messenger-chat.js", "static/js/blog-runtime.js"),
    ),
    StorageItem(
        name="messages", kind=COOKIE, set_by="server (Django xabarlari)",
        purpose="Bir martalik xabar (masalan, “saqlandi”) keyingi sahifada ko'rsatilishi uchun.",
        basis=ZARUR, expiry="Brauzer yopilguncha; ko'rsatilgach o'chadi",
        clearing="Xabar ko'rsatilgach avtomatik",
        code_paths=("core/settings.py",),
    ),
    StorageItem(
        name="blog_visitor", kind=COOKIE, set_by="server (eski blog kuzatuvi)",
        purpose="Endi qo'yilmaydi (PUB1.0g): anonim blog o'qishlari kuzatilmaydi; eski brauzerdagi qiymat o'chiriladi.",
        basis="—", expiry="—", clearing="Blog sahifasi ochilganda o'chiriladi",
        code_paths=("blog/utils.py",), status=REMOVED,
    ),
    StorageItem(
        name="az-v2-theme", kind=LOCAL, set_by="brauzer (JS)",
        purpose="Yorug'/qorong'i mavzu tanlovi (V1 va ilova sahifalari).",
        basis=ZARUR_SOZLAMA, expiry="O'chirilguncha (faqat shu brauzerda)",
        clearing="Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi",
        code_paths=("static/frontend_v1/js/theme.js", "static/js/app.js", "static/js/exam-shell.js",
                    "templates/users/settings/account.html", "templates/base.html",
                    "templates/courses/exam_detail.html"),
    ),
    StorageItem(
        name="az-theme", kind=LOCAL, set_by="brauzer (JS)",
        purpose="Eski public, blog va to'lov sahifalarida mavzu tanlovi.",
        basis=ZARUR_SOZLAMA, expiry="O'chirilguncha (faqat shu brauzerda)",
        clearing="Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi",
        code_paths=("static/js/public-home.js", "static/js/blog-runtime.js", "static/js/billing.js",
                    "static/js/prototype-ui.js"),
    ),
    StorageItem(
        name="lms-theme", kind=LOCAL, set_by="brauzer (JS)",
        purpose="Eski blog sahifasidagi mavzu tanlovi (az-theme bilan birga yoziladi).",
        basis=ZARUR_SOZLAMA, expiry="O'chirilguncha (faqat shu brauzerda)",
        clearing="Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi",
        code_paths=("static/js/blog-runtime.js",),
    ),
    StorageItem(
        name="sit-theme", kind=LOCAL, set_by="brauzer (JS)",
        purpose="“Turkiyada o'qish” sahifalaridagi mavzu tanlovi.",
        basis=ZARUR_SOZLAMA, expiry="O'chirilguncha (faqat shu brauzerda)",
        clearing="Brauzer ma'lumotlarini tozalash; serverga yuborilmaydi",
        code_paths=("static/js/sit-theme.js",),
    ),
    StorageItem(
        name="azurelms:v1:practice:*", kind=SESSION, set_by="brauzer (JS)",
        purpose="Mashq javoblari qoralamasi — sahifa tasodifan yangilansa yo'qolmasin.",
        basis=ZARUR, expiry="Tab yopilguncha",
        clearing="Tab yopilishi, chiqish (shell.js tozalaydi) yoki yuborish",
        code_paths=("static/frontend_v1/js/practice.js", "static/frontend_v1/js/shell.js"),
    ),
    StorageItem(
        name="azurelms:v1:exam:*", kind=SESSION, set_by="brauzer (JS)",
        purpose="Imtihon javoblari qoralamasi va yuborish holati — aloqa uzilsa javob yo'qolmasin.",
        basis=ZARUR, expiry="Tab yopilguncha",
        clearing="Tab yopilishi, chiqish (shell.js tozalaydi) yoki yuborish",
        code_paths=("static/frontend_v1/js/exam-attempt.js", "static/frontend_v1/js/shell.js"),
    ),
    StorageItem(
        name="azurelms:v1:messenger:*", kind=SESSION, set_by="brauzer (JS)",
        purpose="Endi yozilmaydi; eski qoralama kaliti chiqishda o'chiriladi.",
        basis="—", expiry="—", clearing="Chiqishda shell.js o'chiradi",
        code_paths=("static/frontend_v1/js/shell.js",), status=REMOVED,
    ),
    StorageItem(
        name="azurelms:practice:draft:v1:*", kind=SESSION, set_by="brauzer (JS)",
        purpose="Backoffice: mashq yaratish qoralamasi.",
        basis=ZARUR, expiry="Tab yopilguncha", clearing="Tab yopilishi yoki saqlash",
        code_paths=("static/backoffice/practice.js",),
    ),
    StorageItem(
        name="azurelms:workspace:draft:v1:*", kind=SESSION, set_by="brauzer (JS)",
        purpose="Backoffice: kurs/dars tahriri qoralamasi.",
        basis=ZARUR, expiry="Tab yopilguncha", clearing="Tab yopilishi yoki saqlash",
        code_paths=("static/backoffice/workspace.js",),
    ),
)

THIRD_PARTY = (
    ThirdPartyResource(
        origin="https://fonts.googleapis.com", purpose="Shrift uslublari (CSS)",
        loaded_on="Eski (legacy) public, auth va ilova sahifalari", data_seen="IP manzil, brauzer turi",
        note="Cookie qo'yilmaydi. O'z serverimizdan berish — PUB1.7b (tezlik byudjeti) bilan.",
    ),
    ThirdPartyResource(
        origin="https://fonts.gstatic.com", purpose="Shrift fayllari",
        loaded_on="fonts.googleapis.com bilan birga", data_seen="IP manzil, brauzer turi",
        note="Cookie qo'yilmaydi.",
    ),
    ThirdPartyResource(
        origin="https://cdn.jsdelivr.net", purpose="Ikonka shrifti va kutubxonalar (Bootstrap Icons va boshqalar)",
        loaded_on="Eski (legacy) sahifalar", data_seen="IP manzil, brauzer turi",
        note="Cookie qo'yilmaydi.",
    ),
    ThirdPartyResource(
        origin="https://telegram.org", purpose="Telegram Mini App skripti",
        loaded_on="Faqat Telegram ichida ochiladigan Mini App sahifalari", data_seen="IP manzil, brauzer turi",
        note="Public va auth sahifalarida yuklanmaydi.",
    ),
)

# Kuzatuv/reklama xizmatlari: sahifada ham, CSP'da ham bo'lmasligi kerak.
TRACKER_HOSTS = (
    "google-analytics.com", "googletagmanager.com", "doubleclick.net", "facebook.net", "facebook.com/tr",
    "mc.yandex", "metrika", "hotjar", "clarity.ms", "tiktok", "segment.io", "mixpanel",
)

KIND_LABELS = {COOKIE: "Cookie", LOCAL: "localStorage", SESSION: "sessionStorage"}

# Brauzer xotirasi yoki cookie yozadigan kod belgilari.
_JS_STORAGE = re.compile(r"\b(localStorage|sessionStorage)\b|document\.cookie\s*=(?!=)")
_PY_COOKIE = re.compile(r"\.(set_cookie|set_signed_cookie|delete_cookie)\(")
_SKIP_PARTS = {"venv", "node_modules", "playground", ".tools", "staticfiles", "vendor", "django_ckeditor_5", "ckeditor"}
SCAN_ROOTS = ("static", "templates", "core", "frontend", "users", "blog", "courses", "cohorts", "subscriptions",
              "messenger", "bot", "classbook", "library", "sit", "gamification", "aicontrol")


def repo_root():
    return Path(settings.BASE_DIR)


def _skip(path):
    return bool(_SKIP_PARTS & set(path.parts)) or path.name.endswith(".min.js") or path.name.startswith("test_")


def storage_files(root=None):
    """Brauzer xotirasi yoki cookie'ga tegadigan fayllar (repo-nisbiy, `/` bilan)."""
    root = Path(root or repo_root())
    found = set()
    for top in SCAN_ROOTS:
        base = root / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in (".js", ".html", ".py") or _skip(path.relative_to(root)):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            pattern = _PY_COOKIE if path.suffix == ".py" else _JS_STORAGE
            if pattern.search(text):
                found.add(path.relative_to(root).as_posix())
    # Django sessiya/CSRF/xabar cookie'lari sozlamada yashaydi.
    found.add("core/settings.py")
    return found


def covered_files():
    return {path for item in ITEMS for path in item.code_paths}


def uncovered_files(root=None):
    """Ro'yxatda qayd etilmagan, lekin brauzer xotirasiga tegadigan fayllar."""
    return sorted(storage_files(root) - covered_files())


def missing_code_paths(root=None):
    root = Path(root or repo_root())
    return sorted(path for path in covered_files() if not (root / path).exists())


def active_cookie_names():
    return {item.name for item in ITEMS if item.kind == COOKIE and item.status == ACTIVE}


def allowed_origins():
    return {resource.origin for resource in THIRD_PARTY}


def render_markdown():
    """`PUBLIC-COOKIE-INVENTORY.md` matni — deterministik (test qo'lda tahrirni ushlaydi)."""
    lines = [
        "# PUBLIC-COOKIE-INVENTORY — brauzerda nima saqlanadi",
        "",
        "> Avtomatik yaratilgan: `python manage.py privacy_inventory --write` (manba:",
        "> `frontend/privacy_inventory.py`). Qo'lda tahrirlamang — test farqni ushlaydi.",
        "",
        "Hamma yozuv birinchi tomon (azurelms) va **zarur**: xizmat ishlashi yoki foydalanuvchi",
        "tanlagan sozlama. Analitika va marketing cookie'si yo'q (PUB-D6 qaroriga qadar o'chiq),",
        "shuning uchun rozilik banneri ham yo'q. Bu hujjat huquqiy muvofiqlik da'vosi emas.",
        "",
    ]
    for kind in (COOKIE, LOCAL, SESSION):
        lines += [f"## {KIND_LABELS[kind]}", "",
                  "| Nom | Holat | Kim yozadi | Maqsad | Asos | Muddat | Qanday o'chadi | Kod |",
                  "|---|---|---|---|---|---|---|---|"]
        for item in ITEMS:
            if item.kind != kind:
                continue
            status = "faol" if item.status == ACTIVE else "olib tashlangan"
            code = "<br>".join(f"`{path}`" for path in item.code_paths)
            lines.append(f"| `{item.name}` | {status} | {item.set_by} | {item.purpose} | {item.basis} | "
                         f"{item.expiry} | {item.clearing} | {code} |")
        lines.append("")
    lines += ["## Uchinchi tomon manbalari", "",
              "| Manba | Maqsad | Qayerda yuklanadi | Ular nimani ko'radi | Izoh |", "|---|---|---|---|---|"]
    for resource in THIRD_PARTY:
        lines.append(f"| {resource.origin} | {resource.purpose} | {resource.loaded_on} | {resource.data_seen} | {resource.note} |")
    lines += ["", "## Kuzatuv xizmatlari", "",
              "Sahifada ham, Content-Security-Policy'da ham yo'q: " + ", ".join(f"`{host}`" for host in TRACKER_HOSTS) + ".",
              ""]
    from frontend.activity_notices import NOTICES

    lines += ["## Faoliyat eslatmalari (forma yonida)", "", "| Faoliyat | Qayerda | Matn |", "|---|---|---|"]
    for notice in NOTICES.values():
        lines.append(f"| {notice.label} | {notice.where} | {notice.text} |")
    lines.append("")
    return "\n".join(lines)


def inventory_path():
    return repo_root() / "nuclear-program" / "frontend-v1" / "PUBLIC-COOKIE-INVENTORY.md"
