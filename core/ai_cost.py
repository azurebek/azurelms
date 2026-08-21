"""AI sarfini pulga aylantiruvchi ledger (A2).

`AISupplyEvent` so'rov va tokenni hisoblaydi; bu modul ularni owner kiritgan
narx snapshot'lari bilan taxminiy xarajatga aylantiradi.

**Narxlanmagan sarf nol deb yozilmaydi.** Reja buni ochiq talab qiladi:
"«Bepul» cost=0 deb yozilmaydi — quota ham scarcity". Snapshot topilmasa
chaqiruv `unpriced` deb sanaladi va jamiga hech narsa qo'shilmaydi. Aks holda
free-tier sarfi "hech narsa sarflanmadi" bo'lib ko'rinardi, holbuki haqiqiy
cheklov — kvota — yeyilayotgan bo'lardi.

**Xarajat o'qish paytida hisoblanadi**, eventga muzlatib yozilmaydi. Sabab
amaliy: owner narxni ko'pincha sarfdan **keyin** kiritadi, ya'ni muzlatilgan
qiymat abadiy bo'sh qolardi. O'qishda hisoblash o'tmishni to'g'ri to'ldiradi
va xato kiritilgan narxni yangi snapshot bilan tuzatish mumkin. Evaziga:
narx tarixi o'zgarsa hisobot ham o'zgaradi — shuning uchun snapshotlar
append-only va sanali.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

#: Provayderlar narxni million token uchun e'lon qiladi.
TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)


def price_for(model_name, *, on=None, provider="gemini"):
    """Berilgan sanada amal qiladigan eng so'nggi narx snapshot'i yoki `None`."""
    from aicontrol.models import AIModelPrice

    on = on or timezone.localdate()
    return (
        AIModelPrice.objects.filter(
            provider=provider, model_name=model_name, effective_from__lte=on
        )
        .order_by("-effective_from")
        .first()
    )


def cost_for_event(event):
    """Bitta chaqiruvning taxminiy narxi yoki `None` (narxlanmagan).

    `None` — "bepul" degani emas, "narxi ma'lum emas" degani.
    """
    price = price_for(event.model_name, on=event.bucket_date, provider=event.provider)
    if price is None:
        return None

    prompt = Decimal(event.prompt_tokens or 0)
    completion = Decimal(event.completion_tokens or 0)
    return (
        prompt * price.input_per_million + completion * price.output_per_million
    ) / TOKENS_PER_PRICE_UNIT


def cost_rollup(*, start=None, end=None, provider="gemini"):
    """Davr bo'yicha xarajat xulosasi.

    Narxlangan va narxlanmagan sarf **alohida** qaytariladi: ularni qo'shib
    yuborish hisobotni chalg'ituvchi qilardi.
    """
    from aicontrol.models import AISupplyEvent

    events = AISupplyEvent.objects.filter(
        provider=provider, status=AISupplyEvent.STATUS_SUCCEEDED
    )
    if start:
        events = events.filter(bucket_date__gte=start)
    if end:
        events = events.filter(bucket_date__lte=end)

    total = Decimal("0")
    priced_events = 0
    unpriced_events = 0
    unpriced_tokens = 0
    per_model: dict[str, dict] = {}

    for event in events.iterator():
        row = per_model.setdefault(
            event.model_name,
            {"model_name": event.model_name, "cost": None, "tokens": 0, "events": 0},
        )
        row["events"] += 1
        row["tokens"] += int(event.total_tokens or 0)

        cost = cost_for_event(event)
        if cost is None:
            unpriced_events += 1
            unpriced_tokens += int(event.total_tokens or 0)
            continue

        priced_events += 1
        total += cost
        row["cost"] = (row["cost"] or Decimal("0")) + cost

    currency = ""
    sample = price_for_any(provider=provider)
    if sample is not None:
        currency = sample.currency

    return {
        "total": total,
        "currency": currency,
        "priced_events": priced_events,
        "unpriced_events": unpriced_events,
        "unpriced_tokens": unpriced_tokens,
        "by_model": sorted(per_model.values(), key=lambda row: row["model_name"]),
    }


def price_for_any(*, provider="gemini"):
    """Valyutani aniqlash uchun ixtiyoriy mavjud snapshot."""
    from aicontrol.models import AIModelPrice

    return AIModelPrice.objects.filter(provider=provider).order_by("-effective_from").first()


def record_price(
    *,
    provider,
    model_name,
    input_per_million,
    output_per_million,
    effective_from,
    currency="USD",
    note="",
    reason="",
    request=None,
    actor=None,
):
    """Yangi narx snapshot'ini yozadi va auditlaydi.

    Mavjud qator tahrirlanmaydi — narx o'zgarsa yangi sana bilan yangi qator.
    """
    from aicontrol.models import AIModelPrice
    from core.audit import record_audit_event

    price = AIModelPrice.objects.create(
        provider=provider,
        model_name=model_name,
        input_per_million=input_per_million,
        output_per_million=output_per_million,
        currency=currency,
        effective_from=effective_from,
        note=note,
    )
    record_audit_event(
        action="ai_price.record",
        request=request,
        actor=actor,
        target=price,
        target_label=f"AI narx: {model_name} ({effective_from})",
        reason=reason.strip(),
        before=None,
        after={
            "input_per_million": str(input_per_million),
            "output_per_million": str(output_per_million),
            "currency": currency,
            "effective_from": str(effective_from),
        },
    )
    return price
