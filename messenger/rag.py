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
from django.utils.html import strip_tags
from google import genai
from google.genai import types

from cohorts.models import Enrollment, enrollment_active_access_q
from courses.models import Course, Lesson
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
    return genai.Client(api_key=api_key)


def embed_texts(texts: Iterable[str], embedding_model: str = DEFAULT_EMBEDDING_MODEL):
    from django.core.cache import cache

    content_list = [text for text in texts if (text or "").strip()]
    if not content_list:
        return []

    results = [None] * len(content_list)
    to_embed = []
    to_embed_indices = []

    for i, text in enumerate(content_list):
        text_hash = _text_sha(f"{embedding_model}:{text}")
        cache_key = f"emb:{text_hash}"
        cached = cache.get(cache_key)
        if cached:
            results[i] = cached
        else:
            to_embed.append(text)
            to_embed_indices.append(i)

    if to_embed:
        client = _build_embedding_client()
        try:
            response = client.models.embed_content(
                model=embedding_model,
                contents=to_embed,
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_EMBEDDING_DIM),
            )
        except Exception:
            response = client.models.embed_content(
                model=embedding_model,
                contents=to_embed,
            )

        for i, item in enumerate(response.embeddings or []):
            values = list(item.values or [])
            vector = [float(v) for v in values]
            idx = to_embed_indices[i]
            results[idx] = vector

            # Cache for 7 days
            text_hash = _text_sha(f"{embedding_model}:{to_embed[i]}")
            cache.set(f"emb:{text_hash}", vector, timeout=60*60*24*7)

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
                "course_id": item["course_id"],
                "course_title": item["course_title"],
                "chunk_index": item["chunk_index"],
            }
        )
        per_lesson_counter[lesson_id] = lesson_count + 1
        if len(selected) >= top_k:
            break

    return selected


def _retrieve_chunks_pgvector(*, query_vector, embedding_model, course_ids, context_lesson_id, top_k):
    if not is_pgvector_ready():
        return []

    query_vector_literal = _vector_literal(query_vector)
    limit = min(MAX_PGVECTOR_CANDIDATES, max(top_k * 8, 24))

    chunk_table = LessonRAGChunk._meta.db_table
    lesson_table = Lesson._meta.db_table
    course_table = Course._meta.db_table

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

    params.append(limit)

    sql = (
        f'SELECT c.id, c.chunk_text, c.lesson_id, c.course_id, c.chunk_index, '
        f"l.title AS lesson_title, cr.title AS course_title, "
        f"(1 - (c.embedding_vector <=> %s::vector)) AS similarity, "
        f"{score_expr} AS score "
        f'FROM "{chunk_table}" c '
        f'JOIN "{lesson_table}" l ON l.id = c.lesson_id '
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
                "similarity": float(row[7] or 0.0),
                "score": float(row[8] or 0.0),
            }
        )

    return _format_retrieved_chunks(scored_rows, top_k=top_k)


def reindex_lessons(
    *,
    lesson_ids=None,
    course_ids=None,
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

    stats = {
        "total_lessons": 0,
        "indexed_lessons": 0,
        "skipped_unchanged": 0,
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

            content_hash_base = f"{lesson.id}|{embedding_model}|{chunk_words}|{overlap_words}|{normalized_text}"
            content_hash = _text_sha(content_hash_base)

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

            embeddings = embed_texts([chunk["chunk_text"] for chunk in chunks], embedding_model=embedding_model)
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
        except Exception:
            stats["failed_lessons"] += 1
            logger.exception("RAG indexing failed for lesson_id=%s", lesson.id)

    return stats


def retrieve_relevant_chunks(
    *,
    user,
    question: str,
    context_lesson=None,
    top_k: int = DEFAULT_TOP_K,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
):
    query = (question or "").strip()
    if not query:
        return []

    course_ids = _active_course_ids_for_user(user)
    if course_ids == []:
        return []

    try:
        query_vector_list = embed_texts([query], embedding_model=embedding_model)
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
            course_ids=course_ids,
            context_lesson_id=context_lesson.id if context_lesson else None,
            top_k=top_k,
        )
        if pgvector_chunks:
            return pgvector_chunks

    chunks_qs = LessonRAGChunk.objects.filter(embedding_model=embedding_model).select_related("lesson", "course")
    if course_ids is not None:
        chunks_qs = chunks_qs.filter(course_id__in=course_ids)

    if context_lesson:
        prioritized_ids = list(
            chunks_qs.filter(lesson_id=context_lesson.id)
            .order_by("chunk_index")
            .values_list("id", flat=True)[: MAX_CHUNKS_PER_LESSON * 8]
        )
        chunks_qs = chunks_qs.order_by("-updated_at")
        candidate_chunks = list(chunks_qs[:MAX_CANDIDATES])
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
            boost = 0.08
        score = similarity + boost
        scored_rows.append(
            {
                "score": score,
                "similarity": similarity,
                "chunk_id": chunk.id,
                "chunk_text": chunk.chunk_text,
                "lesson_id": chunk.lesson_id,
                "lesson_title": chunk.lesson.title,
                "course_id": chunk.course_id,
                "course_title": chunk.course.title,
                "chunk_index": chunk.chunk_index,
            }
        )

    return _format_retrieved_chunks(scored_rows, top_k=top_k)
