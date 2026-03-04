r"""
Import classrooms from Rockland Access DB "Classes" table into a session.

Reads CLASSNUM, CLASSSIZE, TEACHER, ASSISTANT1, ASSISTANT2. This is the chart that
assigns teacher and assistant1/assistant2 per class number; the roster uses CLASSNUM
from student data to look up these values for each class section.

Usage:
  python manage.py import_classrooms_from_access "C:\...\Rockland 2025-2026.mdb" --session SY2025-26
  python manage.py import_classrooms_from_access --session SY2025-26 --clear
"""
import os

import pyodbc
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession, Classroom, Site


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_PATH = os.path.normpath(
    os.path.join(BACKEND_DIR, "..", "..", "student data", "SY 2025-2026", "Rockland 2025-2026.accdb")
)


def get_db_path(path_arg):
    if not path_arg:
        path_arg = os.environ.get("ROCK_ACCESS_IMPORT_PATH", DEFAULT_PATH)
    path_arg = os.path.normpath(path_arg)
    if os.path.isfile(path_arg):
        return path_arg
    base, ext = os.path.splitext(path_arg)
    other = base + (".mdb" if ext.lower() == ".accdb" else ".accdb")
    if os.path.isfile(other):
        return other
    return path_arg


def str_clean(s, max_len=100):
    if s is None:
        return ""
    out = str(s).strip()
    if max_len and len(out) > max_len:
        out = out[:max_len]
    return out or ""


class Command(BaseCommand):
    help = "Import classrooms from Access 'Classes' table (CLASSNUM, CLASSSIZE, TEACHER, ASSISTANT1, ASSISTANT2)."

    def add_arguments(self, parser):
        parser.add_argument(
            "accdb_path",
            nargs="?",
            default=os.environ.get("ROCK_ACCESS_IMPORT_PATH", DEFAULT_PATH),
            help="Path to Rockland .accdb or .mdb",
        )
        parser.add_argument("--session", default="SY2025-26", help="Session name")
        parser.add_argument("--site", default="rockland", help="Site slug or id (default: rockland)")
        parser.add_argument("--clear", action="store_true", help="Delete existing classrooms for session first")

    def handle(self, *args, **options):
        db_path = get_db_path(options["accdb_path"])
        session_name = options["session"]
        site_arg = (options.get("site") or "rockland").strip()
        clear_first = options["clear"]

        if not os.path.isfile(db_path):
            self.stderr.write(self.style.ERROR(f"File not found: {db_path}"))
            return

        try:
            site = Site.objects.get(slug=site_arg) if not str(site_arg).isdigit() else Site.objects.get(pk=int(site_arg))
        except Site.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Site not found: {site_arg}"))
            return
        try:
            session = AcademicSession.objects.get(site=site, name=session_name)
        except AcademicSession.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Session not found: {session_name} (site: {site.slug})"))
            return

        conn_str = r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=" + os.path.abspath(db_path)
        self.stdout.write(f"Connecting to {db_path} ...")
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT [CLASSNUM], [CLASSSIZE], [TEACHER], [ASSISTANT1], [ASSISTANT2] FROM [Classes]"
            )
        except pyodbc.Error as e:
            conn.close()
            self.stderr.write(self.style.ERROR(f"Could not read Classes table: {e}"))
            return
        rows = cur.fetchall()
        conn.close()

        if clear_first:
            deleted, _ = Classroom.objects.filter(session=session).delete()
            self.stdout.write(self.style.SUCCESS(f"Cleared {deleted} classrooms."))

        created = 0
        updated = 0
        for row in rows:
            class_num = str_clean(row[0], 50)
            if not class_num:
                continue
            class_size = str_clean(row[1], 50) or None
            teacher = str_clean(row[2], 100) or None
            assistant1 = str_clean(row[3], 100) or None
            assistant2 = str_clean(row[4], 100) or None
            obj, created_this = Classroom.objects.update_or_create(
                session=session,
                class_num=class_num,
                defaults={
                    "class_size": class_size,
                    "teacher": teacher,
                    "assistant1": assistant1,
                    "assistant2": assistant2,
                },
            )
            if created_this:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Classrooms for {session_name}: {created} created, {updated} updated, "
                f"{Classroom.objects.filter(session=session).count()} total."
            )
        )
