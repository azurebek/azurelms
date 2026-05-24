from django.contrib.auth import get_user_model

from cohorts.models import Cohort, Enrollment, enrollment_active_access_q

from .models import ChatRoom


User = get_user_model()
DEFAULT_AI_ROOM_TITLE = "Yangi AI chat"
MAX_AI_ROOM_TITLE_LENGTH = 56


def user_has_active_enrollment(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return Enrollment.objects.filter(enrollment_active_access_q(), student=user).exists()


def user_can_use_lesson_context(user, lesson):
    if not user or not user.is_authenticated or not lesson:
        return False
    if user.is_staff or user.is_superuser:
        return True

    course_id = getattr(lesson.module, "course_id", None)
    if not course_id:
        return False

    return Enrollment.objects.filter(
        enrollment_active_access_q(),
        student=user,
        cohort__course_id=course_id,
    ).exists()


def ensure_user_ai_room(user):
    if not user or not user.is_authenticated:
        return None

    room = ChatRoom.objects.filter(room_type="ai", participants=user).order_by("-created_at").first()
    if room:
        return room

    return create_user_ai_room(user)


def create_user_ai_room(user):
    if not user or not user.is_authenticated:
        return None

    room = ChatRoom.objects.create(room_type="ai", name=DEFAULT_AI_ROOM_TITLE)
    room.participants.add(user)
    return room


def derive_ai_room_name_from_prompt(prompt):
    clean_prompt = " ".join((prompt or "").split())
    if not clean_prompt:
        return DEFAULT_AI_ROOM_TITLE

    words = clean_prompt.split(" ")[:7]
    title = " ".join(words).strip(" .,!?;:-")
    if len(title) > MAX_AI_ROOM_TITLE_LENGTH:
        title = title[:MAX_AI_ROOM_TITLE_LENGTH].rsplit(" ", 1)[0].strip(" .,!?;:-")
    return title[:1].upper() + title[1:] if title else DEFAULT_AI_ROOM_TITLE


def maybe_name_ai_room_from_first_prompt(room, prompt):
    if not room or room.room_type != "ai":
        return False

    user_message_count = room.messages.filter(is_ai_response=False).count()
    if user_message_count != 1:
        return False

    new_name = derive_ai_room_name_from_prompt(prompt)
    if room.name == new_name:
        return False

    room.name = new_name
    room.save(update_fields=["name"])
    return True


def user_can_access_room(user, room):
    if not user or not user.is_authenticated:
        return False

    participant_exists = room.participants.filter(id=user.id).exists()

    if room.room_type == "ai":
        return participant_exists

    if room.room_type == "group" and room.cohort_id:
        if user.is_staff or user.is_superuser:
            return participant_exists
        return Enrollment.objects.filter(
            enrollment_active_access_q(),
            student=user,
            cohort_id=room.cohort_id,
        ).exists()

    if room.room_type == "private" and not (user.is_staff or user.is_superuser):
        return participant_exists and user_has_active_enrollment(user)

    return participant_exists


def sync_student_chat_access(student):
    ensure_user_ai_room(student)

    active_cohort_ids = list(
        Enrollment.objects.filter(enrollment_active_access_q(), student=student).values_list("cohort_id", flat=True)
    )

    active_cohorts = Cohort.objects.filter(id__in=active_cohort_ids)
    for cohort in active_cohorts:
        room, _ = ChatRoom.objects.get_or_create(
            room_type="group",
            cohort=cohort,
            defaults={"name": f"{cohort.name} - Muloqot Guruhi"},
        )
        room.participants.add(student)

    stale_group_rooms = (
        ChatRoom.objects.filter(room_type="group", participants=student)
        .exclude(cohort_id__in=active_cohort_ids)
    )
    for room in stale_group_rooms:
        room.participants.remove(student)

    has_active_enrollment = bool(active_cohort_ids)
    private_room_name = f"Ustoz bilan aloqa - {student.username}"
    private_room = ChatRoom.objects.filter(room_type="private", name=private_room_name).first()

    if has_active_enrollment:
        if private_room is None:
            private_room = ChatRoom.objects.create(room_type="private", name=private_room_name)
        private_room.participants.add(student)

        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            private_room.participants.add(admin_user)
    elif private_room is not None:
        private_room.participants.remove(student)
