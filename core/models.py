"""Core domen modellari.

Hozircha bitta model bor: namuna kontent seederining proveniyensiyasi.

**Nega kerak bo'ldi.** `core/content_seed.py` avval yozuvni sarlavha yoki
slug bo'yicha tanirdi. Ko'rsatiladigan identifikator esa egalik dalili emas:
agar bazada aynan shu nomli **haqiqiy** kurs bo'lsa, `get_or_create` uni
namuna deb qabul qilardi va `--wipe` uni modul, dars, imtihon va topshiriqlari
bilan birga o'chirib yuborardi. Bu PR #53 dagi Codex reviewining topilmasi.

**Nega fayl emas, jadval.** Iz aynan o'zi tavsiflayotgan baza bilan birga
yashashi kerak. Baza nusxalansa yoki boshqa mashinaga ko'chirilsa, iz ham
u bilan ketadi; yonidagi JSON fayl esa qolib ketardi va `--wipe` boshqa
bazadagi yozuvlarni o'chirishga urinardi.
"""

from django.db import models


class SeededRecord(models.Model):
    """Namuna kontent seeder **o'zi yaratgan** yozuvning izi.

    Faqat ildiz obyektlar belgilanadi (kurs, guruh, maqola, teg). Modul,
    dars, test va vazifa kursga cascade bilan bog'langan, ya'ni ular alohida
    iz talab qilmaydi.
    """

    #: `"courses.Course"` ko'rinishidagi model yorlig'i. `ContentType` emas,
    #: chunki bu yerda generic relation kerak emas va yorliq migratsiyalar
    #: orasida barqarorroq o'qiladi.
    model_label = models.CharField(max_length=100)
    object_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seeder yaratgan yozuv"
        verbose_name_plural = "Seeder yaratgan yozuvlar"
        constraints = [
            models.UniqueConstraint(
                fields=["model_label", "object_id"],
                name="core_seededrecord_unique_target",
            ),
        ]
        indexes = [models.Index(fields=["model_label"])]

    def __str__(self):
        return f"{self.model_label}#{self.object_id}"
