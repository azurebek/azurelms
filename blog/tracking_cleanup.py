"""PUB1.0g'gacha yig'ilgan blog kuzatuv ma'lumotini ko'rish va tozalash.

Anonim o'qish va olqish endi yozilmaydi. Eskidan qolganlar:

- anonim `BlogPostRead` qatorlari (`anon:<cookie>` kaliti, IP xeshi, user-agent);
- kirgan foydalanuvchi qatorlaridagi IP xeshi va user-agent;
- anonim `BlogPostClap` qatorlari (`anon:<cookie>` kaliti).

Maqoladagi jami `view_count` va `clap_count` o'zgarmaydi — ular alohida maydon.
Tozalash faqat owner `--apply` bilan buyruq berganda bo'ladi.
"""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from blog.models import BlogPostClap, BlogPostRead
from blog.utils import LEGACY_ANONYMOUS_KEY_PREFIX


@dataclass(frozen=True)
class LegacyTracking:
    anonymous_reads: int
    reader_fingerprints: int
    anonymous_claps: int

    @property
    def total(self):
        return self.anonymous_reads + self.reader_fingerprints + self.anonymous_claps


def _anonymous_reads():
    return BlogPostRead.objects.filter(viewer_key__startswith=LEGACY_ANONYMOUS_KEY_PREFIX)


def _fingerprinted_reads():
    return BlogPostRead.objects.exclude(viewer_key__startswith=LEGACY_ANONYMOUS_KEY_PREFIX).filter(
        ~Q(ip_hash="") | ~Q(user_agent="")
    )


def _anonymous_claps():
    return BlogPostClap.objects.filter(viewer_key__startswith=LEGACY_ANONYMOUS_KEY_PREFIX)


def legacy_tracking():
    """Hech narsa yozmaydi — Control Center va buyruqning quruq rejimi uchun."""
    return LegacyTracking(
        anonymous_reads=_anonymous_reads().count(),
        reader_fingerprints=_fingerprinted_reads().count(),
        anonymous_claps=_anonymous_claps().count(),
    )


def purge_legacy_tracking():
    """Anonim qatorlarni o'chiradi, kirganlarnikida IP/UA'ni tozalaydi."""
    with transaction.atomic():
        before = legacy_tracking()
        _anonymous_reads().delete()
        _fingerprinted_reads().update(ip_hash="", user_agent="")
        _anonymous_claps().delete()
    return before
