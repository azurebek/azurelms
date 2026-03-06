from django.contrib import admin
import nested_admin
from .models import Course, Module, Lesson, Assignment, Exam, ExamSection, Quiz, Question, Choice

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
    list_display = ('title', 'is_active', 'created_at') # Jadvalda ko'rinadigan ustunlar
    list_filter = ('is_active',) # O'ng tomondagi filtr
    search_fields = ('title', 'description') # Qidiruv qutisi
    inlines = [ModuleInline] # Kursning ichidayoq Modullarni qo'shib ketish mumkin!

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

# --- Exam Attempts & Grading ---
from .models import ExamAttempt, StudentAnswer

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

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'passed', 'blur_warnings', 'is_completed', 'completed_time')
    list_filter = ('passed', 'is_completed', 'exam__course', 'exam')
    search_fields = ('student__username', 'student__email', 'exam__title')
    inlines = [StudentAnswerInline]
    readonly_fields = ('start_time', 'blur_warnings')
    
    actions = ['recalculate_scores']
    
    @admin.action(description="Tanlangan urinishlar ballarini qaytadan hisoblash")
    def recalculate_scores(self, request, queryset):
        for attempt in queryset:
            attempt.calculate_total_score()
        self.message_user(request, "Ballar muvaffaqiyatli qayta hisoblandi va sertifikatlar yangilandi.")

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