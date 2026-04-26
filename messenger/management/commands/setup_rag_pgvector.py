from django.core.management.base import BaseCommand, CommandError

from messenger.rag import (
    DEFAULT_EMBEDDING_DIM,
    PGVECTOR_IVFFLAT_LISTS,
    ensure_pgvector_schema,
)


class Command(BaseCommand):
    help = "PostgreSQL uchun pgvector schema (extension/column/index)ni tayyorlaydi va embeddinglarni backfill qiladi."

    def add_arguments(self, parser):
        parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
        parser.add_argument("--lists", type=int, default=PGVECTOR_IVFFLAT_LISTS)
        parser.add_argument("--skip-backfill", action="store_true")

    def handle(self, *args, **options):
        embedding_dim = options.get("embedding_dim") or DEFAULT_EMBEDDING_DIM
        lists = options.get("lists") or PGVECTOR_IVFFLAT_LISTS
        backfill = not bool(options.get("skip_backfill"))

        try:
            result = ensure_pgvector_schema(
                embedding_dim=embedding_dim,
                ivfflat_lists=lists,
                backfill=backfill,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        status = result.get("status")
        if status == "skipped_non_postgres":
            self.stdout.write(self.style.WARNING("PostgreSQL emas: pgvector setup o'tkazib yuborildi."))
            return

        self.stdout.write(self.style.SUCCESS("pgvector setup yakunlandi."))
        self.stdout.write(f"enabled={result.get('enabled')}")
        self.stdout.write(f"created_column={result.get('created_column')}")
        self.stdout.write(f"created_index={result.get('created_index')}")
        self.stdout.write(f"backfilled_chunks={result.get('backfilled_chunks')}")
