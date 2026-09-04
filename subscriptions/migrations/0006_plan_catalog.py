from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0005_plan_code")]

    operations = [
        migrations.AddField(
            model_name="plan", name="is_available_for_purchase",
            field=models.BooleanField(default=True, verbose_name="Yangi sotuvga ochiq"),
        ),
        migrations.AddField(
            model_name="plan", name="cohort_capacity_limit",
            field=models.PositiveSmallIntegerField(
                null=True, blank=True, verbose_name="Guruhning maksimal sig'imi",
                help_text="Legacy tarifda bo'sh. Delivery chegarasi; konkret guruh kichikroq bo'lishi mumkin.",
            ),
        ),
    ]
