r"""
Import school districts from Rockland Access DB school district lookup table into a session.

Usage:
  python manage.py import_school_districts_from_access "C:\...\student data\SY 2025-2026\Rockland 2025-2026.accdb" --session SY2025-26
  python manage.py import_school_districts_from_access "C:\...\Rockland 2025-2026.mdb" --session SY2025-26 --clear

Reads table "Schooldist" column "SCHOOLDIST" (or fallback table/column names).
Uses same path env as student import: ROCK_ACCESS_IMPORT_PATH
"""
import os

import pyodbc
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession, SchoolDistrict, Site


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_PATH = os.path.normpath(
    os.path.join(BACKEND_DIR, "..", "..", "student data", "SY 2025-2026", "Rockland 2025-2026.accdb")
)


def get_db_path(path_arg):
    """Prefer .accdb; if path_arg is .mdb or missing file, try the other extension."""
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


class Command(BaseCommand):
    help = "Import school districts from Access lookup table into a session."

    def add_arguments(self, parser):
        parser.add_argument(
            "accdb_path",
            nargs="?",
            default=os.environ.get("ROCK_ACCESS_IMPORT_PATH", DEFAULT_PATH),
            help="Full path to Rockland YYYY-YYYY.accdb or .mdb",
        )
        parser.add_argument(
            "--session",
            default="SY2025-26",
            help="Session name (e.g. SY2025-26)",
        )
        parser.add_argument(
            "--site",
            default="rockland",
            help="Site slug or id (default: rockland)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing school districts for the session before importing",
        )

    def handle(self, *args, **options):
        db_path = get_db_path(options["accdb_path"])
        session_name = options["session"]
        clear_first = options["clear"]

        if not os.path.isfile(db_path):
            self.stderr.write(self.style.ERROR(f"File not found: {db_path}"))
            return

        try:
            session = AcademicSession.objects.get(name=session_name)
        except AcademicSession.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Session not found: {session_name}"))
            return

        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
            + os.path.abspath(db_path)
        )
        self.stdout.write(f"Connecting to {db_path} ...")
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Access table "Schooldist" with column "SCHOOLDIST" (per user's DB); fallback to other common names
        query = None
        for table, col in (
            ("[Schooldist]", "[SCHOOLDIST]"),
            ("[School District]", "[District]"),
            ("[School Districts]", "[Name]"),
        ):
            try:
                cur.execute(f"SELECT {col} FROM {table}")
                query = (table, col)
                break
            except pyodbc.Error:
                continue
        if not query:
            conn.close()
            self.stderr.write(
                self.style.ERROR(
                    "Could not find school district table. Tried: [Schooldist].SCHOOLDIST, "
                    "[School District].District, [School Districts].Name."
                )
            )
            return

        rows = cur.fetchall()
        conn.close()

        if clear_first:
            deleted, _ = SchoolDistrict.objects.filter(session=session).delete()
            self.stdout.write(self.style.SUCCESS(f"Cleared {deleted} existing school districts."))

        created = 0
        for row in rows:
            name = (row[0] or "").strip()
            if not name:
                continue
            if len(name) > 100:
                name = name[:100]
            _, created_this = SchoolDistrict.objects.get_or_create(
                session=session,
                name=name,
                defaults={"name": name},
            )
            if created_this:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported school districts for {session_name}: {created} new, "
            f"{SchoolDistrict.objects.filter(session=session).count()} total."
        ))
