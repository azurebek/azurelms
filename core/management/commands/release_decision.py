"""Release bo'yicha owner qarorini yozadi (A2).

    python manage.py release_decision --sha abc123 --decision go --note "demo ochildi"

Qaror audit ledgeriga ham tushadi. Mantiq `core/release_service.py` da.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from aicontrol.models import ReleaseRecord
from core.release_service import ReleaseNotRecorded, decide_release


class Command(BaseCommand):
    help = "Release bo'yicha owner qarorini yozadi (go/hold/rolled_back)"

    def add_arguments(self, parser):
        parser.add_argument("--sha", required=True)
        parser.add_argument(
            "--decision",
            required=True,
            choices=[choice for choice, _label in ReleaseRecord.DECISION_CHOICES],
        )
        parser.add_argument("--note", default="", help="Sabab — auditga yoziladi")
        parser.add_argument("--actor", default="", help="Owner username")

    def handle(self, *args, **options):
        actor = None
        username = options["actor"].strip()
        if username:
            actor = get_user_model().objects.filter(username=username).first()
            if actor is None:
                raise CommandError(f"Foydalanuvchi topilmadi: {username}")

        try:
            record = decide_release(
                commit_sha=options["sha"].strip(),
                decision=options["decision"],
                actor=actor,
                note=options["note"].strip()[:255],
            )
        except ReleaseNotRecorded as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"{record.commit_sha[:12]}: {record.get_decision_display()}"
            )
        )
