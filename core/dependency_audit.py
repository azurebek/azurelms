"""`pip-audit` hisobotini ma'lum zaifliklar reyestri bilan solishtiradi (A1a).

Nega shunchaki `pip-audit --strict` emas: bugungi `requirements.txt` da allaqachon
o'nlab e'lon qilingan advisory bor va ularning bir qismi major yoki release-candidate
ko'tarilishni talab qiladi. Gate'ni darhol qizil qilib qo'yish uni o'chirib qo'yishga
olib keladi; butunlay ogohlantirishga aylantirish esa gate emas.

O'rtadagi halol variant — **reyestr**: bugungi holat `security/dependency-audit-baseline.json`
da nomma-nom yozilgan, CI esa faqat **yangi** advisory'ga qizil beradi. Ya'ni mavjud
qarz ko'rinib turadi va o'sishi mumkin emas.

Reyestr `name==version` bo'yicha kalitlanadi: paket ko'tarilishi bilan uning eski
istisnolari kuchini yo'qotadi va yangi holat qayta ko'rib chiqilishi shart.
`review_by` sanasi esa reyestrning abadiy indulgensiyaga aylanishini to'xtatadi.
"""

import json
from datetime import date
from pathlib import Path

from django.conf import settings

BASELINE_RELATIVE_PATH = Path("security") / "dependency-audit-baseline.json"


class DependencyAuditError(Exception):
    """Hisobot yoki reyestr o'qib bo'lmaydigan holatda."""


def baseline_path():
    return Path(settings.BASE_DIR) / BASELINE_RELATIVE_PATH


def load_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DependencyAuditError(f"Fayl topilmadi: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DependencyAuditError(f"JSON o'qib bo'lmadi ({path}): {exc}") from exc


def report_findings(report):
    """`pip-audit -f json` chiqishidan `{name==version: {advisory ID}}` yasaydi."""
    if not isinstance(report, dict) or "dependencies" not in report:
        raise DependencyAuditError(
            "Kutilgan `pip-audit -f json` formati emas: `dependencies` kaliti yo'q."
        )

    findings = {}
    for dependency in report["dependencies"]:
        vulns = dependency.get("vulns") or []
        if not vulns:
            continue
        key = f"{dependency['name'].lower()}=={dependency['version']}"
        # pip-audit bir xil ID'ni bir necha marta qaytarishi mumkin.
        findings.setdefault(key, set()).update(vuln["id"] for vuln in vulns)
    return findings


def baseline_findings(baseline):
    known = baseline.get("known") or {}
    return {key.lower(): set(ids) for key, ids in known.items()}


def compare(report, baseline):
    """Reyestrga nisbatan yangi va eskirgan yozuvlarni ajratadi."""
    current = report_findings(report)
    known = baseline_findings(baseline)

    unlisted = {}
    for key, ids in current.items():
        extra = ids - known.get(key, set())
        if extra:
            unlisted[key] = sorted(extra)

    stale = {}
    for key, ids in known.items():
        gone = ids - current.get(key, set())
        if gone:
            stale[key] = sorted(gone)

    return {
        "unlisted": dict(sorted(unlisted.items())),
        "stale": dict(sorted(stale.items())),
        "total_current": sum(len(ids) for ids in current.values()),
        "packages_affected": len(current),
    }


def review_overdue(baseline, today=None):
    """Reyestr qayta ko'rib chiqish muddati o'tganmi."""
    raw = (baseline.get("review_by") or "").strip()
    if not raw:
        return None
    try:
        deadline = date.fromisoformat(raw)
    except ValueError as exc:
        raise DependencyAuditError(f"`review_by` sanasi noto'g'ri: {raw!r}") from exc
    current = today or date.today()
    return deadline if current > deadline else None
