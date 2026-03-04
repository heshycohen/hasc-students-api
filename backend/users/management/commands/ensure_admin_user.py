"""
Create or reset superuser admin@example.com so login works.
Usage: python manage.py ensure_admin_user
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
EMAIL = "admin@example.com"
USERNAME = "admin"
PASSWORD = "admin123"


class Command(BaseCommand):
    help = "Create or reset superuser admin@example.com (password: admin123)."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            email=EMAIL,
            defaults={"username": USERNAME, "role": "admin"},
        )
        user.set_password(PASSWORD)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {EMAIL}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Password reset for: {EMAIL}"))
        self.stdout.write(self.style.WARNING(f"Login with email {EMAIL} and password {PASSWORD}"))
