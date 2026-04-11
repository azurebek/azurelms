import re
import uuid
from io import BytesIO
from pathlib import Path

from django.db import models
from django.core.files.base import ContentFile
from django_ckeditor_5.fields import CKEditor5Field
from django.db.models import Sum
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils import timezone
from PIL import Image, ImageOps

from .cover_art import GRADIENT_PRESET_CHOICES, build_cover_data_uri


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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Kurs narxi (UZS)")
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True, verbose_name="Kurs rasmi")
    cover_mode = models.CharField(
        max_length=20,
        choices=(
            ("image", "Yuklangan rasm"),
            ("gradient", "Gradient cover"),
        ),
        default="image",
        verbose_name="Cover turi",
        help_text="Agar rasm yuklamasangiz, tanlangan gradient preset avtomatik ishlaydi.",
    )
    gradient_preset = models.CharField(
        max_length=40,
        choices=GRADIENT_PRESET_CHOICES,
        default="aurora_blush",
        verbose_name="Gradient preset",
    )
    gradient_cover_title = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Gradient markaziy yozuvi",
        help_text="Bo'sh qoldirilsa kurs nomi ishlatiladi.",
    )
    gradient_cover_label = models.CharField(
        max_length=48,
        blank=True,
        verbose_name="Gradient kichik badge matni",
        help_text="Bo'sh qoldirilsa kurs darajasi ishlatiladi.",
    )
    preview_video = models.FileField(upload_to='courses/previews/', blank=True, null=True, verbose_name="Tanishtiruv videosi")
    
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    created_at = models.DateTimeField(auto_now_add=True)
    STANDARD_COVER_SIZE = (1200, 1100)

    @property
    def lessons_count(self):
        if hasattr(self, 'annotated_lessons_count'):
            return self.annotated_lessons_count
        return Lesson.objects.filter(module__course=self).count()

    @property
    def students_count(self):
        if hasattr(self, 'annotated_students_count'):
            return self.annotated_students_count
        from cohorts.models import Enrollment
        return Enrollment.objects.filter(cohort__course=self, status='active').values('student').distinct().count()

    @property
    def instructor_display_name(self):
        if not self.instructor:
            return "AzureLMS Instructor"
        full_name = self.instructor.get_full_name().strip()
        return full_name or self.instructor.username

    @property
    def instructor_initial(self):
        return self.instructor_display_name[:1].upper()

    @property
    def cover_display_title(self):
        return (self.gradient_cover_title or "").strip() or self.title

    @property
    def cover_display_label(self):
        return (self.gradient_cover_label or "").strip() or self.get_level_display()

    @property
    def uses_gradient_cover(self):
        return self.cover_mode == "gradient" or not bool(self.thumbnail)

    @property
    def uses_uploaded_image_cover(self):
        return bool(self.thumbnail) and self.cover_mode == "image"

    @property
    def show_cover_text_overlay(self):
        return self.uses_uploaded_image_cover

    @cached_property
    def cover_media_url(self):
        if self.thumbnail and self.cover_mode == "image":
            return self.thumbnail.url
        return build_cover_data_uri(
            title=self.cover_display_title,
            preset_key=self.gradient_preset,
        )

    def _thumbnail_needs_normalization(self):
        if not self.thumbnail or self.cover_mode != "image":
            return False

        if not getattr(self.thumbnail, "_committed", True):
            return True

        if not self.pk:
            return True

        current = type(self).objects.filter(pk=self.pk).values("thumbnail", "cover_mode").first()
        if not current:
            return True

        return current["cover_mode"] != "image"

    def _build_normalized_thumbnail(self):
        if not self.thumbnail:
            return None

        self.thumbnail.open("rb")
        try:
            with Image.open(self.thumbnail) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA")

                if image.mode == "RGBA":
                    background = Image.new("RGB", image.size, "#ffffff")
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")

                image = ImageOps.fit(
                    image,
                    self.STANDARD_COVER_SIZE,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=90, optimize=True)
                buffer.seek(0)

                stem = Path(self.thumbnail.name).stem[:40] or "course-cover"
                filename = f"{stem}-{uuid.uuid4().hex[:8]}.jpg"
                return ContentFile(buffer.getvalue(), name=filename)
        finally:
            self.thumbnail.close()

    def save(self, *args, **kwargs):
        if self._thumbnail_needs_normalization():
            normalized_thumbnail = self._build_normalized_thumbnail()
            if normalized_thumbnail is not None:
                self.thumbnail = normalized_thumbnail

        self.__dict__.pop("cover_media_url", None)
        super().save(*args, **kwargs)

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
            # Use youtube-nocookie.com to prevent "Error 153 Video player configuration error" 
            return f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0"
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


