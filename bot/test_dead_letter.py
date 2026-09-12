"""T6 — dead-letter replay: servis va auditlangan yuza.

PR #101 dead-letter'ni qurdi va qaytarish amalini qurmadi: xabar navbatda
abadiy o'lik yotardi, uni qaytarishning yagona yo'li SQL yozish edi.
`05-launch-ops.md` §2 buni ochiq qarz deb yozgan.

Bu fayl uchta shartni qulflaydi:

1. **Idempotentlik** — ikki marta bosish xabarni ikki marta yubormaydi.
   Himoya shartli `UPDATE` da (`WHERE status='failed'`), sahifa holatida emas:
   ikki brauzer oynasi bir vaqtda bosishi mumkin.
2. **Urinish hisoblagichi nolga qaytadi** — aks holda qaytarilgan xabar
   birinchi transient xatoda darhol yana dead-letter bo'lardi va amal amalda
   hech narsa bermasdi.
3. **`permanent` turi uchun alohida tasdiq** — qayta urinish hech qachon
   yordam bermaydigan qatorni jim qaytarish rate budjetini bekorga yeydi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from bot import retry_policy
from bot.dead_letter import (
    QUEUE_DM,
    QUEUE_GROUP,
    counts,
    parse_keys,
    replay,
    snapshot_for_audit,
    visible_rows,
)
from bot.models import BotRuntimeSettings, TelegramOutbox
from users.models import Notification

User = get_user_model()


def make_dm(*, telegram_id=555, kind=retry_policy.KIND_TRANSIENT, status=None, attempts=5,
            username="deadletter", category=Notification.CATEGORY_SYSTEM):
    user = User.objects.filter(username=username).first() or User.objects.create_user(
        username=username, email=f"{username}@azurelms.test", password="pass-12345"
    )
    notification = Notification.objects.create(
        recipient=user, title="Chek tasdiqlandi", message="To'lovingiz qabul qilindi.",
        category=category,
    )
    # Signal qator yaratadi (F4) — uni terminal holatga keltiramiz.
    row = TelegramOutbox.objects.filter(notification=notification).first()
    if row is None:
        row = TelegramOutbox.objects.create(
            notification=notification, telegram_id=telegram_id
        )
    row.status = status or TelegramOutbox.STATUS_FAILED
    row.attempts = attempts
    row.failure_kind = kind
    row.last_error = "Forbidden: bot was blocked by the user"
    row.next_attempt_at = timezone.now()
    row.claimed_at = timezone.now()
    row.claim_token = "abc123"
    row.save()
    return row


def make_group(*, chat_id=-1001234567, kind=retry_policy.KIND_TRANSIENT, status=None,
               attempts=5, suffix="1"):
    """Classbook guruh navbatidagi terminal qator.

    Fixture ataylab minimal: `ClassbookFixtureMixin` o'nlab obyekt yaratadi va
    bu testlarga ularning hech biri kerak emas — faqat bitta guruh qatori.
    """
    from bot.models import TelegramLessonSession
    from classbook.models import TelegramGroupDelivery
    from cohorts.models import Cohort
    from courses.models import Course, Lesson, Module

    teacher = User.objects.filter(username="dl-teacher").first() or User.objects.create_user(
        username="dl-teacher", email="dl-teacher@azurelms.test", password="pass-12345",
        is_staff=True,
    )
    course = Course.objects.filter(title="DL kursi").first() or Course.objects.create(
        title="DL kursi", description="dead-letter testi", instructor=teacher,
        level="beginner",
    )
    module = Module.objects.filter(course=course).first() or Module.objects.create(
        course=course, title="Modul", order=1,
    )
    lesson = Lesson.objects.filter(module=module).first() or Lesson.objects.create(
        module=module, title="Dars", order=1,
    )
    cohort = Cohort.objects.filter(name="DL guruh").first() or Cohort.objects.create(
        name="DL guruh", course=course, start_date=timezone.localdate(), is_active=True,
        telegram_chat_id=chat_id,
    )
    session = TelegramLessonSession.objects.filter(cohort=cohort).first()
    if session is None:
        session = TelegramLessonSession.objects.create(
            cohort=cohort, lesson=lesson, chat_id=chat_id,
            status=TelegramLessonSession.STATUS_CLOSED,
        )
    return TelegramGroupDelivery.objects.create(
        session=session,
        external_key=f"dl-group-{suffix}",
        chat_id=chat_id,
        kind=TelegramGroupDelivery.KIND_TEXT,
        text="Darsimiz natijasi: 12 ta keldi.",
        status=status or TelegramGroupDelivery.STATUS_FAILED,
        attempts=attempts,
        failure_kind=kind,
        last_error="Forbidden: bot was kicked from the group chat",
        next_attempt_at=timezone.now(),
    )


class ParseKeysTests(TestCase):
    def test_valid_keys_are_grouped_by_queue(self):
        selection, unknown = parse_keys(["dm:1", "group:7", "dm:2"])

        self.assertEqual(selection[QUEUE_DM], [1, 2])
        self.assertEqual(selection[QUEUE_GROUP], [7])
        self.assertEqual(unknown, [])

    def test_garbage_is_reported_not_silently_dropped(self):
        """Buzuq element amalni yiqitmasligi, ammo jim ham o'tmasligi kerak."""
        selection, unknown = parse_keys(["dm:1", "axlat", "dm:abc", "sms:3"])

        self.assertEqual(selection[QUEUE_DM], [1])
        self.assertEqual(unknown, ["axlat", "dm:abc", "sms:3"])

    def test_duplicates_are_collapsed(self):
        selection, _ = parse_keys(["dm:4", "dm:4"])

        self.assertEqual(selection[QUEUE_DM], [4])


