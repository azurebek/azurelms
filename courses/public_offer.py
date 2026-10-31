"""Ochiq kurs taklifi — kurs, faol guruh va sotuvdagi tariflarning o'qish proyeksiyasi (PUB1.3b).

Yangi model yoki narx manbai emas. Hammasi checkout ishlatadigan canonical
manbalardan olinadi:

* sotuvdagi tariflar — `subscriptions.catalog.purchase_plans()` (mehmon uchun);
* xaridor qo'shiladigan guruh — `cohorts.checkout_service.choose_checkout_cohort`
  (checkout'dagi `pick_checkout_cohort` ham aynan shu funksiya);
* to'lov davri — `cohorts.checkout_service.checkout_period`;
* narx — `Plan.price` (Kursdagi eski `price` maydoni ishlatilmaydi).

Natija faqat o'qiladi: sahifa ochilishi hech narsa yozmaydi. Joy va narx
render paytidagi surat — checkout POST ularni qayta tekshiradi. Ma'lum
bo'lmagan qiymat taxmin qilinmaydi: guruh yo'q bo'lsa sana ham yo'q.
"""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone

# Mavjudlik sababi (taxonomy). Matn shablonda emas — bitta joyda.
AVAILABLE = "available"
NOT_OPEN = "not_open"  # tarifga mos faol guruh yo'q
FULL = "full"  # mos guruhlar bor, hammasi to'lgan
NO_PLANS = "no_plans"  # sotuvdagi tarif yo'q

REASON_TEXT = {
    AVAILABLE: "Qabul ochiq",
    NOT_OPEN: "Bu kursga qabul hozircha ochilmagan.",
    FULL: "Bu kursdagi guruhlar hozircha to‘lgan.",
    NO_PLANS: "Bu kurs uchun tariflar hali e’lon qilinmagan.",
}
REASON_LABEL = {
    AVAILABLE: "Qabul ochiq",
    NOT_OPEN: "Qabul hali ochilmagan",
    FULL: "Guruhlar to‘lgan",
    NO_PLANS: "Tariflar e’lon qilinmagan",
}

# CTA manzili (enum) — shablon URL'ni o'zi tanlamaydi.
STUDY = "study"
CHECKOUT = "checkout"
CATALOG = "catalog"


@dataclass(frozen=True)
class PlanOffer:
    plan_id: int
    code: str
    name: str
    price: Decimal
    period_days: int
    included: tuple
    excluded: tuple
    group_size_claim: str
    is_popular: bool
    reason: str
    cohort_id: int | None = None
    cohort_start: date | None = None

    @property
    def available(self):
        return self.reason == AVAILABLE


@dataclass(frozen=True)
class CourseOffer:
    course_id: int
    active_cohort_count: int
    plans: tuple
    reason: str
    next_start: date | None
    today: date
    source_revision: str = field(default="")

    @property
    def available(self):
        return self.reason == AVAILABLE

    @property
    def reason_text(self):
        return REASON_TEXT[self.reason]

    @property
    def reason_label(self):
        return REASON_LABEL[self.reason]

    @property
    def starts_later(self):
        """Keyingi guruh hali boshlanmagan (sana kelajakda)."""
        return self.next_start is not None and self.next_start > self.today

    def plan(self, plan_id):
        return next((plan for plan in self.plans if plan.plan_id == plan_id), None)

    @property
    def available_plans(self):
        return tuple(plan for plan in self.plans if plan.available)

    @property
    def lowest_price(self):
        """Hozir sotib olish mumkin bo'lgan eng arzon tarif narxi (yo'q bo'lsa `None`)."""
        prices = [plan.price for plan in self.available_plans]
        return min(prices) if prices else None

    @property
    def period_days(self):
        return self.plans[0].period_days if self.plans else None


@dataclass(frozen=True)
class OfferCta:
    destination: str
    auth_required: bool
    reason: str


def _period_days(today):
    from cohorts.checkout_service import checkout_period

    start, end = checkout_period(None, today=today)
    return (end - start).days


def billing_period_days(today=None):
    """Tarif davri (kun) — kurs taklifidagi `period_days` bilan bir manba (checkout davri)."""
    return _period_days(today or timezone.localdate())


def _sale_plans():
    from subscriptions.catalog import purchase_plans
    from subscriptions.models import PlanFeature

    features = Prefetch("features", queryset=PlanFeature.objects.order_by("order", "id"))
    return list(purchase_plans().prefetch_related(features))


