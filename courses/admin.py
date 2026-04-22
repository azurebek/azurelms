from django.contrib import admin
from django.utils.html import format_html, format_html_join
import nested_admin
from .models import (
    Course,
    Module,
    Lesson,
    LessonProgress,
    Assignment,
    AssignmentSubmission,
    CohortLessonRelease,
    Exam,
    ExamSection,
    ExamSectionAttemptState,
    Quiz,
    Question,
    Choice,
    ExamAttempt,
    StudentAnswer,
    ExamSectionReview,
    ReadingPassage,
    ReadingTask,
    ReadingItem,
    ReadingOption,
    ReadingAcceptedAnswer,
    ReadingResponse,
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


class NestedReadingAcceptedAnswerInline(nested_admin.NestedTabularInline):
    model = ReadingAcceptedAnswer
    extra = 1


class NestedReadingOptionInline(nested_admin.NestedTabularInline):
    model = ReadingOption
    extra = 2
    fk_name = "item"
    fields = ("label", "option_key", "text", "order", "is_correct")


class NestedReadingSharedOptionInline(nested_admin.NestedTabularInline):
    model = ReadingOption
    extra = 3
    fk_name = "task"
    fields = ("label", "option_key", "text", "order")


class NestedReadingItemInline(nested_admin.NestedStackedInline):
    model = ReadingItem
    extra = 1
    inlines = [NestedReadingOptionInline, NestedReadingAcceptedAnswerInline]


class NestedReadingTaskInline(nested_admin.NestedStackedInline):
    model = ReadingTask
    extra = 1
    inlines = [NestedReadingSharedOptionInline, NestedReadingItemInline]
    fields = (
        "title",
        ("task_type", "display_variant"),
        "passage",
        "instructions",
        "body",
        ("question_from", "question_to"),
        ("max_selections_per_item", "max_words_per_answer"),
        ("allow_option_reuse", "allow_review_flag"),
        ("case_sensitive_grading", "punctuation_sensitive"),
        "metadata",
        "order",
    )


class NestedReadingPassageInline(nested_admin.NestedStackedInline):
    model = ReadingPassage
    extra = 1
    fields = ("title", "body", "paragraph_labels", "order")


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
                    (
                        "certificate_requires_all_assignments_approved",
                        "certificate_min_lesson_completion_percent",
                        "certificate_min_attendance_percent",
                    ),
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
        image_url = obj.cover_media_url if obj else build_cover_data_uri(title=title, preset_key="midnight_wave")
        return format_html(
            '<div style="max-width: 360px; border-radius: 24px; overflow: hidden; border: 1px solid rgba(17, 36, 60, 0.08); box-shadow: 0 18px 40px rgba(10, 55, 97, 0.14);">'
            '<img src="{}" alt="Cover preview" style="display:block; width:100%; height:auto;" />'
            "</div>",
            image_url,
        )

    @admin.display(description="Tayyor gradient presetlar")
    def gradient_gallery(self, obj):
        sample_title = obj.cover_display_title if obj else "GPT-5.3-Codex"
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
                    build_cover_data_uri(sample_title, preset["key"]),
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


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "assignment",
        "course_title",
        "status",
        "submitted_at",
        "reviewed_at",
    )
    search_fields = (
        "student__username",
        "student__email",
        "assignment__title",
        "assignment__lesson__title",
    )
    list_filter = ("status", "assignment__lesson__module__course")
    readonly_fields = ("submitted_at", "updated_at")
    actions = ("mark_pending", "mark_approved", "mark_needs_revision")

    @admin.display(description="Kurs")
    def course_title(self, obj):
        return obj.assignment.lesson.module.course.title

    @admin.action(description="Tekshiruvga qaytarish (Pending)")
    def mark_pending(self, request, queryset):
        updated = queryset.update(
            status=AssignmentSubmission.STATUS_PENDING,
            reviewed_by=None,
            reviewed_at=None,
        )
        self.message_user(request, f"{updated} ta submission pending holatga o'tkazildi.")

    @admin.action(description="Tasdiqlash (Approved)")
    def mark_approved(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(
            status=AssignmentSubmission.STATUS_APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{updated} ta submission tasdiqlandi.")

    @admin.action(description="Qayta ishlash kerak (Needs revision)")
    def mark_needs_revision(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(
            status=AssignmentSubmission.STATUS_NEEDS_REVISION,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{updated} ta submission revision holatiga o'tdi.")

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if obj.status == AssignmentSubmission.STATUS_PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        else:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CohortLessonRelease)
class CohortLessonReleaseAdmin(admin.ModelAdmin):
    list_display = ("cohort", "course_title", "lesson", "is_released", "released_at", "released_by")
    list_filter = ("is_released", "cohort", "lesson__module__course")
    search_fields = ("cohort__name", "lesson__title", "lesson__module__course__title")
    actions = ("mark_released", "mark_locked")

    @admin.display(description="Kurs")
    def course_title(self, obj):
        return obj.lesson.module.course.title

    @admin.action(description="Tanlangan darslarni ochish")
    def mark_released(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(
            is_released=True,
            released_by=request.user,
            released_at=timezone.now(),
        )
        self.message_user(request, f"{updated} ta dars ochildi.")

    @admin.action(description="Tanlangan darslarni qulflash")
    def mark_locked(self, request, queryset):
        updated = queryset.update(is_released=False)
        self.message_user(request, f"{updated} ta dars qulflandi.")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("student_username", "course_title", "lesson", "is_completed", "last_accessed_at")
    list_filter = ("is_completed", "lesson__module__course")
    search_fields = ("enrollment__student__username", "lesson__title", "lesson__module__course__title")

    @admin.display(description="O'quvchi")
    def student_username(self, obj):
        return obj.enrollment.student.username

    @admin.display(description="Kurs")
    def course_title(self, obj):
        return obj.lesson.module.course.title

# --- Imtihonlar ---

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'course',
        'exam_type',
        'weight_percentage',
        'passing_score',
        'max_attempts',
        'prerequisite_exam',
    )
    list_filter = ('course', 'exam_type')
    fields = (
        'course',
        'title',
        'exam_type',
        ('weight_percentage', 'passing_score', 'max_attempts'),
        'prerequisite_exam',
        (
            'requires_all_assignments_approved',
            'minimum_lesson_completion_percent',
            'minimum_attendance_percent',
        ),
    )
    inlines = [ExamSectionInline] # Imtihon ichida ro'yxat (Reading, Listening) qo'shish

@admin.register(ExamSection)
class ExamSectionAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'exam', 'section_type', 'max_score', 'order', 'reading_task_count', 'reading_item_count')
    list_filter = ('exam', 'section_type')
    inlines = [NestedReadingPassageInline, NestedReadingTaskInline]
    fields = (
        "exam",
        "title",
        ("section_type", "order"),
        "instructions",
        "reading_text",
        "media_url",
        ("max_score", "time_limit_minutes"),
    )

    @admin.display(description="Reading tasklar")
    def reading_task_count(self, obj):
        return obj.reading_tasks.count()

    @admin.display(description="Reading itemlar")
    def reading_item_count(self, obj):
        return ReadingItem.objects.filter(task__section=obj).count()

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


class ReadingResponseInline(admin.StackedInline):
    model = ReadingResponse
    extra = 0
    fields = (
        "item",
        "task_summary",
        "selected_option",
        "selected_option_ids",
        "text_answer",
        "is_flagged_for_review",
        "awarded_score",
        "is_graded",
        "updated_at",
    )
    readonly_fields = ("item", "task_summary", "updated_at")

    @admin.display(description="Task")
    def task_summary(self, obj):
        return f"{obj.item.task.get_task_type_display()} / {obj.item.task.title or obj.item.task.section.title}"

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'exam',
        'attempt_number',
        'review_state',
        'score',
        'passed',
        'blur_warnings',
        'is_completed',
        'completed_time',
    )
    list_filter = ('passed', 'is_completed', 'is_reviewed', 'exam__course', 'exam')
    search_fields = ('student__username', 'student__email', 'exam__title')
    inlines = [ExamSectionReviewInline, StudentAnswerInline, ReadingResponseInline]
    readonly_fields = ('attempt_number', 'start_time', 'blur_warnings', 'completed_time', 'reviewed_at', 'reviewed_by')
    
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


@admin.register(ReadingPassage)
class ReadingPassageAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "order")
    list_filter = ("section__exam",)
    search_fields = ("title", "section__title", "section__exam__title")


