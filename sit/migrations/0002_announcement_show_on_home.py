from django.db import migrations, models


def preserve_existing_home_announcements(apps, schema_editor):
    Announcement = apps.get_model("sit", "Announcement")
    Announcement.objects.filter(is_published=True).update(show_on_home=True)


class Migration(migrations.Migration):
    dependencies = [
        ("sit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="show_on_home",
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name="Bosh sahifada ko'rsatilsin",
            ),
        ),
        migrations.RunPython(
            preserve_existing_home_announcements,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
