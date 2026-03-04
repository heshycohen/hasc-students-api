"""
Set each employee's email to their HASC email: first_name.last_name@hasc.net
(e.g. Heshy Cohen -> heshy.cohen@hasc.net). First and last names are lowercased
and non-alphanumeric characters are removed.

Usage:
  python manage.py set_employee_hasc_emails
  python manage.py set_employee_hasc_emails --session SY2025-26
  python manage.py set_employee_hasc_emails --dry-run
"""
import re
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession, Employee


def to_hasc_local_part(s):
    """Lowercase and keep only a-z0-9 for email local part."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())


def hasc_email(first_name, last_name):
    """Build first.last@hasc.net; uses 'staff' if name is empty."""
    first = to_hasc_local_part(first_name) or "staff"
    last = to_hasc_local_part(last_name) or "staff"
    return f"{first}.{last}@hasc.net"


class Command(BaseCommand):
    help = "Set employee emails to first_name.last_name@hasc.net (e.g. heshy.cohen@hasc.net)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session",
            default=None,
            help="Session name (e.g. SY2025-26). If omitted, update all employees in all sessions.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be updated, do not save.",
        )

    def handle(self, *args, **options):
        session_name = options.get("session")
        dry_run = options.get("dry_run", False)

        queryset = Employee.objects.all().select_related("session")
        if session_name:
            try:
                session = AcademicSession.objects.get(name=session_name)
                queryset = queryset.filter(session=session)
            except AcademicSession.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Session not found: {session_name}"))
                return

        updated = 0
        for emp in queryset:
            new_email = hasc_email(emp.first_name, emp.last_name)
            if emp.email != new_email:
                self.stdout.write(f"  {emp.first_name} {emp.last_name}: {emp.email} -> {new_email}")
                if not dry_run:
                    emp.email = new_email
                    emp.save()
                updated += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run: would update {updated} employee(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated} employee(s) to HASC email format."))
