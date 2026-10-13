"""Bounded, read-only search across the existing scoped backoffice entrances."""
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Replace
from django.http import Http404, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_GET

from cohorts.models import Enrollment
from core.access import teacher_course_queryset
from core.backoffice_navigation import FLAG, flags, navigation, section_links
from core.student_support_service import support_student_queryset
from courses.models import Lesson

# Rendering bounds, not configurable operational limits or business policy.
PAGE_SIZE = 12
QUERY_MAX_LENGTH = 200
KINDS = (
    ('all', 'Barchasi'), ('course', 'Kurslar'), ('lesson', 'Darslar'),
    ('student', 'O‘quvchilar'), ('section', 'Bo‘limlar'),
)
LABELS = {'course': 'Kurs', 'lesson': 'Dars', 'student': 'O‘quvchi', 'section': 'Bo‘lim'}
APOSTROPHE_VARIANTS = ('‘', '’', 'ʻ', 'ʼ', '`')


def search_view(view):
    @login_required
    @require_GET
    @wraps(view)
    def authorized(request, *args, **kwargs):
        actor = get_user_model().objects.filter(pk=request.user.pk, is_active=True).first()
        if actor is None or not (actor.is_staff or actor.is_superuser):
            raise PermissionDenied
        request.user = actor
        if not flags(request)[FLAG]:
            raise Http404
        if any(len(values) != 1 for _, values in request.GET.lists()):
            return _invalid_search(request, 'Tanlov takrorlangan. Qidiruvni qayta bajaring.')
        return view(request, *args, **kwargs)

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            response = authorized(request, *args, **kwargs)
        except PermissionDenied:
            response = HttpResponseForbidden('Bu sahifaga kirish huquqi yo‘q.')
        except Http404:
            response = HttpResponseNotFound('Tanlangan ma’lumot topilmadi.')
        patch_cache_control(response, private=True, no_store=True)
        return response
    return wrapped


def _url(route, *, kwargs=None, **params):
    query = urlencode({key: value for key, value in params.items() if value not in ('', None)})
    return reverse(route, kwargs=kwargs) + ('?' + query if query else '')


def _normalized_apostrophes(value):
    for apostrophe in APOSTROPHE_VARIANTS:
        value = value.replace(apostrophe, "'")
    return value


def _matching_terms(rows, terms, fields):
    terms = [_normalized_apostrophes(term) for term in terms]
    if any("'" in term for term in terms):
        # Uzbek names may use keyboard or typographic apostrophes. Normalize
        # just the searched short fields in SQL; never fetch content to Python.
        aliases = {}
        for index, field in enumerate(fields):
            expression = F(field)
            for apostrophe in APOSTROPHE_VARIANTS:
                expression = Replace(expression, Value(apostrophe), Value("'"))
            aliases[f'_search_match_{index}'] = expression
        rows = rows.alias(**aliases)
        fields = tuple(aliases)
    for term in terms:
        condition = Q()
        for field in fields:
            condition |= Q(**{f'{field}__icontains': term})
        rows = rows.filter(condition)
    return rows


def _section_rows(request, terms):
    """The presentation registry supplies the entire allowed route set."""
    rows, seen = [], set()
    for section in navigation(request, None):
        links = [section] + section_links(request, section['key'])
        for item in links:
            if item['url'] in seen:
                continue
            seen.add(item['url'])
            searchable = _normalized_apostrophes(f"{item['label']} {section['label']}").casefold()
            if not all(_normalized_apostrophes(term).casefold() in searchable for term in terms):
                continue
            rows.append({'kind': 'section', 'label': LABELS['section'], 'title': item['label'],
                         'subtitle': section['label'] if item['label'] != section['label'] else 'Boshqaruv bo‘limi',
                         'url': item['url']})
    return rows


def _course_row(item):
    return {'kind': 'course', 'label': LABELS['course'], 'title': item['title'],
            'subtitle': 'Katalogda ko‘rinadi' if item['is_active'] else 'Katalogda yashirilgan',
            'url': _url('backoffice_workspace_course', kwargs={'course_id': item['pk']})}


def _lesson_row(item):
    return {'kind': 'lesson', 'label': LABELS['lesson'], 'title': item['title'],
            'subtitle': f"{item['module__course__title']} · {item['module__title']}",
            'url': _url('backoffice_workspace_course', kwargs={'course_id': item['module__course_id']}, lesson=item['pk'])}


def _student_row(item):
    name = ' '.join(value for value in (item['first_name'].strip(), item['last_name'].strip()) if value)
    return {'kind': 'student', 'label': LABELS['student'], 'title': name or item['username'],
            'subtitle': f"@{item['username']} · {item['search_course_title'] or 'Kursga yozilmagan'}",
            'url': _url('backoffice_workspace_student', kwargs={'student_id': item['pk']})}


