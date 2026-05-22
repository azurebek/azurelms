from django.db import migrations


def seed_default_plans(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    PlanFeature = apps.get_model("subscriptions", "PlanFeature")

    if Plan.objects.exists():
        return

    plan_specs = [
        {
            "name": "Starter",
            "price": 99000,
            "description": "Asosiy kurslar va progress kuzatuvi uchun boshlang'ich obuna.",
            "is_popular": False,
            "button_text": "Boshlash",
            "order": 1,
            "features": [
                "Public kurslarga kirish",
                "Video darslar va materiallar",
                "Progress kuzatuvi",
            ],
        },
        {
            "name": "Pro",
            "price": 199000,
            "description": "Kurslar, imtihonlar va sertifikat flow uchun asosiy oylik obuna.",
            "is_popular": True,
            "button_text": "Pro bilan boshlash",
            "order": 2,
            "features": [
                "Barcha asosiy kurslarga kirish",
                "Exam va sertifikat talablari",
                "Mentor izohlari va qo'llab-quvvatlash",
            ],
        },
        {
            "name": "Premium",
            "price": 299000,
            "description": "Intensiv o'qish, ustuvor yordam va kengaytirilgan sertifikat tayyorgarligi.",
            "is_popular": False,
            "button_text": "Premium tanlash",
            "order": 3,
            "features": [
                "Pro imkoniyatlarining barchasi",
                "Ustuvor tekshiruv va feedback",
                "Qo'shimcha imtihon tayyorgarligi",
            ],
        },
    ]

    for plan_spec in plan_specs:
        features = plan_spec.pop("features")
        plan = Plan.objects.create(**plan_spec)
        PlanFeature.objects.bulk_create(
            [
                PlanFeature(plan=plan, name=feature, is_included=True, order=index)
                for index, feature in enumerate(features, start=1)
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0003_promocampaign_promocode_promoredemption"),
    ]

    operations = [
        migrations.RunPython(seed_default_plans, migrations.RunPython.noop),
    ]
