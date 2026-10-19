"""Brauzer xotirasi va uchinchi tomon manbalari ro'yxati (PUB1.5b).

    python manage.py privacy_inventory          # hisobot va tekshiruv
    python manage.py privacy_inventory --write  # PUBLIC-COOKIE-INVENTORY.md ni yangilash

Tekshiruv: kodda brauzer xotirasiga tegadigan, lekin ro'yxatda qayd etilmagan
fayl yoki mavjud bo'lmagan kod yo'li bo'lsa — xato bilan chiqadi. Hujjat
`frontend/privacy_inventory.py`dan yaratiladi; qo'lda tahrir test'da ushlanadi.
"""

from django.core.management.base import BaseCommand, CommandError

from frontend import privacy_inventory as inventory


class Command(BaseCommand):
    help = "Cookie/brauzer xotirasi ro'yxatini tekshiradi yoki hujjatni yangilaydi"

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="PUBLIC-COOKIE-INVENTORY.md ni qayta yozish")

    def handle(self, *args, **options):
        uncovered = inventory.uncovered_files()
        missing = inventory.missing_code_paths()
        for path in uncovered:
            self.stdout.write(f"  ro'yxatda yo'q: {path}")
        for path in missing:
            self.stdout.write(f"  kod yo'li topilmadi: {path}")
        if uncovered or missing:
            raise CommandError("Brauzer xotirasi ro'yxati to'liq emas — frontend/privacy_inventory.py ni yangilang.")
        text = inventory.render_markdown()
        path = inventory.inventory_path()
        if options["write"]:
            path.write_text(text, encoding="utf-8", newline="\n")
            self.stdout.write(f"Yozildi: {path}")
            return
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != text:
            raise CommandError("PUBLIC-COOKIE-INVENTORY.md eskirgan — `privacy_inventory --write` bilan yangilang.")
        cookies = ", ".join(sorted(inventory.active_cookie_names()))
        self.stdout.write(f"Ro'yxat to'liq. Faol cookie'lar: {cookies}; tashqi manbalar: {len(inventory.THIRD_PARTY)}.")