class AssignmentSubmission(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_NEEDS_REVISION = "needs_revision"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Tekshiruv kutilmoqda"),
        (STATUS_APPROVED, "Tasdiqlangan"),
        (STATUS_NEEDS_REVISION, "Qayta ishlash kerak"),
    )

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
        verbose_name="O'quvchi",
    )
    answer_text = models.TextField(blank=True, verbose_name="Javob matni")
    attachment = models.FileField(
        upload_to="assignments/submissions/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Biriktirma",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    teacher_feedback = models.TextField(blank=True, verbose_name="O'qituvchi izohi")
    awarded_xp = models.PositiveIntegerField(default=0, verbose_name="Berilgan XP")
    reviewed_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_assignment_submissions",
        verbose_name="Tekshirgan o'qituvchi",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tekshirilgan vaqt")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-updated_at"]
        verbose_name = "Vazifa topshirig'i"
        verbose_name_plural = "Vazifa topshiriqlari"

    def __str__(self):
        return f"{self.student.username} -> {self.assignment.title}"

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED


class CohortLessonRelease(models.Model):
    cohort = models.ForeignKey("cohorts.Cohort", on_delete=models.CASCADE, related_name="lesson_releases")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="cohort_releases")
    is_released = models.BooleanField(default=True, verbose_name="Ochilganmi")
    released_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="released_lessons",
        verbose_name="Ochgan admin/o'qituvchi",
    )
    released_at = models.DateTimeField(default=timezone.now, verbose_name="Ochilgan vaqt")
    release_note = models.CharField(max_length=255, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cohort", "lesson")
        ordering = ["lesson__module__order", "lesson__order"]
        verbose_name = "Guruh dars accessi"
        verbose_name_plural = "Guruh dars accesslari"

    def __str__(self):
        state = "open" if self.is_released else "locked"
        return f"{self.cohort.name} -> {self.lesson.title} ({state})"


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(
        "cohorts.Enrollment",
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records",
    )
    is_completed = models.BooleanField(default=False, verbose_name="Yakunlanganmi")
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("enrollment", "lesson")
        ordering = ["-last_accessed_at"]
        verbose_name = "Dars progressi"
        verbose_name_plural = "Dars progresslari"
        indexes = [
            models.Index(fields=['enrollment', 'is_completed']),
            models.Index(fields=['last_accessed_at']),
        ]

    def __str__(self):
        return f"{self.enrollment.student.username} -> {self.lesson.title}"


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
    time_limit_minutes = models.PositiveIntegerField(default=30, help_text="Ushbu bo'limni ishlash uchun beriladigan vaqt (daqiqa)")
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

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.lesson and self.exam_section:
            raise ValidationError("Quiz imtihon qismlari bilan birga darsga ham birdaniga biriktirilishi mumkin emas.")
        if not self.lesson and not self.exam_section:
            raise ValidationError("Quiz kamida bitta dars yoki imtihon bo'limiga biriktirilishi shart.")

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizlar"


class Question(models.Model):
    # Questions can belong either to a Quiz or to an ExamSection. 
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    exam_section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)

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


# --- SERTIFIKAT VA IMTIHON NATIJALARI ---

