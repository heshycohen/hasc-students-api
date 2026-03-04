"""
Create superuser hcohen@hasc.net if not present.
Usage: python manage.py create_hcohen_superuser
Optional env: HCOHEN_PASSWORD (default: ChangeMe123!)
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
EMAIL = "hcohen@hasc.net"
USERNAME = "hcohen"
DEFAULT_PASSWORD = os.environ.get("HCOHEN_PASSWORD", "ChangeMe123!")


class Command(BaseCommand):
    help = "Create superuser hcohen@hasc.net if not present."

    def handle(self, *args, **options):
        if User.objects.filter(email=EMAIL).exists():
            self.stdout.write(self.style.WARNING(f"User {EMAIL} already exists. No change."))
            return
        User.objects.create_superuser(
            email=EMAIL,
            username=USERNAME,
            password=DEFAULT_PASSWORD,
        )
        self.stdout.write(self.style.SUCCESS(f"Superuser created: {EMAIL}"))
        self.stdout.write(self.style.WARNING(f"Temporary password: {DEFAULT_PASSWORD} — change it after logging in."))
