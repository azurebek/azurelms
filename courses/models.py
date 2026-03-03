import re
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class Course(models.Model):
    # Kursning asosiy ma'lumotlari
    from django.conf import settings
    
    LEVEL_CHOICES = (
        ('beginner', 'Boshlang\'ich (A1-A2)'),
        ('intermediate', 'O\'rta (B1-B2)'),
        ('advanced', 'Mukammal (C1-C2)'),
    )
    title = models.CharField(max_length=200, verbose_name="Kurs nomi")
    description = CKEditor5Field(verbose_name="Kurs tavsifi", config_name='default')
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='courses', verbose_name="O'qituvchi")
    
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner', verbose_name="Daraja")
    duration = models.PositiveIntegerField(default=20, help_text="Kursning taxminiy davomiyligi (soatlarda)")
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True, verbose_name="Kurs rasmi")
    preview_video = models.FileField(upload_to='courses/previews/', blank=True, null=True, verbose_name="Tanishtiruv videosi")
    
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def lessons_count(self):
        return Lesson.objects.filter(module__course=self).count()

    @property
    def students_count(self):
        # We can count unique users enrolled in active cohorts for this course
        from cohorts.models import Enrollment
        return Enrollment.objects.filter(cohort__course=self).values('student').distinct().count()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"


class Module(models.Model):
    # Kurs ichidagi bo'limlar (Masalan: "1-Oy: Asoslar")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200, verbose_name="Modul nomi")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    def __str__(self):
        return f"{self.course.title} | {self.title}"

    class Meta:
        ordering = ['order']
        verbose_name = "Modul"
        verbose_name_plural = "Modullar"


class Lesson(models.Model):
    # Asosiy dars ma'lumotlari
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200, verbose_name="Dars mavzusi")
    video_url = models.URLField(blank=True, null=True, help_text="YouTube Unlisted havolasi")

    # AI RAG va chiroyli dizayn uchun maydon!
    content = CKEditor5Field(blank=True, null=True, config_name='default',
                             help_text="Dars qoidalari, matnlari va tushuntirishlar")

    order = models.PositiveIntegerField(default=0, verbose_name="Dars tartibi")
    xp_reward = models.PositiveIntegerField(default=10, help_text="Darsga kirgani uchun beriladigan XP")

    @property
    def embed_video_url(self):
        if not self.video_url:
            return None
        # Extract video ID from youtube.com/watch?v=ID or youtu.be/ID
        match = re.search(r'(?:v=|youtu\.be/|youtube\.com/embed/)([^&?]+)', self.video_url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/embed/{video_id}"
        return self.video_url

    def __str__(self):
        return f"{self.module.title} -> {self.title}"

    class Meta:
        ordering = ['order']
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"


class Assignment(models.Model):
    # Darsga biriktirilgan vazifalar
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200, verbose_name="Vazifa nomi")
    description = CKEditor5Field(verbose_name="Vazifa sharti", config_name='default')
    max_xp = models.PositiveIntegerField(default=50, verbose_name="Maksimal XP")

    def __str__(self):
        return f"Vazifa: {self.title}"

    class Meta:
        verbose_name = "Vazifa"
        verbose_name_plural = "Vazifalar"


# --- IMTIHON (EXAM) TIZIMI ---

class Exam(models.Model):
    EXAM_TYPES = (
        ('visa', 'Visa (Orali\'q Imtihon)'),
        ('final', 'Final (Yakuniy Imtihon)'),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200, verbose_name="Imtihon nomi (Masalan: A1 Final)")
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPES, verbose_name="Imtihon turi")
    weight_percentage = models.PositiveIntegerField(help_text="Umumiy bahodagi o'rni (Masalan: Visa=40, Final=60)")
    passing_score = models.PositiveIntegerField(default=60, help_text="O'tish uchun kerakli minimal foiz")

    def __str__(self):
        return f"{self.course.title} - {self.get_exam_type_display()}"

    class Meta:
        verbose_name = "Imtihon"
        verbose_name_plural = "Imtihonlar"


class ExamSection(models.Model):
    SECTION_TYPES = (
        ('reading', 'O\'qish (Reading)'),
        ('listening', 'Eshitish (Listening)'),
        ('writing', 'Yozish (Writing)'),
        ('speaking', 'Gapirish (Speaking)'),
        ('grammar_quiz', 'Grammatika va Lug\'at (Test)'),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200, verbose_name="Bo'lim nomi")
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)

    # Boyitilgan matnlar
    instructions = CKEditor5Field(verbose_name="O'quvchiga shartni tushuntirish", config_name='default')
    reading_text = CKEditor5Field(blank=True, null=True, config_name='default', verbose_name="Reading uchun matn")

    media_url = models.URLField(blank=True, null=True, help_text="Listening uchun YouTube/Audio link")
    max_score = models.PositiveIntegerField(help_text="Ushbu bo'lim uchun beriladigan maksimal ball")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    def __str__(self):
        return f"{self.exam.title} | {self.get_section_type_display()}"

    class Meta:
        ordering = ['order']
        verbose_name = "Imtihon Bo'limi"
        verbose_name_plural = "Imtihon Bo'limlari"


# --- QUIZ TIZIMI ---

class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name="Quiz nomi")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True,
                               help_text="Dars ichidagi quiz bo'lsa tanlang")
    exam_section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name='quizzes', null=True,
                                     blank=True, help_text="Imtihon ichidagi test bo'lsa tanlang")
    xp_reward = models.PositiveIntegerField(default=20, help_text="To'g'ri ishlagani uchun beriladigan XP")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizlar"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')

    # Savol matnini ham CKEditor qildik, mabodo savol ichida rasm yoki qalin yozuv kerak bo'lib qolsa.
    text = CKEditor5Field(verbose_name="Savol matni", config_name='default')
    points = models.PositiveIntegerField(default=1, verbose_name="Savol bali")

    def __str__(self):
        return str(self.text)[:50]  # Savolning bir qismini ko'rsatadi

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200, verbose_name="Variant matni")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javobmi?")

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"