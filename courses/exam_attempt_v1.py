"""Frozen exam-focus adapter. Canonical writers remain in domain services."""
import hashlib
import json
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.flags import flag_enabled
from .exam_api import ExamAPIResponseMixin
from .exam_service import (ExamAttemptStartBlocked,
                          expire_attempt_if_time_limit_reached,
                          start_exam_attempt)
from .exam_section_service import build_section_payload, register_audio_play, save_question_answer, save_exam_audio
from .exam_media import listening_media_url
from .models import Exam, ExamAttempt, ExamActionGate, ExamActionReceipt, ExamSection, Question, ReadingItem
from .policy_service import check_exam_access_policy
from .reading_service import save_reading_response


def exam_snapshot(exam, attempt, request):
    gate = ExamActionGate.objects.filter(student=request.user, exam=exam).first()
    data = {'attempt_id': attempt.pk if attempt else None,
            'operation_epoch': str(gate.epoch) if gate else None,
            'revision': attempt.input_revision if attempt else 0,
            'status': attempt.review_status if attempt else 'not_started',
            'remaining_seconds': None, 'sections': [], 'answers': {},
            'result_url': reverse('exam_result', args=[exam.course_id, exam.pk])}
    if not attempt or attempt.is_completed:
        return data
    deadline = attempt.get_deadline()
    data['remaining_seconds'] = max(0, int((deadline - timezone.now()).total_seconds())) if deadline else None
    for section in exam.sections.order_by('order', 'id'):
        payload = build_section_payload(attempt=attempt, section=section)
        payload['section']['media_url'] = listening_media_url(section, request)
        payload['section']['media_unavailable'] = bool(section.section_type == 'listening' and not payload['section']['media_url'])
        questions = []
        if 'tasks' in payload:
            for task in payload['tasks']:
                for item in task['items']:
                    response = item['response']
                    key = f"r:{item['id']}"
                    kind = ('multi' if task['task_type'] == 'multiple_choice' else
                            'choice' if task['task_type'] == 'single_choice' else
                            'select' if task['shared_options'] else 'short')
                    questions.append({'key': key, 'anchor': key.replace(':', '-'), 'kind': kind,
                                      'prompt': item['prompt'], 'context': task['body'], 'instructions': task['instructions'],
                                      'choices': item['options'] or task['shared_options'], 'title': task['title'],
                                      'max_words': task['max_words_per_answer'], 'max_selections': task['max_selections_per_item'],
                                      'allow_review_flag': task['allow_review_flag']})
                    data['answers'][key] = {'choice_id': str(response['selected_option_id'] or ''),
                                           'option_ids': sorted(str(value) for value in response['selected_option_ids']),
                                           'answer_text': response['text_answer'], 'audio_url': '',
                                           'flagged': task['allow_review_flag'] and response['is_flagged_for_review'], 'version': attempt.answer_versions.get(key, 0)}
        else:
            for question in payload['questions']:
                response = question['response']
                key = f"q:{question['id']}"
                questions.append({'key': key, 'anchor': key.replace(':', '-'),
                                  'kind': 'choice' if question['choices'] else 'audio' if section.section_type == 'speaking' else 'text',
                                  'prompt': question['text'], 'context': '', 'choices': question['choices'],
                                  'title': section.title, 'min_words': question['min_word_count'], 'max_words': question['max_word_count'],
                                  'allow_review_flag': True})
                data['answers'][key] = {'choice_id': str(response['selected_choice_id'] or ''), 'option_ids': [],
                                       'answer_text': response['answer_text'], 'audio_url': response['audio_url'],
                                       'flagged': response['is_flagged_for_review'], 'version': attempt.answer_versions.get(key, 0)}
        for question in questions:
            question['saved'] = data['answers'][question['key']]
        data['sections'].append({**payload['section'], 'questions': questions, 'passages': payload.get('passages', []),
                                 'legacy_reading_text': section.reading_text or ''})
    return data


def _number(value):
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValidationError('Versiya yoki identifikator noto‘g‘ri.')
    return int(value)


