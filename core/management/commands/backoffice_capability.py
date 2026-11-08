"""Xodimga boshqaruv ruxsatini berish yoki olish (DASH1.0a).

    python manage.py backoffice_capability list
    python manage.py backoffice_capability list --user ali
    python manage.py backoffice_capability grant ali finance_receipt_review --reason "Moliya xodimi"
    python manage.py backoffice_capability revoke ali finance_receipt_review --reason "Lavozim o'zgardi"

Django admin default o'chiq (`ENABLE_LEGACY_ADMIN=False`), shuning uchun ruxsat
shu buyruq orqali beriladi. Platforma egasi (superuser) ruxsatsiz ham hammasini
ko'radi; kurs ustozi o'z kursi bilan ishlash uchun ruxsat so'ramaydi. Har o'zgarish
audit ledgeriga sabab bilan yoziladi.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.backoffice_capabilities import CAPABILITIES


def _direct_capabilities(user):
    return sorted(user.user_permissions.filter(
        content_type__app_label="core", codename__in=CAPABILITIES,
    ).values_list("codename", flat=True))


class Command(BaseCommand):
    help = "Xodimga boshqaruv ruxsatini berish, olish yoki ro'yxatini ko'rish"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        listing = sub.add_parser("list", help="Ruxsatlar va ularga ega xodimlar")
        listing.add_argument("--user", default="", help="Faqat shu foydalanuvchi")
        for name in ("grant", "revoke"):
            change = sub.add_parser(name)
            change.add_argument("username")
            change.add_argument("capabilities", nargs="+", metavar="ruxsat")
            change.add_argument("--reason", required=True, help="Nega (audit uchun)")

    def handle(self, *args, **options):
        if options["action"] == "list":
            return self._list(options["user"])
        return self._change(options)

    def _user(self, username):
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"Foydalanuvchi topilmadi: {username}")
        return user

    def _list(self, username):
        if username:
            user = self._user(username)
            owned = "hammasi (platforma egasi)" if user.is_superuser else ", ".join(_direct_capabilities(user)) or "yo'q"
            self.stdout.write(f"{user.username}: {owned}")
            return
        for codename, label in CAPABILITIES.items():
            holders = get_user_model().objects.filter(
                user_permissions__content_type__app_label="core", user_permissions__codename=codename,
            ).order_by("username").values_list("username", flat=True)
            self.stdout.write(f"{codename} — {label}: {', '.join(holders) or '—'}")

    def _change(self, options):
        from aicontrol.models import SystemAuditEvent
        from core.audit import record_audit_event

        unknown = sorted(set(options["capabilities"]) - set(CAPABILITIES))
        if unknown:
            raise CommandError(f"Noma'lum ruxsat: {', '.join(unknown)}. Ro'yxat: {', '.join(CAPABILITIES)}")
        reason = options["reason"].strip()
        if not reason:
            raise CommandError("Sabab bo'sh bo'lmasin.")
        user = self._user(options["username"])
        granting = options["action"] == "grant"
        if granting and (not user.is_active or not user.is_staff):
            raise CommandError("Ruxsat faqat faol xodimga (is_staff) beriladi.")
        if granting and user.is_superuser:
            raise CommandError("Platforma egasi (superuser) ruxsatsiz ham hammasini ko'radi.")

        permissions = list(Permission.objects.filter(
            content_type__app_label="core", codename__in=options["capabilities"],
        ))
        with transaction.atomic():
            before = _direct_capabilities(user)
            if granting:
                user.user_permissions.add(*permissions)
            else:
                user.user_permissions.remove(*permissions)
            after = _direct_capabilities(user)
            record_audit_event(
                action=f"backoffice.capability.{options['action']}",
                source=SystemAuditEvent.SOURCE_CLI,
                target=user,
                target_label=user.username,
                reason=reason,
                # Audit qiymatlari skalyar saqlanadi; ro'yxat vergul bilan.
                before={"capabilities": ",".join(before)},
                after={"capabilities": ",".join(after)},
            )
        self.stdout.write(f"{user.username}: {', '.join(after) or 'ruxsat yo‘q'}")
