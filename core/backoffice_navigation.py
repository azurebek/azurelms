"""Presentation-only route registry. Views/services remain permission authorities."""
from django.urls import reverse

from core.flags import flag_enabled

FLAG = 'backoffice_unified_navigation'

COURSE_ROUTES = {
    'backoffice_courses', 'backoffice_course_create', 'backoffice_course_edit',
    'backoffice_lessons', 'backoffice_lesson_edit', 'backoffice_exams', 'backoffice_exam_edit',
    'backoffice_cohort_create', 'backoffice_cohort_edit', 'backoffice_cohort_members',
    'backoffice_workspace_courses', 'backoffice_workspace_course_create',
    'backoffice_workspace_course_edit', 'backoffice_workspace_course', 'backoffice_workspace_groups',
}
DESIGN_ROUTES = {'backoffice_brand', 'backoffice_landing', 'backoffice_design', 'backoffice_workspace_site'}
PAYMENT_ROUTES = {'backoffice_receipts', 'backoffice_plan_edit', 'backoffice_workspace_payments', 'backoffice_workspace_plans'}
SETTINGS_ROUTES = {
    'backoffice_control', 'backoffice_feature_flags', 'backoffice_runtime_settings',
    'backoffice_ai_cost', 'backoffice_ai_control', 'backoffice_ai_kill_switch',
    'backoffice_ai_circuit_reset', 'backoffice_dead_letter', 'backoffice_workspace_settings',
}
STUDENT_ROUTES = {'backoffice_users', 'backoffice_chats', 'backoffice_workspace_students', 'backoffice_workspace_student'}
SECTION_TITLES = {'home': 'Ish stoli', 'courses': 'Kurslar', 'students': 'O‘quvchilar',
                  'design': 'Sayt va dizayn', 'payments': 'To‘lovlar', 'settings': 'Sozlamalar'}
TEACHER_RETURN_ROUTES = {'teacher_courses', 'teacher_cohorts', 'teacher_students', 'teacher_grading',
                         'teacher_grade_assignment', 'teacher_grade_exam', 'teacher_attendance', 'teacher_release'}


def flags(request):
    if not hasattr(request, '_backoffice_navigation_flags'):
        request._backoffice_navigation_flags = {name: flag_enabled(name) for name in
            (FLAG, 'backoffice_course_workspace', 'backoffice_student_support', 'backoffice_design_workspace')}
    return request._backoffice_navigation_flags


def section_for(request):
    match = request.resolver_match
    if not match:
        return None
    name, namespace = match.url_name, match.namespace
    if namespace == 'sit_backoffice' or (namespace == 'blog' and name in {'studio', 'studio_create', 'studio_edit'}):
        return 'design'
    if namespace == 'library_backoffice':
        return 'courses'
    if namespace:
        return None
    if name in {'backoffice_dashboard', 'backoffice_workspace_home', 'backoffice_catalog'}:
        return 'home' if name != 'backoffice_catalog' else 'payments'
    if name == 'backoffice_users' and request.GET.get('role') in {'teachers', 'admins'} and request.user.is_superuser:
        return 'settings'
    for section, names in [('courses', COURSE_ROUTES), ('design', DESIGN_ROUTES),
                           ('payments', PAYMENT_ROUTES), ('settings', SETTINGS_ROUTES), ('students', STUDENT_ROUTES)]:
        if name in names:
            return section
    return None


def navigation(request, active):
    enabled = flags(request)
    rows = [
        ('home', 'backoffice_workspace_home' if enabled['backoffice_course_workspace'] else 'backoffice_dashboard'),
        ('courses', 'backoffice_workspace_courses' if enabled['backoffice_course_workspace'] else 'backoffice_courses'),
        ('students', 'backoffice_workspace_students' if enabled['backoffice_student_support'] else 'backoffice_users'),
    ]
    if enabled[FLAG]:
        rows += [('design', 'backoffice_workspace_site'), ('payments', 'backoffice_workspace_payments')]
        if request.user.is_superuser:
            rows += [('settings', 'backoffice_workspace_settings')]
    elif request.user.is_superuser:
        rows += [('design', 'backoffice_design' if enabled['backoffice_design_workspace'] else 'backoffice_brand'),
                 ('payments', 'backoffice_receipts'), ('settings', 'backoffice_control')]
    return [{'key': key, 'label': SECTION_TITLES[key], 'url': reverse(name), 'active': key == active} for key, name in rows]


