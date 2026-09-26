import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0004_operationalsettings_backup_retention_days')]
    operations = [migrations.AddField(
        model_name='operationalsettings',
        name='checkout_quote_minutes',
        field=models.PositiveIntegerField(
            default=30,
            validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(1440)],
            verbose_name='Checkout summa tasdig‘i muddati (daqiqa)',
            help_text='1–1440 daqiqa. Keyingi so‘rovdan amal qiladi, ochiq formalar ham yangi muddat bilan tekshiriladi. Narx yuborishda baribir qayta tekshiriladi.',
        ),
    )]
