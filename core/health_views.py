"""Liveness va readiness endpointlari — vendor-neutral (A1a).

Ikkalasi ataylab farqlanadi, chunki orkestrator ularga turlicha munosabatda
bo'ladi:

* `/healthz` — **liveness**: process javob beryaptimi. DB'ga ham, cache'ga ham
  tegmaydi. Sabab: baza yiqilganda processni o'ldirish vaziyatni yaxshilamaydi,
  faqat qayta ishga tushirish siklini boshlaydi.
* `/readyz` — **readiness**: shu instance trafik qabul qila oladimi. Bu yerda
  **critical** capability'lar tekshiriladi; birortasi `red` bo'lsa `503`.

Tekshiruv mantig'i qayta yozilmaydi — Control Center'ning capability registry va
probe'lari ishlatiladi (`rules-for-agents` §"bir control plane"). Shu sabab web
sahifa, `system_audit` CLI va readiness endpointi bir xil haqiqatni ko'radi.

Faqat `critical` probe'lar yugurtiriladi: readiness har necha soniyada
so'raladi, o'nta probe esa har safar bir necha DB so'rovi degani.

Tashqi javob qo'pol (PUB1.7a): begonaga faqat holat — `alive`, `ready` yoki
`not-ready` va status kodi (200/503). Muhit, reliz va probe tafsiloti faqat
Control Center egasiga (sessiya bilan) qo'shiladi. Orkestrator semantikasi
o'zgarmagan: GET, `200`/`503`, keshlanmaydi.
"""

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from core.access import is_control_center_owner
from core.control_center.registry import CAPABILITY_REGISTRY
from core.control_center.snapshot import PROBE_FUNCTIONS, _release_sha

READINESS_CRITICALITY = "critical"


def _owner_detail(request):
    """Tafsilot faqat Control Center egasiga; begonaga hech narsa (`/healthz` bazaga tegmasin).

    Sessiya cookie'si bo'lmagan so'rov (orkestrator) foydalanuvchini bazadan
    yuklamaydi — `/healthz` baza yiqilganda ham yashil qoladi.
    """
    if settings.SESSION_COOKIE_NAME not in request.COOKIES:
        return False
    try:
        return is_control_center_owner(getattr(request, "user", None))
    except Exception:
        return False


@require_GET
@never_cache
def healthz(request):
    """Liveness — hech qanday tashqi bog'liqlikka tegmaydi."""
    payload = {"status": "alive"}
    if _owner_detail(request):
        payload.update(environment=getattr(settings, "APP_ENV", "unknown"), release=_release_sha())
    return JsonResponse(payload)


@require_GET
@never_cache
def readyz(request):
    """Readiness — critical capability'lar bo'yicha `200` yoki `503`."""
    checks = []
    ready = True

    for definition in CAPABILITY_REGISTRY:
        if definition.criticality != READINESS_CRITICALITY:
            continue
        probe = PROBE_FUNCTIONS.get(definition.slug)
        if probe is None:
            continue
        try:
            result = probe(definition)
            status, summary = result.status, result.summary
        except Exception:
            # Readiness sinmasligi kerak: yiqilgan probe `red` sifatida
            # hisoblanadi, ammo endpoint baribir javob qaytaradi.
            status, summary = "red", "Probe xatoga tushdi."
        if status == "red":
            ready = False
        checks.append({"slug": definition.slug, "status": status, "summary": summary})

    payload = {"status": "ready" if ready else "not-ready"}
    if _owner_detail(request):
        payload.update(environment=getattr(settings, "APP_ENV", "unknown"), release=_release_sha(), checks=checks)
    return JsonResponse(payload, status=200 if ready else 503)
