"""Private fayllarga yagona kirish nuqtasi — ruxsat tekshirib uzatadi (A0b).

Fayllarning o'zi `PRIVATE_MEDIA_ROOT` ichida, ya'ni `MEDIA_ROOT` dan tashqarida
turadi va hech qanday static handler ularga yeta olmaydi. Shu sabab bu
view'lar yagona yo'l.

Owner qarori (2026-08-15): signed URL emas, ruxsat tekshiradigan stream.
Local filesystem uchun bu bugunoq to'liq ishlaydi va tashqi xizmat talab
qilmaydi; kelajakda object storage ochilsa shu view signed URL'ga redirect
qiladigan qilib kengaytiriladi — chaqiruvchi tomon o'zgarmaydi.

Ikki qoida:

* **Rad etish `404`** — `403` faylning mavjudligini tasdiqlab qo'yardi.
* **`Content-Type` baytlardan aniqlanadi.** Saqlangan `attachment_content_type`
  ni brauzer yuborgan, unga ishonib bo'lmaydi: `text/html` deb belgilangan
  fayl brauzerda bajarilib ketishi mumkin. Faqat rasm `inline`, qolgani
  `attachment` sifatida beriladi.
"""

import datetime

from django.http import FileResponse, Http404
from django.utils import timezone

from core.upload_validation import sniff_kind

# Sniff qilingan turdan xavfsiz content type. Ro'yxatda yo'q tur —
# `application/octet-stream`, ya'ni brauzer uni bajarishga urinmaydi.
_CONTENT_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "pdf": "application/pdf",
    "text": "text/plain; charset=utf-8",
    "webm": "audio/webm",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "mp4": "audio/mp4",
}
_INLINE_KINDS = {"png", "jpeg", "webp", "gif", "webm", "ogg", "wav", "mp3", "mp4"}


#: Bitta aktordan kelgan takroriy rad etishlar shu oynada bir marta yoziladi.
#: Ledger append-only va tozalanmaydi — URL'larni ketma-ket sinab ko'rayotgan
#: odam minglab qator qoldirmasligi kerak. Skaner baribir ko'rinadi: u oynada
#: bittadan qator qoldiradi.
DENIAL_AUDIT_WINDOW = datetime.timedelta(minutes=15)


def _audit_denial(request, target):
    """Xavfsizlik signali: kimdir o'ziga tegishli bo'lmagan faylga urindi.

    Faqat autentifikatsiyadan o'tgan foydalanuvchi yoziladi — anonim so'rovchi
    aktor emas va uni yozish shovqindan boshqa narsa bermaydi (§3).
    """
    from aicontrol.models import SystemAuditEvent
    from core.audit import record_audit_event

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    target_type = target.__class__.__name__
    recent = SystemAuditEvent.objects.filter(
        action="private_media.denied",
        actor=user,
        target_type=target_type,
        created_at__gte=timezone.now() - DENIAL_AUDIT_WINDOW,
    ).exists()
    if recent:
        return None

    return record_audit_event(
        action="private_media.denied",
        request=request,
        outcome=SystemAuditEvent.OUTCOME_DENIED,
        target=target,
        target_label=f"{target_type} #{getattr(target, 'pk', '')}",
        error="Ruxsat yo'q.",
    )


def _require(condition, *, request=None, target=None):
    """Ruxsat yo'q yoki obyekt yo'q — ikkalasi ham bir xil `404` beradi.

    `request` va `target` berilsa, rad etish audit ledgeriga ham tushadi.
    """
    if not condition:
        if request is not None and target is not None:
            _audit_denial(request, target)
        raise Http404


def serve_private_file(request, file_field, *, download_name=""):
    """Ruxsat allaqachon tekshirilgan faylni xavfsiz sarlavhalar bilan uzatadi."""
    _require(bool(file_field))
    try:
        handle = file_field.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404

    kind = sniff_kind(handle)
    content_type = _CONTENT_TYPES.get(kind, "application/octet-stream")
    as_attachment = kind not in _INLINE_KINDS

    name = download_name or (file_field.name or "fayl").rsplit("/", 1)[-1]
    response = FileResponse(
        handle,
        content_type=content_type,
        as_attachment=as_attachment,
        filename=name,
    )
    # Brauzer content type'ni "taxmin qilib" boshqacha talqin qilmasin.
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=0, no-store"
    return response


def _is_owner(user):
    return bool(user.is_superuser)


def receipt_file(request, receipt_id):
    """To'lov cheki: faqat chek egasi va staff/owner."""
    from cohorts.models import PaymentReceipt

    user = request.user
    _require(user.is_authenticated and user.is_active)
    receipt = PaymentReceipt.objects.filter(pk=receipt_id).select_related("enrollment").first()
    _require(receipt is not None)
    _require(
        receipt.enrollment.student_id == user.id or user.is_staff or user.is_superuser,
        request=request,
        target=receipt,
    )
    return serve_private_file(request, receipt.receipt_image)


def submission_file(request, submission_id):
    """Vazifa fayli: o'quvchining o'zi, kurs o'qituvchisi yoki owner."""
    from core.access import teacher_course_queryset
    from courses.models import AssignmentSubmission

    user = request.user
    _require(user.is_authenticated and user.is_active)
    submission = (
        AssignmentSubmission.objects.filter(pk=submission_id)
        .select_related("assignment__lesson__module__course")
        .first()
    )
    _require(submission is not None)

    if submission.student_id != user.id:
        course_id = submission.assignment.lesson.module.course_id
        _require(
            teacher_course_queryset(user).filter(pk=course_id).exists(),
            request=request,
            target=submission,
        )
    return serve_private_file(request, submission.attachment)


def message_attachment(request, message_id):
    """Chat biriktirmasi: faqat xona ishtirokchilari."""
    from messenger.access import user_can_access_room
    from messenger.models import Message

    user = request.user
    _require(user.is_authenticated and user.is_active)
    message = Message.objects.filter(pk=message_id).select_related("room").first()
    _require(message is not None and not message.is_deleted)
    _require(
        user_can_access_room(user, message.room),
        request=request,
        target=message,
    )
    return serve_private_file(
        request, message.attachment, download_name=message.attachment_name
    )


def exam_answer_audio(request, answer_id):
    """Speaking yozuvi: o'quvchining o'zi, imtihon kursining o'qituvchisi yoki owner."""
    from core.access import teacher_course_queryset
    from core.private_storage import private_media_storage
    from courses.models import StudentAnswer

    user = request.user
    _require(user.is_authenticated and user.is_active)
    answer = (
        StudentAnswer.objects.filter(pk=answer_id)
        .select_related("attempt__exam")
        .first()
    )
    _require(answer is not None and bool(answer.audio_key))

    if answer.attempt.student_id != user.id:
        _require(
            teacher_course_queryset(user).filter(pk=answer.attempt.exam.course_id).exists(),
            request=request,
            target=answer,
        )

    storage = private_media_storage()
    _require(storage.exists(answer.audio_key))
    handle = storage.open(answer.audio_key, "rb")
    kind = sniff_kind(handle)
    response = FileResponse(
        handle,
        content_type=_CONTENT_TYPES.get(kind, "application/octet-stream"),
        as_attachment=kind not in _INLINE_KINDS,
        filename=answer.audio_key.rsplit("/", 1)[-1],
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=0, no-store"
    return response
