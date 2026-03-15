from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from cohorts.models import Cohort, Enrollment
import threading

from .access import sync_student_chat_access
from .models import ChatRoom, Message


# ==========================================
# 1. GURUH YARATILGANDA - AVTOMATIK GURUH CHATI OCHISH
# ==========================================
@receiver(post_save, sender=Cohort)
def create_cohort_group_chat(sender, instance, created, **kwargs):
    if created:
        ChatRoom.objects.get_or_create(
            room_type='group',
            name=f"{instance.name} - Muloqot Guruhi",
            cohort=instance
        )


# ==========================================
# 2. O'QUVCHI GURUHGA QO'SHILGANDA - UNI CHATLARGA ULASH
# ==========================================
@receiver(post_save, sender=Enrollment)
def setup_student_chats(sender, instance, created, **kwargs):
    sync_student_chat_access(instance.student)


@receiver(post_delete, sender=Enrollment)
def teardown_student_chats(sender, instance, **kwargs):
    sync_student_chat_access(instance.student)


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
                try:
                    generate_ai_response.delay(
                        room_id=instance.room.id,
                        student_id=student_id,
                        user_question=user_question,
                        context_lesson_id=context_lesson_id
                    )
                except Exception as e:
                    # Celery vaqtincha ishlamasa ham user xabari saqlanib qolishi va AI javob qaytishi kerak.
                    print(f"Celery dispatch error. Falling back to local thread: {e}")
                    threading.Thread(
                        target=generate_ai_response.run,
                        kwargs={
                            "room_id": instance.room.id,
                            "student_id": student_id,
                            "user_question": user_question,
                            "context_lesson_id": context_lesson_id,
                        },
                        daemon=True,
                    ).start()
