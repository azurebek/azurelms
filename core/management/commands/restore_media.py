"""Media arxivini alohida papkaga tiklab, mashqni hisobot bilan yopadi (A1b).

    python manage.py restore_media --input backups/media-....tar.gz --into /tmp/mashq

Joriy media ildizlarining ustiga tiklash ataylab yo'q: arxiv olingandan keyin
yuklangan har bir fayl jim yo'qolardi. Sabab `core/media_backup.py` da,
qo'lda tiklash tartibi `deploy/README.md` §6 da.

Hech qachon tiklanmagan zaxira — umid, zaxira emas.
"""

from django.core.management.base import BaseCommand, CommandError

from core.media_backup import MediaBackupError, live_media_counts, restore_media_backup


class Command(BaseCommand):
    help = "Media arxivini alohida papkaga tiklaydi (joriy fayllarga tegmaydi)"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Arxiv yo'li")
        parser.add_argument(
            "--into",
            required=True,
            help="Bo'sh papka. Joriy media ildizi ichi bo'lsa rad etiladi.",
        )

    def handle(self, *args, **options):
        try:
            target, restored = restore_media_backup(options["input"], options["into"])
        except MediaBackupError as exc:
            raise CommandError(str(exc)) from exc

        live = live_media_counts()
        self.stdout.write(self.style.SUCCESS(f"Mashq bajarildi: {target}"))
        self.stdout.write(f"  public  : {restored['public']} fayl (joriy: {live['public']})")
        self.stdout.write(f"  private : {restored['private']} fayl (joriy: {live['private']})")
        self.stdout.write(f"  jami    : {restored['total']} fayl (joriy: {live['total']})")
        # Sonlar farq qilishi normal: arxivdan keyin yangi fayl yuklangan
        # bo'lishi mumkin. Muhimi — arxiv ochildi va ichida haqiqiy fayllar bor.
        if restored["total"] < live["total"]:
            self.stdout.write(
                self.style.WARNING(
                    "  Arxivda joriy holatdan kam fayl bor — zaxira eskirgan bo'lishi mumkin."
                )
            )
        self.stdout.write(
            "  Joriy media o'zgarmadi. `private/` papkasi public ildizga "
            "ko'chirilmasligini tekshiring."
        )
