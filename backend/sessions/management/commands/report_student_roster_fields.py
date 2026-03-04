"""
Report how many students have school_district and class_num (CLASSNUM) set.
Use to confirm data before using the student list filters and roster.

Usage:
  python manage.py report_student_roster_fields --session SY2025-26
"""
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession, Student


class Command(BaseCommand):
    help = "Report counts of students with school_district and class_num (CLASSNUM) set per session."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session",
            default=None,
            help="Session name (e.g. SY2025-26). If omitted, report for all sessions.",
        )

    def handle(self, *args, **options):
        session_name = options.get("session")
        if session_name:
            try:
                session = AcademicSession.objects.get(name=session_name)
                sessions = [session]
            except AcademicSession.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Session not found: {session_name}"))
                return
        else:
            sessions = list(AcademicSession.objects.all().order_by("name"))

        for session in sessions:
            total = Student.objects.filter(session=session).count()
            with_sd = Student.objects.filter(session=session).exclude(school_district__isnull=True).exclude(school_district="").count()
            with_cls = Student.objects.filter(session=session).exclude(class_num__isnull=True).exclude(class_num="").count()
            with_both = Student.objects.filter(
                session=session
            ).exclude(school_district__isnull=True).exclude(school_district="").exclude(class_num__isnull=True).exclude(class_num="").count()
            missing_sd = total - with_sd
            missing_cls = total - with_cls

            self.stdout.write(f"\nSession: {session.name}")
            self.stdout.write(f"  Total students: {total}")
            self.stdout.write(f"  With school_district: {with_sd}" + (f" (missing: {missing_sd})" if missing_sd else ""))
            self.stdout.write(f"  With class_num (CLASSNUM): {with_cls}" + (f" (missing: {missing_cls})" if missing_cls else ""))
            self.stdout.write(f"  With both: {with_both}")
            if missing_sd or missing_cls:
                self.stdout.write(
                    self.style.WARNING(
                        "  Re-run import_from_access (and import_classrooms_from_access for roster) to fill missing data."
                    )
                )

        self.stdout.write("")