class ExamAttempt(models.Model):
    """
    Tracks a student's live attempt at an Exam.
    Replaces the simple ExamSubmission by tracking time and cheat warnings.
    """
    from django.conf import settings
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts', verbose_name="O'quvchi")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts', verbose_name="Imtihon")
    
    start_time = models.DateTimeField(auto_now_add=True)
    completed_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    blur_warnings = models.PositiveIntegerField(default=0, help_text="Sahifadan chiqib ketishlar soni (Anti-Cheat)")
    
    # Grading fields
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Olingan jami ball")
    passed = models.BooleanField(default=False, verbose_name="O'tdi")
    is_reviewed = models.BooleanField(default=False, verbose_name="O'qituvchi tasdiqlaganmi?")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tekshirilgan vaqt")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_exam_attempts',
        verbose_name="Tekshirgan o'qituvchi",
    )
    review_notes = models.TextField(blank=True, verbose_name="Yakuniy izoh")
    
    def __str__(self):
        return f"{self.student.username} - {self.exam.title} Attempt"
    
    class Meta:
        verbose_name = "Imtihon Urinishi (Attempt)"
        verbose_name_plural = "Imtihon Urinishlari"
        unique_together = ('student', 'exam')

    @property
    def review_status(self):
        if self.is_reviewed:
            return "approved"
        if self.is_completed:
            return "pending"
        return "in_progress"

    @property
    def review_status_label(self):
        labels = {
            "approved": "Tasdiqlangan",
            "pending": "Tekshiruv kutilmoqda",
            "in_progress": "Jarayonda",
        }
        return labels[self.review_status]

    def ensure_section_reviews(self):
        created_reviews = []
        existing_section_ids = set(self.section_reviews.values_list('section_id', flat=True))
        for section in self.exam.sections.all():
            if section.id in existing_section_ids:
                continue
            created_reviews.append(
                ExamSectionReview(
                    attempt=self,
                    section=section,
                    awarded_score=0,
                )
            )
        if created_reviews:
            ExamSectionReview.objects.bulk_create(created_reviews)
        return self.section_reviews.select_related('section').order_by('section__order')

    def prefill_section_scores_from_answers(self):
        self.ensure_section_reviews()
        answer_totals = (
            self.answers
            .filter(question__exam_section__isnull=False)
            .values('question__exam_section')
            .annotate(total_score=Sum('awarded_score'))
        )
        totals_by_section = {
            row['question__exam_section']: row['total_score'] or 0
            for row in answer_totals
        }
        for review in self.section_reviews.select_related('section').all():
            auto_total = totals_by_section.get(review.section_id, 0)
            clamped_score = min(auto_total, review.section.max_score)
            if review.awarded_score != clamped_score:
                review.awarded_score = clamped_score
                review.save(update_fields=['awarded_score', 'updated_at'])

    def calculate_total_score(self):
        """
        Sums up the manual and auto-graded points from all related StudentAnswers,
        determines if passed, and attempts certificate generation.
        """
        aggregation = self.answers.aggregate(total_score=Sum('awarded_score'))
        total = aggregation['total_score'] or 0
        
        # Convert total raw score into percentage based on Exam max score (assuming sum of section max_scores)
        exam_max = sum(sec.max_score for sec in self.exam.sections.all())
        
        if exam_max > 0:
            percentage_score = (total / exam_max) * 100
        else:
            percentage_score = 0
            
        self.score = percentage_score
        self.passed = self.score >= self.exam.passing_score
        self.save()
        
        if self.passed:
            self.check_and_issue_certificate()

    def finalize_review(self, reviewed_by):
        from django.utils import timezone

        self.ensure_section_reviews()
        section_total = self.section_reviews.aggregate(total_score=Sum('awarded_score'))['total_score'] or 0
        exam_max = sum(sec.max_score for sec in self.exam.sections.all())

        if exam_max > 0:
            percentage_score = (section_total / exam_max) * 100
        else:
            percentage_score = 0

        self.score = round(percentage_score, 2)
        self.passed = self.score >= self.exam.passing_score
        self.is_reviewed = True
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=['score', 'passed', 'is_reviewed', 'reviewed_by', 'reviewed_at', 'updated_at'] if hasattr(self, 'updated_at') else ['score', 'passed', 'is_reviewed', 'reviewed_by', 'reviewed_at'])

        certificate = None
        certificate_created = False
        if self.passed:
            certificate, certificate_created = self.check_and_issue_certificate()
        return certificate, certificate_created

    def check_and_issue_certificate(self):
        from users.notification_service import create_notification

        course = self.exam.course
        student = self.student
        
        # Barcha muvaffaqiyatli imtihonlarni olish
        passing_attempts = ExamAttempt.objects.filter(
            student=student,
            exam__course=course,
            passed=True,
            is_reviewed=True,
        )
        
        has_visa = False
        has_final = False
        visa_score = 0
        final_score = 0
        visa_weight = 0
        final_weight = 0
        
        for attempt in passing_attempts:
            if attempt.exam.exam_type == 'visa':
                has_visa = True
                visa_score = attempt.score
                visa_weight = attempt.exam.weight_percentage
            elif attempt.exam.exam_type == 'final':
                has_final = True
                final_score = attempt.score
                final_weight = attempt.exam.weight_percentage
                
        # Agar ikkalasidan ham o'tgan bo'lsa
        if has_visa and has_final:
            total_weight = visa_weight + final_weight
            final_grade = 0
            if total_weight > 0:
                final_grade = int((visa_score * visa_weight + final_score * final_weight) / total_weight)
            else:
                final_grade = int((visa_score + final_score) / 2)
                
            # Sertifikatni yaratish
            existing_certificate = Certificate.objects.filter(student=student, course=course).first()
            certificate_id = (
                existing_certificate.certificate_id
                if existing_certificate
                else f"AZ-{course.id}-{student.id}-{uuid.uuid4().hex[:6].upper()}"
            )
            certificate, created = Certificate.objects.update_or_create(
                student=student,
                course=course,
                defaults={
                    'final_score': final_grade,
                    'certificate_id': certificate_id,
                }
            )
            if created:
                create_notification(
                    recipient=student,
                    title="Sertifikat tayyor",
                    message=(
                        f"{course.title} kursi bo'yicha sertifikatingiz tayyor bo'ldi. "
                        "Uni ko'rishingiz yoki yuklab olishingiz mumkin."
                    ),
                    icon="award",
                    url=reverse('certificate_detail', kwargs={'certificate_id': certificate.certificate_id}),
                    external_key=f"certificate-issued-{certificate.id}",
                )
            return certificate, created
        return None, False


