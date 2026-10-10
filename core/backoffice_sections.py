"""Read-only task entrances over the existing backoffice writers."""
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_GET

from cohorts.models import Cohort
from core.access import teacher_cohort_queryset
from core.backoffice_navigation import FLAG
from core.flags import flag_enabled
from subscriptions.models import Plan


def section_view(*, owner=False):
    def decorate(view):
        @login_required
        @require_GET
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            actor = request.user
            if not actor.is_active or not (actor.is_staff or actor.is_superuser) or (owner and not actor.is_superuser):
                raise PermissionDenied
            if not flag_enabled(FLAG):
                raise Http404
            if any(len(values) != 1 for _, values in request.GET.lists()):
                return HttpResponseBadRequest('Takrorlangan tanlov. Havolani qayta oching.')
            response = view(request, *args, **kwargs)
            patch_cache_control(response, private=True, no_store=True)
            return response
        return wrapped
    return decorate


def card(title, description, route, action, *, query=None, primary=False):
    return {'title': title, 'description': description, 'url': reverse(route) + ('?' + urlencode(query) if query else ''),
            'action': action, 'primary': primary}


def hub(request, title, description, cards):
    return render(request, 'backoffice/workspace/section.html', {
        'frontend_v1_title': title, 'section_title': title, 'section_description': description, 'section_cards': cards,
    })


@section_view()
def payments(request):
    cards = [card('Chekni tekshirish', 'O‘quvchi yuborgan chekni ko‘ring, to‘lov bo‘yicha qaror bering.',
                  'backoffice_receipts', 'Cheklarni ochish', primary=True)]
    if request.user.is_superuser:
        cards += [card('Tariflar', 'Narx, tarif tarkibi va sotuv holatini boshqaring.',
                       'backoffice_workspace_plans', 'Tariflarni ko‘rish')]
    return hub(request, 'To‘lovlar', 'To‘lovni tekshirish yoki tarifni boshqarishdan boshlang.', cards)


@section_view()
def site(request):
    cards = []
    if request.user.is_superuser:
        if flag_enabled('backoffice_design_workspace'):
            cards += [card('Ko‘rinishni moslash', 'Rang, matn va shakllarni tanlang. Natijani namunalarda ko‘rib, saytga tatbiq qiling.',
                           'backoffice_design', 'Dizayn ustaxonasini ochish', primary=True)]
        cards += [card('Logo va brend', 'Platforma nomi, logotipi va brend ma’lumotlarini yangilang.', 'backoffice_brand', 'Brendni tahrirlash'),
                  card('Sayt bosh sahifasi', 'Tashrif buyuruvchilar ko‘radigan bosh sahifa matni va bo‘limlarini tahrirlang.', 'backoffice_landing', 'Bosh sahifani tahrirlash')]
    cards += [card('Blog', 'Maqola yozing, qoralamalarni davom ettiring va nashr holatini boshqaring.', 'blog:studio', 'Maqolalarni ochish')]
    if request.user.is_superuser:
        cards += [card('Turkiyada o‘qish', 'Universitetlar, e’lonlar va qo‘llanmalarni boshqaring.', 'sit_backoffice:dashboard', 'Kontentni ochish')]
    return hub(request, 'Sayt va dizayn', 'Platforma ko‘rinishi va ochiq sahifalar uchun kerakli ishni tanlang.', cards)


@section_view(owner=True)
def settings(request):
    cards = [
        card('Platforma holati', 'Xizmatlar ishlayaptimi va qayerga e’tibor kerakligini ko‘ring.', 'backoffice_control', 'Holatni tekshirish'),
        card('Muddat va limitlar', 'Eslatma, to‘lov tasdig‘i va material saqlash chegaralarini sozlang.', 'backoffice_runtime_settings', 'Sozlamalarni ochish'),
        card('Yoqish va o‘chirish', 'Platforma imkoniyatlarini yoqing yoki vaqtincha o‘chiring.', 'backoffice_feature_flags', 'Imkoniyatlarni ko‘rish'),
        card('Yetkazilmagan xabarlar', 'Yuborilmay qolgan xabarlarni tekshiring va ruxsatli qayta urinishni tanlang.', 'backoffice_dead_letter', 'Xabarlarni tekshirish'),
        card('AI yordamchi', 'Foydalanish limitlari, tariflar bo‘yicha chegaralar va qo‘shimcha imkoniyatlar.', 'backoffice_ai_control', 'AI sozlamalarini ochish'),
        card('AI sarfi va narxlari', 'Foydalanish sarfini ko‘ring va model narxlarini yangilang.', 'backoffice_ai_cost', 'Sarfni ko‘rish'),
        card('Ustozlar', 'Ustoz akkauntlarini toping va mavjud ma’lumotlarini ko‘ring.', 'backoffice_users', 'Ustozlarni ko‘rish', query={'role': 'teachers'}),
        card('Administratorlar', 'Boshqaruv huquqi bor akkauntlar ro‘yxatini ko‘ring.', 'backoffice_users', 'Administratorlarni ko‘rish', query={'role': 'admins'}),
    ]
    return hub(request, 'Sozlamalar', 'Kerakli vazifani oching. Kam ishlatiladigan texnik tafsilotlar uning ichida.', cards)


@section_view()
def groups(request):
    query = request.GET.get('q', '').strip()[:200]
    status = request.GET.get('status', 'all')
    if status not in {'all', 'active', 'closed'}:
        return HttpResponseBadRequest('Guruh holatini qayta tanlang.')
    rows = Cohort.objects.with_seat_metrics().filter(pk__in=teacher_cohort_queryset(request.user)).select_related('course', 'plan')
    if query:
        rows = rows.filter(Q(name__icontains=query) | Q(course__title__icontains=query))
    if status != 'all':
        rows = rows.filter(is_active=status == 'active')
    return render(request, 'backoffice/workspace/groups.html', {
        'frontend_v1_title': 'Guruhlar', 'page_obj': Paginator(rows.order_by('-start_date', '-pk'), 12).get_page(request.GET.get('page')),
        'q': query, 'status_filter': status,
    })


@section_view(owner=True)
def plans(request):
    return render(request, 'backoffice/workspace/plans.html', {
        'frontend_v1_title': 'Tariflar',
        'page_obj': Paginator(Plan.objects.order_by('order', 'pk'), 12).get_page(request.GET.get('page')),
    })
