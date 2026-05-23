from django.core.management.base import BaseCommand

from messenger.models import AIMemoryFact
from messenger.rag import DEFAULT_EMBEDDING_MODEL, embed_texts


class Command(BaseCommand):
    help = "AI memory faktlarini embedding bilan qayta indexlaydi."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, default=None)
        parser.add_argument("--batch-size", type=int, default=50)
        parser.add_argument("--embedding-model", type=str, default=DEFAULT_EMBEDDING_MODEL)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        batch_size = max(1, int(options.get("batch_size") or 50))
        embedding_model = options.get("embedding_model") or DEFAULT_EMBEDDING_MODEL
        queryset = AIMemoryFact.objects.filter(status=AIMemoryFact.STATUS_ACTIVE).order_by("id")

        if options.get("user_id"):
            queryset = queryset.filter(user_id=options["user_id"])
        if not options.get("force"):
            queryset = queryset.filter(embedding=[])

        updated = 0
        buffer = []
        for fact in queryset.iterator(chunk_size=batch_size):
            buffer.append(fact)
            if len(buffer) >= batch_size:
                updated += self._embed_batch(buffer, embedding_model=embedding_model)
                buffer = []

        if buffer:
            updated += self._embed_batch(buffer, embedding_model=embedding_model)

        self.stdout.write(self.style.SUCCESS(f"{updated} ta AI memory embedding yangilandi."))

    def _embed_batch(self, facts, *, embedding_model):
        vectors = embed_texts(
            [f"{fact.category}: {fact.value}" for fact in facts],
            embedding_model=embedding_model,
        )
        updated = 0
        for fact, vector in zip(facts, vectors):
            if not vector:
                continue
            fact.embedding = vector
            fact.embedding_model = embedding_model
            fact.embedding_dim = len(vector)
            fact.save(update_fields=["embedding", "embedding_model", "embedding_dim", "updated_at"])
            updated += 1
        return updated