class ExamSectionReview(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='section_reviews',
        verbose_name="Imtihon urinishi",
    )
    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        related_name='attempt_reviews',
        verbose_name="Imtihon bo'limi",
    )
    awarded_score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Berilgan ball")
    feedback = models.TextField(blank=True, verbose_name="O'qituvchi izohi")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Imtihon bo'limi bali"
        verbose_name_plural = "Imtihon bo'limi ballari"
        unique_together = ('attempt', 'section')
        ordering = ['section__order']

    def __str__(self):
        return f"{self.attempt.student.username} - {self.section.title}"


class StudentAnswer(models.Model):
    """
    Granular answer tracking per question for an ExamAttempt.
    Handles Text (Writing), Audio URL (Speaking), or Choice ID (Reading/Listening).
    """
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers')
    
    # Support different answer types based on ExamSection type
    answer_text = models.TextField(blank=True, null=True, help_text="Writing yoki ochiq savollar uchun javob")
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    audio_file_url = models.URLField(blank=True, null=True, help_text="Speaking yozuvi havolasi (S3/DigitalOcean)")
    
    # Grading
    awarded_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="O'qituvchi qo'ygan yoki avto tekshirilgan ball")
    is_graded = models.BooleanField(default=False, help_text="O'qituvchi tekshirib balldan qoniqdimi?")
    
    def __str__(self):
        return f"Answer by {self.attempt.student.username} for Q: {self.question.id}"


# --- QUIZ NATIJALARI ---

class QuizAttempt(models.Model):
    """
    Tracks a student's attempt at a lesson Quiz.
    """
    from django.conf import settings
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Foizdagi ball (0-100)")
    total_correct = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.score}%)"

    class Meta:
        verbose_name = "Quiz Urinishi"
        verbose_name_plural = "Quiz Urinishlari"
        ordering = ['-completed_at']


class QuizAnswer(models.Model):
    """
    Individual answer for each question in a QuizAttempt.
    """
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Q{self.question.id}: {'✅' if self.is_correct else '❌'}"

    class Meta:
        verbose_name = "Quiz Javobi"
        verbose_name_plural = "Quiz Javoblari"
        unique_together = ('attempt', 'question')


class Certificate(models.Model):
    # Dasturni yakunlagandagi sertifikat hujjati
    from django.conf import settings
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_certificates', verbose_name="O'quvchi")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates', verbose_name="Kurs darajasi")
    issued_at = models.DateTimeField(auto_now_add=True, verbose_name="Berilgan sana")
    certificate_id = models.CharField(max_length=50, unique=True, verbose_name="Sertifikat ID")
    final_score = models.PositiveIntegerField(verbose_name="Yakuniy ball")

    def __str__(self):
        return f"{self.student.username} - {self.course.title} Sertifikati"

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"
        unique_together = ('student', 'course')
