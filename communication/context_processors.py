from .utils import build_room_groups, get_user_rooms


def communication_rooms(request):
    rooms = get_user_rooms(request.user)
    return build_room_groups(rooms)
