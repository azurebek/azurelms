from django.contrib import admin
from django.utils.html import format_html, format_html_join
import nested_admin
from .models import (
    Course,
    Module,
    Lesson,
    Assignment,
    Exam,
    ExamSection,
    Quiz,
    Question,
    Choice,
    ExamAttempt,
    StudentAnswer,
    ExamSectionReview,
    Certificate,
)
from .cover_art import GRADIENT_PRESETS, build_cover_data_uri

# ==========================================
# 1. INLINES (Ichma-ich ochiladigan oynalar)
# ==========================================

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1  # Yangi kurs ochganda nechta bo'sh modul qutisi chiqib turishi

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

class AssignmentInline(admin.StackedInline):
    model = Assignment
    extra = 1

class ExamSectionInline(admin.StackedInline):
    model = ExamSection
    extra = 1

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3  # Savol qo'shayotganda avtomatik 3 ta variant yozish qutisi chiqadi

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

# --- Quiz uchun Nested Inlines (1 sahifada Quiz + Savol + Variant) ---

class NestedChoiceInline(nested_admin.NestedTabularInline):
    model = Choice
    extra = 4
    min_num = 2  # Kamida 2 ta variant bo'lishi kerak

class NestedQuestionInline(nested_admin.NestedStackedInline):
    model = Question
    extra = 1
    inlines = [NestedChoiceInline]


# ==========================================
# 2. ASOSIY ADMIN PANEL SOZLAMALARI
# ==========================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'cover_mode', 'gradient_preset', 'is_active', 'created_at') # Jadvalda ko'rinadigan ustunlar
    list_filter = ('is_active',) # O'ng tomondagi filtr
    search_fields = ('title', 'description') # Qidiruv qutisi
    inlines = [ModuleInline] # Kursning ichidayoq Modullarni qo'shib ketish mumkin!
    readonly_fields = ('cover_preview', 'gradient_gallery')
    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {
                "fields": (
                    "title",
                    "description",
                    "instructor",
                    ("level", "duration", "price"),
                    "is_active",
                )
            },
        ),
        (
            "Kurs cover'i",
            {
                "description": "Rasm yuklashingiz yoki tayyor gradient preset ishlatishingiz mumkin.",
                "fields": (
                    ("cover_mode", "gradient_preset"),
                    ("gradient_cover_title", "gradient_cover_label"),
                    "thumbnail",
                    "cover_preview",
                    "gradient_gallery",
                    "preview_video",
                ),
            },
        ),
    )

    @admin.display(description="Hozirgi cover preview")
    def cover_preview(self, obj):
        title = obj.cover_display_title if obj else "Turk tili A2"
        image_url = obj.cover_media_url if obj else build_cover_data_uri(title=title, preset_key="midnight_wave", kicker="A1-A2")
        return format_html(
            '<div style="max-width: 360px; border-radius: 24px; overflow: hidden; border: 1px solid rgba(17, 36, 60, 0.08); box-shadow: 0 18px 40px rgba(10, 55, 97, 0.14);">'
            '<img src="{}" alt="Cover preview" style="display:block; width:100%; height:auto;" />'
            "</div>",
            image_url,
        )

    @admin.display(description="Tayyor gradient presetlar")
    def gradient_gallery(self, obj):
        sample_title = obj.cover_display_title if obj else "GPT-5.3-Codex"
        sample_label = obj.cover_display_label if obj else "A1-A2"
        cards = format_html_join(
            "",
            (
                '<div style="width: 148px;">'
                '<div style="overflow:hidden; border-radius:18px; box-shadow:0 12px 28px rgba(10, 55, 97, 0.12); border:1px solid rgba(17, 36, 60, 0.06);">'
                '<img src="{}" alt="{}" style="display:block; width:100%; height:auto;" />'
                "</div>"
                '<div style="margin-top:8px; font-size:12px; font-weight:700; color:#1c3551;">{}</div>'
                "</div>"
            ),
            (
                (
                    build_cover_data_uri(sample_title, preset["key"], kicker=sample_label),
                    preset["label"],
                    preset["label"],
                )
                for preset in GRADIENT_PRESETS
            ),
        )
        return format_html(
            '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(148px, 1fr)); gap:14px;">{}</div>',
            cards,
        )

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title',)
    inlines = [LessonInline] # Modulning ichida Darslarni qo'shib ketish mumkin

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order', 'xp_reward')
    list_filter = ('module__course', 'module')
    search_fields = ('title',)
    inlines = [AssignmentInline] # Darsning ichida Vazifalarni qo'shish

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'max_xp')
    search_fields = ('title',)
    list_filter = ('lesson__module__course',)

