from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('library', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='libraryresource', name='edit_revision',
            field=models.PositiveBigIntegerField(default=0, editable=False),
        ),
    ]
