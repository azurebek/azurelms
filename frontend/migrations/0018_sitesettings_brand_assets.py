from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0017_landingpage_cta_background_image_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="logo_image",
            field=models.ImageField(
                blank=True,
                help_text="Oq yoki yorug' fonlarda ishlatiladigan gorizontal wordmark.",
                null=True,
                upload_to="site/logo/primary/",
                verbose_name="Asosiy logo",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="logo_dark_image",
            field=models.ImageField(
                blank=True,
                help_text="Login kabi qorong'i fonlarda ishlatiladi. Bo'sh bo'lsa matnli fallback chiqadi.",
                null=True,
                upload_to="site/logo/dark/",
                verbose_name="Qorong'i fon uchun logo",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="logo_mark_image",
            field=models.ImageField(
                blank=True,
                help_text="Sidebar, messenger, Mini App va sertifikatlar uchun kvadrat belgi.",
                null=True,
                upload_to="site/logo/mark/",
                verbose_name="Ixcham logo belgisi",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="favicon_image",
            field=models.ImageField(
                blank=True,
                help_text="PNG, JPG yoki WebP. Tavsiya: kvadrat 64x64 yoki 128x128.",
                null=True,
                upload_to="site/logo/favicon/",
                verbose_name="Brauzer ikonkasi",
            ),
        ),
    ]
