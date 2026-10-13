"""Scoped, read-only operator workflow for finding a learner's access problem."""
from functools import wraps
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_GET

from cohorts.models import Enrollment
from core.access import teacher_course_queryset
from core.backoffice_workspace import _id, _nav
from core.flags import flag_enabled
from core.student_support_service import build_student_support, support_student_queryset
from courses.models import Course, Lesson

FLAG = 'backoffice_student_support'
TOPICS = {'access': 'Darsga kirish', 'results': 'Topshiriq va natijalar', 'delivery': 'Bildirishnomalar'}
RESULT_KINDS = {'assignments': 'Topshiriqlar', 'quizzes': 'Dars testlari', 'exams': 'Imtihonlar'}
EVIDENCE_PAGES = ('assignment_page', 'quiz_page', 'exam_page', 'delivery_page')


def support_view(view):
    @login_required
    @require_GET
    @wraps(view)
    def authorized(request, *args, **kwargs):
        actor = get_user_model().objects.filter(pk=request.user.pk, is_active=True).first()
        if actor is None or not (actor.is_staff or actor.is_superuser):
            raise PermissionDenied
        request.user = actor
        if not flag_enabled(FLAG):
            raise Http404
        if any(len(values) != 1 for _, values in request.GET.lists()):
            return HttpResponseBadRequest('Bir maydon ikki marta berilgan. Tanlovni qayta oching.')
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


def _url(name, *, kwargs=None, **params):
    query = urlencode({key: value for key, value in params.items() if value not in ('', None)})
    return reverse(name, kwargs=kwargs) + ('?' + query if query else '')


def _course_filter(actor, raw):
    if not raw:
        return None
    try:
        return teacher_course_queryset(actor).get(pk=_id(raw))
    except Course.DoesNotExist:
        raise Http404 from None


def _render(request, page, context):
    return render(request, f'backoffice/workspace/{page}.html', {
        'workspace_nav': _nav(request, 'students'), 'frontend_v1_title': 'O‘quvchiga yordam', **context,
    })


@support_view
def students(request):
    query = request.GET.get('q', '').strip()[:200]
    selected_course = _course_filter(request.user, request.GET.get('course'))
    courses = teacher_course_queryset(request.user).order_by('title', 'pk')
    rows = support_student_queryset(request.user)
    if selected_course:
        rows = rows.filter(enrollments__cohort__course=selected_course).distinct()
    # A displayed full name spans two fields; require each word somewhere in
    # the same scoped learner record, regardless of first/last name order.
    for term in query.split():
        rows = rows.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
                           | Q(username__icontains=term) | Q(email__icontains=term)
                           | Q(phone_number__icontains=term))
    rows = rows.prefetch_related(Prefetch('enrollments', queryset=Enrollment.objects.filter(
        cohort__course__in=courses).select_related('cohort__course').order_by('-joined_at', '-pk'),
        to_attr='support_enrollments')).order_by('first_name', 'last_name', 'username', 'pk')
    page = Paginator(rows, 20).get_page(request.GET.get('page'))
    student_rows = []
    for student in page:
        labels = list(dict.fromkeys(item.cohort.course.title for item in student.support_enrollments))
        student_rows.append({
            'name': student.get_full_name().strip() or student.username,
            'identity_hint': student.email or student.username,
            'courses_label': ', '.join(labels[:3]) + (' …' if len(labels) > 3 else '') if labels else 'Kursga yozilmagan',
            'account_label': 'Hisob faol' if student.is_active else 'Hisobga kirish yopilgan',
            'detail_url': _url('backoffice_workspace_student', kwargs={'student_id': student.pk},
                q=query, page=page.number, filter_course=selected_course.pk if selected_course else '',
                course=selected_course.pk if selected_course else ''),
        })
    return _render(request, 'students', {
        'page_obj': page, 'student_rows': student_rows, 'q': query, 'course_options': courses,
        'selected_course_id': str(selected_course.pk) if selected_course else '',
        'filters': {'q': query, 'course': selected_course.pk if selected_course else '', 'page': page.number},
        'pagination_query': urlencode({'q': query, 'course': selected_course.pk if selected_course else ''}),
    })