class _BoundedResults:
    """Paginator sequence: COUNT each group; fetch only this page's intersections.

    QuerySet slices are deliberately evaluated after pagination. In particular,
    a learner result never prefetches their unbounded enrollment history.
    """
    def __init__(self, groups):
        self.groups = [(rows, project, rows.count() if hasattr(rows, 'query') else len(rows))
                       for rows, project in groups]

    def __len__(self):
        return sum(count for _, _, count in self.groups)

    def __getitem__(self, bounds):
        if not isinstance(bounds, slice) or bounds.step not in (None, 1):
            raise TypeError('Search results require a bounded page slice.')
        start, stop, _ = bounds.indices(len(self))
        output, offset = [], 0
        for rows, project, count in self.groups:
            left, right = max(start - offset, 0), min(stop - offset, count)
            if left < right:
                output.extend(project(item) for item in rows[left:right])
            offset += count
            if offset >= stop:
                break
        return output


def search_context(request, *, query, kind='all', page='1'):
    """Read projection; caller supplies the freshly authorized request actor."""
    terms, groups = query.split(), []
    enabled = flags(request)
    course_scope = teacher_course_queryset(request.user)
    if terms and enabled['backoffice_course_workspace']:
        if kind in {'all', 'course'}:
            rows = _matching_terms(course_scope, terms, ('title',)).order_by('title', 'pk')
            groups.append((rows.values('pk', 'title', 'is_active'), _course_row))
        if kind in {'all', 'lesson'}:
            rows = _matching_terms(Lesson.objects.filter(module__course__in=course_scope), terms,
                                   ('title', 'module__title', 'module__course__title'))
            rows = rows.order_by('module__course__title', 'module__course_id', 'module__order',
                                 'module_id', 'order', 'pk')
            groups.append((rows.values('pk', 'title', 'module__title', 'module__course_id',
                                      'module__course__title'), _lesson_row))
    if terms and enabled['backoffice_student_support'] and kind in {'all', 'student'}:
        students = _matching_terms(support_student_queryset(request.user), terms,
                                   ('first_name', 'last_name', 'username'))
        visible_course = Enrollment.objects.filter(student_id=OuterRef('pk'), cohort__course__in=course_scope)
        students = students.annotate(search_course_title=Subquery(
            visible_course.order_by('-joined_at', '-pk').values('cohort__course__title')[:1],
        )).order_by('first_name', 'last_name', 'username', 'pk')
        groups.append((students.values('pk', 'first_name', 'last_name', 'username', 'search_course_title'), _student_row))
    if kind in {'all', 'section'}:
        groups.append((_section_rows(request, terms), lambda row: row))
    page_obj = Paginator(_BoundedResults(groups), PAGE_SIZE).get_page(page)
    rows = list(page_obj)
    tabs = [{'key': key, 'label': label, 'active': key == kind,
             'url': _url('backoffice_workspace_search', q=query, kind=key)} for key, label in KINDS
            if key not in {'course', 'lesson'} or enabled['backoffice_course_workspace']]
    if not enabled['backoffice_student_support']:
        tabs = [tab for tab in tabs if tab['key'] != 'student']
    return {'frontend_v1_title': 'Qidiruv', 'workspace_nav': navigation(request, None),
            'rows': rows, 'search_rows': rows, 'page_obj': page_obj, 'q': query, 'kind': kind,
            'tabs': tabs, 'search_tabs': tabs, 'pagination_query': urlencode({'q': query, 'kind': kind})}


def _invalid_search(request, message):
    # Invalid inputs do not search entity records. Keep a usable, scoped shell
    # and a bounded query value so the user can correct their search in place.
    context = search_context(request, query='')
    bounded_query = request.GET.get('q', '')[:QUERY_MAX_LENGTH]
    visible_query = ''.join(character if ord(character) >= 32 and ord(character) != 127 else ' '
                            for character in bounded_query)
    context.update(q=visible_query, search_error=message)
    return render(request, 'backoffice/workspace/search.html', context, status=400)


@search_view
def search(request):
    raw_query = request.GET.get('q', '')
    kind, page = request.GET.get('kind', 'all'), request.GET.get('page', '1')
    if len(raw_query) > QUERY_MAX_LENGTH:
        return _invalid_search(request, 'Qidiruv juda uzun. Dastlabki 200 belgi qoldirildi; nom yoki foydalanuvchi nomini yozing.')
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_query):
        return _invalid_search(request, 'Qidiruvni bir qatorda yozing. Ko‘rinmaydigan belgilar olib tashlandi; qayta qidiring.')
    if kind not in dict(KINDS):
        return _invalid_search(request, 'Qidiruv turini qayta tanlang.')
    if not page.isascii() or not page.isdecimal() or len(page) > 8 or int(page) < 1:
        return _invalid_search(request, 'Qidiruv sahifasi noto‘g‘ri. Qidiruvni qayta bajaring.')
    context = search_context(request, query=' '.join(raw_query.split()), kind=kind, page=page)
    from core.backoffice_return import make_return
    token = make_return(request, 'search', q=context['q'], kind=kind, page=context['page_obj'].number)
    for row in context['search_rows']:
        if row['kind'] in {'course', 'lesson', 'student'}:
            row['url'] += ('&' if '?' in row['url'] else '?') + urlencode({'return_to': token})
    return render(request, 'backoffice/workspace/search.html', context)
