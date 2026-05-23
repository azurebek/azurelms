from dataclasses import dataclass, field

from messenger.rag import normalize_lesson_text, retrieve_relevant_chunks


@dataclass(frozen=True)
class RAGContext:
    lesson_context: str = ""
    rag_context: str = ""
    chunks: list[dict] = field(default_factory=list)


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
        return RAGContext(
            lesson_context=lesson_context,
            rag_context=self.render_chunks(chunks),
            chunks=chunks,
        )

    def render_chunks(self, chunks) -> str:
        if not chunks:
            return ""

        context_lines = []
        for index, chunk in enumerate(chunks, start=1):
            context_lines.append(
                f"[Manba {index}] Kurs: {chunk['course_title']} | Dars: {chunk['lesson_title']} | Score: {chunk['score']}\n"
                f"{chunk['chunk_text']}"
            )
        return "\n\n".join(context_lines)
