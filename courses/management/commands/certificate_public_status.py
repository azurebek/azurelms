"""Sertifikatning ochiq tekshiruv holatini o'zgartirish (PUB1.5c).

    python manage.py certificate_public_status 42                         # holatni ko'rish
    python manage.py certificate_public_status 42 --status revoked --reason "Imtihon qayta ko'rildi"
    python manage.py certificate_public_status 42 --status verifiable --name-mode full --reason "O'quvchi so'radi"

Sertifikat ichki raqami (pk) bilan — kod chiqarilmaydi. O'zgarish
`certificate_verifier.set_public_status` orqali: sabab majburiy, revizion tekshiriladi,
audit yoziladi; bekor qilish sababi ochiq sahifada ko'rinmaydi.
"""

from django.core.management.base import BaseCommand, CommandError

from courses import certificate_verifier as verifier
from courses.models import Certificate


class Command(BaseCommand):
    help = "Sertifikatning ochiq tekshiruv holati: ko'rish yoki o'zgartirish (sabab bilan)"

    def add_arguments(self, parser):
        parser.add_argument("certificate_pk", type=int)
        parser.add_argument("--status", choices=[value for value, _ in Certificate.PUBLIC_STATUS_CHOICES])
        parser.add_argument("--name-mode", choices=[value for value, _ in Certificate.NAME_MODE_CHOICES])
        parser.add_argument("--reason", default="")

    def handle(self, *args, **options):
        certificate = Certificate.objects.filter(pk=options["certificate_pk"]).select_related("course").first()
        if certificate is None:
            raise CommandError("Bunday sertifikat yo'q.")
        if options["status"] is None:
            self.stdout.write(
                f"#{certificate.pk} · {certificate.course.title} · holat: {certificate.public_status} · "
                f"ism: {certificate.public_name_mode} · kod: {'bor' if certificate.public_token else 'yoq'} · "
                f"revizion: {certificate.verification_revision}"
            )
            return
        try:
            row = verifier.set_public_status(
                certificate, status=options["status"], name_mode=options["name_mode"], actor=None,
                reason=options["reason"], expected_revision=certificate.verification_revision,
            )
        except (ValueError, verifier.VerifierConflict) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"#{row.pk}: holat {row.public_status}, ism {row.public_name_mode}, revizion {row.verification_revision}.")
