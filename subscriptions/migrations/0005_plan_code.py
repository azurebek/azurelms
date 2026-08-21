"""Planga barqaror `code` qo'shadi (A4).

Kirish huquqi shu kod bo'yicha aniqlanadi, `name` bo'yicha emas — ko'rsatiladigan
nomni o'zgartirish huquqni jimgina buzmasligi kerak.

Uch bosqich bitta faylda: maydon avval `unique` siz qo'shiladi, mavjud qatorlar
nomdan to'ldiriladi, keyin `unique` qo'yiladi. Bir qadamda qilinsa uchala mavjud
plan ham bo'sh kod bilan qolib, `unique` darhol buzilardi.
"""

from django.db import migrations, models
from django.utils.text import slugify


def backfill_codes(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    seen = set()
    for plan in Plan.objects.all().order_by("id"):
        base = slugify(plan.name)[:40] or f"plan-{plan.pk}"
        code = base
        suffix = 2
        while code in seen:
            code = f"{base[:36]}-{suffix}"
            suffix += 1
        seen.add(code)
        plan.code = code
        plan.save(update_fields=["code"])


def clear_codes(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    Plan.objects.all().update(code="")


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_seed_default_subscription_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="code",
            field=models.SlugField(
                blank=True, default="", max_length=40, verbose_name="Kod",
                help_text="Kirish huquqi uchun barqaror identifikator. Nomdan mustaqil.",
            ),
        ),
        migrations.RunPython(backfill_codes, clear_codes),
        migrations.AlterField(
            model_name="plan",
            name="code",
            field=models.SlugField(
                blank=True, default="", max_length=40, unique=True, verbose_name="Kod",
                help_text="Kirish huquqi uchun barqaror identifikator. Nomdan mustaqil.",
            ),
        ),
    ]
