r"""
Import employees/teachers from Rockland Access DB into a session.

Usage:
  python manage.py import_employees_from_access "C:\...\Rockland 2025-2026.accdb" --session SY2025-26 --clear
  python manage.py import_employees_from_access "C:\...\file.accdb" --session SY2025-26 --table "Employee data" --clear

To discover table names in the database:
  python manage.py import_employees_from_access "C:\...\Rockland 2025-2026.accdb" --list-tables
"""
import os
from datetime import date, datetime

import pyodbc
from django.core.management.base import BaseCommand
from django.db import connection

from sessions.models import AcademicSession, Employee, Site

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_ACCDB = os.path.normpath(
    os.path.join(BACKEND_DIR, "..", "..", "student data", "SY 2025-2026", "Rockland 2025-2026.accdb")
)


def date_from_value(v):
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return datetime.strptime(v[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    return None


def str_clean(s, max_len=None):
    if s is None:
        return ""
    out = str(s).strip()
    if max_len and len(out) > max_len:
        out = out[:max_len]
    return out


def get_col(rec, *names):
    """Get first present column (case-insensitive) from row dict."""
    keys_lower = {k.lower(): k for k in rec}
    for name in names:
        for key, orig in keys_lower.items():
            if name.lower() == key or name.lower() in key:
                return rec.get(orig)
    return None


def hasc_email(first_name, last_name, existing_emails):
    """Build firstname.lastname@hasc.net; if taken, append 2, 3, ... for uniqueness."""
    first = "".join(c for c in (first_name or "").lower() if c.isalnum() or c in " .-").replace(" ", ".").strip(".")
    last = "".join(c for c in (last_name or "").lower() if c.isalnum() or c in " .-").replace(" ", ".").strip(".")
    if not first:
        first = "first"
    if not last:
        last = "last"
    base = f"{first}.{last}@hasc.net"
    if base not in existing_emails:
        existing_emails.add(base)
        return base
    n = 2
    while True:
        candidate = f"{first}.{last}{n}@hasc.net"
        if candidate not in existing_emails:
            existing_emails.add(candidate)
            return candidate
        n += 1


class Command(BaseCommand):
    help = "Import employees/teachers from Access DB (.accdb) into an academic session."

    def add_arguments(self, parser):
        parser.add_argument(
            "accdb_path",
            nargs="?",
            default=os.environ.get("ROCK_ACCESS_IMPORT_PATH", DEFAULT_ACCDB),
            help="Full path to .accdb file",
        )
        parser.add_argument(
            "--session",
            default="SY2025-26",
            help="Session name to import into (e.g. SY2025-26)",
        )
        parser.add_argument(
            "--table",
            default="Teacher data",
            help="Access table name (e.g. 'Teacher data' or 'Employee data'). Use --list-tables to discover.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing employees in the session before importing",
        )
        parser.add_argument(
            "--list-tables",
            action="store_true",
            help="Only list table names in the database and exit",
        )

    def handle(self, *args, **options):
        accdb_path = options["accdb_path"]
        session_name = options["session"]
        table_name = options["table"]
        clear_first = options["clear"]
        list_tables = options["list_tables"]

        if not os.path.isfile(accdb_path):
            self.stderr.write(self.style.ERROR(f"File not found: {accdb_path}"))
            return

        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
            + os.path.abspath(accdb_path)
        )
        self.stdout.write(f"Connecting to {accdb_path} ...")
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        if list_tables:
            tables = []
            for row in cur.tables(tableType="TABLE"):
                # row has: table_cat, table_schem, table_name, table_type, remarks
                name = getattr(row, "table_name", None) or (row[2] if len(row) > 2 else None)
                if name and not name.startswith("MSys"):
                    tables.append(name)
            self.stdout.write("Tables: " + ", ".join(sorted(tables)))
            conn.close()
            return

        site_arg = (options.get("site") or "rockland").strip()
        try:
            site = Site.objects.get(slug=site_arg) if not str(site_arg).isdigit() else Site.objects.get(pk=int(site_arg))
        except Site.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Site not found: {site_arg}"))
            conn.close()
            return
        try:
            session = AcademicSession.objects.get(site=site, name=session_name)
        except AcademicSession.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Session not found: {session_name} (site: {site.slug})"))
            conn.close()
            return

        # Access table names with spaces need brackets
        if " " in table_name and not table_name.startswith("["):
            table_sql = f"[{table_name}]"
        else:
            table_sql = table_name

        try:
            cur.execute(f"SELECT * FROM {table_sql}")
        except pyodbc.Error as e:
            self.stderr.write(self.style.ERROR(f"Table '{table_name}' not found or error: {e}"))
            self.stdout.write("Use --list-tables to see available tables.")
            conn.close()
            return

        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()

        if clear_first:
            self.stdout.write(f"Clearing existing employees in {session_name} ...")
            with connection.cursor() as c:
                c.execute("DELETE FROM employees WHERE session_id = %s", [session.id])
            self.stdout.write(self.style.SUCCESS("Cleared."))

        created = 0
        skipped = 0
        existing_emails = set()
        for row in rows:
            rec = dict(zip(cols, row))
            first = str_clean(get_col(rec, "FIRSTNAME", "First Name", "FirstName") or "", 100)
            last = str_clean(get_col(rec, "LASTNAME", "Last Name", "LastName") or "", 100)
            if not first and not last:
                skipped += 1
                continue
            if not first:
                first = " "
            if not last:
                last = " "

            # All employees use firstname.lastname@hasc.net
            email = hasc_email(first, last, existing_emails)
            position = str_clean(get_col(rec, "POSITION", "Title", "Job Title", "Position") or "Staff", 100)
            phone = str_clean(get_col(rec, "PHONE", "Phone", "Phone Number") or "", 20) or None
            mobile_phone = str_clean(get_col(rec, "Cell", "Cell Phone", "Mobile", "MOBILE") or "", 20) or None
            notes = str_clean(get_col(rec, "NOTES", "Notes", "Note") or "", 2000) or None

            Employee.objects.create(
                session=session,
                first_name=first,
                last_name=last,
                email=email,
                position=position,
                phone=phone,
                mobile_phone=mobile_phone,
                notes=notes,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} employees into {session_name} (skipped {skipped})."))