@admin.register(ReadingTask)
class ReadingTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "task_type", "display_variant", "order")
    list_filter = ("task_type", "display_variant", "section__exam")
    search_fields = ("title", "section__title", "section__exam__title")


@admin.register(ReadingItem)
class ReadingItemAdmin(admin.ModelAdmin):
    list_display = ("display_label", "task", "points", "order")
    list_filter = ("task__task_type", "task__section__exam")
    search_fields = ("short_label", "task__title", "task__section__title")


@admin.register(ReadingOption)
class ReadingOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "label", "option_key", "parent_summary", "is_correct", "order")
    list_filter = ("task__task_type", "item__task__task_type")
    search_fields = ("text", "label", "option_key")

    @admin.display(description="Parent")
    def parent_summary(self, obj):
        if obj.item_id:
            return f"Item: {obj.item}"
        return f"Task: {obj.task}"


@admin.register(ReadingAcceptedAnswer)
class ReadingAcceptedAnswerAdmin(admin.ModelAdmin):
    list_display = ("value", "item", "order")
    list_filter = ("item__task__task_type",)
    search_fields = ("value", "item__short_label", "item__task__title")


@admin.register(ReadingResponse)
class ReadingResponseAdmin(admin.ModelAdmin):
    list_display = ("attempt", "item", "is_flagged_for_review", "awarded_score", "is_graded", "updated_at")
    list_filter = ("item__task__task_type", "item__task__section__exam", "is_flagged_for_review", "is_graded")
    search_fields = ("attempt__student__username", "item__short_label", "item__task__title")


@admin.register(ExamSectionAttemptState)
class ExamSectionAttemptStateAdmin(admin.ModelAdmin):
    list_display = ("attempt", "section", "started_at", "updated_at")
    list_filter = ("section__exam", "section__section_type")
    search_fields = ("attempt__student__username", "section__title")
