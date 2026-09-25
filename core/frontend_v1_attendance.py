"""Native attendance form/presentation. Canonical service owns all writes."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import salted_hmac

from cohorts.attendance_service import attendance_sheet_state, save_attendance_sheet
from cohorts.models import Attendance
from core.frontend_v1 import render_teacher_v1


class AttendanceSheetForm(forms.Form):
    revision = forms.CharField(widget=forms.HiddenInput, error_messages={'required': 'Davomat varag‘ini yangilab, qayta tekshiring.'})
    confirm_attendance = forms.BooleanField(label='Guruh, dars va tanlovlarni tekshirdim. Davomat va unga tegishli XP saqlansin.',
        error_messages={'required': 'Saqlashdan oldin tasdiq belgisini qo‘ying.'})

    def __init__(self, *args, enrollments, current, **kwargs):
        super().__init__(*args, **kwargs)
        for enrollment in enrollments:
            name = f'att_{enrollment.pk}'
            record = current.get(enrollment.pk)
            status = record.status if record else ''
            self.fields[name] = forms.ChoiceField(required=False,
                label=f'{enrollment.student.get_full_name() or enrollment.student.username} — davomat',
                choices=(('', 'Tanlanmagan — yozilmaydi'), *Attendance.STATUS_CHOICES), initial=status,
                error_messages={'invalid_choice': 'Ro‘yxatdagi davomat holatidan birini tanlang.'},
                widget=forms.Select(attrs={'class':'c-field', 'data-draft-field':'', 'data-draft-saved':status, 'aria-describedby':'attendance-errors'}))

    def clean(self):
        data = super().clean()
        if any(name.startswith('att_') and name not in self.fields for name in self.data):
            raise forms.ValidationError('Ro‘yxatda bo‘lmagan o‘quvchi tanlandi. Hech narsa saqlanmadi.')
        return data


def attendance_page(request, context):
    cohort, lesson = context['cohort'], context.get('lesson')
    if not cohort or not lesson:
        return render_teacher_v1(request, 'teacher/attendance.html', context)
    enrollments, current, revision = attendance_sheet_state(cohort=cohort, lesson=lesson)
    data = request.POST.copy() if request.method == 'POST' else None
    form = AttendanceSheetForm(data, enrollments=enrollments, current=current, initial={'revision':revision})
    status = 200
    if request.method == 'POST':
        status = 400
        if data.get('revision') and data['revision'] != revision:
            data['revision'] = revision
            data.pop('confirm_attendance', None)
            form = AttendanceSheetForm(data, enrollments=enrollments, current=current)
            form.is_valid()
            form.add_error(None, 'Davomat yoki faol ro‘yxat yangilangan. Saqlanmadi; joriy holatni qayta tekshiring.')
            status = 409
        if status == 400 and form.is_valid():
            try:
                count, saved_revision = save_attendance_sheet(cohort=cohort, lesson=lesson, actor=request.user, request=request,
                    marks={e.pk: form.cleaned_data[f'att_{e.pk}'] for e in enrollments}, expected_revision=form.cleaned_data['revision'])
            except ValidationError as exc:
                enrollments, current, revision = attendance_sheet_state(cohort=cohort, lesson=lesson)
                data['revision'] = revision
                data.pop('confirm_attendance', None)
                form = AttendanceSheetForm(data, enrollments=enrollments, current=current)
                form.is_valid(); form.add_error(None, exc)
                status = 409
            else:
                request.session['frontend_v1_attendance_saved'] = {
                    'sheet': [cohort.pk, lesson.pk], 'revision': saved_revision,
                    'values': {f'att_{e.pk}': form.cleaned_data[f'att_{e.pk}'] for e in enrollments},
                }
                messages.success(request, f'Davomat saqlandi ({count} o‘quvchi). Dars ruxsatlari o‘zgarmadi.')
                return redirect(f'{request.path}?cohort={cohort.pk}&lesson={lesson.pk}')
        form.data = form.data.copy(); form.data.pop('confirm_attendance', None)
    receipt = request.session.get('frontend_v1_attendance_saved')
    if request.method == 'GET' and receipt and receipt['sheet'] == [cohort.pk, lesson.pk]:
        request.session.pop('frontend_v1_attendance_saved')
        if receipt['revision'] == revision:
            context['attendance_ack'] = True
            for name, value in receipt['values'].items():
                if name in form.fields:
                    form.fields[name].widget.attrs['data-draft-saved'] = value
    percentages = {row['enrollment'].pk: row['percent'] for row in context.get('rows', [])}
    context.update(attendance_form=form, attendance_revision=revision, attendance_date=timezone.localdate(),
        practice_scope=salted_hmac('frontend-v1-practice', f'{request.user.pk}:{request.session.session_key}').hexdigest(),
        rows=[{'enrollment':e, 'record':current.get(e.pk), 'percent':percentages.get(e.pk), 'field':form[f'att_{e.pk}']} for e in enrollments])
    return render_teacher_v1(request, 'teacher/attendance.html', context, status=status)
