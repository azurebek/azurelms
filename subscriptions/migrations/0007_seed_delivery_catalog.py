from django.db import migrations


def seed_catalog(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    Feature = apps.get_model("subscriptions", "PlanFeature")
    Policy = apps.get_model("aicontrol", "AIPlanPolicy")
    alias = schema_editor.connection.alias
    packages = (
        ("economic", "Economic", 89000, 60, 50000, 300000),
        ("standard", "Standard", 259000, 8, 100000, 800000),
        ("intensive", "Intensive", 399000, 3, 200000, 1500000),
    )
    for order, (code, name, price, capacity, short, weekly) in enumerate(packages, 1):
        plan, created = Plan.objects.using(alias).get_or_create(
            code=code,
            defaults={
                "name": name, "price": price, "cohort_capacity_limit": capacity,
                "description": "To'liq curriculum, jonli darslar va AzureAI.",
                "is_popular": code == "standard", "is_available_for_purchase": False,
                "order": order, "button_text": f"{name}'ni tanlash",
            },
        )
        # Owner-created rows (including their policies) are never reinterpreted.
        if not created:
            continue
        Policy.objects.using(alias).create(
            plan=plan, token_limit_5h=short, token_limit_weekly=weekly, is_active=True,
        )
        for rank, name in enumerate((
            f"Maksimum {capacity} kishilik guruh", "To'liq curriculum va dars materiallari",
            "Jonli darslar", "Vazifalar, testlar va imtihonlar", "AzureAI", "Sertifikat",
        )):
            Feature.objects.using(alias).create(plan=plan, name=name, order=rank)


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0006_plan_catalog"),
        ("aicontrol", "0008_aimodelprice"),
    ]
    # Do not delete catalog/payment history on reverse.
    operations = [migrations.RunPython(seed_catalog, migrations.RunPython.noop)]
