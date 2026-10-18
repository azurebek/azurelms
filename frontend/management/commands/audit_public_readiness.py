"""Public sirt tayyorligi hisoboti: da'volar, fikrlar, huquqiy sahifalar (PUB1.2a).

    python manage.py audit_public_readiness

Faqat o'qiydi. Seed/default qatorlar hech qachon "tasdiqlangan" deb
ko'rsatilmaydi — dalil faqat owner amali bilan paydo bo'ladi.
"""

from django.core.management.base import BaseCommand

from core.public_readiness import contact_readiness, legal_readiness
from frontend.models import Testimonial
from frontend.public_claims import all_claims


class Command(BaseCommand):
    help = "Public da'volar dalili, fikrlar roziligi va huquqiy sahifalar holati (o'qish)"

    def handle(self, *args, **options):
        self.stdout.write("Da'volar (statistika):")
        for claim in all_claims():
            expires = f" — {claim.evidence.expires_at:%Y-%m-%d} gacha" if claim.is_public else ""
            self.stdout.write(f"  [{claim.status}] {claim.key}: {claim.text}{expires}")
        self.stdout.write("\nO'quvchilar fikri:")
        for item in Testimonial.objects.order_by("order", "id"):
            state = "public" if item.has_public_consent else ("revoked" if item.consent_revoked_at else "missing-consent")
            active = "" if item.is_active else " (faol emas)"
            self.stdout.write(f"  [{state}] #{item.pk} {item.public_name}{active}")
        self.stdout.write("\nHuquqiy sahifalar:")
        for page in legal_readiness():
            self.stdout.write(f"  [{page.state}] {page.page_type}")
        contact = ", ".join(contact_readiness())
        self.stdout.write(f"\nPublic aloqa: {contact or 'sozlanmagan (namuna qiymatlar ko‘rsatilmaydi)'}")
