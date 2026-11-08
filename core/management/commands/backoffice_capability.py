"""Xodimga boshqaruv ruxsatini berish yoki olish (DASH1.0a).

    python manage.py backoffice_capability list
    python manage.py backoffice_capability list --user ali
    python manage.py backoffice_capability grant ali finance_receipt_review --reason "Moliya xodimi"
    python manage.py backoffice_capability revoke ali finance_receipt_review --reason "Lavozim o'zgardi"

Django admin default o'chiq (`ENABLE_LEGACY_ADMIN=False`), shuning uchun ruxsat
shu buyruq orqali beriladi. Platforma egasi (superuser) ruxsatsiz ham hammasini
ko'radi; kurs ustozi o'z kursi bilan ishlash uchun ruxsat so'ramaydi. Har o'zgarish
audit ledgeriga sabab bilan yoziladi.

Buyruq faqat foydalanuvchiga **to'g'ridan-to'g'ri** berilgan ruxsatni o'zgartiradi.
Ruxsat Django guruhi orqali ham kelishi mumkin (`has_capability` uni ham hisoblaydi),
shuning uchun `list` guruhdan kelganini ham ko'rsatadi, `revoke` esa olishdan keyin
ham amal qilayotgan ruxsat qolsa, "olindi" demaydi: manbasini aytib xato bilan
tugaydi.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.backoffice_capabilities import CAPABILITIES, has_capability


def _direct_capabilities(user):
    return sorted(user.user_permissions.filter(
        content_type__app_label="core", codename__in=CAPABILITIES,
    ).values_list("codename", flat=True))


def _group_capabilities(user):
    """codename → shu ruxsatni beradigan guruh nomlari."""
    result = {}
    rows = Permission.objects.filter(
        content_type__app_label="core", codename__in=CAPABILITIES, group__in=user.groups.all(),
    ).values_list("codename", "group__name")
    for codename, group in rows:
        result.setdefault(codename, set()).add(group)
    return {codename: sorted(groups) for codename, groups in sorted(result.items())}


def _describe(user):
    if user.is_superuser:
        return "hammasi (platforma egasi)"
    parts = _direct_capabilities(user)
    parts += [f"{codename} (guruh: {', '.join(groups)})" for codename, groups in _group_capabilities(user).items()]
    text = ", ".join(parts) or "yo'q"
    if parts and not (user.is_active and user.is_staff):
        text += " — amal qilmaydi: hisob faol xodim emas"
    return text


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
            self.stdout.write(f"{user.username}: {_describe(user)}")
            return
        users = get_user_model().objects
        for codename, label in CAPABILITIES.items():
            direct = users.filter(
                user_permissions__content_type__app_label="core", user_permissions__codename=codename,
            ).values_list("username", flat=True)
            via_group = users.filter(
                groups__permissions__content_type__app_label="core", groups__permissions__codename=codename,
            ).values_list("username", flat=True)
            holders = sorted(set(direct)) + [f"{name} (guruh)" for name in sorted(set(via_group) - set(direct))]
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
        if user.is_superuser:
            raise CommandError("Platforma egasi (superuser) har doim hammasini ko'radi; bu buyruq unga ta'sir qilmaydi.")

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
            via_groups = _group_capabilities(user)
            # Django ruxsatlarni obyektda keshlaydi: amaldagi holatni yangidan o'qiymiz.
            fresh = get_user_model().objects.get(pk=user.pk)
            still_effective = [] if granting else [
                codename for codename in options["capabilities"] if has_capability(fresh, codename)
            ]
            record_audit_event(
                action=f"backoffice.capability.{options['action']}",
                source=SystemAuditEvent.SOURCE_CLI,
                target=user,
                target_label=user.username,
                reason=reason,
                # Audit qiymatlari skalyar saqlanadi; ro'yxat vergul bilan.
                before={"capabilities": ",".join(before)},
                after={
                    "capabilities": ",".join(after),
                    "via_groups": ";".join(f"{codename}:{'|'.join(groups)}" for codename, groups in via_groups.items()),
                    "still_effective": ",".join(still_effective),
                },
            )
        if still_effective:
            sources = "; ".join(
                f"{codename} — guruh: {', '.join(via_groups.get(codename, ['?']))}" for codename in still_effective
            )
            raise CommandError(
                f"To'g'ridan-to'g'ri ruxsat olindi, lekin bu ruxsat hali guruh orqali amal qiladi: {sources}. "
                "To'liq olish uchun xodimni shu guruhdan chiqaring yoki guruhdan ruxsatni olib tashlang."
            )
        self.stdout.write(f"{user.username}: {_describe(fresh)}")
