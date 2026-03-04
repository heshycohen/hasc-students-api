"""
Create a few placeholder employees per session so the Employees list is not empty.
Use when no employee import source is available; you can edit or add real employees in the app.

Usage:
  python manage.py seed_employees
  python manage.py seed_employees --session SY2025-26
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from sessions.models import AcademicSession, Employee


# Placeholder employees to create per session (only if the session has none)
PLACEHOLDERS = [
    {"first_name": "Staff", "last_name": "One", "email": "staff1@example.local", "position": "Teacher"},
    {"first_name": "Staff", "last_name": "Two", "email": "staff2@example.local", "position": "Assistant"},
    {"first_name": "Staff", "last_name": "Three", "email": "staff3@example.local", "position": "Admin"},
]


class Command(BaseCommand):
    help = "Seed placeholder employees for sessions that have none."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session",
            default=None,
            help="Session name (e.g. SY2025-26). If omitted, seed all sessions that have 0 employees.",
        )

    def handle(self, *args, **options):
        session_name = options["session"]

        if session_name:
            try:
                sessions = [AcademicSession.objects.get(name=session_name)]
            except AcademicSession.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Session not found: {session_name}"))
                return
        else:
            sessions = AcademicSession.objects.all().order_by("-start_date")

        created_total = 0
        with transaction.atomic():
            for session in sessions:
                count = Employee.objects.filter(session=session).count()
                if count > 0:
                    self.stdout.write(f"Session {session.name} already has {count} employees, skipping.")
                    continue
                for i, p in enumerate(PLACEHOLDERS):
                    email = p["email"].replace("@", f".{session.id}.{i}@")
                    Employee.objects.create(
                        session=session,
                        first_name=p["first_name"],
                        last_name=p["last_name"],
                        email=email,
                        position=p["position"],
                    )
                    created_total += 1
                self.stdout.write(self.style.SUCCESS(f"Seeded {len(PLACEHOLDERS)} employees for {session.name}."))

        if created_total:
            self.stdout.write(self.style.SUCCESS(f"Created {created_total} placeholder employees total."))
        else:
            self.stdout.write("No sessions needed seeding (all already have employees).")
