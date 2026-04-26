# AzureLMS BLITZKRIEG PLAN: Path to Production

This document outlines the strategic roadmap and immediate execution steps to transition AzureLMS from a prototype to a production-ready professional platform.

---

## 1. Performance & Scalability

### Audit Results
*   **RAG Bottleneck**: Repeated API calls for identical embeddings increase latency and costs.
*   **Database**: High-traffic tables (`Message`, `Attendance`, `LessonProgress`) lack specialized indexes for concurrent access patterns.
*   **Concurrent Users**: Django's default synchronous views and connection management need optimization for 100+ students.

### Strategic Roadmap
*   **Phase 1 (Immediate)**: Implement Redis caching for `embed_texts`.
*   **Phase 2**: Introduce Django DB connection pooling (e.g., via PgBouncer or persistent connections).
*   **Phase 3**: Partition `messenger.Message` table by `room_id` or `created_at` if growth exceeds 1M+ rows.

### Quick Win: Redis Embedding Cache
```python
# messenger/rag.py snippet
from django.core.cache import cache

def embed_texts(texts, embedding_model=DEFAULT_EMBEDDING_MODEL):
    results = []
    for text in texts:
        text_hash = _text_sha(f"{embedding_model}:{text}")
        cached_embedding = cache.get(f"emb:{text_hash}")
        if cached_embedding:
            results.append(cached_embedding)
        else:
            # Call API
            embedding = call_gemini_embedding_api(text)
            cache.set(f"emb:{text_hash}", embedding, timeout=60*60*24*7) # 7 days
            results.append(embedding)
    return results
```

---

## 2. Production Security

### Audit Results
*   **Prompt Injection**: Current system prompt is vulnerable to "ignore previous instructions" overrides.
*   **CSP**: Missing strict Content Security Policy to prevent XSS.
*   **Secrets**: Ensure `.env` is the sole source of truth and no sensitive keys are hardcoded.

### Strategic Roadmap
*   **Phase 1 (Immediate)**: Hardening the AI System Prompt and implementing a strict CSP.
*   **Phase 2**: Regular dependency audits and automated vulnerability scanning in CI.

### Quick Win: Security Headers & CSP
```python
# core/settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com")
CSP_FRAME_SRC = ("'self'", "https://www.youtube.com", "https://player.vimeo.com")
```

---

## 3. Holistic UX/UI (Bootstrap + Vanilla JS)

### Audit Results
*   **User Journey**: Dashboard currently requires 4-5 clicks to start a specific lesson. Target: 3 clicks.
*   **Perceived Speed**: AI response time (~3-5s) feels like "hanging" without visual feedback.
*   **Consistency**: Mixing custom CSS with Bootstrap utilities leads to spacing inconsistencies.

### Strategic Roadmap
*   **Phase 1 (Immediate)**: Bootstrap "Shimmer" Skeletons for AI Chat and Video areas.
*   **Phase 2**: Mobile-first UI audit of all Dashboard components.
*   **Phase 3**: Streamlining the navigation flow (Dashboard -> Active Course -> Resume Lesson).

### Quick Win: Bootstrap Shimmer Skeleton
```html
<div class="placeholder-glow">
  <div class="placeholder col-12 mb-2 rounded" style="height: 100px;"></div>
  <div class="placeholder col-8 rounded" style="height: 20px;"></div>
</div>
```

---

## 4. Reliability & Feedback

### Audit Results
*   **Monitoring**: No centralized error tracking (Sentry) or performance metrics (Prometheus).
*   **Feedback**: Students have no way to flag incorrect AI hallucinations, leading to distrust.

### Strategic Roadmap
*   **Phase 1 (Immediate)**: `AIFeedback` model and "Thumbs Up/Down" UI.
*   **Phase 2**: Sentry integration for real-time error reporting.
*   **Phase 3**: Prometheus/Grafana dashboard for system health.

### Quick Win: AI Feedback UI
```html
<div class="ai-feedback-btns mt-2">
  <button class="btn btn-sm btn-outline-success" onclick="rateAI(msgId, 1)"><i class="bi bi-hand-thumbs-up"></i></button>
  <button class="btn btn-sm btn-outline-danger" onclick="rateAI(msgId, -1)"><i class="bi bi-hand-thumbs-down"></i></button>
</div>
```

---

## Execution Priority (April 15 Sprint)
1.  **High**: DB Indexing & Redis Caching (Scalability).
2.  **High**: Security Headers & Prompt Hardening (Security).
3.  **Medium**: Shimmer Skeletons (UX).
4.  **Medium**: AI Feedback Mechanism (Reliability).
