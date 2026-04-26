from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_attendance_status(apps, schema_editor):
    Attendance = apps.get_model('cohorts', 'Attendance')
    for row in Attendance.objects.all().only('id', 'is_present'):
        row.status = 'present' if row.is_present else 'absent'
        row.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('cohorts', '0003_alter_paymentreceipt_receipt_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='status',
            field=models.CharField(
                choices=[('present', 'Keldi'), ('absent', 'Kelmadi'), ('partial', 'Qisman kirdi')],
                default='present',
                max_length=10,
                verbose_name='Davomat holati',
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='xp_awarded',
            field=models.PositiveIntegerField(default=0, verbose_name='Berilgan XP'),
        ),
        migrations.AddField(
            model_name='attendance',
            name='marked_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='marked_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='marked_attendance_records',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Belgilagan xodim',
            ),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.RunPython(migrate_attendance_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='attendance',
            name='is_present',
        ),
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together={('enrollment', 'lesson', 'date')},
        ),
    ]
