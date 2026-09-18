"""O'quvchiga ochiq yagona manzil: **bitta biriktirmaning** fayli.

Kutubxonaning o'zi uchun o'quvchi tomonda hech qanday ro'yxat, qidiruv yoki
manzil yo'q — bu modulning asosiy shartlaridan biri. Fayl ochiladigan yagona
yo'l shu view va u uch narsani serverda tekshiradi:

1. biriktirma ochiqmi (ko'rinadi, auditoriyasi o'quvchi, vaqti kelgan);
2. o'quvchining kursga faol obunasi bormi;
3. dars qulfi ochiqmi (`courses/access_service.py`).

Rad etish `404` beradi — `403` materialning mavjudligini tasdiqlab qo'yardi
(`core/private_media_views.py` dagi bir xil qoida).

`is_downloadable=False` — bu **DRM emas**: fayl baytlari baribir brauzerga
boradi. U faqat "yuklab olish" tugmasini olib tashlaydi va faylni brauzerda
ochadi; nusxa ko'chirishni to'sish uchun watermark kabi alohida ish kerak
(kelajakdagi personalizatsiya bandi).
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404

from core.access import teacher_course_queryset
from core.private_media_views import serve_private_file

from .models import LessonMaterial
from .services import student_can_open


@login_required
def material_file(request, material_id):
    material = get_object_or_404(
        LessonMaterial.objects.select_related("resource", "lesson__module__course"),
        pk=material_id,
    )
    user = request.user
    if not user.is_active:
        raise Http404

    is_owner_side = teacher_course_queryset(user).filter(
        pk=material.lesson.module.course_id
    ).exists()
    if not is_owner_side and not student_can_open(user, material):
        raise Http404

    return serve_private_file(
        request,
        material.resource.file,
        download_name=material.resource.original_filename or material.title,
        inline=not material.is_downloadable,
    )
