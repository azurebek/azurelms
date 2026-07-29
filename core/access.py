def is_backoffice_user(user):
    return user.is_staff or user.is_superuser


def is_control_center_owner(user):
    return user.is_active and user.is_superuser
