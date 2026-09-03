import hashlib
import html
import json
import logging
import math
import os
import re
from typing import Iterable

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Max, Q
from django.utils.html import strip_tags
from google import genai
from google.genai import types

from aicontrol.supply import (
    estimate_tokens,
    fingerprint_request,
    reconcile_supply,
    reserve_supply,
    SupplyDuplicate,
)
from cohorts.models import Enrollment, enrollment_active_access_q
from courses.models import Course, Lesson, Module
from .models import LessonRAGChunk


logger = logging.getLogger(__name__)


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "gemini-embedding-001").strip()
DEFAULT_EMBEDDING_DIM = max(64, int(os.getenv("RAG_EMBEDDING_DIM", "768")))
DEFAULT_CHUNK_WORDS = max(80, int(os.getenv("RAG_CHUNK_WORDS", "180")))
DEFAULT_CHUNK_OVERLAP_WORDS = max(10, int(os.getenv("RAG_CHUNK_OVERLAP_WORDS", "40")))
DEFAULT_TOP_K = max(1, int(os.getenv("RAG_TOP_K", "4")))
MAX_CANDIDATES = max(50, int(os.getenv("RAG_MAX_CANDIDATES", "600")))
MAX_CHUNKS_PER_LESSON = max(1, int(os.getenv("RAG_MAX_CHUNKS_PER_LESSON", "2")))
MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.15"))
USE_PGVECTOR = _env_bool("RAG_USE_PGVECTOR", True)
PGVECTOR_IVFFLAT_LISTS = max(10, int(os.getenv("RAG_PGVECTOR_LISTS", "100")))
MAX_PGVECTOR_CANDIDATES = max(50, int(os.getenv("RAG_PGVECTOR_MAX_CANDIDATES", "240")))

_PGVECTOR_READY_CACHE = None


