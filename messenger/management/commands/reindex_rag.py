from django.core.management.base import BaseCommand

from messenger.rag import (
    DEFAULT_CHUNK_OVERLAP_WORDS,
    DEFAULT_CHUNK_WORDS,
    DEFAULT_EMBEDDING_MODEL,
    get_rag_index_status,
    reindex_lessons,
)


class Command(BaseCommand):
    help = "Lesson contentlarini RAG uchun chunk+embedding qilib qayta indexlaydi."

    def add_arguments(self, parser):
        parser.add_argument("--lesson-id", type=int, action="append", dest="lesson_ids", help="Bitta yoki bir nechta lesson id")
        parser.add_argument("--course-id", type=int, action="append", dest="course_ids", help="Bitta yoki bir nechta course id")
        parser.add_argument("--module-id", type=int, action="append", dest="module_ids", help="Bitta yoki bir nechta module id")
        parser.add_argument("--embedding-model", type=str, default=DEFAULT_EMBEDDING_MODEL)
        parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
        parser.add_argument("--overlap-words", type=int, default=DEFAULT_CHUNK_OVERLAP_WORDS)
        parser.add_argument("--force", action="store_true", help="Kontent o'zgarmagan bo'lsa ham qayta indexing")
        parser.add_argument("--status", action="store_true", help="Index statusini ko'rsatadi, qayta indexing qilmaydi")

    def handle(self, *args, **options):
        if options.get("status"):
            status = get_rag_index_status(
                embedding_model=options.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
                chunk_words=options.get("chunk_words") or DEFAULT_CHUNK_WORDS,
                overlap_words=options.get("overlap_words") or DEFAULT_CHUNK_OVERLAP_WORDS,
            )
            self.stdout.write(self.style.SUCCESS("RAG index status."))
            self.stdout.write(f"embedding_model={status['embedding_model']}")
            self.stdout.write(f"eligible_lessons={status['eligible_lessons']}")
            self.stdout.write(f"indexed_lessons={status['indexed_lessons']}")
            self.stdout.write(f"ready_lessons={status['ready_lessons']}")
            self.stdout.write(f"missing_lessons={status['missing_lessons']}")
            self.stdout.write(f"stale_lessons={status['stale_lessons']}")
            self.stdout.write(f"total_chunks={status['total_chunks']}")
            self.stdout.write(f"pgvector_ready={status['pgvector_ready']}")
            return

        stats = reindex_lessons(
            lesson_ids=options.get("lesson_ids"),
            course_ids=options.get("course_ids"),
            module_ids=options.get("module_ids"),
            embedding_model=options.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
            chunk_words=options.get("chunk_words") or DEFAULT_CHUNK_WORDS,
            overlap_words=options.get("overlap_words") or DEFAULT_CHUNK_OVERLAP_WORDS,
            force=bool(options.get("force")),
        )

        self.stdout.write(self.style.SUCCESS("RAG indexing yakunlandi."))
        self.stdout.write(f"total_lessons={stats['total_lessons']}")
        self.stdout.write(f"indexed_lessons={stats['indexed_lessons']}")
        self.stdout.write(f"skipped_unchanged={stats['skipped_unchanged']}")
        self.stdout.write(f"skipped_duplicate={stats['skipped_duplicate']}")
        self.stdout.write(f"cleared_lessons={stats['cleared_lessons']}")
        self.stdout.write(f"failed_lessons={stats['failed_lessons']}")
        self.stdout.write(f"total_chunks={stats['total_chunks']}")
        if "vector_synced_chunks" in stats:
            self.stdout.write(f"vector_synced_chunks={stats['vector_synced_chunks']}")
