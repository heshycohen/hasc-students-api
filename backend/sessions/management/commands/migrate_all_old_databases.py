r"""
Migrate all Access databases from OLD DATABASES (Summer 2008–Summer 2024, SY2009–SY2023-24).

Scans a folder for .mdb/.accdb files, creates AcademicSession for each, then runs:
  import_from_access, import_classrooms_from_access, import_employees_from_access,
  import_funding_codes_from_access, import_school_districts_from_access

Older DBs may use "Student data" instead of "QRY_student Data Center Based", and
"Employee data" instead of "Teacher data"; the command detects which tables exist.

Usage:
  python manage.py migrate_all_old_databases
  python manage.py migrate_all_old_databases "C:\Dev\Rock-Access\OLD DATABASES"
  python manage.py migrate_all_old_databases --dry-run
  python manage.py migrate_all_old_databases --session "SY2021-22"  # only that session
"""
import os
import re
from datetime import date
from django.core.management import call_command
from django.core.management.base import BaseCommand

from sessions.models import AcademicSession


DEFAULT_OLD_DATABASES = r"C:\Dev\Rock-Access\OLD DATABASES"

# Table names to try (first existing wins)
STUDENT_TABLE_CANDIDATES = ["QRY_student Data Center Based", "Student data"]
EMPLOYEE_TABLE_CANDIDATES = ["Teacher data", "Employee data"]


def get_access_tables(db_path):
    """Return set of table names in the Access database (no MSys)."""
    try:
        import pyodbc
    except ImportError:
        return set()
    conn_str = r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=" + os.path.abspath(db_path)
    conn = pyodbc.connect(conn_str)
    try:
        tables = set()
        for row in conn.cursor().tables(tableType="TABLE"):
            name = getattr(row, "table_name", None) or (row[2] if len(row) > 2 else None)
            if name and not name.startswith("MSys"):
                tables.add(name)
        return tables
    finally:
        conn.close()


def pick_table(candidates, available):
    """Return first candidate that is in available, or candidates[0] if none match."""
    for c in candidates:
        if c in available:
            return c
    return candidates[0]


def parse_session_from_filename(filename):
    """
    Return (session_name, session_type, start_date, end_date) or None.
    session_name must match AcademicSession.name (e.g. "Summer 2008", "SY2008-09").
    """
    base = os.path.splitext(filename)[0]
    base_lower = base.lower()
    # Skip backups and noise
    if "backup" in base_lower or base_lower.startswith("backup of"):
        return None
    # Summer YYYY
    m = re.search(r"summer\s*(\d{4})", base_lower, re.I)
    if m:
        y = int(m.group(1))
        return (
            f"Summer {y}",
            "SUMMER",
            date(y, 6, 1),
            date(y, 8, 31),
        )
    # SY yyyy-yyyy or SYyyyy-yyyy or SY yyyy-yy
    m = re.search(r"sy\s*(\d{4})[-_\s]*(\d{2,4})", base_lower, re.I)
    if m:
        y1 = int(m.group(1))
        y2_str = m.group(2).strip()
        if len(y2_str) == 2:
            y2 = 2000 + int(y2_str)
        else:
            y2 = int(y2_str)
        return (
            f"SY{y1}-{str(y2)[-2:]}",
            "SY",
            date(y1, 9, 1),
            date(y2, 6, 30),
        )
    # "School Year Database 2007-08" or "Rockland 2009-2010"
    m = re.search(r"(?:school\s*year\s*database|rockland)\s*(\d{4})[-_\s]*(\d{2,4})", base_lower, re.I)
    if m:
        y1 = int(m.group(1))
        y2_str = m.group(2).strip()
        if len(y2_str) == 2:
            y2 = 2000 + int(y2_str)
        else:
            y2 = int(y2_str)
        return (
            f"SY{y1}-{str(y2)[-2:]}",
            "SY",
            date(y1, 9, 1),
            date(y2, 6, 30),
        )
    return None