class ExamAttemptV1View(ExamAPIResponseMixin, LoginRequiredMixin, View):
    """One locked action adapter; GET alone never starts a new attempt."""

    def _scope(self, request, course_id, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id, course_id=course_id)
        policy = check_exam_access_policy(student=request.user, exam=exam)
        if not policy.is_allowed:
            return exam, JsonResponse({'error': policy.message}, status=403)
        return exam, None

    @transaction.atomic
    def get(self, request, course_id, exam_id):
        exam, denied = self._scope(request, course_id, exam_id)
        if denied is not None:
            return denied
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if flag_enabled('frontend_v1_exam_attempt'):
            ExamActionGate.objects.get_or_create(student=request.user, exam=exam)
        attempt = ExamAttempt.objects.select_for_update().filter(student=request.user, exam=exam).order_by('-attempt_number', '-id').first()
        expire_attempt_if_time_limit_reached(attempt)
        receipt = None
        if request.GET.get('operation'):
            try:
                operation = uuid.UUID(request.GET['operation'])
            except ValueError:
                return JsonResponse({'error': 'Amal ID noto‘g‘ri.'}, status=400)
            row = ExamActionReceipt.objects.filter(student=request.user, exam=exam, operation_id=operation).first()
            if row:
                receipt = {'id': str(row.operation_id), 'command': row.command, 'attempt_id': row.attempt_id}
        return JsonResponse({'state': exam_snapshot(exam, attempt, request), 'receipt': receipt})

    @transaction.atomic
    def post(self, request, course_id, exam_id):
        exam, denied = self._scope(request, course_id, exam_id)
        if denied is not None:
            return denied
        try:
            data = json.loads(request.POST.get('payload', '{}')) if request.content_type == 'multipart/form-data' else json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError
            operation = uuid.UUID(str(data.get('operation_id', '')))
            epoch = uuid.UUID(str(data.get('operation_epoch', '')))
            command = data.get('command')
            if command not in ('start', 'save', 'submit', 'listen', 'reconcile') or 'audio_key' in data:
                raise ValueError
            upload = request.FILES.get('audio')
            digest_input = dict(data)
            if upload:
                digest = hashlib.sha256()
                for chunk in upload.chunks():
                    digest.update(chunk)
                upload.seek(0)
                digest_input['upload_sha256'] = digest.hexdigest()
            digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        except (ValueError, TypeError, UnicodeDecodeError):
            return JsonResponse({'error': 'So‘rov formati noto‘g‘ri.'}, status=400)
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        previous = ExamActionReceipt.objects.filter(student=request.user, exam=exam, operation_id=operation).first()
        gate = ExamActionGate.objects.filter(student=request.user, exam=exam).first()
        if command == 'reconcile':
            # Rotation is a bounded cancellation barrier under the same user lock
            # as all actions. Never INSERT one cancelled receipt per supplied UUID.
            attempt = ExamAttempt.objects.select_for_update().filter(student=request.user, exam=exam).order_by('-attempt_number', '-id').first()
            if not gate:
                return JsonResponse({'error': 'Amal sessiyasi berilmagan. Sahifani qayta oching.'}, status=409)
            if previous is None and gate.epoch == epoch:
                gate.epoch = uuid.uuid4()
                gate.save(update_fields=['epoch'])
            return JsonResponse({'receipt': {'id': str(operation), 'command': previous.command if previous else 'cancelled',
                                             'attempt_id': previous.attempt_id if previous else (attempt.pk if attempt else None)},
                                 'state': exam_snapshot(exam, attempt, request)})
        if not flag_enabled('frontend_v1_exam_attempt'):
            return JsonResponse({'error': 'Yangi ko‘rinish o‘chirilgan. Sahifani qayta oching.'}, status=409)
        if previous:
            if previous.command == 'cancelled':
                return JsonResponse({'error': 'Bu noma’lum amal yopilgan; kechikkan so‘rov bajarilmadi.'}, status=409)
            if previous.payload_digest != digest:
                return JsonResponse({'error': 'Bu amal IDsi boshqa so‘rov uchun ishlatilgan.'}, status=409)
            return JsonResponse({'receipt': {'id': str(operation), 'command': command, 'attempt_id': previous.attempt_id},
                                 'state': exam_snapshot(exam, ExamAttempt.objects.select_for_update().filter(
                                     student=request.user, exam=exam).order_by('-attempt_number', '-id').first(), request)})
        attempt = ExamAttempt.objects.select_for_update().filter(student=request.user, exam=exam).order_by('-attempt_number', '-id').first()
        if not gate or gate.epoch != epoch:
            return JsonResponse({'error': 'Amal sessiyasi yangilangan. Qoralama saqlandi; holatni tekshiring.',
                                 'state': exam_snapshot(exam, attempt, request)}, status=409)
        if data.get('attempt_id') != (attempt.pk if attempt else None):
            return JsonResponse({'error': 'Urinish boshqa oynada o‘zgardi. Holatni tekshiring.'}, status=409)
        if expire_attempt_if_time_limit_reached(attempt):
            return JsonResponse({'error': 'Vaqt tugadi. Faqat saqlangan javoblar topshirildi.', 'state': exam_snapshot(exam, attempt, request)}, status=409)
        try:
            # A savepoint rolls back a partially validated command, not prior expiry.
            with transaction.atomic():
                if command == 'start':
                    if data.get('confirmed') is not True:
                        raise ValidationError('Boshlash shartlarini tasdiqlang.')
                    if attempt and not attempt.is_completed:
                        raise ValidationError('Urinish allaqachon boshlangan. Holatni tekshiring.')
                    attempt, _ = start_exam_attempt(student=request.user, exam=exam)
                else:
                    if not attempt or attempt.is_completed:
                        raise ValidationError('Urinish yopilgan. Holatni tekshiring.')
                    if command == 'save':
                        key = data.get('key', '')
                        if not isinstance(key, str):
                            raise ValidationError('Savol identifikatori noto‘g‘ri.')
                        if _number(data.get('version')) != attempt.answer_versions.get(key, 0):
                            return JsonResponse({'error': 'Javob boshqa oynada o‘zgardi.', 'state': exam_snapshot(exam, attempt, request)}, status=409)
                        self._save(attempt, key, data.get('value'), upload)
                    elif command == 'listen':
                        section = get_object_or_404(ExamSection, pk=_number(data.get('section_id')), exam=exam)
                        source = listening_media_url(section, request)
                        if not source:
                            raise ValidationError('Audio manbasi bu sahifada ochilmaydi. Ustozga xabar bering; limit sarflanmadi.')
                        if data.get('media_url') != source:
                            return JsonResponse({'error': 'Audio manbasi o‘zgargan. Holatni tekshiring; limit sarflanmadi.',
                                                 'state': exam_snapshot(exam, attempt, request)}, status=409)
                        result = register_audio_play(attempt=attempt, section=section)
                        if not result['allowed']:
                            return JsonResponse({'error': 'Tinglash limiti tugagan.'}, status=403)
                    else:
                        if data.get('confirmed') is not True:
                            raise ValidationError('Topshirishni tasdiqlang.')
                        if _number(data.get('version')) != attempt.input_revision:
                            return JsonResponse({'error': 'Javoblar o‘zgardi. Qayta ko‘rib chiqing.'}, status=409)
                        attempt.submit_for_review()
                        from users.streak import record_activity
                        record_activity(request.user)
                ExamActionReceipt.objects.create(student=request.user, exam=exam, attempt=attempt,
                                                 operation_id=operation, command=command, payload_digest=digest)
        except (ValidationError, ExamAttemptStartBlocked, ValueError, TypeError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) else str(exc)
            return JsonResponse({'error': message or 'Javob formati noto‘g‘ri.'}, status=400)
        attempt.refresh_from_db()
        return JsonResponse({'receipt': {'id': str(operation), 'command': command, 'attempt_id': attempt.pk},
                             'state': exam_snapshot(exam, attempt, request)})

    @staticmethod
    def _save(attempt, key, value, upload):
        if not isinstance(value, dict) or not isinstance(value.get('answer_text', ''), str) or not isinstance(value.get('flagged'), bool):
            raise ValidationError('Javob formati noto‘g‘ri.')
        kind, pk = key.split(':')
        pk = _number(pk)
        if kind == 'r':
            if upload:
                raise ValidationError('Bu savol audio qabul qilmaydi.')
            item = get_object_or_404(ReadingItem, pk=pk, task__section__exam_id=attempt.exam_id)
            save_reading_response(attempt=attempt, item=item, payload={
                'option_id': value.get('choice_id'), 'option_ids': value.get('option_ids', []),
                'text_answer': value.get('answer_text', ''), 'flag_for_review': value['flagged']})
        elif kind == 'q':
            question = get_object_or_404(Question, pk=pk, exam_section__exam_id=attempt.exam_id)
            if upload:
                if question.exam_section.section_type != 'speaking':
                    raise ValidationError('Audio faqat speaking savoliga biriktiriladi.')
                save_exam_audio(attempt=attempt, question=question, upload=upload, flagged=value['flagged'])
            else:
                payload = {'flag_for_review': value['flagged']}
                if question.choices.exists():
                    payload['choice_id'] = value.get('choice_id')
                elif question.exam_section.section_type != 'speaking':
                    payload['answer_text'] = value.get('answer_text', '')
                save_question_answer(attempt=attempt, question=question, payload=payload)
        else:
            raise ValidationError('Savol turi noto‘g‘ri.')