class ReplayServiceTests(TestCase):
    def test_a_terminal_row_returns_to_the_queue(self):
        row = make_dm()

        result = replay(keys=[f"dm:{row.pk}"])

        row.refresh_from_db()
        self.assertEqual(result.total_replayed, 1)
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)

    def test_the_attempt_counter_is_reset(self):
        """Aks holda qator birinchi xatoda darhol yana dead-letter bo'lardi."""
        row = make_dm(attempts=5)

        replay(keys=[f"dm:{row.pk}"])

        row.refresh_from_db()
        self.assertEqual(row.attempts, 0)

    def test_the_backoff_and_lease_fields_are_cleared(self):
        row = make_dm()

        replay(keys=[f"dm:{row.pk}"])

        row.refresh_from_db()
        self.assertIsNone(row.next_attempt_at, "kutish vaqti qolsa xabar darhol olinmaydi")
        self.assertIsNone(row.claimed_at)
        self.assertEqual(row.claim_token, "")
        self.assertEqual(row.failure_kind, "")
        self.assertEqual(row.last_error, "")

    def test_replaying_twice_changes_nothing_the_second_time(self):
        """Idempotentlik: ikki marta bosish xabarni ikki marta yubormaydi."""
        row = make_dm()

        first = replay(keys=[f"dm:{row.pk}"])
        second = replay(keys=[f"dm:{row.pk}"])

        self.assertEqual(first.total_replayed, 1)
        self.assertEqual(second.total_replayed, 0)
        self.assertEqual(second.skipped, 1)

    def test_a_row_that_is_not_terminal_is_never_touched(self):
        """Navbatdagi sog'lom qator tasodifan qayta yuborilmasligi kerak."""
        row = make_dm(status=TelegramOutbox.STATUS_SENT, attempts=2)

        result = replay(keys=[f"dm:{row.pk}"])

        row.refresh_from_db()
        self.assertEqual(result.total_replayed, 0)
        self.assertEqual(row.status, TelegramOutbox.STATUS_SENT)
        self.assertEqual(row.attempts, 2, "yuborilgan qator hisoblagichi tiklanmadi")

    def test_permanent_rows_are_counted_so_the_surface_can_warn(self):
        row = make_dm(kind=retry_policy.KIND_PERMANENT)

        result = replay(keys=[f"dm:{row.pk}"])

        self.assertEqual(result.permanent, 1)

    def test_the_permanent_count_describes_rows_that_actually_moved(self):
        """Son `UPDATE` dan keladi, alohida `COUNT` dan emas (PR #109 review).

        Ilgari `permanent` alohida `COUNT` bilan olinardi va keyin `UPDATE`
        qatorlarni qaytarardi. Ikkisi orasida qator holatini boshqa
        tranzaksiya o'zgartirsa, son sodir bo'lmagan ishni bildirardi — ya'ni
        ogohlantirish ham, audit yozuvi ham yolg'on bo'lardi.

        Shart shu yerda invariant sifatida qulflanadi: `permanent` soni
        so'ralgan va **hozir navbatda turgan** permanent qatorlar sonidan
        oshmasligi kerak.
        """
        moved = make_dm(username="dl-perm-moved", kind=retry_policy.KIND_PERMANENT)
        # Bu qator allaqachon navbatda — ya'ni `UPDATE` unga tegmaydi.
        already = make_dm(
            username="dl-perm-already",
            kind=retry_policy.KIND_PERMANENT,
            status=TelegramOutbox.STATUS_PENDING,
        )

        result = replay(keys=[f"dm:{moved.pk}", f"dm:{already.pk}"])

        self.assertEqual(result.total_replayed, 1)
        self.assertEqual(result.permanent, 1, "tegilmagan qator sanalmasligi kerak")
        self.assertLessEqual(result.permanent, result.total_replayed)

    def test_the_two_updates_do_not_double_count_a_row(self):
        """Permanent qator ikkinchi `UPDATE` ga qayta tushmasligi kerak.

        Ikkinchi so'rov `status='failed'` bo'yicha filtrlaydi, birinchisi esa
        qatorni allaqachon `pending` qilgan — shu sabab u avtomatik chetlab
        o'tiladi. Aks holda bitta qator ikki marta sanalardi.
        """
        permanent = make_dm(username="dl-dbl-p", kind=retry_policy.KIND_PERMANENT)
        transient = make_dm(username="dl-dbl-t", kind=retry_policy.KIND_TRANSIENT)

        result = replay(keys=[f"dm:{permanent.pk}", f"dm:{transient.pk}"])

        self.assertEqual(result.total_replayed, 2)
        self.assertEqual(result.permanent, 1)

    def test_the_limit_is_enforced(self):
        rows = [make_dm(username=f"dl{index}") for index in range(3)]

        with self.assertRaises(ValueError):
            replay(keys=[f"dm:{row.pk}" for row in rows], limit=2)

    def test_nothing_is_written_when_the_limit_is_exceeded(self):
        """Chegara xatosi yarim bajarilgan amal qoldirmasligi kerak."""
        rows = [make_dm(username=f"dlx{index}") for index in range(3)]

        with self.assertRaises(ValueError):
            replay(keys=[f"dm:{row.pk}" for row in rows], limit=2)

        for row in rows:
            row.refresh_from_db()
            self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED)


