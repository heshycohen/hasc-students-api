r"""
Remove sample employees and import staff from Rockland Staff Rosters.mdb.

Usage:
  python manage.py import_from_staff_rosters
  python manage.py import_from_staff_rosters "C:\Dev\Rock-Access\ROSTERS\Rockland Staff Rosters.mdb"

Tables in the .mdb are mapped to sessions:
  - "Staff September 2025" -> SY2025-26
  - "Staff Summer 2025" -> Summer 2025
"""
import os
from datetime import date, datetime

import pyodbc
from django.core.management.base import BaseCommand
from django.db import connection

from sessions.models import AcademicSession, Employee

# Default: Rock-Access/ROSTERS/Rockland Staff Rosters.mdb
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_MDB = os.path.normpath(
    os.path.join(BACKEND_DIR, "..", "..", "ROSTERS", "Rockland Staff Rosters.mdb")
)

# Table name -> session name
TABLE_SESSION_MAP = [
    ("Staff September 2025", "SY2025-26"),
    ("Staff Summer 2025", "Summer 2025"),
]


def date_from_value(v):
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()[:16]
    if not s:
        return None
    for c in ("/", "."):
        s = s.replace(c, "-")
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            continue
    return None


def str_clean(s, max_len=None):
    if s is None:
        return ""
    out = str(s).strip()
    if max_len and len(out) > max_len:
        out = out[:max_len]
    return out


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


def get_col(rec, *names):
    """First present column (case-insensitive) from row dict."""
    keys_lower = {k.lower(): k for k in rec}
    for name in names:
        for key, orig in keys_lower.items():
            if name.lower() == key or name.lower() in key:
                return rec.get(orig)
    return None


class Command(BaseCommand):
    help = "Remove sample employees and import from Rockland Staff Rosters.mdb."

    def add_arguments(self, parser):
        parser.add_argument(
            "mdb_path",
            nargs="?",
            default=os.environ.get("ROCK_STAFF_ROSTERS_PATH", DEFAULT_MDB),
            help="Path to Rockland Staff Rosters.mdb",
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Do not delete existing employees before import (default: delete all first)",
        )

    def handle(self, *args, **options):
        mdb_path = options["mdb_path"]
        skip_clear = options["no_clear"]

        if not os.path.isfile(mdb_path):
            self.stderr.write(self.style.ERROR(f"File not found: {mdb_path}"))
            return

        if not skip_clear:
            self.stdout.write("Removing all existing employees (sample data)...")
            with connection.cursor() as c:
                c.execute("DELETE FROM employees")
            self.stdout.write(self.style.SUCCESS("Removed."))

        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ="
            + os.path.abspath(mdb_path)
        )
        self.stdout.write(f"Connecting to {mdb_path} ...")
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        total_created = 0
        for table_name, session_name in TABLE_SESSION_MAP:
            try:
                session = AcademicSession.objects.get(name=session_name)
            except AcademicSession.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Session {session_name} not found, skipping table {table_name}."))
                continue

            table_sql = f"[{table_name}]" if " " in table_name else table_name
            try:
                cur.execute(f"SELECT * FROM {table_sql}")
            except pyodbc.Error as e:
                self.stdout.write(self.style.WARNING(f"Table '{table_name}' not found: {e}"))
                continue

            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            created = 0
            skipped = 0
            existing_emails = set()

            for row in rows:
                rec = dict(zip(cols, row))
                first = str_clean(get_col(rec, "First Name", "FirstName", "FIRSTNAME") or "", 100)
                last = str_clean(get_col(rec, "Last Name", "LastName", "LASTNAME") or "", 100)
                if not first and not last:
                    skipped += 1
                    continue
                if not first:
                    first = " "
                if not last:
                    last = " "

                # All employees use firstname.lastname@hasc.net
                email = hasc_email(first, last, existing_emails)

                position = str_clean(get_col(rec, "Position", "Title", "POSITION") or "Staff", 100)

                home_phone = str_clean(get_col(rec, "Phone", "PHONE") or "", 20) or None
                mobile_phone = str_clean(get_col(rec, "Cell Phone#", "Cell Phone", "Cell Phone Number") or "", 20) or None
                notes = str_clean(get_col(rec, "Notes", "NOTES", "Nurses Notes") or "", 2000) or None

                Employee.objects.create(
                    session=session,
                    first_name=first,
                    last_name=last,
                    email=email,
                    position=position,
                    phone=home_phone,
                    mobile_phone=mobile_phone,
                    notes=notes,
                )
                created += 1
                total_created += 1

            self.stdout.write(self.style.SUCCESS(f"  {table_name} -> {session_name}: imported {created} (skipped {skipped})."))

        conn.close()
        self.stdout.write(self.style.SUCCESS(f"Total employees imported: {total_created}."))
