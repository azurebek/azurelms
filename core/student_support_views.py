"""Scoped, read-only operator workflow for finding a learner's access problem."""
from functools import wraps
from urllib.parse import urlencode

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
    if query:
        rows = rows.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)
                           | Q(username__icontains=query) | Q(email__icontains=query)
                           | Q(phone_number__icontains=query))
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
        for receipt in context['pending_receipts'][:1]:
            steps.append({'label': 'To‘lov chekini tekshirish',
                          'url': _url('backoffice_receipts', enrollment=receipt.enrollment_id, receipt=receipt.pk),
                          'note': 'Avval chek dalilini tekshiring. Qaror tegishli a’zolikka qo‘llanadi.'})
        if actor.is_superuser and relevant:
            steps.append({'label': 'Guruh a’zoligini ko‘rish',
                          'url': _url('backoffice_cohort_members', kwargs={'cohort_id': relevant.cohort_id}, enrollment=relevant.pk),
                          'note': 'Joyni qaytarishning o‘zi to‘lov muddatini uzaytirmaydi yoki darsni ochmaydi.'})
    return steps


@support_view
def student(request, student_id):
    # A diagnosis is for the default active group shown on the card. Do not
    # silently pretend to diagnose a caller's arbitrary cohort-specific URL.
    if 'cohort' in request.GET:
        return HttpResponseBadRequest('Bu kartada kurs va darsni tanlang. Amaldagi guruh natijada ko‘rsatiladi.')
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
    enrollment_rows = []
    for enrollment in context['enrollments']:
        plan = enrollment.active_plan()
        enrollment_rows.append({
            'cohort_name': enrollment.cohort.name, 'status_label': enrollment.support_effective_label,
            'deadline': enrollment.next_payment_deadline, 'plan_name': plan.name if plan else 'Tarif biriktirilmagan',
            'membership_url': _url('backoffice_cohort_members', kwargs={'cohort_id': enrollment.cohort_id}, enrollment=enrollment.pk)
                              if request.user.is_superuser else '',
        })
    receipt_rows = [{
        'id': receipt.pk, 'submitted_at': receipt.submitted_at, 'label': receipt.enrollment.cohort.name,
        'amount': receipt.amount,
        'action_url': _url('backoffice_receipts', enrollment=receipt.enrollment_id, receipt=receipt.pk),
    } for receipt in context['pending_receipts']]
    context.update(
        display_name=target.get_full_name().strip() or target.username,
        contact_phone=target.phone_number if request.user.is_superuser else '',
        enrollment_rows=enrollment_rows, receipt_rows=receipt_rows,
        next_steps=_resolution_links(request.user, context), list_context=list_context,
        back_url=_url('backoffice_workspace_students', q=list_context['q'], page=list_context['page'], course=list_context['filter_course']),
        recheck_url=_url('backoffice_workspace_student', kwargs={'student_id': student_id}, **list_context,
                        course=course.pk if course else '', lesson=lesson.pk if lesson else ''),
    )
    guidance = {
        'account_inactive': 'Hisob faolligini administrator tekshirishi kerak. Bu sahifa hisobni avtomatik faollashtirmaydi.',
        'no_enrollment': 'O‘quvchi avval shu kursga yozilishi kerak. Keyin a’zolik va to‘lov qaydini shu kartada tekshiring.',
        'open': 'Muammo davom etsa, o‘quvchi aynan shu hisob va guruh bilan kirayotganini tekshiring. Qurilma yoki internetdagi xato bu yerda tekshirilmaydi.',
    }
    code = context['diagnosis']['code']
    context['support_guidance'] = guidance.get(code, '')
    if not context['next_steps']:
        if code in {'pending', 'expired', 'frozen', 'no_active_enrollment'} and not receipt_rows:
            context['support_guidance'] = 'Tekshirishni kutayotgan chek topilmadi. O‘quvchining to‘lov yoki a’zolik ma’lumotini administrator bilan aniqlashtiring.'
        elif code == 'drip' and context['effective_enrollment'] and not context['effective_enrollment'].cohort.is_active:
            context['support_guidance'] = 'Guruh boshqaruvda nofaol. Administrator guruh sozlamalarini tekshirishi kerak.'
        elif code == 'sequence' and context['previous_assignments_missing']:
            context['support_guidance'] = 'O‘quvchi oldingi darsdagi topshiriqlarni yuborishi kerak. Yuborilgach ustoz tekshiradi.'
    return _render(request, 'student', context)
