from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from cohorts.models import Cohort, Enrollment
from .models import ChatRoom, Message
import google.generativeai as genai
from django.conf import settings

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
            user_question = text.replace('@azure', '').strip()

            context_info = ""
            if instance.context_lesson and instance.context_lesson.content:
                context_info = f"\nO'quvchi hozir o'qiyotgan dars matni: {instance.context_lesson.content}"

            try:
                # Yangi, zamonaviy usulda ulanish
                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                prompt = (
                    "Sen AzureLMS platformasining aqlli yordamchisi va tajribali Turk tili ustozisan. "
                    "Sening isming Azure AI. O'quvchiga o'zbek tilida, do'stona, qisqa va aniq javob ber. "
                    f"O'quvchining savoli: {user_question} {context_info}"
                )

                # Eng yangi "gemini-2.0-flash" modelidan foydalanamiz
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                ai_reply = response.text

            except Exception as e:
                print(f"\n❌ GEMINI XATOSI: {e}\n")
                ai_reply = "Kechirasiz, hozircha ulanishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring."

            Message.objects.create(
                room=instance.room,
                text=ai_reply,
                is_ai_response=True,
                context_lesson=instance.context_lesson
            )