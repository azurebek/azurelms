from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('courses', '0023_exam_action_gate')]
    operations = [migrations.AddField(
        model_name='examattempt', name='review_revision',
        field=models.PositiveBigIntegerField(default=0, editable=False),
    )]
