"""Owner-only, read-only delivery evidence for one learner's whole account.

Notifications have no course relationship. Neither their URL nor external key
is a reliable substitute, so a selected support course never filters this data.
Reading this projection does not generate notifications, claim an outbox row,
send a message, mark it read, or initialize runtime settings.
"""

from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import BooleanField, Case, Count, F, Q, Value, When
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramOutbox
from bot.outbox import QUIET_HOUR_CATEGORIES, quiet_hours_active
from bot import retry_policy
from core.access import is_control_center_owner
from core.flags import flag_enabled
from core.student_support_service import support_student_queryset
from users.models import Notification


# A presentation page size, not an operational delivery/retry limit.
PAGE_SIZE = 10
CATEGORY_LABELS = {
    Notification.CATEGORY_MANUAL: 'E’lon',
    Notification.CATEGORY_SUBSCRIPTION: 'Obuna haqida',
    Notification.CATEGORY_SYSTEM: 'Platformadan xabar',
    Notification.CATEGORY_STREAK: 'Muntazam o‘qish',
    Notification.CATEGORY_REMINDER: 'Eslatma',
}


def _owner(actor):
    if not getattr(actor, 'is_authenticated', False) or not getattr(actor, 'pk', None):
        raise PermissionDenied
    current = get_user_model().objects.filter(pk=actor.pk).only(
        'pk', 'is_active', 'is_superuser', 'is_staff',
    ).first()
    if current is None or not is_control_center_owner(current):
        raise PermissionDenied
    return current


def _delivery(row, *, student_id, connected, sending_enabled, quiet, now):
    """Describe recorded state and current holds without rewriting either."""
    status = row['telegram_outbox__status']
    next_attempt = row['telegram_outbox__next_attempt_at']
    failure = row['telegram_outbox__failure_kind']
    state, label, detail = 'unknown', 'Holat aniqlanmagan', 'Yetkazish qaydini tizim holatida tekshiring.'
    action_url, action_label = '', ''
    if status is None:
        state, label = 'absent', 'Telegram navbatida yo‘q'
        detail = ('Saytda xabar bor, lekin Telegramga yuborish qaydi yaratilmagan. '
                  'Bu xabar ilgari nima sababdan navbatga tushmagani qayd etilmagan.')
        if not connected:
            detail += ' Hozir o‘quvchi hisobiga Telegram bog‘lanmagan.'
        action_url, action_label = '', ''
    elif status == TelegramOutbox.STATUS_SENT:
        state, label = 'sent', 'Telegramga yuborilgan'
        detail = 'Telegram yuborishni qabul qilgan. Bu o‘quvchi xabarni o‘qiganini bildirmaydi.'
        action_url, action_label = '', ''
    elif status == TelegramOutbox.STATUS_FAILED:
        state, label = 'failed', 'Yuborish to‘xtagan'
        if failure == retry_policy.KIND_PERMANENT:
            detail = ('Qabul qiluvchi bilan bog‘lanishda davomli to‘siq qayd etilgan. '
                      'Bot bloklangan yoki manzil mavjud bo‘lmasligi mumkin. '
                      'Avval sababni aniqlang, keyin qayta yuborish haqida qaror qiling.')
        else:
            detail = ('Avtomatik yuborish yakunlanmagan va qayta urinish to‘xtagan. '
                      'Sababni tekshirib, mavjud boshqaruv sahifasida qayta urinishni tanlash mumkin.')
        action_url = reverse('backoffice_dead_letter') + '?' + urlencode({
            'student': student_id, 'notification': row['pk'],
        })
        action_label = 'Shu xabarni tekshirish'
    elif status == TelegramOutbox.STATUS_SENDING:
        state, label = 'sending', 'Yuborilmoqda'
        detail = 'Yuborish jarayoni boshlangan; yakuniy tasdiq hali qayd etilmagan. Keyinroq qayta tekshiring.'
        action_url, action_label = '', ''
    elif status == TelegramOutbox.STATUS_PENDING:
        state, label = 'queued', 'Navbatda'
        action_url, action_label = '', ''
        if not sending_enabled:
            detail = 'Telegramga yuborish hozir platforma bo‘yicha vaqtincha to‘xtatilgan. Xabar navbatda saqlanmoqda.'
        elif quiet and row['category'] in QUIET_HOUR_CATEGORIES:
            detail = 'Eslatma tinch vaqt tugashini kutmoqda. Saytdagi xabar hozir ham mavjud.'
        elif failure == retry_policy.KIND_CONFIG:
            detail = 'Yuboruvchi xizmat sozlamasida muammo qayd etilgan. Xabar navbatda saqlanmoqda.'
        elif failure == retry_policy.KIND_RATE_LIMITED:
            detail = 'Telegram yuborishni sekinlatishni so‘ragan. Xabar qayta urinish uchun navbatda.'
        elif next_attempt and next_attempt > now:
            detail = 'Yuborish yakunlanmagan. Keyingi avtomatik urinish vaqti belgilangan.'
        else:
            detail = 'Xabar yuborish navbatida. Hali yuborilgan degan tasdiq yo‘q.'

    target_warning = ''
    if status is not None and not row['target_matches_current']:
        target_warning = ('Bu yuborish qaydidagi Telegram manzili o‘quvchining hozir bog‘langan '
                          'hisobiga mos emas. Eski manzil bo‘yicha yetkazish holatini tekshiring.'
                          if connected else
                          'Hozir Telegram bog‘lanmagan. Bu qayd avvalgi yuborish manziliga tegishli.')
    return {
        'telegram_state': state, 'status_label': label, 'detail': detail,
        'target_warning': target_warning,
        'action_url': action_url, 'action_label': action_label,
    }


