r"""
Import students from Rockland Access DB (Rockland YYYY-YYYY.accdb) into a session.

Uses query "QRY_student Data Center Based" by default (has CLASSNUM; rows with
CLASSNUM 17 are skipped). CLASSNUM maps to Teacher/Assistant1/Assistant2 via the
Classroom table—run import_classrooms_from_access to load from [Classes].

Usage:
  python manage.py import_from_access "C:\...\Rockland 2025-2026.accdb" --session SY2025-26 --clear
  python manage.py import_from_access --table "Student data" --session SY2025-26  # legacy table

Or set default path via env:
  ROCK_ACCESS_IMPORT_PATH="C:\...\Rockland 2025-2026.accdb"
  python manage.py import_from_access --session SY2025-26 --clear
"""
import csv
import os
from collections import Counter, defaultdict
from datetime import date, datetime

import pyodbc
from django.core.management.base import BaseCommand
from django.db import connection

from sessions.models import AcademicSession, Student, Site


# Default path: Rock-Access/student data/SY 2025-2026/Rockland 2025-2026.accdb (sibling of rock-access-web)
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


def parse_dob_robust(val):
    """
    Parse DOB from CSV/Access. Returns date or None.
    Accepts: YYYY-MM-DD, MM/DD/YYYY, M/D/YYYY, M/D/YY (2-digit year).
    Access/PowerShell CSV export frequently yields "M/D/YYYY 0:00:00"; normalize by
    dropping the time portion before parsing.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Access/PowerShell CSV export frequently yields: "M/D/YYYY 0:00:00"
    # Normalize by dropping the time portion.
    if " " in s:
        first_token = s.split(" ", 1)[0].strip()
        if "/" in first_token or "-" in first_token:
            s = first_token
    # Now parse s using existing formats: %Y-%m-%d, %m/%d/%Y, M/D/YYYY, %m/%d/%y, etc.
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d/%m/%y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(s[:10], fmt).date()
            # 2-digit year: 00-68 -> 2000-2068, 69-99 -> 1969-1999 (strptime %y behavior)
            return parsed
        except ValueError:
            continue
    # Try M/D/YYYY or M/D/YY with single-digit month/day (e.g. "1/5/2020")
    parts = s.replace("-", "/").split("/")
    if len(parts) == 3:
        try:
            m, d, y = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if len(y) == 2:
                y = int(y)
                y = 2000 + y if y < 50 else 1900 + y
            else:
                y = int(y)
            month = int(m)
            day = int(d)
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= y <= 2100:
                return date(y, month, day)
        except (ValueError, TypeError):
            pass
    return None


def str_clean(s, max_len=None):
    if s is None:
        return ""
    out = str(s).strip()
    if max_len and len(out) > max_len:
        out = out[:max_len]
    return out


def get_first(rec, keys, default=None):
    """Return first non-empty value from rec for any of the given keys (case-insensitive)."""
    rec_lower = {str(k).lower(): v for k, v in rec.items()}
    for k in keys:
        v = rec_lower.get(str(k).lower()) or rec.get(k)
        if v is not None and str(v).strip():
            return v
    return default


def normalize_x_bool(val):
    """Return True if val looks like a yes/true/x flag; else False. Used for DISCHARGE -> is_discharged."""
    if val is None:
        return False
    s = str(val).strip().lower()
    if not s:
        return False
    return s in ("x", "1", "yes", "true", "y")


def _normalize_contact(val):
    if val is None or not str(val).strip():
        return ""
    return str(val).strip().lower()


def _narrow_by_contact(candidates_queryset, access_phone, access_email, access_address):
    """
    When multiple DB students match (same name+DOB), try to pick one by contact overlap.
    Returns the single Student if exactly one candidate matches any of phone/email/address; else None.
    """
    access_phone = _normalize_contact(access_phone)
    access_email = _normalize_contact(access_email)
    access_address = _normalize_contact(access_address)
    if not access_phone and not access_email and not access_address:
        return None
    matched = []
    for student in candidates_queryset:
        p = _normalize_contact(student.parent_phone) or _normalize_contact(student.home_phone)
        e = _normalize_contact(student.email) or _normalize_contact(getattr(student, "parent_email", None))
        a = _normalize_contact(student.address)
        if access_phone and p and (access_phone in p or p in access_phone):
            matched.append(student)
            continue
        if access_email and e and (access_email in e or e in access_email):
            matched.append(student)
            continue
        if access_address and a and (access_address[:20] in a or a[:20] in access_address):
            matched.append(student)
            continue
    if len(matched) == 1:
        return matched[0]
    return None


def _pick_best_duplicate_row(candidates, session_start):
    """
    From multiple (row_idx, rec, data) for the same student, pick one by rule:
    prefer non-empty Student ID, else latest medical_end_date, else latest medical_start_date,
    else most non-empty fields, else first row.
    """
    date_min = date(1900, 1, 1)

    def score(t):
        row_idx, rec, data = t
        has_student_id = bool(get_first(rec, ["Student ID", "StudentID", "STUDENT ID"]))
        med_end = data.get("medical_end_date") or date_min
        med_start = data.get("medical_start_date") or date_min
        non_empty = sum(1 for v in data.values() if v not in (None, ""))
        return (has_student_id, med_end, med_start, non_empty, -row_idx)

    return max(candidates, key=score)


def derive_service_type(spedserv_raw, class_num, sped_indiv_code_raw=None):
    """
    Derive service_type from Access SPEDSERV, CLASSNUM, and/or SPEDINDIV codes.
    SPEDINDIV codes (ctr/rs/seit) is the main source in many Access exports; SPEDSERV is often empty.
    """
    spedserv = (str_clean(spedserv_raw or "")).upper()
    indiv = (str_clean(sped_indiv_code_raw or "")).upper()
    if "SEIT" in spedserv or indiv == "SEIT":
        return "seit"
    if "RS" in spedserv or "RELATED" in spedserv or "RELATED SERVICE" in spedserv or indiv == "RS":
        return "related_service"
    if indiv in ("CTR", "EIC") or (class_num and str(class_num).strip()):
        return "center_based"
    if class_num and str(class_num).strip():
        return "center_based"
    return "unknown"


def _normalize_profile_val(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    return s if s else None


class Command(BaseCommand):
    help = "Import students from Rockland Access DB (.accdb) into an academic session."

    def _profile_column_values(self, rows, cols, top_n=20):
        """Print top N distinct values (case-insensitive, trimmed) for candidate service-type columns."""
        candidate_names = [
            "SPEDSERV", "SPED SERV", "SERVICE TYPE", "PROGRAM", "CLASSNUM", "SPEDINDIV codes",
            "SPED INDIV", "SpedIndiv", "SPEDINDIV",
        ]
        col_lower_to_actual = {str(c).lower(): c for c in cols}
        for cand in candidate_names:
            actual = col_lower_to_actual.get(cand.lower())
            if actual is None:
                continue
            vals = []
            for row in rows:
                rec = dict(zip(cols, row))
                v = rec.get(actual)
                n = _normalize_profile_val(v)
                if n:
                    vals.append(n)
            counter = Counter(vals)
            self.stdout.write(f"\n--- {actual!r} (top {top_n}) ---")
            for val, count in counter.most_common(top_n):
                self.stdout.write(f"  {count:4d}  {val!r}")
            rs_seit_related = [v for v in counter if "seit" in v or "rs" in v or "related" in v]
            if rs_seit_related:
                self.stdout.write(self.style.SUCCESS(f"  -> RS/SEIT/Related-like values: {rs_seit_related}"))
        self.stdout.write("")

    def add_arguments(self, parser):
        parser.add_argument(
            "accdb_path",
            nargs="?",
            default=os.environ.get("ROCK_ACCESS_IMPORT_PATH", DEFAULT_ACCDB),
            help="Full path to Rockland YYYY-YYYY.accdb",
        )
        parser.add_argument(
            "--session",
            default="SY2025-26",
            help="Session name to import into (e.g. SY2025-26)",
        )
        parser.add_argument(
            "--site",
            default="rockland",
            help="Site slug or id (default: rockland). Session name is scoped per site.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing students in the session before importing",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing students (match by first name, last name, DOB) with roster fields: school_district, funding_code, class_num, aide_1to1, phone, email, notes. Use without --clear to refresh data from Access.",
        )
        parser.add_argument(
            "--list-columns",
            action="store_true",
            help="Only list column names in the student table/query and exit (useful to verify MDB column names).",
        )
        parser.add_argument(
            "--table",
            default="QRY_student Data Center Based",
            help="Access table or query name for student data (default: QRY_student Data Center Based). Use 'Student data' for legacy.",
        )
        parser.add_argument(
            "--no-skip-class-17",
            action="store_true",
            help="Do not skip rows with CLASSNUM 17 (by default they are ignored).",
        )
        parser.add_argument(
            "--list-tables",
            action="store_true",
            help="List all tables and queries in the .accdb and exit (to find SEIT/RS sources).",
        )
        parser.add_argument(
            "--profile-columns",
            action="store_true",
            help="Scan Access rows and print top 20 distinct values for SPEDSERV, CLASSNUM, etc. (no session needed).",
        )

    def handle(self, *args, **options):
        accdb_path = options["accdb_path"]
        session_name = options["session"]
        clear_first = options["clear"]
        update_existing = options.get("update_existing", False)

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

        if options.get("list_tables"):
            tables = []
            try:
                for row in cur.tables(tableType="TABLE"):
                    tables.append(row.table_name)
                for row in cur.tables(tableType="VIEW"):
                    tables.append(row.table_name)
            except Exception:
                try:
                    cur.execute("SELECT Name FROM MSysObjects WHERE Type IN (1, 5) AND Flags=0 ORDER BY Name")
                    tables = [r[0] for r in cur.fetchall()]
                except Exception:
                    tables = []
            self.stdout.write("Tables and queries in database:")
            for t in sorted(set(tables)):
                self.stdout.write(f"  {t!r}")
            keywords = ("seit", "rs", "related", "service", "center", "student")
            self.stdout.write("\nNames containing SEIT/RS/Related/Service/Center/Student:")
            for t in sorted(set(tables)):
                lower = t.lower()
                if any(k in lower for k in keywords):
                    self.stdout.write(self.style.SUCCESS(f"  -> {t!r}"))
            conn.close()
            return

        table_name = (options.get("table") or "QRY_student Data Center Based").strip()
        try:
            cur.execute(f"SELECT * FROM [{table_name}]")
        except pyodbc.Error as e:
            conn.close()
            self.stderr.write(self.style.ERROR(f"Could not read table [{table_name}]: {e}"))
            return
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        if options.get("list_columns"):
            self.stdout.write(f"Columns in [{table_name}]:")
            for c in cols:
                self.stdout.write(f"  {c!r}")
            conn.close()
            return

        if options.get("profile_columns"):
            self._profile_column_values(rows, cols)
            conn.close()
            return

        site_arg = (options.get("site") or "rockland").strip()
        try:
            site = Site.objects.get(slug=site_arg) if not str(site_arg).isdigit() else Site.objects.get(pk=int(site_arg))
        except Site.DoesNotExist:
            conn.close()
            self.stderr.write(self.style.ERROR(f"Site not found: {site_arg}"))
            return
        try:
            session = AcademicSession.objects.get(site=site, name=session_name)
        except AcademicSession.DoesNotExist:
            conn.close()
            self.stderr.write(self.style.ERROR(f"Session not found: {session_name} (site: {site.slug})"))
            return

        skip_class_17 = not options.get("no_skip_class_17", False)
        conn.close()
        self.stdout.write(f"Using table/query [{table_name}], skip CLASSNUM 17: {skip_class_17}")

        if clear_first:
            self.stdout.write(f"Clearing existing students in {session_name} ...")
            with connection.cursor() as c:
                c.execute("DELETE FROM students WHERE session_id = %s", [session.id])
            self.stdout.write(self.style.SUCCESS("Cleared."))

        session_start = session.start_date
        count_before = Student.objects.filter(session=session).count()
        self.stdout.write(f"Students in session before import: {count_before}")

        created = 0
        skipped = 0
        ambiguous_skipped = 0
        ambiguous_rows = []
        pending_updates = []
        seen = defaultdict(list)
        coverage = defaultdict(lambda: {"applied": 0, "ambiguous": 0, "no_match": 0, "skipped": 0})
        for row_idx, row in enumerate(rows):
            rec = dict(zip(cols, row))
            first = str_clean(rec.get("FIRSTNAME"), 100)
            last = str_clean(rec.get("LASTNAME"), 100)
            if not first and not last:
                skipped += 1
                continue
            if not first:
                first = " "
            if not last:
                last = " "

            dob = date_from_value(rec.get("DOB"))
            if dob is None:
                dob = session_start  # required field fallback

            start = date_from_value(rec.get("STARTDATE")) or session_start
            status = "active"
            discharge_raw = get_first(rec, ["DISCHARGE", "Discharge"])
            is_discharged = normalize_x_bool(discharge_raw)
            if is_discharged:
                status = "transferred"
            is_active = not is_discharged
            discharge_date = date_from_value(get_first(rec, ["DISCHARGE DATE", "Discharge Date"]))

            email_val = str_clean(get_first(rec, ["EMAIL", "Email", "PARENTS", "Parents"])) or None
            if email_val and len(email_val) > 254:
                email_val = email_val[:254]
            parent_email = email_val
            email = email_val
            mother_cell = str_clean(get_first(rec, ["MOTHER CELL", "Mother Cell", "MOTHERCELL"]), 30) or None
            father_cell = str_clean(get_first(rec, ["FATHER CELL", "Father Cell", "FATHERCELL"]), 30) or None
            phone = str_clean(get_first(rec, ["PHONE", "Phone", "HOME PHONE", "Home Phone"]), 30) or None
            if not phone and mother_cell:
                phone = mother_cell
            elif not phone and father_cell:
                phone = father_cell
            home_phone = phone
            address = str_clean(get_first(rec, ["ADDRESS", "Address"]), 500) or None
            notes = str_clean(get_first(rec, ["Notes", "NOTES"]), 2000) or None
            class_num = str_clean(get_first(rec, ["CLASSNUM", "ClassNum", "Class Num"]), 20) or None
            sped_indiv_code = str_clean(
                get_first(rec, ["SPEDINDIV codes", "SPED INDIV CODE", "SPEDINDIVCODE", "SPED INDIV", "SpedIndiv", "SPEDINDIV"]),
                50
            ) or None
            spedserv_raw = get_first(rec, ["SPEDSERV", "SPED SERV", "Program", "SERVICE TYPE", "Service Type"])
            row_service_type = derive_service_type(spedserv_raw, class_num, sped_indiv_code)
            # Ignore rows with CLASSNUM 17 (per requirement) unless --no-skip-class-17
            if skip_class_17 and class_num is not None and str(class_num).strip() == "17":
                coverage[row_service_type]["skipped"] += 1
                skipped += 1
                continue
            # Funding: FUNDING column first; SPEDINDIV (CTR=center-based, RS=related services, SEIT=itinerant) as fallback
            funding_code = str_clean(
                get_first(rec, ["FUNDING", "Funding", "SPEDINDIV", "SpedIndiv", "SPED INDIV"]),
                20
            ) or None
            # School district: SCHOOLDIST and common variants (MDB often uses SCHOOLDIST)
            school_district = str_clean(
                get_first(rec, [
                    "SCHOOLDIST", "Schooldist", "SchoolDist",
                    "School District", "SCHOOL DISTRICT", "SCHOOLDISTRICT", "DISTRICT",
                ]),
                100
            ) or None
            district = school_district
            aide_1to1 = str_clean(
                get_first(rec, ["1:1AIDE", "1:1 AIDE", "AIDE", "1:1Aide"]),
                100
            ) or None

            # Medical and vaccines (roster columns)
            medical_start_date = date_from_value(
                get_first(rec, ["MEDICALDATE", "MEDICAL START", "Medical Start", "MEDICALSTART", "MEDICAL START DATE", "Medical Start Date"])
            )
            medical_end_date = date_from_value(
                get_first(rec, ["MEDICAL DUE", "Medical Due", "MEDICALDUE", "MEDICAL END", "Medical End", "MEDICALEND", "MEDICAL END DATE", "Medical End Date"])
            )
            medical_due_date = date_from_value(
                get_first(rec, ["MEDICAL DUE", "Medical Due", "MEDICALDUE"])
            ) or medical_end_date
            vaccines_status = str_clean(
                get_first(rec, ["VACCINES", "Vaccines", "VACCINE STATUS", "Vaccine Status"]),
                100
            ) or None
            if not sped_indiv_code and funding_code:
                sped_indiv_code = funding_code
            discharge_date = date_from_value(get_first(rec, ["DISCHARGE DATE", "Discharge Date"]))
            discharge_notes = str_clean(get_first(rec, ["DISCHARGE NOTES", "Discharge Notes"]), 2000) or None

            service_type = derive_service_type(
                get_first(rec, ["SPEDSERV", "SPED SERV", "Program", "SERVICE TYPE", "Service Type"]),
                class_num,
                sped_indiv_code,
            )

            if update_existing and not clear_first:
                access_student_id = get_first(rec, ["Student ID", "StudentID", "STUDENT ID"])
                existing = None
                if access_student_id and str(access_student_id).strip():
                    try:
                        sid = int(access_student_id)
                        existing = Student.objects.filter(session=session, pk=sid).first()
                    except (ValueError, TypeError):
                        pass
                if existing is None:
                    matches = Student.objects.filter(
                        session=session,
                        first_name=first,
                        last_name=last,
                        date_of_birth=dob,
                    )
                    if matches.count() == 0:
                        coverage[row_service_type]["no_match"] += 1
                        continue
                    if matches.count() > 1:
                        narrowed = _narrow_by_contact(matches, phone, email, address)
                        if narrowed is not None:
                            existing = narrowed
                        else:
                            ambiguous_skipped += 1
                            coverage[row_service_type]["ambiguous"] += 1
                            dob_str = dob.isoformat() if hasattr(dob, "isoformat") else str(dob)
                            for m in matches:
                                ambiguous_rows.append((
                                    row_idx, first, last, dob_str,
                                    m.id, m.first_name, m.last_name,
                                    m.date_of_birth.isoformat() if m.date_of_birth else "",
                                ))
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Ambiguous: row {row_idx} matches {matches.count()} students in session (first={first!r}, last={last!r}, dob={dob}). Skipped."
                                )
                            )
                            continue
                    if existing is None:
                        existing = matches.first()
                if existing:
                    seen[existing.id].append((row_idx, first, last, dob))
                    data = {
                        "school_district": school_district, "district": district, "funding_code": funding_code,
                        "class_num": class_num, "aide_1to1": aide_1to1, "parent_phone": phone, "home_phone": home_phone,
                        "parent_email": parent_email, "email": email, "mother_cell": mother_cell, "father_cell": father_cell,
                        "address": address, "notes": notes, "status": status, "is_active": is_active,
                        "enrollment_date": start, "medical_start_date": medical_start_date, "medical_end_date": medical_end_date,
                        "medical_due_date": medical_due_date, "vaccines_status": vaccines_status,
                        "sped_indiv_code": sped_indiv_code, "discharge_date": discharge_date, "discharge_notes": discharge_notes,
                        "service_type": service_type,
                    }
                    pending_updates.append((existing.id, row_idx, rec, data))
                    coverage[service_type]["applied"] += 1
                continue

            Student.objects.create(
                session=session,
                first_name=first,
                last_name=last,
                date_of_birth=dob,
                enrollment_date=start,
                status=status,
                is_active=is_active,
                service_type=service_type,
                class_num=class_num,
                funding_code=funding_code,
                school_district=school_district,
                district=district,
                aide_1to1=aide_1to1,
                parent_email=parent_email,
                email=email,
                parent_phone=phone,
                home_phone=home_phone,
                mother_cell=mother_cell,
                father_cell=father_cell,
                address=address,
                notes=notes,
                medical_start_date=medical_start_date,
                medical_end_date=medical_end_date,
                medical_due_date=medical_due_date,
                vaccines_status=vaccines_status,
                sped_indiv_code=sped_indiv_code,
                discharge_date=discharge_date,
                discharge_notes=discharge_notes,
            )
            coverage[service_type]["applied"] += 1
            created += 1

        updates_by_student = defaultdict(list)
        for student_id, row_idx, rec, data in pending_updates:
            updates_by_student[student_id].append((row_idx, rec, data))

        for student_id, candidates in updates_by_student.items():
            if len(candidates) == 1:
                row_idx, rec, data = candidates[0]
                student = Student.objects.get(pk=student_id)
                for k, v in data.items():
                    setattr(student, k, v)
                student.save()
                created += 1
            else:
                row_idx, rec, data = _pick_best_duplicate_row(candidates, session_start)
                student = Student.objects.get(pk=student_id)
                for k, v in data.items():
                    setattr(student, k, v)
                student.save()
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Duplicate resolution: student_id={student_id} -> chose Access row {row_idx} (deterministic rule).")
                )

        count_after = Student.objects.filter(session=session).count()
        self.stdout.write(f"Students in session after import: {count_after}")

        if ambiguous_rows:
            amb_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "import_ambiguous_matches.csv"))
            try:
                with open(amb_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow([
                        "access_row_index", "access_first", "access_last", "access_dob",
                        "candidate_id", "candidate_first", "candidate_last", "candidate_dob",
                    ])
                    for r in ambiguous_rows:
                        w.writerow(r)
                self.stdout.write(f"Wrote ambiguous matches (needs manual resolution): {amb_path}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Could not write ambiguous report: {e}"))

        duplicate_matches = {sid: indices for sid, indices in seen.items() if len(indices) > 1}
        if duplicate_matches:
            self.stdout.write(
                self.style.WARNING(
                    f"Duplicate matches: {len(duplicate_matches)} student(s) matched by multiple Access rows."
                )
            )
            report_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "import_duplicate_matches.csv")
            report_path = os.path.normpath(os.path.abspath(report_path))
            try:
                with open(report_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["student_id", "row_index", "first_name", "last_name", "dob"])
                    for sid, indices in sorted(duplicate_matches.items()):
                        for row_idx, first, last, dob in indices:
                            w.writerow([sid, row_idx, first, last, dob])
                self.stdout.write(f"Wrote duplicate report: {report_path}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Could not write duplicate report: {e}"))

        type_label = {"center_based": "CTR", "related_service": "RS", "seit": "SEIT", "unknown": "Unknown"}
        total_rows = sum(sum(c.values()) for c in coverage.values())
        if total_rows:
            self.stdout.write("\n--- Coverage report (Access rows by inferred type) ---")
            self.stdout.write(f"Total Access rows (with name): {total_rows}")
            for st in ("center_based", "related_service", "seit", "unknown"):
                c = coverage[st]
                applied = c["applied"]
                ambiguous = c["ambiguous"]
                no_match = c["no_match"]
                skipped = c["skipped"]
                n = applied + ambiguous + no_match + skipped
                if n == 0:
                    continue
                label = type_label.get(st, st)
                self.stdout.write(
                    f"  {label}: inferred={n} -> applied={applied}, ambiguous={ambiguous}, no_match={no_match}, skipped={skipped}"
                )
            self.stdout.write("")

        if update_existing and not clear_first and count_after != count_before:
            self.stdout.write(
                self.style.WARNING(
                    f"Guardrail: expected no change in student count when using --update-existing (was {count_before}, now {count_after}). Check matching logic."
                )
            )
        elif not update_existing and count_after != count_before:
            self.stdout.write(f"Net change: {count_after - count_before:+d} students.")

        skip_msg = f" (skipped {skipped}, including CLASSNUM 17)" if skip_class_17 else f" (skipped {skipped})"
        if ambiguous_skipped:
            self.stdout.write(self.style.WARNING(f"Ambiguous matches skipped: {ambiguous_skipped}"))
        self.stdout.write(self.style.SUCCESS(f"Imported {created} students into {session_name}{skip_msg}"))
