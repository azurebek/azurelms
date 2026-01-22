from django import template

register = template.Library()

@register.filter
def display_name_for(room, user):
    """
    Returns the display name of a chat room for a specific user.
    Usage: {{ room|display_name_for:user }}
    """
    if hasattr(room, 'display_name_for'):
        return room.display_name_for(user)
    return str(room)
