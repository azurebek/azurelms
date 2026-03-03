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
            def process_ai_response():
                try:
                    # Identify the student who sent the message
                    student = instance.sender
                    user_question = text.replace('@azure', '').strip()
                    
                    # --- 1. Short-Term Memory ---
                    recent_msgs = Message.objects.filter(room=instance.room).order_by('-created_at')[:10]
                    dialogue = "\n".join([f"{msg.sender.username if msg.sender else 'Azure AI'}: {msg.text}" for msg in reversed(recent_msgs)])
                    
                    # --- 2. Long-Term Memory ---
                    long_term_memory, _ = AILongTermMemory.objects.get_or_create(user=student)

                    context_info = ""
                    if instance.context_lesson and instance.context_lesson.content:
                        context_info = f"\nO'quvchi hozir o'qiyotgan dars matni: {instance.context_lesson.content}"

                    # Yangi google-genai SDK orqali ulanish
                    client = genai.Client(api_key=settings.GEMINI_API_KEY)

                    prompt = (
                        "Sen AzureLMS platformasining aqlli yordamchisi va tajribali ustozisan. "
                        "Sening isming Azure AI. O'quvchiga doimo o'zbek tilida, do'stona, qisqa va aniq javob ber. "
                        "Sen AzureLMS qoidalarini yaxshi bilasan, kodlash va til o'rganishda professorsan.\n\n"
                        f"O'quvchi haqida joriy faktlar (Uzoq muddatli xotira):\n{long_term_memory.learned_facts}\n\n"
                        "Agar suhbat davomida o'quvchi haqida YANGI va MUHIM fakt (qiziqishi, yoshi, ishlash vaqti, kodi va hokazo) o'rgansang, uni albatta javobing oxirida <SAVE_MEMORY>...fakt...</SAVE_MEMORY> tegida qoldir. "
                        "Masalan: <SAVE_MEMORY>O'quvchi Pythonni asosan tunda o'rganishni yaxshi ko'radi.</SAVE_MEMORY>\n\n"
                        f"Suhbat tarixi (Qisqa muddatli xotira - oxirgi 10 xabar):\n{dialogue}\n\n"
                        f"O'quvchi hozirgi ochgan dars konteksti: {context_info}\n\n"
                        f"Yangi xabar: {user_question}"
                    )

                    # Eng yangi flash modelidan foydalanamiz
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    ai_reply_raw = response.text
                    ai_reply = ai_reply_raw
                    
                    # --- 3. Parse <SAVE_MEMORY> tag ---
                    memory_match = re.search(r'<SAVE_MEMORY>(.*?)</SAVE_MEMORY>', ai_reply_raw, re.DOTALL)
                    if memory_match:
                        new_fact = memory_match.group(1).strip()
                        long_term_memory.learned_facts += f"\n- {new_fact}"
                        long_term_memory.save()
                        ai_reply = ai_reply_raw.replace(memory_match.group(0), "").strip()

                except Exception as e:
                    print(f"\n❌ GEMINI XATOSI: {e}\n")
                    ai_reply = "Kechirasiz, hozircha ulanishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring."

                ai_message = Message.objects.create(
                    room=instance.room,
                    text=ai_reply,
                    is_ai_response=True,
                    context_lesson=instance.context_lesson
                )
                
                # --- 4. WebSocket Broadcast ---
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"chat_{instance.room.id}",
                    {
                        "type": "chat_message",
                        "id": ai_message.id,
                        "message": ai_message.text,
                        "sender_name": "Azure AI",
                        "sender_id": None,
                        "created_at": ai_message.created_at.strftime('%H:%M')
                    }
                )
                
                # Close DB connections created by thread
                close_old_connections()

            # Background thread to avoid blocking WebSocket from broadcasting the user's message
            threading.Thread(target=process_ai_response).start()