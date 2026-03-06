from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from cohorts.models import Cohort, Enrollment
from .models import ChatRoom, Message, AILongTermMemory
from google import genai
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import re
import threading
from django.db import close_old_connections

User = get_user_model()


# ==========================================
# 1. GURUH YARATILGANDA - AVTOMATIK GURUH CHATI OCHISH
# ==========================================
@receiver(post_save, sender=Cohort)
def create_cohort_group_chat(sender, instance, created, **kwargs):
    if created:
        ChatRoom.objects.create(
            room_type='group',
            name=f"{instance.name} - Muloqot Guruhi",
            cohort=instance
        )


# ==========================================
# 2. O'QUVCHI GURUHGA QO'SHILGANDA - UNI CHATLARGA ULASH
# ==========================================
@receiver(post_save, sender=Enrollment)
def setup_student_chats(sender, instance, created, **kwargs):
    if created:
        student = instance.student

        # A) O'quvchini guruh chatiga avtomatik qo'shish
        group_chat = ChatRoom.objects.filter(cohort=instance.cohort, room_type='group').first()
        if group_chat:
            group_chat.participants.add(student)

        # B) AI Chatni tekshirish va yaratish (Bitta o'quvchiga 1 ta AI xonasi yetadi)
        ai_chat, ai_created = ChatRoom.objects.get_or_create(
            room_type='ai',
            name=f"Azure AI - {student.username}"
        )
        if ai_created:
            ai_chat.participants.add(student)

        # C) Ustoz (Admin) bilan 1:1 chat yaratish
        tutor_chat, tutor_created = ChatRoom.objects.get_or_create(
            room_type='private',
            name=f"Ustoz bilan aloqa - {student.username}"
        )
        if tutor_created:
            tutor_chat.participants.add(student)

            # Tizimdagi asosiy adminni (masalan, o'zingizni) shu chatga ustoz sifatida qo'shib qo'yish:
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                tutor_chat.participants.add(admin_user)


# ==========================================
# 3. HAQIQIY AZURE AI JAVOB QAYTARISH MANTIG'I (YANGI SDK)
# ==========================================
@receiver(post_save, sender=Message)
def trigger_azure_ai(sender, instance, created, **kwargs):
    if created and not instance.is_ai_response:
        text = instance.text.lower()

        if instance.room.room_type == 'ai' or '@azure' in text:
            # Delegate to Celery background task instead of native threading.Thread
            from .tasks import generate_ai_response
            
            user_question = text.replace('@azure', '').strip()
            student_id = instance.sender.id if instance.sender else None
            context_lesson_id = instance.context_lesson.id if instance.context_lesson else None
            
            if student_id:
                generate_ai_response.delay(
                    room_id=instance.room.id,
                    student_id=student_id,
                    user_question=user_question,
                    context_lesson_id=context_lesson_id
                )