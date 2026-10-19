"""Forma yonidagi qisqa eslatma: shu amalda qaysi ma'lumot va nima uchun saqlanadi (PUB1.5b).

Har matn kodda tekshirilgan haqiqatga mos bo'lishi shart — model maydonlari,
cheklov (PUB1.0c, xesh), fayl ruxsati (`core/private_media_views.py`). Saqlash
muddati va huquqiy asos bu yerda va'da qilinmaydi: ular maxfiylik siyosatida,
uni owner yoki yurist yozadi (PUB1.5a). Yangi ma'lumot yig'adigan forma shu
ro'yxatga qo'shiladi; `PUBLIC-COOKIE-INVENTORY.md` ham undan yaratiladi.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityNotice:
    key: str
    label: str
    where: str
    text: str


NOTICES = {
    notice.key: notice
    for notice in (
        ActivityNotice(
            key="register", label="Ro‘yxatdan o‘tish", where="Ro‘yxat formasi (V1 va legacy)",
            text=("Hisob uchun ismingiz, familiyangiz (ixtiyoriy) va emailingiz saqlanadi; parolning o‘zi emas, "
                  "faqat shifrlangan izi. Ko‘p urinishni cheklash uchun IP manzilingiz xesh ko‘rinishida vaqtincha sanaladi."),
        ),
        ActivityNotice(
            key="password_reset", label="Parolni tiklash", where="Tiklash so‘rovi formasi (V1 va legacy)",
            text=("Email faqat tiklash havolasini yuborish uchun ishlatiladi; bu sahifa hisob bor-yo‘qligini aytmaydi. "
                  "Ko‘p so‘rovni cheklash uchun email va IP xesh ko‘rinishida vaqtincha sanaladi."),
        ),
        ActivityNotice(
            key="telegram_login", label="Telegram orqali kirish", where="Telegram paneli (kirish va ro‘yxat sahifalari)",
            text=("Telegrami ulangan hisobga kirasiz; ulanmagan bo‘lsa yangi profil ochiladi va unga Telegram ismingiz "
                  "hamda username’ingiz yoziladi. Telefon raqamingiz so‘ralmaydi."),
        ),
        ActivityNotice(
            key="blog_comment", label="Blogga izoh", where="Maqola ostidagi izoh formasi (V1 va legacy)",
            text="Izohingiz va hisobingizdagi ism maqola ostida hammaga ko‘rinadi.",
        ),
        ActivityNotice(
            key="payment_receipt", label="To‘lov cheki", where="To‘lov sahifasi (V1 va legacy)",
            text=("Chek rasmi, tarif va summa to‘lovni tekshirish uchun saqlanadi. Chek yopiq saqlanadi: uni faqat siz va "
                  "platforma xodimlari ochadi."),
        ),
    )
}
