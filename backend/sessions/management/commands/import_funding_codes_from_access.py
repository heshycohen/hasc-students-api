r"""
Import funding codes from Rockland Access DB "Funding Codes" table into a session.

Usage:
  python manage.py import_funding_codes_from_access "C:\...\student data\SY 2025-2026\Rockland 2025-2026.accdb" --session SY2025-26
  python manage.py import_funding_codes_from_access "C:\...\Rockland 2025-2026.mdb" --session SY2025-26 --clear

Uses same path env as student import: ROCK_ACCESS_IMPORT_PATH
"""
import os

import pyodbc
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession, FundingCode, Site


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
    help = "Import funding codes from Access 'Funding Codes' table (FUNDING column) into a session."

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
            help="Delete existing funding codes for the session before importing",
        )

    def handle(self, *args, **options):
        db_path = get_db_path(options["accdb_path"])
        session_name = options["session"]
        clear_first = options["clear"]

        if not os.path.isfile(db_path):
            self.stderr.write(self.style.ERROR(f"File not found: {db_path}"))
            return

        site_arg = (options.get("site") or "rockland").strip()
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

        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
            + os.path.abspath(db_path)
        )
        self.stdout.write(f"Connecting to {db_path} ...")
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        # Table name may be "Funding Codes" (with space)
        try:
            cur.execute('SELECT [FUNDING] FROM [Funding Codes]')
        except pyodbc.Error:
            try:
                cur.execute('SELECT [FUNDING] FROM [FundingCodes]')
            except pyodbc.Error as e:
                conn.close()
                self.stderr.write(self.style.ERROR(f"Could not read Funding Codes table: {e}"))
                return
        rows = cur.fetchall()
        conn.close()

        if clear_first:
            deleted, _ = FundingCode.objects.filter(session=session).delete()
            self.stdout.write(self.style.SUCCESS(f"Cleared {deleted} existing funding codes."))

        created = 0
        for row in rows:
            code = (row[0] or "").strip()
            if not code:
                continue
            if len(code) > 50:
                code = code[:50]
            _, created_this = FundingCode.objects.get_or_create(
                session=session,
                code=code,
                defaults={"code": code},
            )
            if created_this:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported funding codes for {session_name}: {created} new, {FundingCode.objects.filter(session=session).count()} total."
        ))