class RowsAndCountsTests(TestCase):
    def test_only_terminal_rows_are_listed(self):
        failed = make_dm(username="dl-failed")
        make_dm(username="dl-sent", status=TelegramOutbox.STATUS_SENT)

        rows = visible_rows(limit=50)

        self.assertEqual([row.pk for row in rows], [failed.pk])

    def test_the_limit_caps_the_list(self):
        for index in range(4):
            make_dm(username=f"dl-cap{index}")

        self.assertEqual(len(visible_rows(limit=2)), 2)

    def test_the_limit_caps_the_two_queues_together_not_each_one(self):
        """Chegara **umumiy**, navbat boshiga emas.

        Nazorat yugurishi shu bo'shliqni ochdi: faqat DM qatorlari bo'lgan
        fixture'da har navbatning o'z qirqimi chegarani bajargandek
        ko'rsatardi, ya'ni umumiy chegarani olib tashlash testni qizartirmasdi.
        Ikki navbatda ham qator bo'lgandagina u ma'no kasb etadi.
        """
        make_dm(username="dl-mix1")
        make_dm(username="dl-mix2")
        make_group(suffix="mix1")
        make_group(suffix="mix2")

        self.assertEqual(len(visible_rows(limit=3)), 3)

    def test_permanent_rows_are_counted_separately(self):
        make_dm(username="dl-perm", kind=retry_policy.KIND_PERMANENT)
        make_dm(username="dl-tran", kind=retry_policy.KIND_TRANSIENT)

        summary = counts()

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["permanent"], 1)

    def test_a_row_carries_the_diagnosis_the_owner_needs(self):
        row = make_dm(username="dl-detail", kind=retry_policy.KIND_PERMANENT)

        item = visible_rows(limit=10)[0]

        self.assertEqual(item.pk, row.pk)
        self.assertTrue(item.is_permanent)
        self.assertIn("blocked", item.last_error)
        self.assertEqual(item.key, f"dm:{row.pk}")

    def test_the_audit_snapshot_keeps_the_failure_diagnosis(self):
        """`last_error` replay paytida tozalanadi — sabab faqat shu yerda qoladi."""
        make_dm(username="dl-snap", kind=retry_policy.KIND_PERMANENT)
        make_dm(username="dl-snap2", kind=retry_policy.KIND_TRANSIENT)

        snapshot = snapshot_for_audit(visible_rows(limit=10))

        self.assertEqual(snapshot["count"], 2)
        self.assertEqual(snapshot["kinds"][retry_policy.KIND_PERMANENT], 1)
        self.assertEqual(snapshot["kinds"][retry_policy.KIND_TRANSIENT], 1)


class DeadLetterSurfaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="t6owner", email="t6owner@azurelms.test", password="pass-12345"
        )
        self.url = reverse("backoffice_dead_letter")

    def _payload(self, row, **overrides):
        data = {
            "rows": [f"dm:{row.pk}"],
            "change_reason": "Token tuzatildi",
            "confirm_change": "on",
        }
        data.update(overrides)
        return data

    def test_non_owner_cannot_open_the_page(self):
        student = User.objects.create_user(
            username="t6student", email="t6student@azurelms.test", password="pass-12345"
        )
        self.client.force_login(student)

        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_the_page_renders_each_terminal_row(self):
        row = make_dm(username="dl-page")
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="dm:{row.pk}"')
        self.assertContains(response, "dl-page")

    def test_an_empty_queue_says_so_instead_of_showing_an_empty_form(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertContains(response, "Qaytariladigan narsa yo'q")
        self.assertNotContains(response, 'name="change_reason"')

    def test_replay_is_audited(self):
        row = make_dm(username="dl-audit")
        self.client.force_login(self.owner)

        self.client.post(self.url, self._payload(row))

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        event = SystemAuditEvent.objects.filter(
            action="telegram.dead_letter.replay"
        ).first()
        self.assertIsNotNone(event, "audit yozuvi yozilmadi")
        self.assertEqual(event.reason, "Token tuzatildi")
        self.assertEqual(event.after["replayed"], 1)
        self.assertEqual(event.actor, self.owner)

    def test_the_audit_before_snapshot_records_why_it_had_died(self):
        row = make_dm(username="dl-why", kind=retry_policy.KIND_PERMANENT)
        self.client.force_login(self.owner)

        self.client.post(
            self.url, self._payload(row, acknowledge_permanent="on")
        )

        event = SystemAuditEvent.objects.get(action="telegram.dead_letter.replay")
        self.assertEqual(event.before["kinds"][retry_policy.KIND_PERMANENT], 1)

    def test_reason_is_mandatory(self):
        row = make_dm(username="dl-noreason")
        self.client.force_login(self.owner)

        response = self.client.post(self.url, self._payload(row, change_reason=""))

        row.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_confirmation_is_mandatory(self):
        row = make_dm(username="dl-noconfirm")
        self.client.force_login(self.owner)
        payload = self._payload(row)
        payload.pop("confirm_change")

        self.client.post(self.url, payload)

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_a_permanent_row_needs_the_extra_acknowledgement(self):
        """Bloklagan foydalanuvchiga qayta yuborish rate budjetini yeydi."""
        row = make_dm(username="dl-perm-ack", kind=retry_policy.KIND_PERMANENT)
        self.client.force_login(self.owner)

        response = self.client.post(self.url, self._payload(row))

        row.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED, "tasdiqsiz qaytdi")
        self.assertContains(response, "tuzalmaydi")

    def test_a_permanent_row_replays_once_acknowledged(self):
        """Ogohlantirish to'siq emas: owner blokni yechgan bo'lishi mumkin."""
        row = make_dm(username="dl-perm-ok", kind=retry_policy.KIND_PERMANENT)
        self.client.force_login(self.owner)

        self.client.post(self.url, self._payload(row, acknowledge_permanent="on"))

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)

    def test_a_transient_row_does_not_need_the_extra_acknowledgement(self):
        row = make_dm(username="dl-tran-ok", kind=retry_policy.KIND_TRANSIENT)
        self.client.force_login(self.owner)

        self.client.post(self.url, self._payload(row))

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)

    def test_a_row_that_was_never_shown_is_rejected(self):
        """Brauzerdan kelgan tasodifiy id qabul qilinmaydi."""
        make_dm(username="dl-shown")
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {
                "rows": ["dm:999999"],
                "change_reason": "sinov",
                "confirm_change": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_a_second_identical_post_writes_no_audit_event(self):
        """No-op yo'l: audit tarixi hech narsa qilmagan bosishlar bilan to'lmaydi."""
        row = make_dm(username="dl-twice")
        self.client.force_login(self.owner)
        self.client.post(self.url, self._payload(row))

        # Qator endi `pending`, ya'ni sahifada ko'rinmaydi — tanlov ham
        # qabul qilinmaydi. Ikkala himoya ham bitta natijaga olib keladi.
        self.client.post(self.url, self._payload(row))

        self.assertEqual(
            SystemAuditEvent.objects.filter(
                action="telegram.dead_letter.replay"
            ).count(),
            1,
        )

    def test_a_replay_that_changes_nothing_writes_no_audit_event(self):
        """Yuzaning no-op tarmog'i — ustidagi test unga yetib bormaydi.

        Nazorat yugurishi shuni ko'rsatdi: `if result.total_replayed:` shartini
        olib tashlaganda **hech bir test qizarmadi**, chunki ikkinchi POST
        formadan o'tmay qaytadi va yuzaning bu tarmog'iga umuman kirmaydi.
        Poygani (qator POST bilan `replay()` orasida boshqa jarayon tomonidan
        qaytarilishi) tabiiy yo'l bilan yasab bo'lmaydi, shuning uchun servis
        natijasi to'g'ridan-to'g'ri almashtiriladi: tekshirilayotgan narsa —
        yuzaning qaroridir, servisning ishi emas.
        """
        from unittest.mock import patch

        from bot.dead_letter import ReplayResult

        row = make_dm(username="dl-noop")
        self.client.force_login(self.owner)
        empty = ReplayResult(replayed={"dm": 0, "group": 0}, requested={"dm": [row.pk]})

        with patch("bot.dead_letter.replay", return_value=empty):
            response = self.client.post(self.url, self._payload(row), follow=True)

        self.assertFalse(
            SystemAuditEvent.objects.filter(
                action="telegram.dead_letter.replay"
            ).exists(),
            "hech narsa o'zgarmaganda ledgerga yozilmasligi kerak",
        )
        self.assertContains(response, "allaqachon navbatda")

    def test_selecting_nothing_is_rejected(self):
        make_dm(username="dl-none")
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url, {"change_reason": "sinov", "confirm_change": "on"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_the_page_honours_the_owner_limit(self):
        # Ikki navbatdan ham qator: umumiy chegara faqat shunda o'lchanadi.
        for index in range(2):
            make_dm(username=f"dl-limit{index}")
        for index in range(2):
            make_group(suffix=f"limit{index}")
        settings_row = BotRuntimeSettings.load()
        settings_row.dead_letter_replay_limit = 2
        settings_row.save()
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["rows"]), 2)
        self.assertEqual(response.context["truncated"], 2)
        self.assertContains(response, "ko'rinmayapti")


