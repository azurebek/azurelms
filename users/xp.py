"""XP hisobining yagona yozuv nuqtasi (A3).

Ilgari XP uch joyda bir xil naqsh bilan yozilardi:

    user.total_xp = user.total_xp + delta
    user.save(update_fields=["total_xp"])

Bu `read-modify-write`, ya'ni **yo'qolgan yangilanish** (lost update)
naqshi: qiymat Python xotirasidagi nusxadan o'qiladi va o'sha nusxa
asosida qaytib yoziladi. Ikki yo'l bir vaqtda XP bersa yoki chaqiruvchi
eskirgan `user` obyektini ushlab tursa, keyingi yozuv oldingisini
**jimgina o'chiradi** — xato ham bermaydi, log ham qoldirmaydi.

Bu aynan oltin oqim testida chiqdi: bot bitta `lms_user` nusxasini bir
necha servis chaqiruvi bo'ylab uzatadi. O'qituvchi vazifani tasdiqlab
+25 XP bergandan keyin quiz baholanganda jami XP `25` dan `20` ga
**tushib** ketdi.

Yechim — qo'shishni bazada bajarish (`F()`), Pythonda emas. Nol chegarasi
`Greatest` bilan bazada qo'yiladi, aks holda uni ushlash uchun yana o'qish
kerak bo'lardi va muammo qaytib kelardi.

XP pulga o'xshaydi: uni o'qib, o'ylab, keyin qaytarib yozish mumkin emas.
"""

from django.contrib.auth import get_user_model
from django.db.models import F, Value
from django.db.models.functions import Greatest


def award_xp(user, delta):
    """`user.total_xp` ni atomik o'zgartiradi va xotiradagi nusxani yangilaydi.

    `delta` manfiy bo'lishi mumkin (baho pasaytirilganda). Natija hech
    qachon noldan past tushmaydi.

    Qaytaradi: yangilangan `total_xp`.
    """
    delta = int(delta or 0)
    if delta == 0:
        return user.total_xp

    # `get_user_model()` ataylab: web'da `request.user` — `SimpleLazyObject`,
    # ya'ni `type(user)` model klassi emas, o'ram klassi bo'lib chiqadi.
    get_user_model().objects.filter(pk=user.pk).update(
        total_xp=Greatest(F("total_xp") + delta, Value(0))
    )
    # Chaqiruvchilar ko'pincha shu obyektni keyin ham ishlatadi (xabar
    # matni, javob payload'i), shuning uchun nusxa yangilanadi.
    user.refresh_from_db(fields=["total_xp"])
    return user.total_xp
