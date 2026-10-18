"""Public sirtning tayyorligi: owner yozishi shart bo'lgan kontent bormi (PUB1.0e).

Public GET endi hech narsa yaratmaydi. Shuning uchun yo'q narsa jimgina umumiy
namuna bilan to'ldirilmaydi — u shu yerda va Control Center'da ko'rinadi.
"""

from dataclasses import dataclass

# PUB1.0e'gacha birinchi GET yo'q huquqiy sahifani shu umumiy namuna matn
# bilan yaratib, siyosat sifatida e'lon qilardi. Bunday qatorlar productionda
# qolgan bo'lishi mumkin: owner haqiqiy matn bilan almashtirishi kerak.
LEGACY_GENERATED_LEGAL_CONTENT = {
    "privacy": (
        "<h3>Ma'lumotlarni yig'ish</h3><p>Platforma foydalanuvchi hisobini yuritish uchun zarur "
        "ma'lumotlarni yig'adi.</p><h3>Ma'lumotlardan foydalanish</h3><p>Ma'lumotlar xizmat sifatini "
        "oshirish va tizimni ishlatish uchun foydalaniladi.</p>"
    ),
    "terms": (
        "<h3>Umumiy qoidalar</h3><p>Platformadan foydalanish orqali siz xizmat shartlariga rozilik "
        "bildirasiz.</p><h3>Foydalanuvchi majburiyatlari</h3><p>Hisob ma'lumotlarini xavfsiz saqlash "
        "foydalanuvchi zimmasida.</p>"
    ),
    "faq": (
        "<h3>Qanday ro'yxatdan o'taman?</h3><p>Bosh sahifadagi ro'yxatdan o'tish tugmasini bosing va "
        "formani to'ldiring.</p><h3>To'lov qanday ishlaydi?</h3><p>Obuna tarifini tanlab, mavjud to'lov "
        "usuli orqali to'lovni amalga oshirasiz.</p>"
    ),
}

STATE_READY = "ready"
STATE_MISSING = "missing"
STATE_GENERATED = "generated_default"


@dataclass(frozen=True)
class LegalPageState:
    page_type: str
    state: str


@dataclass(frozen=True)
class PublicReadiness:
    legal: tuple[LegalPageState, ...]
    missing_singletons: tuple[str, ...]
    # PUB1.0g'gacha yig'ilgan anonim blog kuzatuvi (qator soni).
    legacy_blog_tracking: int = 0
    # PUB1.2a: da'vo holatlari soni ({status: count}) va fikrlar.
    claims: tuple = ()
    testimonials_public: int = 0
    testimonials_hidden: int = 0
    # PUB1.2d: public sahifada ko'rinadigan (namuna emas) aloqa kanallari.
    public_contact: tuple = ()

    def claim_count(self, status):
        return dict(self.claims).get(status, 0)

    @property
    def missing_legal(self):
        return tuple(item.page_type for item in self.legal if item.state == STATE_MISSING)

    @property
    def generated_legal(self):
        return tuple(item.page_type for item in self.legal if item.state == STATE_GENERATED)


def legal_readiness():
    from frontend.models import LegalPage

    rows = {page.page_type: page for page in LegalPage.objects.all()}
    states = []
    for page_type, _label in LegalPage.PAGE_CHOICES:
        page = rows.get(page_type)
        if page is None:
            state = STATE_MISSING
        elif (page.content or "").strip() == LEGACY_GENERATED_LEGAL_CONTENT[page_type]:
            state = STATE_GENERATED
        else:
            state = STATE_READY
        states.append(LegalPageState(page_type, state))
    return tuple(states)


def missing_singletons():
    """Qatori yo'q public sozlamalar — sahifa kod default'lari bilan chiqadi."""
    from blog.models import BlogHomeSettings
    from frontend.models import AboutPage, AuthPageSettings, LandingPage, SiteSettings

    models = (SiteSettings, AuthPageSettings, LandingPage, AboutPage, BlogHomeSettings)
    return tuple(model._meta.label for model in models if not model.objects.filter(pk=1).exists())


def claim_readiness():
    """(holat bo'yicha da'volar soni, public fikrlar, yashirin faol fikrlar)."""
    from collections import Counter

    from frontend.models import Testimonial
    from frontend.public_claims import all_claims, public_testimonials

    counts = Counter(claim.status for claim in all_claims())
    public = len(public_testimonials(limit=None))
    hidden = Testimonial.objects.filter(is_active=True).count() - public
    return tuple(sorted(counts.items())), public, hidden


def contact_readiness():
    """Owner sozlagan aloqa kanallari; model namunasi hisoblanmaydi (PUB-D7)."""
    from frontend.models import SiteSettings

    settings = SiteSettings.current()
    channels = (("telefon", settings.public_contact_phone), ("email", settings.public_contact_email))
    return tuple(name for name, value in channels if value)


def public_readiness():
    from blog.tracking_cleanup import legacy_tracking

    claims, testimonials_public, testimonials_hidden = claim_readiness()
    return PublicReadiness(
        legal=legal_readiness(),
        missing_singletons=missing_singletons(),
        legacy_blog_tracking=legacy_tracking().total,
        claims=claims,
        testimonials_public=testimonials_public,
        testimonials_hidden=testimonials_hidden,
        public_contact=contact_readiness(),
    )