class BothQueuesTests(TestCase):
    """Ikki navbat bitta amal bilan qaytariladi.

    Modulning butun mavjudlik sababi shu: `bot.TelegramOutbox` va
    `classbook.TelegramGroupDelivery` alohida modellar, ammo bu amal uchun bir
    xil shaklda. Faqat DM sinalsa, guruh yo'li jim buzilishi mumkin edi —
    qayta urinish siyosatida aynan shu xavf uchun bitta canonical modul bor.
    """

    def test_a_group_row_is_listed_next_to_a_dm_row(self):
        make_dm(username="dl-both-dm")
        group = make_group(suffix="listed")

        keys = {row.key for row in visible_rows(limit=50)}

        self.assertIn(f"group:{group.pk}", keys)
        self.assertEqual(len(keys), 2)

    def test_one_action_replays_rows_from_both_queues(self):
        dm = make_dm(username="dl-both-replay")
        group = make_group(suffix="replay")

        result = replay(keys=[f"dm:{dm.pk}", f"group:{group.pk}"])

        dm.refresh_from_db()
        group.refresh_from_db()
        self.assertEqual(result.total_replayed, 2)
        self.assertEqual(dm.status, TelegramOutbox.STATUS_PENDING)
        self.assertEqual(group.status, group.STATUS_PENDING)
        self.assertEqual(group.attempts, 0)
        self.assertIsNone(group.next_attempt_at)
        self.assertEqual(group.failure_kind, "")

    def test_counts_cover_both_queues(self):
        make_dm(username="dl-both-count")
        make_group(suffix="count", kind=retry_policy.KIND_PERMANENT)

        summary = counts()

        self.assertEqual(summary["dm"], 1)
        self.assertEqual(summary["group"], 1)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["permanent"], 1)

    def test_a_group_row_replays_from_the_page(self):
        group = make_group(suffix="surface")
        owner = User.objects.create_superuser(
            username="t6group", email="t6group@azurelms.test", password="pass-12345"
        )
        self.client.force_login(owner)

        self.client.post(
            reverse("backoffice_dead_letter"),
            {
                "rows": [f"group:{group.pk}"],
                "change_reason": "Bot guruhga qaytarildi",
                "confirm_change": "on",
            },
        )

        group.refresh_from_db()
        self.assertEqual(group.status, group.STATUS_PENDING)
        self.assertEqual(
            SystemAuditEvent.objects.get(
                action="telegram.dead_letter.replay"
            ).after["group"],
            1,
        )


class ControlCenterLinkTests(TestCase):
    def test_the_page_is_reachable_from_the_control_center(self):
        """Yuza qurildi, ammo unga yo'l bo'lmasa owner uni topmaydi."""
        owner = User.objects.create_superuser(
            username="t6nav", email="t6nav@azurelms.test", password="pass-12345"
        )
        self.client.force_login(owner)

        response = self.client.get(reverse("backoffice_control"))

        self.assertContains(response, reverse("backoffice_dead_letter"))
