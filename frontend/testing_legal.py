"""Testlar uchun: amaldagi huquqiy hujjat versiyasi (PUB1.5a).

Maxfiylik va shartlar endi `LegalRevision`dan o'qiladi — `LegalPage` qatori
sahifani ochmaydi. Bu yordamchi hayot siklini chetlab o'tib, darhol amaldagi
versiya yozadi; jarayonning o'zi `frontend/test_legal_revisions.py`da sinaladi.
"""

from datetime import timedelta

from django.utils import timezone

from frontend.legal_revisions import digest
from frontend.models import LegalDocument, LegalRevision


def publish_legal(kind, title=None, content="<p>Owner matni</p>", version_label="1.0", effective_at=None):
    document, _ = LegalDocument.objects.get_or_create(kind=kind)
    now = timezone.now()
    return LegalRevision.objects.create(
        document=document, version_label=version_label, title=title or f"Owner {kind}",
        content=content, content_digest=digest(content), status=LegalRevision.STATUS_PUBLISHED,
        approved_at=now, published_at=now, effective_at=effective_at or now - timedelta(minutes=1),
    )


def publish_all_legal(**kwargs):
    return [publish_legal(kind, **kwargs) for kind in (LegalDocument.KIND_PRIVACY, LegalDocument.KIND_TERMS)]
