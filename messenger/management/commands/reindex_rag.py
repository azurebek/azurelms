from django.core.management.base import BaseCommand

from messenger.rag import (
    DEFAULT_CHUNK_OVERLAP_WORDS,
    DEFAULT_CHUNK_WORDS,
    DEFAULT_EMBEDDING_MODEL,
    reindex_lessons,
)


class Command(BaseCommand):
    help = "Lesson contentlarini RAG uchun chunk+embedding qilib qayta indexlaydi."

    def add_arguments(self, parser):
        parser.add_argument("--lesson-id", type=int, action="append", dest="lesson_ids", help="Bitta yoki bir nechta lesson id")
        parser.add_argument("--course-id", type=int, action="append", dest="course_ids", help="Bitta yoki bir nechta course id")
        parser.add_argument("--embedding-model", type=str, default=DEFAULT_EMBEDDING_MODEL)
        parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
        parser.add_argument("--overlap-words", type=int, default=DEFAULT_CHUNK_OVERLAP_WORDS)
        parser.add_argument("--force", action="store_true", help="Kontent o'zgarmagan bo'lsa ham qayta indexing")

    def handle(self, *args, **options):
        stats = reindex_lessons(
            lesson_ids=options.get("lesson_ids"),
            course_ids=options.get("course_ids"),
            embedding_model=options.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
            chunk_words=options.get("chunk_words") or DEFAULT_CHUNK_WORDS,
            overlap_words=options.get("overlap_words") or DEFAULT_CHUNK_OVERLAP_WORDS,
            force=bool(options.get("force")),
        )

        self.stdout.write(self.style.SUCCESS("RAG indexing yakunlandi."))
        self.stdout.write(f"total_lessons={stats['total_lessons']}")
        self.stdout.write(f"indexed_lessons={stats['indexed_lessons']}")
        self.stdout.write(f"skipped_unchanged={stats['skipped_unchanged']}")
        self.stdout.write(f"cleared_lessons={stats['cleared_lessons']}")
        self.stdout.write(f"failed_lessons={stats['failed_lessons']}")
        self.stdout.write(f"total_chunks={stats['total_chunks']}")
        if "vector_synced_chunks" in stats:
            self.stdout.write(f"vector_synced_chunks={stats['vector_synced_chunks']}")