def _resolution_links(actor, context):
    """Presentation only: destinations retain their existing decision services."""
    diagnosis = context['diagnosis']
    code = diagnosis['code']
    course, lesson = context['selected_course'], context['selected_lesson']
    active = context['effective_enrollment']
    relevant = context['relevant_enrollment']
    steps = []
    if code == 'drip' and active and lesson:
        if active.cohort.is_active:
            steps.append({
                'label': 'Guruhda shu darsni ochish',
                'url': _url('teacher_release', cohort=active.cohort_id, lesson=lesson.pk, action='release') + (
                    '#release-confirm' if flag_enabled('frontend_v1_teacher') else f'#support-lesson-{lesson.pk}'),
                'note': 'Bu amal faqat shu o‘quvchiga emas, butun guruhga ta’sir qiladi. Guruh va darsni tekshiring.',
            })
        elif actor.is_superuser:
            steps.append({'label': 'Guruh sozlamalarini ko‘rish',
                          'url': reverse('backoffice_cohort_edit', kwargs={'cohort_id': active.cohort_id}),
                          'note': 'Guruh boshqaruvda nofaol. Dars ochish sahifasida tanlash uchun guruh holatini ko‘rib chiqing.'})
    elif code == 'sequence':
        for submission in context['previous_submissions']:
            steps.append({'label': f'Topshiriqni ko‘rish: {submission.assignment.title}',
                          'url': reverse('teacher_grade_assignment', kwargs={'submission_id': submission.pk}),
                          'note': 'Ishni tekshirib qaror qiling. Tasdiqlash baho va rag‘batga ta’sir qilishi mumkin.'})
    elif code in {'pending', 'expired', 'frozen', 'no_enrollment'}:
        receipt = context['relevant_pending_receipt']
        if receipt is not None:
            steps.append({'label': 'To‘lov chekini tekshirish',
                          'url': _url('backoffice_receipts', enrollment=receipt.enrollment_id, receipt=receipt.pk,
                                      lesson=lesson.pk if lesson else ''),
                          'note': 'Avval chek dalilini tekshiring. Qaror tegishli a’zolikka qo‘llanadi.'})
        if actor.is_superuser and relevant:
            steps.append({'label': 'Guruh a’zoligini ko‘rish',
                          'url': _url('backoffice_cohort_members', kwargs={'cohort_id': relevant.cohort_id}, enrollment=relevant.pk,
                                      lesson=lesson.pk if lesson else ''),
                          'note': 'Joyni qaytarishning o‘zi to‘lov muddatini uzaytirmaydi yoki darsni ochmaydi.'})
    return steps


