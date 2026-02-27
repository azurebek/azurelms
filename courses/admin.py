from django.contrib import admin
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

# --- Quizlar va Savollar ---

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'exam_section', 'xp_reward')
    list_filter = ('lesson__module__course', 'exam_section__exam')
    search_fields = ('title',)
    inlines = [QuestionInline] # Quiz ichida Savollarni qo'shib ketish

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('get_short_text', 'quiz', 'points')
    inlines = [ChoiceInline] # Savolning ichidayoq uning Variantlarini qo'shish!

    def get_short_text(self, obj):
        return str(obj.text)[:50] + "..." # Matn juda uzun bo'lib ketmasligi uchun
    get_short_text.short_description = 'Savol matni'