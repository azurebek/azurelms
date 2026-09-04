"""Seed yozgan guruh o'lchami qatorini olib tashlaydi.

`0007` har tarifga `Maksimum N kishilik guruh` degan `PlanFeature` yozgan
edi. Egasi standartni o'zgartirganda o'sha matn eskirib qolardi va sotuv
sahifasi bir sonni, checkout esa boshqasini ko'rsatardi. Endi da'vo
`Plan.cohort_capacity_limit` dan hosil qilinadi.

Faqat seed yozgan naqshdagi qator o'chiriladi — egasi o'z so'zi bilan
yozgan matnga tegilmaydi.
"""

import re

from django.db import migrations

SEEDED = re.compile(r"^Maksimum \d+ kishilik guruh$")


def drop_seeded_claim(apps, schema_editor):
    Feature = apps.get_model("subscriptions", "PlanFeature")
    alias = schema_editor.connection.alias
    stale = [
        feature.pk
        for feature in Feature.objects.using(alias).all()
        if SEEDED.match(feature.name or "")
    ]
    Feature.objects.using(alias).filter(pk__in=stale).delete()


def noop(apps, schema_editor):
    """Ortga qaytarish matnni tiklamaydi — u endi raqamdan chiqadi."""


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0007_seed_delivery_catalog")]

    operations = [migrations.RunPython(drop_seeded_claim, noop)]