@support_view
def student(request, student_id):
    # A diagnosis is for the default active group shown on the card. Do not
    # silently pretend to diagnose a caller's arbitrary cohort-specific URL.
    if 'cohort' in request.GET:
        return HttpResponseBadRequest('Bu kartada kurs va darsni tanlang. Amaldagi guruh natijada ko‘rsatiladi.')
    topic = request.GET.get('topic', 'access')
    result_kind = request.GET.get('result_kind', 'assignments')
    delivery_filter = request.GET.get('delivery_filter', 'all')
    if topic not in TOPICS or result_kind not in RESULT_KINDS or delivery_filter not in {'all', 'failed'}:
        return HttpResponseBadRequest('Tekshiruv turini qayta tanlang.')
    if topic == 'delivery' and not request.user.is_superuser:
        raise PermissionDenied
    evidence_pages = {key: _id(request.GET[key]) if request.GET.get(key) else 1 for key in EVIDENCE_PAGES}
    list_course = _course_filter(request.user, request.GET.get('filter_course'))
    list_context = {'q': request.GET.get('q', '').strip()[:200],
                    'page': request.GET.get('page', '1')[:10],
                    'filter_course': str(list_course.pk) if list_course else ''}
    try:
        context = build_student_support(actor=request.user, student_id=student_id,
            course_id=_id(request.GET['course']) if request.GET.get('course') else None,
            lesson_id=_id(request.GET['lesson']) if request.GET.get('lesson') else None)
    except (get_user_model().DoesNotExist, Course.DoesNotExist, Lesson.DoesNotExist):
        raise Http404 from None
    target, course, lesson = context['student'], context['selected_course'], context['selected_lesson']
    from core.backoffice_return import with_return
    case_params = {**list_context, 'course': course.pk if course else '',
                   'lesson': lesson.pk if lesson else ''}

    def case_url(**changes):
        return with_return(request, _url('backoffice_workspace_student', kwargs={'student_id': student_id},
                           **{**case_params, 'topic': topic, 'result_kind': result_kind,
                              'delivery_filter': delivery_filter, **evidence_pages, **changes}))

    context.update(
        support_topic=topic, support_topic_label=TOPICS[topic], result_kind=result_kind, delivery_filter=delivery_filter,
        support_topics=[{'key': key, 'label': label, 'url': case_url(topic=key), 'active': key == topic}
                        for key, label in TOPICS.items() if key != 'delivery' or request.user.is_superuser],
    )
    if topic in {'results', 'delivery'}:
        from core.student_support_return import make_support_return
        support_token = make_support_return(request, student_id=target.pk, course_id=course.pk if course else None,
                                            lesson_id=lesson.pk if lesson else None, topic=topic)

        def action_return(rows):
            for row in rows:
                if row.get('action_url') and support_token:
                    parsed = urlsplit(row['action_url'])
                    query = parse_qsl(parsed.query, keep_blank_values=True) + [('support_from', support_token)]
                    row['action_url'] = urlunsplit(('', '', parsed.path, urlencode(query), parsed.fragment))

        if topic == 'results' and course:
            from core.student_support_results import build_student_results
            evidence = build_student_results(actor=request.user, student_id=target.pk, course_id=course.pk,
                lesson_id=lesson.pk if lesson else None,
                **{key: evidence_pages[key] for key in EVIDENCE_PAGES if key != 'delivery_page'})
            groups = []
            for key, prefix in (('assignments', 'assignment'), ('quizzes', 'quiz'), ('exams', 'exam')):
                page = evidence[f'{prefix}_page_obj']
                rows = evidence[f'{prefix}_rows']
                action_return(rows)
                groups.append({'key': key, 'label': RESULT_KINDS[key], 'url': case_url(result_kind=key),
                               'active': key == result_kind, 'count': page.paginator.count})
                if key == result_kind:
                    context.update(result_rows=rows, result_page=page,
                        result_previous_url=case_url(**{f'{prefix}_page': page.previous_page_number()}) if page.has_previous() else '',
                        result_next_url=case_url(**{f'{prefix}_page': page.next_page_number()}) if page.has_next() else '')
            context.update(result_groups=groups, result_label=RESULT_KINDS[result_kind],
                           result_scope=evidence['exam_scope_label' if result_kind == 'exams' else 'scope_label'])
        elif topic == 'delivery':
            from core.student_support_delivery import build_student_delivery
            delivery = build_student_delivery(actor=request.user, student_id=target.pk,
                                              page=evidence_pages['delivery_page'], status=delivery_filter)
            page = delivery['page_obj']
            action_return(delivery['rows'])
            context.update(delivery=delivery,
                delivery_filters=[{'label': label, 'count': count, 'active': key == delivery_filter,
                                   'url': case_url(delivery_filter=key, delivery_page=1)} for key, label, count in (
                                       ('all', 'Hammasi', delivery['summary']['total']),
                                       ('failed', 'Yuborish to‘xtagan', delivery['summary']['failed']))],
                delivery_previous_url=case_url(delivery_page=page.previous_page_number()) if page.has_previous() else '',
                delivery_next_url=case_url(delivery_page=page.next_page_number()) if page.has_next() else '')
    enrollment_rows = []
    for enrollment in context['enrollments']:
        plan = enrollment.active_plan()
        enrollment_rows.append({
            'cohort_name': enrollment.cohort.name, 'status_label': enrollment.support_effective_label,
            'deadline': enrollment.next_payment_deadline, 'plan_name': plan.name if plan else 'Tarif biriktirilmagan',
            'membership_url': _url('backoffice_cohort_members', kwargs={'cohort_id': enrollment.cohort_id}, enrollment=enrollment.pk,
                                   lesson=lesson.pk if lesson else '')
                              if request.user.is_superuser else '',
        })
    receipt_rows = [{
        'id': receipt.pk, 'submitted_at': receipt.submitted_at, 'label': receipt.enrollment.cohort.name,
        'amount': receipt.amount,
        'action_url': _url('backoffice_receipts', enrollment=receipt.enrollment_id, receipt=receipt.pk,
                           lesson=lesson.pk if lesson else ''),
    } for receipt in context['pending_receipts']]
    context.update(
        display_name=target.get_full_name().strip() or target.username,
        contact_phone=target.phone_number if request.user.is_superuser else '',
        enrollment_rows=enrollment_rows, receipt_rows=receipt_rows,
        next_steps=_resolution_links(request.user, context), list_context=list_context,
        back_url=_url('backoffice_workspace_students', q=list_context['q'], page=list_context['page'], course=list_context['filter_course']),
        recheck_url=case_url(),
    )
    guidance = {
        'account_inactive': 'Hisob faolligini administrator tekshirishi kerak. Bu sahifa hisobni avtomatik faollashtirmaydi.',
        'no_enrollment': 'O‘quvchi avval shu kursga yozilishi kerak. Keyin a’zolik va to‘lov qaydini shu kartada tekshiring.',
        'open': 'Muammo davom etsa, o‘quvchi aynan shu hisob va guruh bilan kirayotganini tekshiring. Qurilma yoki internetdagi xato bu yerda tekshirilmaydi.',
    }
    code = context['diagnosis']['code']
    context['support_guidance'] = guidance.get(code, '')
    if not context['next_steps']:
        if code in {'pending', 'expired', 'frozen', 'no_active_enrollment'} and not context['relevant_pending_receipt']:
            context['support_guidance'] = 'Shu a’zolik uchun tekshirishni kutayotgan chek topilmadi. O‘quvchining to‘lov yoki a’zolik ma’lumotini administrator bilan aniqlashtiring.'
        elif code == 'drip' and context['effective_enrollment'] and not context['effective_enrollment'].cohort.is_active:
            context['support_guidance'] = 'Guruh boshqaruvda nofaol. Administrator guruh sozlamalarini tekshirishi kerak.'
        elif code == 'sequence' and context['previous_assignments_missing']:
            context['support_guidance'] = 'O‘quvchi oldingi darsdagi topshiriqlarni yuborishi kerak. Yuborilgach ustoz tekshiradi.'
    response = _render(request, 'student', context)
    from core.backoffice_recent import record_opened
    return record_opened(request, response, kind='student', student_id=target.pk,
                         course_id=course.pk if course else None,
                         lesson_id=lesson.pk if lesson else None,
                         filter_course_id=list_course.pk if list_course else None,
                         page=list_context['page'], topic=topic if topic != 'access' else None,
                         result_kind=result_kind if topic == 'results' else None,
                         delivery_filter=delivery_filter if topic == 'delivery' else None,
                         **{key: value for key, value in evidence_pages.items() if value != 1})