def _text_sha(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _vector_literal(values):
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


def _chunk_table_name():
    return LessonRAGChunk._meta.db_table


def reset_pgvector_cache():
    global _PGVECTOR_READY_CACHE
    _PGVECTOR_READY_CACHE = None


def is_pgvector_ready(refresh=False):
    global _PGVECTOR_READY_CACHE

    if not USE_PGVECTOR:
        _PGVECTOR_READY_CACHE = False
        return False

    if _PGVECTOR_READY_CACHE is not None and not refresh:
        return _PGVECTOR_READY_CACHE

    if connection.vendor != "postgresql":
        _PGVECTOR_READY_CACHE = False
        return False

    table_name = _chunk_table_name()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            extension_exists = bool(cursor.fetchone()[0])
            if not extension_exists:
                _PGVECTOR_READY_CACHE = False
                return False

            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = %s
                      AND column_name = 'embedding_vector'
                )
                """,
                [table_name],
            )
            has_column = bool(cursor.fetchone()[0])
            _PGVECTOR_READY_CACHE = has_column
            return has_column
    except Exception:
        logger.exception("pgvector readiness check failed")
        _PGVECTOR_READY_CACHE = False
        return False


def _sync_pgvector_embeddings(rows):
    if not rows:
        return 0
    if not is_pgvector_ready():
        return 0

    updates = []
    for chunk_id, embedding in rows:
        if not embedding:
            continue
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except Exception:
                continue
        updates.append((_vector_literal(embedding), chunk_id))

    if not updates:
        return 0

    table_name = _chunk_table_name()
    sql = f'UPDATE "{table_name}" SET embedding_vector = %s::vector WHERE id = %s'
    with connection.cursor() as cursor:
        cursor.executemany(sql, updates)
    return len(updates)


def sync_all_pgvector_embeddings(embedding_model: str = DEFAULT_EMBEDDING_MODEL, batch_size: int = 300):
    if not is_pgvector_ready():
        return 0

    synced_count = 0
    buffer = []
    queryset = (
        LessonRAGChunk.objects.filter(embedding_model=embedding_model)
        .values_list("id", "embedding")
        .order_by("id")
    )
    for row in queryset.iterator(chunk_size=batch_size):
        buffer.append(row)
        if len(buffer) >= batch_size:
            synced_count += _sync_pgvector_embeddings(buffer)
            buffer = []

    if buffer:
        synced_count += _sync_pgvector_embeddings(buffer)

    return synced_count


def ensure_pgvector_schema(
    *,
    embedding_dim: int = DEFAULT_EMBEDDING_DIM,
    ivfflat_lists: int = PGVECTOR_IVFFLAT_LISTS,
    backfill: bool = True,
):
    result = {
        "enabled": False,
        "created_column": False,
        "created_index": False,
        "backfilled_chunks": 0,
    }

    if connection.vendor != "postgresql":
        result["status"] = "skipped_non_postgres"
        return result

    table_name = _chunk_table_name()
    index_name = f"{table_name}_embedding_vector_ivfflat_idx"
    embedding_dim = max(64, int(embedding_dim))
    ivfflat_lists = max(10, int(ivfflat_lists))

    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = 'embedding_vector'
            )
            """,
            [table_name],
        )
        has_vector_column = bool(cursor.fetchone()[0])

        if not has_vector_column:
            cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN embedding_vector vector({embedding_dim})')
            result["created_column"] = True
        else:
            cursor.execute(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = %s
                  AND n.nspname = current_schema()
                  AND a.attname = 'embedding_vector'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """,
                [table_name],
            )
            row = cursor.fetchone()
            current_type = row[0] if row else ""
            expected_type = f"vector({embedding_dim})"
            if current_type and current_type != expected_type:
                raise RuntimeError(
                    f"embedding_vector turi {current_type}, kutilgani {expected_type}. "
                    "Dimension o'zgarishi uchun alohida migration/DDL kerak."
                )

        cursor.execute(
            f'CREATE INDEX IF NOT EXISTS "{index_name}" '
            f'ON "{table_name}" USING ivfflat (embedding_vector vector_cosine_ops) '
            f"WITH (lists = {ivfflat_lists})"
        )
        result["created_index"] = True
        cursor.execute(f'ANALYZE "{table_name}"')

    reset_pgvector_cache()
    result["enabled"] = is_pgvector_ready(refresh=True)
    if backfill and result["enabled"]:
        result["backfilled_chunks"] = sync_all_pgvector_embeddings()

    return result


def normalize_lesson_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = strip_tags(raw_text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def split_into_word_chunks(text: str, max_words: int = DEFAULT_CHUNK_WORDS, overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS):
    normalized = (text or "").strip()
    if not normalized:
        return []

    words = normalized.split()
    if not words:
        return []

    max_words = max(40, int(max_words))
    overlap_words = max(0, min(int(overlap_words), max_words - 1))

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words).strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "token_count": max(1, len(chunk_words)),
                    "chunk_hash": _text_sha(chunk_text),
                }
            )
            chunk_index += 1

        if end >= len(words):
            break

        start = end - overlap_words
        if start < 0:
            start = 0

    return chunks


def _build_embedding_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY mavjud emas, embedding yaratib bo'lmadi.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=max(1, int(getattr(settings, "GEMINI_EMBEDDING_TIMEOUT_MS", 8000))),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _embedding_cache_key(
    text: str,
    *,
    embedding_model: str,
    embedding_dim: int = DEFAULT_EMBEDDING_DIM,
) -> str:
    return f"emb:{_text_sha(f'{embedding_model}:{embedding_dim}:{text}')}"


def _embedding_input_hash(texts: Iterable[str]) -> str:
    payload = json.dumps(list(texts), ensure_ascii=False, separators=(",", ":"))
    return _text_sha(payload)


def _embedding_supply_request_key(
    *,
    request_key: str | None,
    call_type: str,
    embedding_model: str,
    embedding_dim: int,
    input_hash: str,
) -> str:
    return fingerprint_request(
        request_key or "embedding",
        call_type,
        embedding_model,
        embedding_dim,
        input_hash,
        daily=True,
    )


def embed_texts(
    texts: Iterable[str],
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    *,
    call_type: str = "rag_embedding",
    user=None,
    request_key: str | None = None,
):
    from django.core.cache import cache

    content_list = [text for text in texts if (text or "").strip()]
    if not content_list:
        return []

    results = [None] * len(content_list)
    to_embed = []
    to_embed_indices = []

    for i, text in enumerate(content_list):
        cache_key = _embedding_cache_key(text, embedding_model=embedding_model)
        cached = cache.get(cache_key)
        if cached is not None:
            results[i] = cached
        else:
            to_embed.append(text)
            to_embed_indices.append(i)

    if to_embed:
        max_inputs = int(getattr(settings, "GEMINI_EMBEDDING_MAX_INPUTS", 64))
        max_input_chars = int(
            getattr(settings, "GEMINI_EMBEDDING_MAX_INPUT_CHARS", 8000)
        )
        max_batch_chars = int(
            getattr(settings, "GEMINI_EMBEDDING_MAX_BATCH_CHARS", 64000)
        )
        if len(to_embed) > max_inputs:
            raise ValueError(f"Embedding batch input cap oshdi: {len(to_embed)} > {max_inputs}")
        if any(len(text) > max_input_chars for text in to_embed):
            raise ValueError("Embedding input char cap oshdi.")
        if sum(len(text) for text in to_embed) > max_batch_chars:
            raise ValueError("Embedding batch char cap oshdi.")
        input_hash = _embedding_input_hash(to_embed)
        supply_request_key = _embedding_supply_request_key(
            request_key=request_key,
            call_type=call_type,
            embedding_model=embedding_model,
            embedding_dim=DEFAULT_EMBEDDING_DIM,
            input_hash=input_hash,
        )
        reservation = reserve_supply(
            request_key=supply_request_key,
            call_type=call_type,
            provider="gemini",
            model_name=embedding_model,
            user=user,
            reserved_requests=1,
            reserved_tokens=estimate_tokens("\n".join(to_embed)),
            metadata={
                "embedding_dim": DEFAULT_EMBEDDING_DIM,
                "input_count": len(to_embed),
                "input_hash": input_hash,
            },
        )
        network_attempted = False
        try:
            client = _build_embedding_client()
            network_attempted = True
            response = client.models.embed_content(
                model=embedding_model,
                contents=to_embed,
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_EMBEDDING_DIM),
            )
            response_embeddings = list(response.embeddings or [])
            if len(response_embeddings) != len(to_embed):
                raise RuntimeError(
                    "Embedding soni remote input soniga mos kelmadi: "
                    f"{len(response_embeddings)} != {len(to_embed)}"
                )
            vectors = [
                [float(value) for value in list(item.values or [])]
                for item in response_embeddings
            ]
            if any(not vector for vector in vectors):
                raise RuntimeError("Gemini embedding javobida bo'sh vector qaytdi.")
        except Exception as exc:
            reconcile_supply(
                reservation,
                succeeded=False,
                actual_requests=1 if network_attempted else 0,
                usage=None,
                model_name=embedding_model,
                error=exc,
            )
            raise

        # Embed endpoint usage bermasa supply ledger konservativ reservationni
        # accounted_tokens sifatida saqlaydi.
        reconcile_supply(
            reservation,
            succeeded=True,
            actual_requests=1,
            usage=None,
            model_name=embedding_model,
        )

        for i, vector in enumerate(vectors):
            idx = to_embed_indices[i]
            results[idx] = vector

            # Cache for 7 days
            cache.set(
                _embedding_cache_key(to_embed[i], embedding_model=embedding_model),
                vector,
                timeout=60 * 60 * 24 * 7,
            )

    return results


def _active_course_ids_for_user(user):
    if not user:
        return []
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return None
    return list(
        Enrollment.objects.filter(enrollment_active_access_q(), student=user)
        .values_list("cohort__course_id", flat=True)
        .distinct()
    )


def _normalize_id_list(values):
    if values is None:
        return None
    if isinstance(values, (int, str)):
        values = [values]

    normalized = []
    for value in values:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item not in normalized:
            normalized.append(item)
    return normalized


def _intersect_ids(allowed_ids, requested_ids):
    if requested_ids is None:
        return allowed_ids
    if allowed_ids is None:
        return requested_ids
    allowed_set = set(allowed_ids)
    return [item for item in requested_ids if item in allowed_set]


def lesson_content_hash(
    lesson,
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS,
):
    normalized_text = normalize_lesson_text(lesson.content or "")
    if not normalized_text:
        return ""
    content_hash_base = f"{lesson.id}|{embedding_model}|{chunk_words}|{overlap_words}|{normalized_text}"
    return _text_sha(content_hash_base)


def get_rag_index_status(
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS,
):
    lesson_qs = Lesson.objects.select_related("module__course")
    lessons_with_text = [
        lesson
        for lesson in lesson_qs.exclude(Q(content__isnull=True) | Q(content="")).only(
            "id",
            "title",
            "content",
            "module_id",
            "module__title",
            "module__course_id",
            "module__course__title",
        )
        if normalize_lesson_text(lesson.content or "")
    ]

    chunk_qs = LessonRAGChunk.objects.filter(embedding_model=embedding_model)
    indexed_hashes = {}
    for row in chunk_qs.order_by("lesson_id", "chunk_index").values("lesson_id", "content_hash"):
        indexed_hashes.setdefault(row["lesson_id"], row["content_hash"])

    missing_lessons = []
    stale_lessons = []
    for lesson in lessons_with_text:
        expected_hash = lesson_content_hash(
            lesson,
            embedding_model=embedding_model,
            chunk_words=chunk_words,
            overlap_words=overlap_words,
        )
        current_hash = indexed_hashes.get(lesson.id)
        if not current_hash:
            missing_lessons.append(lesson)
        elif current_hash != expected_hash:
            stale_lessons.append(lesson)

    last_indexed_at = chunk_qs.aggregate(last=Max("updated_at")).get("last")
    total_lessons = Lesson.objects.count()
    indexed_lessons = chunk_qs.values("lesson_id").distinct().count()
    ready_lessons = max(0, len(lessons_with_text) - len(missing_lessons) - len(stale_lessons))
    ready_percent = round((ready_lessons / len(lessons_with_text)) * 100) if lessons_with_text else 0

    return {
        "embedding_model": embedding_model,
        "total_lessons": total_lessons,
        "eligible_lessons": len(lessons_with_text),
        "indexed_lessons": indexed_lessons,
        "ready_lessons": ready_lessons,
        "ready_percent": ready_percent,
        "missing_lessons": len(missing_lessons),
        "stale_lessons": len(stale_lessons),
        "empty_lessons": max(0, total_lessons - len(lessons_with_text)),
        "total_chunks": chunk_qs.count(),
        "last_indexed_at": last_indexed_at,
        "pgvector_ready": is_pgvector_ready(),
        "index_command": "python manage.py reindex_rag --force",
        "scoped_command": "python manage.py reindex_rag --course-id <id> --module-id <id> --lesson-id <id> --force",
        "sample_missing_lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "course_title": lesson.module.course.title,
                "module_title": lesson.module.title,
            }
            for lesson in missing_lessons[:5]
        ],
        "sample_stale_lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "course_title": lesson.module.course.title,
                "module_title": lesson.module.title,
            }
            for lesson in stale_lessons[:5]
        ],
    }


def _cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for av, bv in zip(a, b):
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a <= 0 or norm_b <= 0:
        return -1.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _format_retrieved_chunks(scored_rows, top_k):
    top_k = max(1, int(top_k))
    selected = []
    per_lesson_counter = {}

    scored_rows.sort(key=lambda item: item["score"], reverse=True)
    for item in scored_rows:
        if item["similarity"] < MIN_SIMILARITY:
            continue
        lesson_id = item["lesson_id"]
        lesson_count = per_lesson_counter.get(lesson_id, 0)
        if lesson_count >= MAX_CHUNKS_PER_LESSON:
            continue

        selected.append(
            {
                "score": round(item["score"], 4),
                "similarity": round(item["similarity"], 4),
                "chunk_id": item["chunk_id"],
                "chunk_text": item["chunk_text"],
                "lesson_id": item["lesson_id"],
                "lesson_title": item["lesson_title"],
                "module_id": item.get("module_id"),
                "module_title": item.get("module_title", ""),
                "course_id": item["course_id"],
                "course_title": item["course_title"],
                "chunk_index": item["chunk_index"],
                "source_label": " > ".join(
                    part
                    for part in [
                        item["course_title"],
                        item.get("module_title", ""),
                        item["lesson_title"],
                    ]
                    if part
                ),
            }
        )
        per_lesson_counter[lesson_id] = lesson_count + 1
        if len(selected) >= top_k:
            break

    return selected


def _retrieve_chunks_pgvector(
    *,
    query_vector,
    embedding_model,
    course_ids,
    module_ids,
    lesson_ids,
    context_lesson_id,
    top_k,
):
    if not is_pgvector_ready():
        return []

    query_vector_literal = _vector_literal(query_vector)
    limit = min(MAX_PGVECTOR_CANDIDATES, max(top_k * 8, 24))

    chunk_table = LessonRAGChunk._meta.db_table
    lesson_table = Lesson._meta.db_table
    course_table = Course._meta.db_table
    module_table = Module._meta.db_table

    score_expr = "(1 - (c.embedding_vector <=> %s::vector))"
    params = [query_vector_literal]
    score_params = [query_vector_literal]

    if context_lesson_id:
        score_expr += " + CASE WHEN c.lesson_id = %s THEN 0.08 ELSE 0 END"
        score_params.append(int(context_lesson_id))

    where_clauses = [
        "c.embedding_model = %s",
        "c.embedding_vector IS NOT NULL",
    ]

    params.extend(score_params)
    params.append(embedding_model)

    if course_ids is not None:
        where_clauses.append("c.course_id = ANY(%s)")
        params.append(course_ids)
    if module_ids is not None:
        where_clauses.append("l.module_id = ANY(%s)")
        params.append(module_ids)
    if lesson_ids is not None:
        where_clauses.append("c.lesson_id = ANY(%s)")
        params.append(lesson_ids)

    params.append(limit)

    sql = (
        f'SELECT c.id, c.chunk_text, c.lesson_id, c.course_id, c.chunk_index, '
        f"l.title AS lesson_title, cr.title AS course_title, l.module_id, m.title AS module_title, "
        f"(1 - (c.embedding_vector <=> %s::vector)) AS similarity, "
        f"{score_expr} AS score "
        f'FROM "{chunk_table}" c '
        f'JOIN "{lesson_table}" l ON l.id = c.lesson_id '
        f'JOIN "{module_table}" m ON m.id = l.module_id '
        f'JOIN "{course_table}" cr ON cr.id = c.course_id '
        f"WHERE {' AND '.join(where_clauses)} "
        f"ORDER BY score DESC "
        f"LIMIT %s"
    )

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    scored_rows = []
    for row in rows:
        scored_rows.append(
            {
                "chunk_id": row[0],
                "chunk_text": row[1],
                "lesson_id": row[2],
                "course_id": row[3],
                "chunk_index": row[4],
                "lesson_title": row[5],
                "course_title": row[6],
                "module_id": row[7],
                "module_title": row[8],
                "similarity": float(row[9] or 0.0),
                "score": float(row[10] or 0.0),
            }
        )

    return _format_retrieved_chunks(scored_rows, top_k=top_k)


def reindex_lessons(
    *,
    lesson_ids=None,
    course_ids=None,
    module_ids=None,
    force=False,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS,
):
    queryset = Lesson.objects.select_related("module__course").all()
    if lesson_ids:
        queryset = queryset.filter(id__in=lesson_ids)
    if course_ids:
        queryset = queryset.filter(module__course_id__in=course_ids)
    if module_ids:
        queryset = queryset.filter(module_id__in=module_ids)

    stats = {
        "total_lessons": 0,
        "indexed_lessons": 0,
        "skipped_unchanged": 0,
        "skipped_duplicate": 0,
        "cleared_lessons": 0,
        "failed_lessons": 0,
        "total_chunks": 0,
        "vector_synced_chunks": 0,
    }

    for lesson in queryset.iterator():
        stats["total_lessons"] += 1
        try:
            normalized_text = normalize_lesson_text(lesson.content or "")
            existing_qs = LessonRAGChunk.objects.filter(lesson=lesson, embedding_model=embedding_model)

            if not normalized_text:
                deleted_count, _ = existing_qs.delete()
                if deleted_count:
                    stats["cleared_lessons"] += 1
                continue

            content_hash = lesson_content_hash(
                lesson,
                embedding_model=embedding_model,
                chunk_words=chunk_words,
                overlap_words=overlap_words,
            )

            if not force and existing_qs.filter(content_hash=content_hash).exists():
                stats["skipped_unchanged"] += 1
                continue

            chunks = split_into_word_chunks(
                normalized_text,
                max_words=chunk_words,
                overlap_words=overlap_words,
            )
            if not chunks:
                deleted_count, _ = existing_qs.delete()
                if deleted_count:
                    stats["cleared_lessons"] += 1
                continue

            embeddings = embed_texts(
                [chunk["chunk_text"] for chunk in chunks],
                embedding_model=embedding_model,
                call_type="reindex",
                user=None,
                request_key=f"rag-reindex:lesson:{lesson.pk}",
            )
            if len(embeddings) != len(chunks):
                raise RuntimeError(
                    f"Embedding soni mos kelmadi (lesson_id={lesson.id}): {len(embeddings)} != {len(chunks)}"
                )

            chunk_objects = []
            for chunk, vector in zip(chunks, embeddings):
                chunk_objects.append(
                    LessonRAGChunk(
                        lesson=lesson,
                        course=lesson.module.course,
                        chunk_index=chunk["chunk_index"],
                        chunk_text=chunk["chunk_text"],
                        chunk_hash=chunk["chunk_hash"],
                        content_hash=content_hash,
                        token_count=chunk["token_count"],
                        embedding=vector,
                        embedding_model=embedding_model,
                        embedding_dim=len(vector),
                    )
                )

            with transaction.atomic():
                existing_qs.delete()
                LessonRAGChunk.objects.bulk_create(chunk_objects, batch_size=100)

            if is_pgvector_ready():
                inserted_rows = list(
                    LessonRAGChunk.objects.filter(
                        lesson=lesson,
                        embedding_model=embedding_model,
                        content_hash=content_hash,
                    ).values_list("id", "embedding")
                )
                stats["vector_synced_chunks"] += _sync_pgvector_embeddings(inserted_rows)

            stats["indexed_lessons"] += 1
            stats["total_chunks"] += len(chunk_objects)
        except SupplyDuplicate:
            # Bu nosozlik emas, himoyaning ishlagani: shu dars uchun aynan
            # shu kirish bugun allaqachon embed qilingan (yoki hozir boshqa
            # yugurish uni bajaryapti). `reserve_supply` tarmoqqa chiqmasdan
            # rad etadi. Ilgari bu `failed_lessons` ga tushib, operatorga
            # "dars indekslanmadi" deb ko'rinardi va u qayta urinaverardi —
            # holbuki qayta urinish kun oxirigacha hech qachon o'tmasdi.
            stats["skipped_duplicate"] += 1
            logger.info(
                "RAG reindex skipped as duplicate for lesson_id=%s", lesson.id
            )
        except Exception:
            stats["failed_lessons"] += 1
            logger.exception("RAG indexing failed for lesson_id=%s", lesson.id)

    return stats


def retrieve_relevant_chunks(
    *,
    user,
    question: str,
    context_lesson=None,
    course_ids=None,
    module_ids=None,
    lesson_ids=None,
    top_k: int = DEFAULT_TOP_K,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
):
    query = (question or "").strip()
    if not query:
        return []

    allowed_course_ids = _active_course_ids_for_user(user)
    if allowed_course_ids == []:
        return []

    requested_course_ids = _normalize_id_list(course_ids)
    requested_module_ids = _normalize_id_list(module_ids)
    requested_lesson_ids = _normalize_id_list(lesson_ids)

    if context_lesson:
        context_course_id = context_lesson.module.course_id
        context_module_id = context_lesson.module_id
        requested_course_ids = requested_course_ids or [context_course_id]
        requested_module_ids = requested_module_ids or [context_module_id]

    scoped_course_ids = _intersect_ids(allowed_course_ids, requested_course_ids)
    if scoped_course_ids == []:
        return []

    try:
        user_id = getattr(user, "pk", None) or "anonymous"
        query_vector_list = embed_texts(
            [query],
            embedding_model=embedding_model,
            call_type="rag_embedding",
            user=user,
            request_key=f"rag-query:user:{user_id}",
        )
    except Exception:
        logger.exception("RAG query embedding failed")
        return []

    if not query_vector_list:
        return []

    query_vector = query_vector_list[0]

    if is_pgvector_ready():
        pgvector_chunks = _retrieve_chunks_pgvector(
            query_vector=query_vector,
            embedding_model=embedding_model,
            course_ids=scoped_course_ids,
            module_ids=requested_module_ids,
            lesson_ids=requested_lesson_ids,
            context_lesson_id=context_lesson.id if context_lesson else None,
            top_k=top_k,
        )
        if pgvector_chunks:
            return pgvector_chunks

    chunks_qs = LessonRAGChunk.objects.filter(embedding_model=embedding_model).select_related("lesson__module", "course")
    if scoped_course_ids is not None:
        chunks_qs = chunks_qs.filter(course_id__in=scoped_course_ids)
    if requested_module_ids is not None:
        chunks_qs = chunks_qs.filter(lesson__module_id__in=requested_module_ids)
    if requested_lesson_ids is not None:
        chunks_qs = chunks_qs.filter(lesson_id__in=requested_lesson_ids)

    if context_lesson:
        prioritized_ids = list(
            chunks_qs.filter(lesson_id=context_lesson.id)
            .order_by("chunk_index")
            .values_list("id", flat=True)[: MAX_CHUNKS_PER_LESSON * 8]
        )
        candidate_chunks = list(chunks_qs.filter(id__in=prioritized_ids).order_by("chunk_index"))
        candidate_chunks.extend(
            list(chunks_qs.exclude(id__in=prioritized_ids).order_by("-updated_at")[:MAX_CANDIDATES])
        )
        if prioritized_ids:
            prioritized = [chunk for chunk in candidate_chunks if chunk.id in prioritized_ids]
            other = [chunk for chunk in candidate_chunks if chunk.id not in prioritized_ids]
            candidate_chunks = prioritized + other
    else:
        candidate_chunks = list(chunks_qs.order_by("-updated_at")[:MAX_CANDIDATES])

    if not candidate_chunks:
        return []

    scored_rows = []
    for chunk in candidate_chunks:
        similarity = _cosine_similarity(query_vector, chunk.embedding or [])
        if similarity < MIN_SIMILARITY:
            continue
        boost = 0.0
        if context_lesson and chunk.lesson_id == context_lesson.id:
            boost = 0.12
        elif context_lesson and chunk.lesson.module_id == context_lesson.module_id:
            boost = 0.04
        score = similarity + boost
        scored_rows.append(
            {
                "score": score,
                "similarity": similarity,
                "chunk_id": chunk.id,
                "chunk_text": chunk.chunk_text,
                "lesson_id": chunk.lesson_id,
                "lesson_title": chunk.lesson.title,
                "module_id": chunk.lesson.module_id,
                "module_title": chunk.lesson.module.title,
                "course_id": chunk.course_id,
                "course_title": chunk.course.title,
                "chunk_index": chunk.chunk_index,
            }
        )

    return _format_retrieved_chunks(scored_rows, top_k=top_k)
