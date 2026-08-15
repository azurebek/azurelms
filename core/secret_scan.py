"""Repozitoriyda qolib ketgan sirlarni topadi (A1a CI gate).

Repo public: bir marta commit qilingan kalit o'chirilsa ham tarixda qoladi va
kompromentatsiya qilingan hisoblanadi. Shuning uchun gate push'dan oldin, CI
darajasida turadi.

Dizayn qarori — **yuqori signal, past shovqin**. Umumiy `secret=...` uslubidagi
qoidalar yuzlab false positive beradi va odam ularni o'chirib qo'yadi; o'chirilgan
gate esa yo'q gate bilan barobar. Shu sababli faqat formati o'ziga xos, aniq
identifikatsiya qilinadigan kalitlar qidiriladi (Telegram token, Google API key,
AWS key, private key bloki, parolli DSN) va bitta strukturaviy qoida: `.env`
fayllari umuman kuzatuvda bo'lmasligi kerak.

Faqat git kuzatayotgan fayllar tekshiriladi: `.gitignore` dagi lokal fayllar
(`.env.local`, `db.sqlite3`, `media/`) push qilinmaydi, ularni tekshirish esa
faqat noto'g'ri ogohlantirish beradi.
"""

import re
import subprocess
from pathlib import Path

from django.conf import settings

# Skanerlash mumkin bo'lmagan (yoki ma'nosiz) kengaytmalar.
BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".zip", ".gz", ".xz", ".7z", ".exe", ".dll", ".so", ".dylib",
    ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".sqlite3", ".pyc",
})
MAX_FILE_BYTES = 2 * 1024 * 1024

# Har bir qoida: (kod, tavsif, regex).
RULES = (
    (
        "telegram_bot_token",
        "Telegram bot tokeni",
        re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    ),
    (
        "google_api_key",
        "Google/Gemini API kaliti",
        re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ),
    (
        "aws_access_key_id",
        "AWS access key ID",
        re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[0-9A-Z]{16}\b"),
    ),
    (
        "private_key_block",
        "PEM private key bloki",
        re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    ),
    (
        "slack_token",
        "Slack tokeni",
        re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    ),
    (
        "url_inline_password",
        "URL ichida ochiq parol",
        # postgres://user:parol@host — placeholder parollar quyida chiqarib tashlanadi.
        re.compile(
            r"\b(?:postgres|postgresql|mysql|mongodb|amqp|redis|rediss)://"
            r"[^\s:/@'\"]+:([^\s@/'\"]+)@"
        ),
    ),
)

# Namuna/placeholder qiymatlar: hujjat va sozlama fayllarida ataylab turadi.
PLACEHOLDER_MARKERS = (
    "example", "namuna", "placeholder", "changeme", "change-me", "your",
    "insecure", "dummy", "fake", "sample", "xxx", "<", "${", "{{",
    "password", "parol", "secret", "token", "user", "pass",
)


def _is_placeholder(value):
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def tracked_files(root):
    """Git kuzatayotgan fayllar ro'yxati."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(root),
        capture_output=True,
        check=True,
    )
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


def tracked_env_files(names):
    """Kuzatuvda qolgan `.env` fayllari (`*.example` bundan mustasno)."""
    leaked = []
    for name in names:
        base = name.rsplit("/", 1)[-1]
        if not base.startswith(".env"):
            continue
        if base.endswith(".example") or base.endswith(".sample"):
            continue
        leaked.append(name)
    return sorted(leaked)


def scan_text(name, text):
    """Bitta fayl matnidan topilgan sirlar ro'yxati."""
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "secret-scan: allow" in line:
            continue
        for code, label, pattern in RULES:
            match = pattern.search(line)
            if not match:
                continue
            captured = match.group(match.lastindex or 0)
            if _is_placeholder(captured):
                continue
            findings.append({
                "file": name,
                "line": line_number,
                "rule": code,
                "label": label,
                # Xulosaning o'zi sirni oshkor qilmasligi kerak.
                "preview": captured[:4] + "…" if len(captured) > 4 else "…",
            })
    return findings


def scan_repository(root=None):
    """Kuzatuvdagi barcha fayllarni tekshiradi va topilmalarni qaytaradi."""
    base = Path(root or settings.BASE_DIR)
    names = tracked_files(base)

    findings = []
    for name in tracked_env_files(names):
        findings.append({
            "file": name,
            "line": 0,
            "rule": "tracked_env_file",
            "label": "Kuzatuvdagi .env fayli",
            "preview": "…",
        })

    for name in names:
        path = base / name
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings.extend(scan_text(name, text))

    return findings