def section_links(request, section):
    owner = request.user.is_superuser
    enabled = flags(request)
    rows = []
    if section == 'courses':
        rows = [('Kurslar', 'backoffice_workspace_courses' if enabled['backoffice_course_workspace'] else 'backoffice_courses'),
                ('Guruhlar', 'backoffice_workspace_groups'), ('Materiallar', 'library_backoffice:resources'),
                ('Imtihonlar', 'backoffice_exams'), ('Tekshiruv', 'teacher_grading')]
    elif section == 'students':
        rows = [('O‘quvchilar', 'backoffice_workspace_students' if enabled['backoffice_student_support'] else 'backoffice_users'),
                ('Suhbatlar', 'backoffice_chats')]
    elif section == 'design':
        if owner:
            if enabled['backoffice_design_workspace']:
                rows += [('Ko‘rinish', 'backoffice_design')]
            rows += [('Logo va brend', 'backoffice_brand'), ('Sayt bosh sahifasi', 'backoffice_landing')]
        rows += [('Blog', 'blog:studio')]
        if owner:
            rows += [('Turkiyada o‘qish', 'sit_backoffice:dashboard')]
    elif section == 'payments':
        rows = [('Cheklar', 'backoffice_receipts')]
        if owner:
            rows += [('Tariflar', 'backoffice_workspace_plans')]
    elif section == 'settings' and owner:
        rows = [('Barcha sozlamalar', 'backoffice_workspace_settings'), ('Platforma holati', 'backoffice_control'),
                ('Muddat va limitlar', 'backoffice_runtime_settings'), ('Yoqish/o‘chirish', 'backoffice_feature_flags')]
    match = request.resolver_match
    selected = match.view_name if match else ''
    aliases = {
        'backoffice_cohort_create': 'backoffice_workspace_groups', 'backoffice_cohort_edit': 'backoffice_workspace_groups',
        'backoffice_cohort_members': 'backoffice_workspace_groups', 'backoffice_plan_edit': 'backoffice_workspace_plans',
        'blog:studio_create': 'blog:studio', 'blog:studio_edit': 'blog:studio',
        'backoffice_exam_edit': 'backoffice_exams', 'backoffice_workspace_course': 'backoffice_workspace_courses',
        'backoffice_workspace_course_create': 'backoffice_workspace_courses', 'backoffice_workspace_course_edit': 'backoffice_workspace_courses',
    }
    if match and match.namespace == 'sit_backoffice':
        selected = 'sit_backoffice:dashboard'
    elif match and match.namespace == 'library_backoffice':
        selected = 'library_backoffice:resources'
    selected = aliases.get(selected, selected)
    return [{'label': label, 'url': reverse(name), 'active': selected == name} for label, name in rows]


def workspace_context(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_active or not (user.is_staff or user.is_superuser):
        return {}
    match = request.resolver_match
    if match and not match.namespace and match.url_name in TEACHER_RETURN_ROUTES:
        enabled = flags(request)
        if enabled[FLAG]:
            route = 'backoffice_workspace_groups'
            if match.url_name == 'teacher_students':
                route = 'backoffice_workspace_students' if enabled['backoffice_student_support'] else 'backoffice_users'
            return {'backoffice_return_url': reverse(route)}
        return {}
    section = section_for(request)
    if section is None or not flags(request)[FLAG]:
        return {}
    nav = navigation(request, section)
    section_url = next((item['url'] for item in nav if item['key'] == section), nav[0]['url'])
    return {
        'backoffice_unified_enabled': True,
        'backoffice_base_template': 'backoffice/workspace/legacy_bridge.html',
        'blog_workspace_base': 'backoffice/workspace/blog_bridge.html',
        'workspace_nav': nav,
        'workspace_section_links': [item for item in section_links(request, section) if item['url'] != section_url],
        'workspace_section_title': SECTION_TITLES[section],
        'workspace_section_url': section_url,
    }
