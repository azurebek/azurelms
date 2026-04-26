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


def user_can_access_room(user, room):
    if not user or not user.is_authenticated:
        return False

    participant_exists = room.participants.filter(id=user.id).exists()

    if room.room_type == "group" and room.cohort_id:
        if user.is_staff or user.is_superuser:
            return participant_exists
        return Enrollment.objects.filter(
            enrollment_active_access_q(),
            student=user,
            cohort_id=room.cohort_id,
        ).exists()

    if room.room_type in {"ai", "private"} and not (user.is_staff or user.is_superuser):
        return participant_exists and user_has_active_enrollment(user)

    return participant_exists


def sync_student_chat_access(student):
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
    personal_rooms = {
        "ai": f"Azure AI - {student.username}",
        "private": f"Ustoz bilan aloqa - {student.username}",
    }

    for room_type, room_name in personal_rooms.items():
        room = ChatRoom.objects.filter(room_type=room_type, name=room_name).first()

        if has_active_enrollment:
            if room is None:
                room = ChatRoom.objects.create(room_type=room_type, name=room_name)
            room.participants.add(student)

            if room_type == "private":
                admin_user = User.objects.filter(is_superuser=True).first()
                if admin_user:
                    room.participants.add(admin_user)
        elif room is not None:
            room.participants.remove(student)
