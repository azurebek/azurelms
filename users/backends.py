from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """
    Foydalanuvchiga ham username, ham email orqali tizimga kirish imkonini beruvchi backend.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Username yoki Email orqali foydalanuvchini qidiramiz (case-insensitive for email)
            user = User.objects.get(Q(username=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        
        # Parolni tekshiramiz
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
