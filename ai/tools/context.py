from dataclasses import dataclass, field

from django.db.models import Count
from django.utils.html import strip_tags

from cohorts.models import Enrollment
from courses.models import Assignment, AssignmentSubmission, Course, Lesson, LessonProgress, Quiz, QuizAttempt


@dataclass(frozen=True)
class ToolContext:
    rendered: str = ""
    used_tools: list[str] = field(default_factory=list)


class ToolContextService:
    """Builds deterministic app-side context for agent skills."""

    MAX_EXCERPT_CHARS = 700
    # SIT katalogi o'sganda prompt cheksiz kattalashmasligi uchun chegaralar.
    SIT_MAX_UNIVERSITIES = 25
    SIT_MAX_PROGRAMS_PER_UNIVERSITY = 8
    SIT_MAX_GUIDES = 12

    def build(self, *, request, skill) -> ToolContext:
        sections = []
        used_tools = []

        for tool_slug in getattr(skill, "tool_slugs", ()):
            renderer = getattr(self, f"_render_{tool_slug}", None)
            if not renderer:
                continue
            text = renderer(request=request)
            if not text:
                continue
            used_tools.append(tool_slug)
            sections.append(f"[tool:{tool_slug}]\n{text}")

        return ToolContext(rendered="\n\n".join(sections), used_tools=used_tools)

    def _render_lesson_context(self, *, request) -> str:
        lesson = getattr(request, "context_lesson", None)
        if not lesson:
            return ""

        lesson = (
            Lesson.objects.select_related("module", "module__course")
            .filter(id=lesson.id)
            .first()
            or lesson
        )
        assignments = list(Assignment.objects.filter(lesson=lesson).order_by("id")[:5])
        quizzes = list(
            Quiz.objects.filter(lesson=lesson)
            .annotate(question_count=Count("questions"))
            .order_by("id")[:5]
        )
        lines = [
            f"Course: {lesson.module.course.title}",
            f"Module: {lesson.module.title}",
            f"Lesson: {lesson.title}",
            f"Lesson order: {lesson.order}",
            f"Has video: {'yes' if lesson.video_url else 'no'}",
        ]
        content_excerpt = self._clean_excerpt(lesson.content)
        if content_excerpt:
            lines.append(f"Lesson notes excerpt: {content_excerpt}")
        if assignments:
            lines.append("Assignments:")
            for assignment in assignments:
                lines.append(f"- {assignment.title}: {self._clean_excerpt(assignment.description, 220)}")
        if quizzes:
            lines.append("Quizzes:")
            for quiz in quizzes:
                lines.append(f"- {quiz.title}: {quiz.question_count} questions")
        return "\n".join(lines)

    def _render_homework_context(self, *, request) -> str:
        lesson = getattr(request, "context_lesson", None)
        student = getattr(request, "student", None)
        if not lesson:
            return ""

        assignments = list(Assignment.objects.filter(lesson=lesson).order_by("id")[:6])
        if not assignments:
            return ""

        submissions = {}
        if student:
            submissions = {
                submission.assignment_id: submission
                for submission in AssignmentSubmission.objects.filter(
                    student=student,
                    assignment_id__in=[assignment.id for assignment in assignments],
                ).select_related("reviewed_by")
            }

        lines = [f"Homework for lesson: {lesson.title}"]
        for assignment in assignments:
            lines.append(f"- Assignment: {assignment.title}")
            description = self._clean_excerpt(assignment.description, 260)
            if description:
                lines.append(f"  Requirement: {description}")
            submission = submissions.get(assignment.id)
            if submission:
                lines.append(f"  Student submission status: {submission.get_status_display()}")
                if submission.answer_text:
                    lines.append(f"  Student draft excerpt: {self._clean_excerpt(submission.answer_text, 260)}")
                if submission.teacher_feedback:
                    lines.append(f"  Teacher feedback: {self._clean_excerpt(submission.teacher_feedback, 220)}")
            else:
                lines.append("  Student submission status: not submitted")
        return "\n".join(lines)

    def _render_quiz_context(self, *, request) -> str:
        lesson = getattr(request, "context_lesson", None)
        if not lesson:
            return ""

        quizzes = list(
            Quiz.objects.filter(lesson=lesson)
            .prefetch_related("questions__choices")
            .order_by("id")[:3]
        )
        if not quizzes:
            return ""

        lines = [f"Existing quiz context for lesson: {lesson.title}"]
        for quiz in quizzes:
            lines.append(f"- Quiz: {quiz.title}")
            for question in list(quiz.questions.all())[:4]:
                lines.append(f"  Question: {self._clean_excerpt(question.text, 180)}")
                choices = [choice.text for choice in question.choices.all()[:4]]
                if choices:
                    lines.append(f"  Choices: {', '.join(choices)}")
        lines.append("Do not expose stored correct-answer flags from existing quizzes.")
        return "\n".join(lines)

    def _render_student_progress(self, *, request) -> str:
        student = getattr(request, "student", None)
        if not student:
            return ""

        enrollments = list(
            Enrollment.objects.filter(student=student)
            .select_related("cohort", "cohort__course")
            .order_by("-joined_at", "-id")[:4]
        )
        if not enrollments:
            return "Student has no enrollments yet."

        lines = ["Student progress snapshot:"]
        for enrollment in enrollments:
            course = enrollment.cohort.course
            total_lessons = Lesson.objects.filter(module__course=course).count()
            completed_lessons = LessonProgress.objects.filter(
                enrollment=enrollment,
                lesson__module__course=course,
                is_completed=True,
            ).count()
            percent = round((completed_lessons / total_lessons) * 100) if total_lessons else 0
            pending_homework = AssignmentSubmission.objects.filter(
                student=student,
                assignment__lesson__module__course=course,
                status=AssignmentSubmission.STATUS_PENDING,
            ).count()
            latest_quiz = (
                QuizAttempt.objects.filter(student=student, quiz__lesson__module__course=course)
                .select_related("quiz")
                .order_by("-completed_at")
                .first()
            )
            lines.append(
                f"- {course.title}: status {enrollment.get_effective_status_display()}, "
                f"{completed_lessons}/{total_lessons} lessons completed ({percent}%)."
            )
            if pending_homework:
                lines.append(f"  Pending homework reviews: {pending_homework}")
            if latest_quiz:
                lines.append(f"  Latest quiz: {latest_quiz.quiz.title}, score {latest_quiz.score}%")
        return "\n".join(lines)

    def _render_course_navigator(self, *, request) -> str:
        student = getattr(request, "student", None)
        if not student:
            return ""

        enrollments = list(
            Enrollment.objects.filter(student=student)
            .select_related("cohort", "cohort__course")
            .order_by("-joined_at", "-id")[:4]
        )
        if not enrollments:
            courses = list(Course.objects.filter(is_active=True).order_by("-created_at")[:5])
            if not courses:
                return "No active courses are available."
            lines = ["Student has no enrollments. Active public courses:"]
            for course in courses:
                lines.append(f"- {course.title}: {course.get_level_display()}, {course.lessons_count} lessons")
            return "\n".join(lines)

        lines = ["Course navigation snapshot:"]
        for enrollment in enrollments:
            course = enrollment.cohort.course
            lessons = list(
                Lesson.objects.filter(module__course=course)
                .select_related("module")
                .order_by("module__order", "order", "id")
            )
            completed_ids = set(
                LessonProgress.objects.filter(
                    enrollment=enrollment,
                    lesson__module__course=course,
                    is_completed=True,
                ).values_list("lesson_id", flat=True)
            )
            next_lesson = next((lesson for lesson in lessons if lesson.id not in completed_ids), None)
            lines.append(f"- Course: {course.title} | Cohort: {enrollment.cohort.name}")
            lines.append(f"  Access status: {enrollment.get_effective_status_display()}")
            if next_lesson:
                lines.append(f"  Suggested next lesson by progress: {next_lesson.module.title} -> {next_lesson.title}")
            elif lessons:
                lines.append("  All lessons appear completed.")
            else:
                lines.append("  No lessons found in this course.")
        return "\n".join(lines)

    def _render_sit_catalog(self, *, request) -> str:
        """SIT (Study in Turkey) katalogining tekshirilgan snapshot'i.

        Faqat `is_published=True` yozuvlar chiqadi — nashr uchun `source_url` va
        `last_verified_on` majburiy bo'lgani sabab bu ma'lumot manbasi tekshirilgan.
        Embedding/RAG emas, deterministik so'rov: narx yoki muddat "taxmin" qilinmaydi.
        """
        from django.db.models import Case, IntegerField, When

        from sit.models import KnowledgeArticle, University
        from sit.selectors import advisor_catalog_queryset

        status_rank = Case(
            When(admission_status=University.AdmissionStatus.OPEN, then=0),
            When(admission_status=University.AdmissionStatus.SOON, then=1),
            default=2,
            output_field=IntegerField(),
        )
        universities = list(
            advisor_catalog_queryset()
            .annotate(_status_rank=status_rank)
            .order_by("_status_rank", "order", "name")[: self.SIT_MAX_UNIVERSITIES]
        )
        total_published = University.objects.published().count()

        if not universities:
            return (
                "SIT katalogida hozircha nashr etilgan universitet yo'q. "
                "Universitet, kontrakt narxi yoki qabul muddati haqida MA'LUMOT BERMA va TO'QIMA — "
                "halol ayt: katalog hali to'ldirilmoqda, va foydalanuvchini mutaxassis bilan bog'lanishga taklif qil."
            )

        lines = [
            "SIT (Study in Turkey) tekshirilgan katalogi — universitet, kontrakt narxi va qabul muddati uchun "
            "YAGONA ruxsat etilgan manba.",
            f"Nashr etilgan universitetlar: {total_published} ta (quyida {len(universities)} tasi).",
            "",
        ]

        for university in universities:
            deadline = university.admission_deadline.strftime("%d.%m.%Y") if university.admission_deadline else "aniqlanmagan"
            lines.append(
                f"- {university.name} | {university.city} | {university.get_university_type_display()} "
                f"| qabul: {university.get_admission_status_display()} | muddat: {deadline} "
                f"| eng arzon kontrakt: {university.display_tuition_from} "
                f"| tillar: {university.language_summary} | darajalar: {university.degree_summary}"
            )

            programs = []
            for faculty in getattr(university, "visible_faculties", []):
                for program in getattr(faculty, "visible_programs", []):
                    programs.append(
                        f"{program.name} ({faculty.name}, {program.get_degree_level_display()}, "
                        f"{program.get_language_display()}, {program.duration}, {program.display_tuition})"
                    )
            if programs:
                shown = programs[: self.SIT_MAX_PROGRAMS_PER_UNIVERSITY]
                suffix = f" (+{len(programs) - len(shown)} ta yana)" if len(programs) > len(shown) else ""
                lines.append(f"  dasturlar: {'; '.join(shown)}{suffix}")

            preparation = [
                f"{course.language} — {course.display_tuition} / {course.duration}"
                for course in getattr(university, "visible_preparation_courses", [])
            ]
            if preparation:
                lines.append(f"  til tayyorlov: {'; '.join(preparation)}")

        if total_published > len(universities):
            lines.append(f"... yana {total_published - len(universities)} ta universitet katalogda bor (bu ro'yxatga sig'madi).")

        guides = list(
            KnowledgeArticle.objects.published().order_by("order", "-published_on")[: self.SIT_MAX_GUIDES]
        )
        if guides:
            lines.append("")
            lines.append("Portaldagi qo'llanmalar: " + "; ".join(guide.title for guide in guides))

        lines.append("")
        lines.append(
            "QAT'IY QOIDALAR: (1) Faqat yuqoridagi ro'yxatdagi universitet, dastur, narx va muddatni ayt — "
            "ro'yxatda yo'q universitetni, narxni yoki sanani TO'QIMA. (2) Ma'lumot yetishmasa halol ayt va "
            "foydalanuvchini mutaxassis bilan bog'lanishga yo'naltir. (3) Viza, denklik va rasmiy qabul "
            "qoidalarida yakuniy huquqiy maslahat BERMA — umumiy yo'nalish ber va rasmiy manbaga/mutaxassisga "
            "yo'naltir. (4) Narx va muddat o'zgarishi mumkinligini eslat."
        )
        return "\n".join(lines)

    def _render_web_search(self, *, request) -> str:
        # DIQQAT: matnda '(Manba N)' yozish yoki manba ro'yxatini qo'shish TAQIQLANADI —
        # platforma manbalarni alohida UI elementida o'zi ko'rsatadi (web_search SKILL.md).
        return (
            "Foydalanuvchi savoli jonli/yangi ma'lumot talab qiladi. Agar qidiruv natijalari mavjud bo'lsa, "
            "faktlarni AVVALO shularga tayangan holda ber va o'zing biladigandek tabiiy yoz — "
            "javob matnida '(Manba 1)' kabi belgilar yozma, oxiriga 'Manbalar:' ro'yxati qo'shma. "
            "Bir nechta manba mos kelsa birlashtir, ziddiyat bo'lsa buni aniq ayt. "
            "Agar jonli natija bo'lmasa, sana/narx/statistikani TO'QIMA — halol ayt: eng so'nggi "
            "ma'lumotni tekshira olmayotganingni bildir va savolni aniqlashtirishni taklif qil."
        )

    def _clean_excerpt(self, value: str | None, limit: int | None = None) -> str:
        limit = limit or self.MAX_EXCERPT_CHARS
        text = strip_tags(value or "")
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."
