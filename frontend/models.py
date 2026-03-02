from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class LandingPage(SingletonModel):
    # Hero Section
    hero_badge = models.CharField(max_length=100, default="2026 yilning eng yaxshi platformasi", verbose_name="Bosh sahifa nishonchasi (Badge)")
    hero_title_start = models.CharField(max_length=100, default="Turk tilini", verbose_name="Sarlavha boshi")
    hero_title_highlight = models.CharField(max_length=100, default="professional", verbose_name="Sarlavha ajratilgan qismi")
    hero_title_end = models.CharField(max_length=100, default="darajada o'rganing", verbose_name="Sarlavha oxiri")
    hero_subtitle = CKEditor5Field(default="Tajribali o'qituvchilar, interaktiv darslar va sertifikatlar bilan turk tilini A1 dan C1 gacha o'rganing.", verbose_name="Kichik matn (Subtitle)", config_name='default')
    
    hero_image = models.ImageField(upload_to='landing/', blank=True, null=True, verbose_name="Asosiy rasm (Hero Image)")
    
    # CTA Section
    cta_title = models.CharField(max_length=100, default="Bugun o'rganishni boshlang!", verbose_name="Bottom CTA Sarlavhasi")
    cta_description = CKEditor5Field(default="Minglab o'quvchilar safiga qo'shiling va turk tilini professional darajada o'rganing.", verbose_name="Bottom CTA matni", config_name='default')

    class Meta:
        verbose_name = "Bosh sahifa sozlamasi"
        verbose_name_plural = "1. Bosh sahifa sozlamalari"

    def __str__(self):
        return "Bosh sahifa dizayn matnlari"


class Statistic(models.Model):
    value = models.CharField(max_length=50, help_text="Masalan: 5,000+", verbose_name="Qiymati")
    label = models.CharField(max_length=100, help_text="Masalan: Faol o'quvchilar", verbose_name="Nomi")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Bosh sahifa statistikasi"
        verbose_name_plural = "2. Bosh sahifa statistikalari"

    def __str__(self):
        return f"{self.value} - {self.label}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ism-familiya")
    role = models.CharField(max_length=100, verbose_name="Kasbi/Darajasi", default="Talaba")
    text = models.TextField(verbose_name="Fikr matni")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="Baho (1-5)")
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True, verbose_name="Rasm")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    
    class Meta:
        verbose_name = "Fikr"
        verbose_name_plural = "3. O'quvchilar fikrlari"

    def __str__(self):
        return self.name


class AboutPage(SingletonModel):
    hero_title_start = models.CharField(max_length=100, default="Sifatli ta'lim orqali", verbose_name="Sarlavha boshi")
    hero_title_highlight = models.CharField(max_length=100, default="maqsad sari", verbose_name="Sarlavha ajratilgan qismi")
    hero_subtitle = CKEditor5Field(default="AzureLMS — turk tilini zamonaviy, interaktiv va qulay usulda o'rganishni xohlovchilar uchun...", verbose_name="Kichik matn (Subtitle)", config_name='default')
    
    mission_title = models.CharField(max_length=200, default="Bizning maqsadimiz (Missiya)", verbose_name="Missiya Sarlavhasi")
    mission_text = CKEditor5Field(verbose_name="Missiya matni", blank=True, config_name='default')
    
    vision_title = models.CharField(max_length=200, default="Bizning qarashimiz (Vision)", verbose_name="Vision Sarlavhasi")
    vision_text = CKEditor5Field(verbose_name="Vision matni", blank=True, config_name='default')
    
    class Meta:
        verbose_name = "Biz haqimizda sozlamasi"
        verbose_name_plural = "4. Biz haqimizda sozlamalari"

    def __str__(self):
        return "Biz haqimizda matnlari"


class AboutStatistic(models.Model):
    value = models.CharField(max_length=50, verbose_name="Qiymati")
    label = models.CharField(max_length=100, verbose_name="Nomi")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Biz haqimizda statistikasi"
        verbose_name_plural = "5. Biz haqimizda statistikalari"

    def __str__(self):
        return f"{self.value} - {self.label}"


class TeamMember(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ism-familiya")
    role_1 = models.CharField(max_length=100, verbose_name="Asosiy rol (Masalan: O'qituvchi)")
    role_2 = models.CharField(max_length=100, verbose_name="Qo'shimcha rol (Masalan: CEO)")
    bio = CKEditor5Field(verbose_name="Qisqa ma'lumot", config_name='default')
    avatar = models.ImageField(upload_to='team/', blank=True, null=True, verbose_name="Rasm")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Jamoa a'zosi"
        verbose_name_plural = "6. Jamoa a'zolari"

    def __str__(self):
        return self.name
