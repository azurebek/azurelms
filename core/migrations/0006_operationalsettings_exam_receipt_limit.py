import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0005_operationalsettings_checkout_quote_minutes')]

    operations = [
        migrations.AddField(
            model_name='operationalsettings', name='exam_receipt_limit',
            field=models.PositiveIntegerField(default=1000,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10000)],
                verbose_name='Imtihon amallari jurnali sig‘imi',
                help_text='Har o‘quvchi–imtihon uchun 1–10000 ta oxirgi texnik tasdiq. Keyingi muvaffaqiyatli amaldan qo‘llanadi. Eski tasdiqlar chiqariladi, javob va baholar o‘chirilmaydi; eski oynada holatni yangilash kerak bo‘lishi mumkin.'),
        ),
    ]
