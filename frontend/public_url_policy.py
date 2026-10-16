"""Admin kiritgan public URL'lar uchun yagona siyosat (PUBLIC-01 · PUB1.0a).

Ikki xil havola bor va ular ataylab farq qiladi:

* **Navigatsiya** — navbar, footer, ijtimoiy tarmoq tugmalari. Bu sayt
  "ichidagi" yo'l hisoblanadi, shuning uchun faqat lokal yo'l, ``https``,
  ``mailto`` va ``tel``. Oddiy ``http`` rad: brendning o'z menyusi shifrlanmagan
  manzilga olib bormasligi kerak.
* **Kontent/manba havolasi** — SIT rasmiy manbasi, universitet sayti, video.
  Bu tashqi dalilga havola; ba'zi rasmiy saytlar hali ``http``da, ularni
  yashirish dalilni yo'qotardi. Shu sabab ``http`` ham qabul qilinadi — rich
  text ichidagi havolalar bilan bir xil qoida.

Ikkalasi ham `core.rich_content_policy.safe_url` ustida: ``javascript:``,
``data:``, ``//host``, ``/\\host``, control belgi va ``user@host`` hamma joyda
bir xil rad etiladi. Legacy va V1 rendererlar shu ikki funksiyani ishlatadi.
"""

from core.rich_content_policy import LINK_SCHEMES, NAV_SCHEMES, safe_url


def public_nav_url(value):
    """Navbar/footer/ijtimoiy havola: lokal yo'l, https, mailto yoki tel."""
    return safe_url(value, schemes=NAV_SCHEMES, allow_local=True)


def public_link_url(value):
    """Kontent yoki manba havolasi: lokal yo'l, http(s), mailto yoki tel."""
    return safe_url(value, schemes=LINK_SCHEMES, allow_local=True)