def _plan_offer(plan, cohorts, *, today, period_days):
    from cohorts.checkout_service import choose_checkout_cohort, cohort_matches_plan

    cohort = choose_checkout_cohort(cohorts, today=today, plan=plan)
    if cohort is not None:
        reason = AVAILABLE
    elif any(cohort_matches_plan(candidate, plan) for candidate in cohorts):
        reason = FULL
    else:
        reason = NOT_OPEN
    features = list(plan.features.all())
    return PlanOffer(
        plan_id=plan.pk,
        code=plan.code,
        name=plan.name,
        price=plan.price,
        period_days=period_days,
        included=tuple(feature.name for feature in features if feature.is_included),
        excluded=tuple(feature.name for feature in features if not feature.is_included),
        group_size_claim=plan.group_size_claim,
        is_popular=plan.is_popular,
        reason=reason,
        cohort_id=cohort.pk if cohort else None,
        cohort_start=cohort.start_date if cohort else None,
    )


def _course_offer(course_id, cohorts, plans, *, today, period_days):
    plan_offers = tuple(_plan_offer(plan, cohorts, today=today, period_days=period_days) for plan in plans)
    reasons = {offer.reason for offer in plan_offers}
    if not plan_offers:
        reason = NO_PLANS
    elif AVAILABLE in reasons:
        reason = AVAILABLE
    elif FULL in reasons:
        reason = FULL
    else:
        reason = NOT_OPEN
    starts = [offer.cohort_start for offer in plan_offers if offer.available]
    offer = CourseOffer(
        course_id=course_id,
        active_cohort_count=len(cohorts),
        plans=plan_offers,
        reason=reason,
        next_start=min(starts) if starts else None,
        today=today,
    )
    return _with_revision(offer)


def _with_revision(offer):
    """Kirish faktlarining barmoq izi: ularning birortasi o'zgarsa qiymat o'zgaradi."""
    facts = {
        "course": offer.course_id,
        "cohorts": offer.active_cohort_count,
        "reason": offer.reason,
        "plans": [
            [plan.plan_id, plan.code, plan.name, str(plan.price), plan.period_days, plan.included, plan.excluded,
             plan.group_size_claim, plan.reason, plan.cohort_id, plan.cohort_start]
            for plan in offer.plans
        ],
    }
    digest = hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return replace(offer, source_revision=digest)


def build_offers(courses, *, today=None):
    """Bir nechta kurs uchun takliflar `{course_id: CourseOffer}` — kurslar sonidan qat'i nazar 3 so'rov."""
    from cohorts.models import Cohort

    course_ids = [course.pk for course in courses]
    if not course_ids:
        return {}
    today = today or timezone.localdate()
    plans = _sale_plans()
    cohorts = defaultdict(list)
    for cohort in (
        Cohort.objects.filter(course_id__in=course_ids, is_active=True)
        .with_seat_metrics(today=today)
        .order_by("course_id", "start_date", "id")
    ):
        cohorts[cohort.course_id].append(cohort)
    period_days = _period_days(today)
    return {
        course_id: _course_offer(course_id, cohorts[course_id], plans, today=today, period_days=period_days)
        for course_id in course_ids
    }


def build_offer(course, *, today=None):
    return build_offers([course], today=today)[course.pk]


@dataclass(frozen=True)
class CourseFacts:
    """Kurs sahifasidagi faktlar — faqat bazada borini; 0 yoki bo'sh fakt ko'rsatilmaydi (PUB1.3c)."""

    lessons: int
    modules: int
    exams: int
    learners: int
    certificate: bool
    certificate_conditions: tuple
    preview_video_url: str


def build_course_facts(course, modules, *, learners):
    """`modules` — `lessons` bilan prefetch qilingan; `course.exams` ham prefetch qilingan.

    Sertifikat faqat kursda oraliq (visa) va yakuniy imtihon ikkalasi bo'lsa
    va'da qilinadi: `courses.completion_service` aynan shu ikkisidan o'tishni
    talab qiladi. Qo'shimcha shartlar kurs sozlamasidan (`policy_service`).
    """
    exam_types = {exam.exam_type for exam in course.exams.all()}
    conditions = []
    if course.certificate_min_lesson_completion_percent:
        conditions.append(f"darslarning kamida {course.certificate_min_lesson_completion_percent}% bajarilgan bo‘lishi")
    if course.certificate_min_attendance_percent:
        conditions.append(f"davomat kamida {course.certificate_min_attendance_percent}% bo‘lishi")
    if course.certificate_requires_all_assignments_approved:
        conditions.append("barcha topshiriqlar tasdiqlangan bo‘lishi")
    video = getattr(course, "preview_video", None)
    return CourseFacts(
        lessons=sum(len(module.lessons.all()) for module in modules),
        modules=len(modules),
        exams=len(course.exams.all()),
        learners=learners,
        certificate={"visa", "final"} <= exam_types,
        certificate_conditions=tuple(conditions),
        preview_video_url=video.url if video else "",
    )