def build_student_delivery(*, actor, student_id, page=1, status='all'):
    """Return bounded account-wide evidence after fresh owner/target checks."""
    actor = _owner(actor)
    if not isinstance(status, str) or status not in {'all', 'failed'}:
        raise ValueError('Noma’lum bildirishnoma filtri.')
    student = support_student_queryset(actor).filter(pk=student_id).annotate(
        has_telegram=Case(
            When(Q(telegram_id__isnull=True) | Q(telegram_id=0), then=Value(False)),
            default=Value(True), output_field=BooleanField(),
        ),
    ).values('pk', 'has_telegram').get()
    checked_at = timezone.now()
    sending_enabled = flag_enabled('telegram_outbox_sending')
    quiet = quiet_hours_active(checked_at)
    notes = Notification.objects.filter(recipient_id=student['pk'])
    summary = notes.aggregate(
        total=Count('pk'),
        absent=Count('pk', filter=Q(telegram_outbox__isnull=True)),
        queued=Count('pk', filter=Q(telegram_outbox__status=TelegramOutbox.STATUS_PENDING)),
        sending=Count('pk', filter=Q(telegram_outbox__status=TelegramOutbox.STATUS_SENDING)),
        sent=Count('pk', filter=Q(telegram_outbox__status=TelegramOutbox.STATUS_SENT)),
        failed=Count('pk', filter=Q(telegram_outbox__status=TelegramOutbox.STATUS_FAILED)),
    )
    if status == 'failed':
        notes = notes.filter(telegram_outbox__status=TelegramOutbox.STATUS_FAILED)
    # Values (rather than model objects) keep bodies, contact IDs, stored URLs,
    # external keys, claim tokens and raw provider errors outside the renderer.
    notes = notes.annotate(target_matches_current=Case(
        When(telegram_outbox__telegram_id=F('recipient__telegram_id'), then=Value(True)),
        default=Value(False), output_field=BooleanField(),
    )).values(
        'pk', 'title', 'category', 'created_at', 'is_read',
        'telegram_outbox__status', 'telegram_outbox__sent_at',
        'telegram_outbox__next_attempt_at', 'telegram_outbox__failure_kind',
        'target_matches_current',
    ).order_by('-created_at', '-pk')
    paginator = Paginator(notes, PAGE_SIZE)
    paginator.count = summary['failed' if status == 'failed' else 'total']
    page_obj = paginator.get_page(page)
    rows = []
    for row in page_obj:
        rows.append({
            'id': row['pk'], 'title': row['title'] or 'Bildirishnoma',
            'category_label': CATEGORY_LABELS.get(row['category'], 'Bildirishnoma'),
            'created_at': row['created_at'],
            'website_label': ('Saytda o‘qilgan deb belgilangan' if row['is_read'] else 'Saytda bor; o‘qilgan deb belgilanmagan'),
            'sent_at': row['telegram_outbox__sent_at'],
            'next_attempt_at': row['telegram_outbox__next_attempt_at']
                if row['telegram_outbox__status'] == TelegramOutbox.STATUS_PENDING else None,
            **_delivery(row, student_id=student['pk'], connected=student['has_telegram'], sending_enabled=sending_enabled,
                        quiet=quiet, now=checked_at),
        })
    # The paginator itself must not retain the raw database dictionaries.
    page_obj.object_list = rows
    return {
        'rows': rows, 'page_obj': page_obj, 'summary': summary, 'checked_at': checked_at,
        'selected_status': status,
        'scope_label': 'O‘quvchining barcha kurslari va umumiy hisobidagi bildirishnomalar',
        'scope_note': 'Xabarlar alohida kurs bilan bog‘lanmagan. Kurs tanlovi bu ro‘yxatni cheklamaydi.',
        'telegram_connected': student['has_telegram'], 'sending_enabled': sending_enabled,
        'empty_message': ('Bu o‘quvchi uchun yuborishi to‘xtagan xabar topilmadi. '
                          'Qolgan holatlarni ko‘rish uchun barcha bildirishnomalarni oching.'
                          if status == 'failed' else
                          'Bu o‘quvchi uchun saqlangan bildirishnoma topilmadi. '
                          'Bu xabar yaratilishi kerak bo‘lganini yoki nega yaratilmaganini isbotlamaydi.'),
    }
