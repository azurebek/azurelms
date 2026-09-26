"""Frozen editor presentation and form snapshots; canonical forms own validation."""
import json

from django.shortcuts import get_object_or_404, render
from django.utils.cache import patch_cache_control
from django.utils.crypto import constant_time_compare, salted_hmac

from core.access import teacher_course_queryset
from core.flags import flag_enabled
from core.frontend_v1 import teacher_v1_navigation
from core.backoffice_forms import CourseBackofficeForm, LessonBackofficeForm
from library.frontend_v1 import style_form


def enabled(request):
    return flag_enabled('frontend_v1_editors') or request.POST.get('frontend_v1_editors') == '1'


def revision(user, obj, action):
    state = None
    if obj is not None:
        fields = CourseBackofficeForm.Meta.fields if action == 'course' else LessonBackofficeForm.Meta.fields
        state = [obj.pk, [str(obj._meta.get_field(name).value_from_object(obj)) for name in fields]]
    return _sign(user, action, state)


def _sign(user, action, state):
    return salted_hmac('frontend-v1-editors', json.dumps([user.pk, action, state], default=str), algorithm='sha256').hexdigest()


def material_revision(user, material, action):
    # Resource policy may change even when the link itself did not.
    state = [str(field.value_from_object(material)) for field in material._meta.concrete_fields]
    state += [str(material.resource.updated_at), material.resource.is_teacher_only]
    return _sign(user, action, state)


def reorder_revision(user, lesson):
    return _sign(user, 'reorder', [lesson.pk, list(lesson.materials.order_by('pk').values_list('pk', 'order', 'updated_at'))])


def write_error(request, expected):
    if not enabled(request):
        return None
    if request.GET:
        return 'Amal manzilidagi qo‘shimcha parametr tanilmadi. Hech narsa saqlanmadi.', 400
    if not constant_time_compare(request.POST.get('editor_revision', ''), expected):
        return 'Ma’lumot boshqa oynada o‘zgargan. Saqlanmadi; qoralamangizni olib, so‘nggi holatni oching.', 409
    if request.POST.get('confirm_scope') != 'yes':
        return 'Amal doirasini tasdiqlang. Hech narsa saqlanmadi.', 400
    return None


def invalid_query(request, page):
    allowed = {'list': {'q', 'status', 'page'}, 'index': {'course'}}.get(page, set())
    if any(key not in allowed or len(values) != 1 for key, values in request.GET.lists()):
        return True
    if page == 'list' and request.GET.get('status', 'all') not in ('all', 'active', 'draft'):
        return True
    for key in ('page', 'course'):
        value = request.GET.get(key, '')
        if value and (not value.isascii() or not value.isdecimal() or len(value) > 18 or int(value) < 1):
            return True
    return False


def lesson_index(request, context):
    courses = teacher_course_queryset(request.user).order_by('title', 'pk')
    context['course_options'] = courses
    selected = request.GET.get('course', '')
    if selected and not invalid_query(request, 'index'):
        course = get_object_or_404(courses, pk=int(selected))
        courses = courses.filter(pk=course.pk)
    context.update(courses=courses.prefetch_related('modules__lessons'), selected_course=selected)
    return render_editor(request, 'index', context)


def render_editor(request, page, context, *, status=200):
    if not enabled(request):
        legacy = {'list': 'courses', 'course': 'course_form', 'lesson': 'lesson_form'}[page]
        return render(request, f'backoffice/{legacy}.html', context, status=status)
    context.update(teacher_v1_navigation('teacher_dashboard'))
    if not flag_enabled('frontend_v1_teacher'):
        context['frontend_v1_legacy_nav'] += [item for item in context['frontend_v1_nav'] if item['name'].startswith('teacher_')]
        context['frontend_v1_nav'] = [item for item in context['frontend_v1_nav'] if not item['name'].startswith('teacher_')]
    context.update(active_nav='backoffice_courses' if page in ('list', 'course') else 'backoffice_lessons',
                   frontend_v1_title={'list': 'Kurslar boshqaruvi', 'course': 'Kurs ma’lumotlari',
                                      'index': 'Dars tanlash', 'lesson': 'Dars ma’lumotlari',
                                      'material': 'Darsga xos sozlama', 'reorder': 'Materiallar tartibi',
                                      'conflict': 'Amal bajarilmadi'}[page],
                   editor_invalid_query=invalid_query(request, page),
                   editor_library_ready=flag_enabled('frontend_v1_library'))
    form = context.get('form')
    if form:
        style_form(form)
        labels = {'duration': 'Davomiylik · soat', 'module': 'Modul',
                  'video_url': 'Video manzili', 'content': 'Dars matni', 'xp_reward': 'XP sozlamasi',
                  'cover_mode': 'Muqova turi', 'gradient_preset': 'Gradient uslubi',
                  'certificate_requires_all_assignments_approved': 'Sertifikat uchun barcha topshiriqlar tasdiqlansin',
                  'certificate_min_lesson_completion_percent': 'Sertifikat uchun minimal dars bajarilishi (%)',
                  'certificate_min_attendance_percent': 'Sertifikat uchun minimal davomat (%)'}
        for name, label in labels.items():
            if name in form.fields:
                form.fields[name].label = label
    if page in ('course', 'lesson', 'index') and form:
        action = 'course' if page == 'course' else 'lesson'
        context['editor_revision'] = request.POST.get('editor_revision', '') if request.method == 'POST' else revision(request.user, context.get(action), action)
    if page == 'lesson' and context.get('lesson'):
        for material, mform in context['material_forms']:
            # Each independent form needs unique IDs, but unchanged POST names.
            mform.auto_id = f'material_{material.pk}_%s'
            style_form(mform)
            material.save_revision = material_revision(request.user, material, 'material')
            material.detach_revision = material_revision(request.user, material, 'detach')
        context['reorder_revision'] = reorder_revision(request.user, context['lesson'])
    response = render(request, f'frontend_v1/editors/{page}.html', context, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response
