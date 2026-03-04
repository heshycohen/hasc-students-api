"""
Custom auth backends so JWT login can use email (frontend sends email, not username).
"""
from django.contrib.auth.backends import ModelBackend
from .models import User


class EmailBackend(ModelBackend):
    """Authenticate using email and password (for JWT token endpoint)."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        if email is None:
            email = username
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
