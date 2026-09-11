"""Rolga mos doimiy klaviatura testlari (T1).

Bu yerdagi eng muhim test — **o'lik tugma yo'qligi**. Klaviatura tugmasi oddiy
matn xabari bo'lib keladi; agar biror tugma uchun handler ro'yxatdan
o'tmagan bo'lsa, u onboarding routeridagi catch-all (erkin matn → AI) ga
tushadi va foydalanuvchi "Darslarim" deb yozganida AI repetitor javob berib
qoladi. Nosozlik **jim**: xato ham, log ham bo'lmaydi.

Shu sabab handlerlar ro'yxati introspeksiya bilan tekshiriladi — dispatcher
ishga tushirilmaydi (u haqiqiy `Bot` va token talab qiladi, test esa tarmoqqa
chiqmasligi kerak).
"""

from types import SimpleNamespace

from aiogram import Router
from django.test import SimpleTestCase

from bot.keyboards import (
    ALL_BUTTON_LABELS,
    BTN_AI,
    BTN_ATTENDANCE,
    BTN_COURSES,
    BTN_GRADING,
    BTN_GROUPS,
    BTN_HIDE,
    BTN_PAYMENT,
    BTN_RECEIPTS,
    BTN_STATS,
    WORKSPACE_KEYBOARDS,
    hide_keyboard,
    keyboard_labels,
    workspace_keyboard,
)


def _text_handler_labels(router: Router):
    """Router handlerlari qabul qiladigan tugma matnlari.

    `F.text == "..."` — `MagicFilter`; uni soxta obyektga qarshi hisoblash
    mumkin. `Command(...)` filtrlari async va bot talab qiladi, shuning uchun
    ular hisobga olinmaydi: bizni faqat **matnli** tugma qiziqtiradi.
    """
    accepted = set()
    for handler in router.message.handlers:
        for flt in handler.filters or []:
            # aiogram har filtrni `FilterObject` ga o'raydi; `MagicFilter`
            # bo'lsa u `.magic` da yotadi, `Command` kabi filtrlarda `None`.
            magic = getattr(flt, "magic", None)
            if magic is None:
                continue
            for label in ALL_BUTTON_LABELS:
                try:
                    matches = bool(magic.resolve(SimpleNamespace(text=label)))
                    # Aynan shu matnga mo'ljallanganmi yoki har qanday matnni
                    # qabul qiladimi? Routerda `F.text` kabi keng filtrlar bor
                    # (vazifa javobi, AI suhbati) va ular har qanday satrga
                    # rost qaytaradi. Ularni "tugma handleri" deb hisoblash
                    # testni yolg'on yashil qilardi — nazorat yugurishi aynan
                    # shuni ko'rsatdi.
                    catch_all = bool(magic.resolve(SimpleNamespace(text=label + "…x")))
                except Exception:  # noqa: BLE001 — matnga aloqasi yo'q filtr
                    continue
                if matches and not catch_all:
                    accepted.add(label)
    return accepted


class KeyboardShapeTests(SimpleTestCase):
    def test_each_role_gets_its_own_button_set(self):
        student = keyboard_labels("student")
        teacher = keyboard_labels("teacher")
        admin = keyboard_labels("admin")

        self.assertIn(BTN_COURSES, student)
        self.assertIn(BTN_ATTENDANCE, student)
        self.assertIn(BTN_PAYMENT, student)
        self.assertNotIn(BTN_GRADING, student, "o'quvchida baholash tugmasi bo'lmasin")

        self.assertIn(BTN_GROUPS, teacher)
        self.assertIn(BTN_GRADING, teacher)

        self.assertIn(BTN_STATS, admin)
        self.assertIn(BTN_RECEIPTS, admin)

    def test_guest_gets_no_keyboard(self):
        """Telefon ulashish klaviaturasi almashib ketmasligi kerak.

        Telegramda chatda bir vaqtda faqat bitta reply klaviatura bo'ladi.
        Guestga ish stoli klaviaturasi qo'yilsa, ro'yxatdan o'tish oqimi
        o'rtasida `request_contact` tugmasi yo'qolib qolardi.
        """
        self.assertIsNone(workspace_keyboard("guest"))
        self.assertIsNone(workspace_keyboard(None))
        self.assertIsNone(workspace_keyboard("nomalum-rol"))

    def test_keyboard_stays_small(self):
        """Klaviatura ekranning pastini egallaydi — uzun ro'yxat chatni siqadi."""
        for role, rows in WORKSPACE_KEYBOARDS.items():
            actions = [label for row in rows for label in row if label != BTN_HIDE]
            self.assertLessEqual(len(actions), 4, f"{role}: {len(actions)} ta tugma")

    def test_every_role_can_hide_the_keyboard(self):
        for role in WORKSPACE_KEYBOARDS:
            self.assertIn(BTN_HIDE, keyboard_labels(role), role)

    def test_markup_is_persistent_and_resized(self):
        markup = workspace_keyboard("student")
        self.assertTrue(markup.resize_keyboard)
        self.assertTrue(markup.is_persistent)
        self.assertEqual(
            [[b.text for b in row] for row in markup.keyboard],
            WORKSPACE_KEYBOARDS["student"],
        )

    def test_hide_keyboard_removes_it(self):
        self.assertTrue(hide_keyboard().remove_keyboard)


