"""Mascot seriya xabarlari — jonli, hazilomuz undash matnlari.

Xabarlar seriya HOLATI va KUN VAQTI bo'yicha tartiblangan. `pick_message`
holat va vaqtga qarab mos variantni tanlaydi. Matnlar mascot (Azure)
nomidan yuboriladi.
"""

import random

# Kun vaqtiga bog'liq undash (seriya bor, lekin bugun hali harakat yo'q).
AT_RISK_BY_TIME = {
    "morning": [
        "Bugun ham boshlaymizmi? ☀️",
        "Vaqti keldi!",
        "3 daqiqangiz bormi?",
        "Boshlab yuboramizmi?",
        "Bugungi navbat sizda.",
        "Keling, ozgina mashq qilamiz.",
        "Kutib turibman. 👀",
        "Bir dars qilib qo'ying.",
        "Bugun ham seriya davom etsin!",
        "Tayyormisiz?",
    ],
    "midday": [
        "Hali ham ulgurasiz.",
        "Men kutyapman. 😐",
        "Mashq qilamizmi?",
        "Bugungi rejangizda men ham bormanmi?",
        "Birgina dars.",
        "Boshlash uchun ayni vaqt.",
        "Bahona qidiryapsizmi? 😏",
        "5 daqiqada tugaydi.",
        "Hali kech emas.",
        "Men hali shu yerdaman.",
    ],
    "evening": [
        "Endi vaqt oz qoldi.",
        "Seriyangizni unutmang.",
        "Bugun ham davom ettiramizmi?",
        "Men hali kutyapman...",
        "Tayyormisiz yoki yana bahonami? 😏",
        "Hozir qilmasangiz, keyin afsus bo'ladi.",
        "Vaqt yuguryapti.",
        "Hali ulguramiz.",
        "Bugun ham tashlab ketmang.",
        "Oxirgi imkoniyatlar.",
    ],
    "night": [
        "Juda kech bo'lyapti...",
        "Hozir yoki hech qachon.",
        "Seriyangiz xavf ostida.",
        "Men hali uxlaganim yo'q.",
        "Hali ham kutyapman.",
        "Yarim tunga oz qoldi!",
        "Qayerdasiz? 👀",
        "Iltimos...",
        "Bugunni bo'sh qoldirmang.",
        "Men sizga ishonardim... 🥲",
        "Seriyangiz muzlayapti. 🥶",
        "Tezroq qayting!",
    ],
}

# Vazifa bajarilgandan keyingi tabrik.
DONE = [
    "Zo'r! Ertaga ko'rishamiz.",
    "Barakalla!",
    "Ajoyib ish!",
    "Seriya saqlab qolindi. 🔥",
    "Ertaga ham kutaman.",
    "Hali ko'rishamiz.",
    "Juda yaxshi!",
    "Endi bemalol dam oling.",
    "Bugungi ish tugadi.",
    "Tez orada yana ko'rishamiz.",
]

# Seriya endigina buzilganda.
BROKEN = [
    "Yo'q... 😭",
    "Bunday bo'lishi shart emasdi.",
    "Seriya ketdi...",
    "Qayta boshlaymizmi?",
    "Hammasini tiklash mumkin.",
    "Endi yana boshidan.",
    "Afsus...",
    "Juda achinarli.",
    "Men ham xafa bo'ldim.",
    "Bugundan yana boshlaymiz.",
]

# Uzoq vaqt kirmaganda — sog'inch + hazil + biroz "toksik" Duo uslubi.
ABSENT = [
    "Yo'qolib qoldingizmi?",
    "Sizni sog'indim.",
    "Hali eslaysizmi meni? 😅",
    "Salom? 👋",
    "Qachon qaytasiz?",
    "Meni unutdingizmi?",
    "Nega jim bo'lib qoldingiz?",
    "Sizsiz zerikyapman.",
    "Hali ham qaytishingizga ishonaman.",
    "Faqat bitta dars.",
    "Sizni internet yutib yubordimi?",
    "Bahonalar fabrikasi yana ishlayaptimi?",
    "Telefon qo'lingizdami o'zi? 📱",
    "Men sizni ko'rib turibman. 👀",
    "Yana \"ertadan boshlayman\"mi?",
    "Meni ghost qilyapsizmi?",
    "Siz bilan munosabatimiz sovib qoldi.",
    "Xafa qildingiz.",
]

STATE_AT_RISK = "at_risk"
STATE_BROKEN = "broken"
STATE_ABSENT = "absent"
STATE_DONE = "done"


def time_bucket(now):
    """Soatga qarab kun vaqti bo'lagi."""
    hour = now.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "midday"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def pick_message(state, now, *, rng=random):
    """Holat va vaqtga mos tasodifiy mascot xabari."""
    if state == STATE_AT_RISK:
        pool = AT_RISK_BY_TIME[time_bucket(now)]
    elif state == STATE_BROKEN:
        pool = BROKEN
    elif state == STATE_ABSENT:
        pool = ABSENT
    elif state == STATE_DONE:
        pool = DONE
    else:
        pool = AT_RISK_BY_TIME["midday"]
    return rng.choice(pool)