def discover_db_files(folder):
    """Yield (full_path, session_name, session_type, start_date, end_date) for each .mdb/.accdb."""
    if not os.path.isdir(folder):
        return
    seen_session = set()
    files_with_sessions = []
    for name in os.listdir(folder):
        low = name.lower()
        if low.endswith(".lnk") or low.endswith(".ldb") or low.endswith(".laccdb"):
            continue
        if low.endswith(".mde"):
            # .mde is compiled Access; treat like .mdb
            pass
        elif not (low.endswith(".mdb") or low.endswith(".accdb")):
            continue
        # Ignore any file with "backup" in the name
        if "backup" in low:
            continue
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        parsed = parse_session_from_filename(name)
        if not parsed:
            continue
        session_name, session_type, start_d, end_d = parsed
        if session_name in seen_session:
            # Prefer .accdb over .mdb when same session has both
            existing = next((f for f in files_with_sessions if f[1] == session_name), None)
            if existing and name.lower().endswith(".accdb") and not existing[0].lower().endswith(".accdb"):
                files_with_sessions.remove(existing)
                seen_session.discard(session_name)
            else:
                continue
        seen_session.add(session_name)
        files_with_sessions.append((path, session_name, session_type, start_d, end_d))

    # Sort: Summer 2008, 2009, ... then SY2007-08, SY2008-09, ...
    def key(item):
        path, session_name, session_type, start_d, end_d = item
        if session_type == "SUMMER":
            return (0, start_d)
        return (1, start_d)

    files_with_sessions.sort(key=key)
    for item in files_with_sessions:
        yield item


class Command(BaseCommand):
    help = "Migrate all Access databases from OLD DATABASES into academic sessions."

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            nargs="?",
            default=DEFAULT_OLD_DATABASES,
            help=f"Folder containing .mdb/.accdb files (default: {DEFAULT_OLD_DATABASES})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only list files and sessions that would be created/imported",
        )
        parser.add_argument(
            "--session",
            type=str,
            default=None,
            help="Only process this session name (e.g. SY2021-22 or 'Summer 2020')",
        )

    def handle(self, *args, **options):
        folder = os.path.abspath(options["folder"])
        dry_run = options["dry_run"]
        only_session = options.get("session")

        if not os.path.isdir(folder):
            self.stderr.write(self.style.ERROR(f"Folder not found: {folder}"))
            return

        db_list = list(discover_db_files(folder))
        if not db_list:
            self.stdout.write(self.style.WARNING(f"No .mdb/.accdb files found in {folder}"))
            return

        if only_session:
            db_list = [(p, sn, st, sd, ed) for p, sn, st, sd, ed in db_list if sn == only_session]
            if not db_list:
                self.stderr.write(self.style.ERROR(f"No file mapped to session: {only_session}"))
                return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: would process {len(db_list)} database(s) from {folder}"))
            for path, session_name, session_type, start_d, end_d in db_list:
                self.stdout.write(f"  {session_name}  ({session_type})  {start_d} – {end_d}  <- {os.path.basename(path)}")
            return

        for path, session_name, session_type, start_d, end_d in db_list:
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO(f"=== {session_name} <- {os.path.basename(path)} ==="))

            # Create or get session
            session, created = AcademicSession.objects.get_or_create(
                name=session_name,
                defaults={
                    "session_type": session_type,
                    "start_date": start_d,
                    "end_date": end_d,
                    "is_active": False,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created session: {session_name}"))

            tables = get_access_tables(path)
            student_table = pick_table(STUDENT_TABLE_CANDIDATES, tables)
            employee_table = pick_table(EMPLOYEE_TABLE_CANDIDATES, tables)

            # 1) Students
            call_command(
                "import_from_access",
                path,
                "--session", session_name,
                "--clear",
                "--table", student_table,
                stdout=self.stdout,
                stderr=self.stderr,
            )

            # 2) Classrooms
            try:
                call_command(
                    "import_classrooms_from_access",
                    path,
                    "--session", session_name,
                    "--clear",
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Classrooms skipped: {e}"))

            # 3) Employees
            call_command(
                "import_employees_from_access",
                path,
                "--session", session_name,
                "--clear",
                "--table", employee_table,
                stdout=self.stdout,
                stderr=self.stderr,
            )

            # 4) Funding codes
            try:
                call_command(
                    "import_funding_codes_from_access",
                    path,
                    "--session", session_name,
                    "--clear",
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Funding codes skipped: {e}"))

            # 5) School districts
            try:
                call_command(
                    "import_school_districts_from_access",
                    path,
                    "--session", session_name,
                    "--clear",
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  School districts skipped: {e}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done. Processed {len(db_list)} database(s)."))