class NoDeadButtonTests(SimpleTestCase):
    """Har bir tugma matni biror handlerga tushishi kerak.

    Aks holda u catch-all (erkin matn → AI) ga tushadi va "Darslarim" deb
    yozgan o'quvchiga AI repetitor javob beradi.
    """

    def test_every_button_label_has_a_handler(self):
        from bot.routers.onboarding import router as onboarding_router
        from bot.routers.staff import router as staff_router
        from bot.routers.workspace import router as workspace_router

        handled = set()
        for router in (workspace_router, staff_router, onboarding_router):
            handled |= _text_handler_labels(router)

        missing = sorted(set(ALL_BUTTON_LABELS) - handled)
        self.assertEqual(missing, [], f"handlersiz tugma: {missing}")

    def test_the_check_actually_finds_handlers(self):
        """Nazorat: introspeksiya haqiqatan ishlayaptimi.

        Aks holda aiogram ichki tuzilishi o'zgarganda test hech narsa
        topmasdan ham "hammasi joyida" deb ko'rsatib turardi.
        """
        from bot.routers.workspace import router as workspace_router

        found = _text_handler_labels(workspace_router)
        self.assertIn(BTN_COURSES, found)
        self.assertIn(BTN_AI, found)


class _FakeMessage:
    """`answer()` chaqiruvlarini yozib boruvchi soxta xabar."""

    def __init__(self):
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))
        return SimpleNamespace(message_id=len(self.answers))


class SendWorkspaceKeyboardTests(SimpleTestCase):
    async def _send(self, role):
        from bot.routers.onboarding import send_workspace_keyboard

        message = _FakeMessage()
        await send_workspace_keyboard(message, role)
        return message

    def test_keyboard_is_sent_as_a_second_message(self):
        """Bitta xabarda bitta `reply_markup` bo'ladi — inline menyu o'z o'rnida."""
        import asyncio

        message = asyncio.run(self._send("student"))
        self.assertEqual(len(message.answers), 1)
        markup = message.answers[0][1]["reply_markup"]
        self.assertEqual(
            [[b.text for b in row] for row in markup.keyboard],
            WORKSPACE_KEYBOARDS["student"],
        )

    def test_nothing_is_sent_to_a_guest(self):
        import asyncio

        message = asyncio.run(self._send("guest"))
        self.assertEqual(message.answers, [], "guestga klaviatura yuborilmasligi kerak")


class ButtonIsNeverAnAnswerTests(SimpleTestCase):
    """Klaviatura tugmasi vazifa javobi sifatida topshirilmasligi kerak.

    PR #106 dagi Codex review topdi: vazifa kutayotgan o'quvchi
    "Klaviaturani yopish" bosganda o'sha matn **javob sifatida** ketardi va
    pending action tozalanardi — tugma ishlamaydi, ustiga vazifa noto'g'ri
    javob bilan yopiladi. Sabab router tartibi edi: onboarding routeri
    workspace'dan keyin ulanadi, workspace'dagi `AwaitingAssignment()` esa
    buyruq bo'lmagan har qanday matnni qabul qilardi.
    """

    def _assignment_text_filter(self):
        from bot.routers.workspace import router as workspace_router

        for handler in workspace_router.message.handlers:
            names = {
                type(getattr(f, "callback", None)).__name__ for f in handler.filters or []
            }
            if "AwaitingAssignment" not in names:
                continue
            for flt in handler.filters or []:
                magic = getattr(flt, "magic", None)
                if magic is not None:
                    return magic
        return None

    def test_the_assignment_handler_rejects_every_button_label(self):
        magic = self._assignment_text_filter()
        self.assertIsNotNone(magic, "vazifa matn handleri topilmadi")
        for label in ALL_BUTTON_LABELS:
            self.assertFalse(
                bool(magic.resolve(SimpleNamespace(text=label))),
                f"{label} vazifa javobi sifatida qabul qilinyapti",
            )

    def test_the_assignment_handler_still_accepts_a_real_answer(self):
        """Nazorat: filtr haqiqiy javobni bloklab qo'ymasin."""
        magic = self._assignment_text_filter()
        self.assertTrue(
            bool(magic.resolve(SimpleNamespace(text="Mening javobim: merhaba")))
        )
        # Buyruq esa avvalgidek o'tmaydi.
        self.assertFalse(bool(magic.resolve(SimpleNamespace(text="/bekor"))))
