from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
from cohorts.models import Cohort, Enrollment
from courses.models import Lesson
from contextlib import contextmanager
from contextvars import ContextVar
import threading
import sys
import re

from .access import maybe_name_ai_room_from_first_prompt, sync_student_chat_access
from .models import ChatRoom, Message


_suppress_ai_signal = ContextVar("suppress_ai_signal", default=False)


@contextmanager
def suppress_ai_signal():
    token = _suppress_ai_signal.set(True)
    try:
        yield
    finally:
        _suppress_ai_signal.reset(token)


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
    if _suppress_ai_signal.get():
        return

    if created and not instance.is_ai_response:
        raw_text = instance.text or ""
        text_lower = raw_text.lower()
        maybe_name_ai_room_from_first_prompt(instance.room, raw_text)

        if instance.room.room_type == 'ai' or '@azure' in text_lower:
            # Delegate to Celery background task instead of native threading.Thread
            from .tasks import generate_ai_response

            user_question = re.sub(r"@azure", "", raw_text, flags=re.IGNORECASE).strip()
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


@receiver(post_save, sender=Lesson)
def reindex_lesson_chunks(sender, instance, **kwargs):
    from .tasks import reindex_lesson_rag

    if not getattr(settings, "GEMINI_API_KEY", None):
        return

    def _dispatch():
        try:
            reindex_lesson_rag.delay(lesson_id=instance.id)
        except Exception as e:
            print(f"Celery dispatch error for lesson reindex. Falling back to local execution: {e}")
            if "test" in sys.argv:
                reindex_lesson_rag.run(lesson_id=instance.id)
                return
            threading.Thread(
                target=reindex_lesson_rag.run,
                kwargs={"lesson_id": instance.id},
                daemon=True,
            ).start()

    transaction.on_commit(_dispatch)
