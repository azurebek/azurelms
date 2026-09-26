from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0021_remindersettings_teacher_review_hour')]

    operations = [
        migrations.AddField(
            model_name='customuser', name='ai_preferences_version',
            field=models.PositiveBigIntegerField(default=0, editable=False),
        ),
    ]