# --- Imtihonlar ---

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'exam_type', 'weight_percentage', 'passing_score')
    list_filter = ('course', 'exam_type')
    inlines = [ExamSectionInline] # Imtihon ichida ro'yxat (Reading, Listening) qo'shish

@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'section_type', 'max_score', 'order')
    list_filter = ('exam', 'section_type')

class StudentAnswerInline(admin.StackedInline):
    model = StudentAnswer
    extra = 0
    fields = ('question', 'get_question_type', 'answer_text', 'audio_file_url', 'selected_choice', 'is_correct_choice', 'awarded_score', 'is_graded')
    readonly_fields = ('question', 'get_question_type', 'answer_text', 'audio_file_url', 'selected_choice', 'is_correct_choice')
    
    @admin.display(description='Bo\'lim turi')
    def get_question_type(self, obj):
        if obj.question.exam_section:
            return obj.question.exam_section.get_section_type_display()
        return "Noma'lum"
    
    @admin.display(description='Test yechimi to\'g\'rimi?')
    def is_correct_choice(self, obj):
        if obj.selected_choice:
            return obj.selected_choice.is_correct
        return None


class ExamSectionReviewInline(admin.TabularInline):
    model = ExamSectionReview
    extra = 0
    fields = ('section', 'section_max_score', 'awarded_score', 'feedback', 'updated_at')
    readonly_fields = ('section', 'section_max_score', 'updated_at')

    @admin.display(description='Max ball')
    def section_max_score(self, obj):
        return obj.section.max_score

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'review_state', 'score', 'passed', 'blur_warnings', 'is_completed', 'completed_time')
    list_filter = ('passed', 'is_completed', 'is_reviewed', 'exam__course', 'exam')
    search_fields = ('student__username', 'student__email', 'exam__title')
    inlines = [ExamSectionReviewInline, StudentAnswerInline]
    readonly_fields = ('start_time', 'blur_warnings', 'completed_time', 'reviewed_at', 'reviewed_by')
    
    actions = ['prepare_reviews', 'approve_selected_attempts', 'recalculate_scores']

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('student', 'exam', 'exam__course', 'reviewed_by')
        if request.user.is_superuser:
            return qs
        return qs.filter(exam__course__instructor=request.user)

    def get_inline_instances(self, request, obj=None):
        if obj:
            obj.ensure_section_reviews()
        return super().get_inline_instances(request, obj)

    @admin.display(description='Review holati')
    def review_state(self, obj):
        return obj.review_status_label

    @admin.action(description="Tanlangan urinishlar uchun bo'lim ballarini tayyorlash")
    def prepare_reviews(self, request, queryset):
        count = 0
        for attempt in queryset:
            attempt.ensure_section_reviews()
            attempt.prefill_section_scores_from_answers()
            count += 1
        self.message_user(request, f"{count} ta urinish uchun bo'lim ballari tayyorlandi.")

    @admin.action(description="Tanlangan urinishlarni tasdiqlash va sertifikatni yaratish")
    def approve_selected_attempts(self, request, queryset):
        approved_count = 0
        certificate_count = 0
        for attempt in queryset:
            if not attempt.is_completed:
                continue
            certificate, created = attempt.finalize_review(reviewed_by=request.user)
            approved_count += 1
            if created and certificate:
                certificate_count += 1
        self.message_user(
            request,
            f"{approved_count} ta urinish tasdiqlandi. {certificate_count} ta yangi sertifikat yaratildi.",
        )
    
    @admin.action(description="Tanlangan urinishlar ballarini qaytadan hisoblash")
    def recalculate_scores(self, request, queryset):
        for attempt in queryset:
            if attempt.is_reviewed:
                attempt.finalize_review(reviewed_by=request.user)
            else:
                attempt.prefill_section_scores_from_answers()
        self.message_user(request, "Ballar muvaffaqiyatli yangilandi.")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'final_score', 'certificate_id', 'issued_at')
    list_filter = ('course', 'issued_at')
    search_fields = ('student__username', 'student__email', 'course__title', 'certificate_id')

# --- Quizlar va Savollar ---

@admin.register(Quiz)
class QuizAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'lesson', 'exam_section', 'xp_reward', 'get_questions_count')
    list_filter = ('lesson__module__course', 'exam_section__exam')
    search_fields = ('title',)
    inlines = [NestedQuestionInline]  # 1 sahifada: Quiz → Savol → Variant

    @admin.display(description='Savollar soni')
    def get_questions_count(self, obj):
        return obj.questions.count()

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('get_short_text', 'quiz', 'points')
    inlines = [ChoiceInline]  # Savolning ichidayoq uning Variantlarini qo'shish!

    @admin.display(description='Savol matni')
    def get_short_text(self, obj):
        text_str = str(obj.text)
        return text_str[:50] + "..." if len(text_str) > 50 else text_str
