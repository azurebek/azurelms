from dataclasses import dataclass, field

from messenger.rag import normalize_lesson_text, retrieve_relevant_chunks
from messenger.access import user_has_active_enrollment


@dataclass(frozen=True)
class RAGContext:
    lesson_context: str = ""
    rag_context: str = ""
    chunks: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    access_note: str = ""


class RAGContextService:
    def build(self, *, user, question: str, context_lesson=None) -> RAGContext:
        lesson_context = ""
        if context_lesson and context_lesson.content:
            lesson_context = normalize_lesson_text(context_lesson.content)

        chunks = retrieve_relevant_chunks(
            user=user,
            question=question,
            context_lesson=context_lesson,
        )
        sources = self.build_sources(chunks)
        return RAGContext(
            lesson_context=lesson_context,
            rag_context=self.render_chunks(chunks),
            chunks=chunks,
            sources=sources,
            access_note=self.access_note(user=user, context_lesson=context_lesson, chunks=chunks),
        )

    def access_note(self, *, user, context_lesson=None, chunks=None) -> str:
        if context_lesson:
            return (
                "Foydalanuvchi hozir shu dars sahifasidan kelgan: "
                f"{context_lesson.module.course.title} > {context_lesson.module.title} > {context_lesson.title}. "
                "Javobda avvalo shu kurs/modul/dars kontekstiga suyan."
            )
        if not user_has_active_enrollment(user):
            return (
                "Foydalanuvchida faol kurs obunasi yo'q. Kurs ichki materiallariga tayangan javob berma; "
                "savolga umumiy, xavfsiz va kursga bog'lanmagan yordam sifatida javob ber."
            )
        if not chunks:
            return "Faol obuna bor, lekin mos RAG manba topilmadi. Aniqlik yetmasa savolni toraytir."
        return "Faol obuna bo'yicha topilgan RAG manbalar ishlatilishi mumkin."

    def build_sources(self, chunks) -> list[dict]:
        sources = []
        for index, chunk in enumerate(chunks or [], start=1):
            sources.append(
                {
                    "number": index,
                    "course_id": chunk.get("course_id"),
                    "course_title": chunk.get("course_title", ""),
                    "module_id": chunk.get("module_id"),
                    "module_title": chunk.get("module_title", ""),
                    "lesson_id": chunk.get("lesson_id"),
                    "lesson_title": chunk.get("lesson_title", ""),
                    "chunk_id": chunk.get("chunk_id"),
                    "score": chunk.get("score"),
                    "label": chunk.get("source_label", ""),
                }
            )
        return sources

    def render_chunks(self, chunks) -> str:
        if not chunks:
            return ""

        context_lines = []
        for index, chunk in enumerate(chunks, start=1):
            context_lines.append(
                f"[Manba {index}] Kurs: {chunk['course_title']} | Modul: {chunk.get('module_title', '-')} | "
                f"Dars: {chunk['lesson_title']} | Score: {chunk['score']}\n"
                f"{chunk['chunk_text']}"
            )
        return "\n\n".join(context_lines)
