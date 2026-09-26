from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('courses', '0020_studentanswer_audio_key_and_more')]

    operations = [
        migrations.CreateModel(
            name='ExamResultPublication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payload', models.JSONField(editable=False)),
                ('published_at', models.DateTimeField(auto_now=True)),
                ('attempt', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result_publication', to='courses.examattempt')),
            ],
        ),
    ]
