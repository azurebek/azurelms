from django.contrib.auth import get_user_model

from cohorts.models import Cohort, Enrollment, enrollment_active_access_q

from .models import ChatRoom


User = get_user_model()


def user_has_active_enrollment(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return Enrollment.objects.filter(enrollment_active_access_q(), student=user).exists()


def ensure_user_ai_room(user):
    if not user or not user.is_authenticated:
        return None

    room = ChatRoom.objects.filter(room_type="ai", participants=user).order_by("created_at").first()
    if room:
        return room

    room_name = f"Azure AI - {user.username}"
    room = ChatRoom.objects.filter(room_type="ai", name=room_name).order_by("created_at").first()
    if room is None:
        room = ChatRoom.objects.create(room_type="ai", name=room_name)
    room.participants.add(user)
    return room


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
