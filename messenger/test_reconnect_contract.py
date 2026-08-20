"""Messenger uzilgan ulanishni o'zi tiklashi kerak (A5).

Ilgari `new WebSocket(...)` bir marta chaqirilardi va `close` hodisasida
faqat "Sahifani yangilang" deb yozilardi. Telefonda bu eng ko'p uchraydigan
holat: ekran qulflanadi yoki ilova fonga o'tadi — socket yopiladi va
foydalanuvchi qaytib kelganda chat jim o'lik turadi.

Ikki yopilish turini ajratish shart:

* `4403` — server kirish huquqi tugaganini aytadi (A0b). Qayta ulanish bu
  yerda mantiqsiz: har urinish yana rad etiladi, ya'ni tsikl.
* boshqa yopilish — tarmoq uzilishi, qayta ulanish o'rinli.

Server kodi bilan klient kodi bir xil raqamni bilishi kerak; ular ikki
faylda yashaydi va biri o'zgarsa ikkinchisi jim eskiradi — shuning uchun
test ikkalasini solishtiradi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from messenger.consumers import ChatConsumer

JS = Path(settings.BASE_DIR) / "static" / "js" / "messenger-chat.js"


class ReconnectContractTests(SimpleTestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")

    def _scheduler_body(self):
        match = re.search(
            r"function\s+scheduleReconnect\s*\([^)]*\)\s*\{(.*?)\n  \}",
            self.js,
            re.S,
        )
        return match.group(1) if match else None

    def test_client_reconnects_after_a_dropped_connection(self):
        self.assertRegex(
            self.js, r"function\s+connect\s*\(",
            "socket bir marta yaratilsa, uzilgandan keyin tiklanmaydi",
        )
        body = self._scheduler_body()
        self.assertIsNotNone(body, "qayta ulanishni rejalashtiruvchi yo'q")
        self.assertIn("setTimeout", body, "qayta ulanish kechikish bilan rejalashtirilsin")
        self.assertIn("connect()", body, "rejalashtirish `connect()` ni chaqirsin")

    def test_reconnect_backoff_is_bounded(self):
        """Cheksiz tez urinish serverni ham, batareyani ham yeydi."""
        self.assertRegex(
            self.js, r"MAX_RECONNECT_ATTEMPTS\s*=\s*\d+",
            "urinishlar soni cheklanmagan",
        )
        body = self._scheduler_body() or ""
        self.assertIn("Math.min", body, "kechikish o'sadi, ammo yuqori chegarasi bo'lishi kerak")
        self.assertIn("RECONNECT_MAX_DELAY", body, "yuqori chegara nomlangan bo'lsin")

    def test_access_revoked_close_is_not_retried(self):
        """4403 da qayta ulanish har safar rad etiladi — bu tsikl."""
        code = ChatConsumer.ACCESS_REVOKED_CLOSE_CODE
        named = re.search(r"ACCESS_REVOKED_CLOSE_CODE\s*=\s*(\d+)", self.js)
        self.assertIsNotNone(named, "kod klientda nomlangan konstanta bo'lishi kerak")
        self.assertEqual(
            int(named.group(1)), code,
            "server va klient bir xil kodni bilishi shart — biri o'zgarsa "
            "ikkinchisi jim eskiradi va klient tsiklga tushadi",
        )
        self.assertIn(
            "accessRevoked", self.js,
            "huquq tugaganda qayta ulanish to'xtashi kerak",
        )

    def test_client_retries_when_the_device_comes_back(self):
        """Telefon fondan qaytganda backoff kutib turmasin."""
        self.assertIn("'online'", self.js, "tarmoq qaytganda darhol urinish kerak")
        self.assertIn("visibilitychange", self.js, "ilova fondan qaytganda darhol urinish kerak")

    def test_sending_does_not_use_a_stale_socket_reference(self):
        """`connect()` yangi socket yaratadi; eski `const socket` qolib ketsa jim buziladi."""
        self.assertNotRegex(
            self.js, r"const\s+socket\s*=\s*new\s+WebSocket",
            "socket qayta yaratilishi kerak, ya'ni `const` bo'la olmaydi",
        )
        self.assertRegex(
            self.js, r"function\s+socketIsOpen\s*\(",
            "holat tekshiruvi bitta joydan o'tsin, aks holda eski havola qoladi",
        )
