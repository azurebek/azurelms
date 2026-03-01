from django.db import models

class Plan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ta'rif nomi (Masalan: Oddiy)")
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Oylik to'lov (so'm)")
    description = models.TextField(verbose_name="Qisqa izoh", help_text="Ta'rif haqida qisqacha ma'lumot")
    is_popular = models.BooleanField(default=False, verbose_name="Ommabopmi?")
    button_text = models.CharField(max_length=50, default="Boshlash", verbose_name="Tugma matni")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Ta'rif"
        verbose_name_plural = "Ta'riflar"
        
    def __str__(self):
        return f"{self.name} - {self.price} so'm"


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="features")
    name = models.CharField(max_length=200, verbose_name="Imkoniyat (Masalan: Barcha darslarga kirish)")
    is_included = models.BooleanField(default=True, verbose_name="Kiritilganmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Imkoniyat"
        verbose_name_plural = "Imkoniyatlar"
        
    def __str__(self):
        return self.name