def offer_cta(offer, *, user, is_enrolled):
    """Ko'rayotgan odam uchun keyingi qadam.

    O'qiyotgan a'zo — darsga. Qabul ochiq bo'lsa — checkout (mehmonga avval
    kirish kerak). Qabul yopiq bo'lsa ham kursda a'zoligi bor odam (muddati
    o'tgan, kutilayotgan) checkout'da davom eta oladi — checkout shuni
    ruxsat beradi. Qolganlarga — sabab va katalog.
    """
    if is_enrolled:
        return OfferCta(STUDY, False, "enrolled")
    authenticated = bool(getattr(user, "is_authenticated", False))
    if offer.available:
        return OfferCta(CHECKOUT, not authenticated, AVAILABLE)
    if authenticated and _has_continuing_membership(user, offer.course_id):
        return OfferCta(CHECKOUT, False, "continuing_member")
    return OfferCta(CATALOG, False, offer.reason)


def _has_continuing_membership(user, course_id):
    from cohorts.models import Enrollment

    return (
        Enrollment.objects.filter(student=user, cohort__course_id=course_id)
        .exclude(status=Enrollment.STATUS_FROZEN)
        .exists()
    )


@dataclass(frozen=True)
class IntentResolution:
    url: str
    message: str = ""
    outcome: str = ""


def resolve_purchase_intent(intent, *, user, today=None):
    """Imzoli niyatni hozirgi holatga ko'ra manzilga aylantiradi (PUB1.3d) — hech narsa yozmaydi.

    Niyat buyurtma emas: kurs faolligi, o'quvchining a'zoligi, qabul va tarif
    shu yerda qayta tekshiriladi; narxni checkout o'zi hisoblaydi. Kurs yopilgan
    yoki tarif endi sotilmasa odam checkout'ga yuborilib qaytarilmaydi — sabab
    xabar bilan aytiladi.
    """
    from django.urls import reverse

    from cohorts.models import Enrollment, enrollment_active_access_q
    from courses.models import Course
    from frontend import public_intent

    catalog = reverse("courses")
    if intent.destination == public_intent.CATALOG:
        return IntentResolution(catalog, outcome="catalog")
    course = Course.objects.filter(pk=intent.course_id, is_active=True).first()
    if course is None:
        return IntentResolution(catalog, "Bu kurs hozir mavjud emas. Boshqa kurslarni ko‘ring.", "course_gone")
    detail = reverse("course_detail", args=[course.pk])
    if intent.destination == public_intent.COURSE_DETAIL:
        return IntentResolution(detail, outcome="course_detail")
    if Enrollment.objects.filter(enrollment_active_access_q(), student=user, cohort__course=course).exists():
        return IntentResolution(detail, "Siz bu kursda allaqachon o‘qiyapsiz.", "enrolled")
    offer = build_offer(course, today=today)
    if offer_cta(offer, user=user, is_enrolled=False).destination != CHECKOUT:
        return IntentResolution(detail, offer.reason_text, "closed")
    checkout = reverse("cohorts:checkout", kwargs={"course_id": course.pk})
    if not intent.plan_code:
        return IntentResolution(checkout, outcome="checkout")
    plan = next((plan for plan in offer.plans if plan.code == intent.plan_code), None)
    if plan is not None and plan.available:
        return IntentResolution(f"{checkout}?plan_id={plan.plan_id}", outcome="checkout_plan")
    return IntentResolution(
        checkout, "Tanlangan tarif hozir mavjud emas — mavjud tariflardan birini tanlang.", "plan_unavailable",
    )


def plan_links(offer, *, course_id, user):
    """Sidebar'dagi har mavjud tarif uchun “shu tarif bilan davom etish” manzili.

    Kirgan odam — to'g'ridan-to'g'ri checkout (`plan_id` bilan; checkout uni qayta
    tekshiradi). Mehmon — imzoli niyat bilan kirish sahifasi.
    """
    from urllib.parse import urlencode

    from django.urls import reverse

    from frontend import public_intent

    links = []
    for plan in offer.available_plans:
        if getattr(user, "is_authenticated", False):
            url = reverse("cohorts:checkout", kwargs={"course_id": course_id}) + f"?plan_id={plan.plan_id}"
        else:
            target = public_intent.continue_url(public_intent.COURSE_CHECKOUT, course_id=course_id, plan_code=plan.code or None)
            url = reverse("login") + "?" + urlencode({"next": target})
        links.append((plan, url))
    return links
