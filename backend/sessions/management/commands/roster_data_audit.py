"""
Full data path audit: DB → Serializer → Roster.

1) Dump raw DB row for one student (by id or first in session).
2) Run SQL counts: how many students have non-null mother_cell, email, medical_*, etc.
3) Optionally compare with API response (run GET /api/sessions/students/<id>/ and diff).

Usage:
  python manage.py roster_data_audit --session SY2025-26
  python manage.py roster_data_audit --session SY2025-26 --student-id 123
  python manage.py roster_data_audit --session SY2025-26 --with-api  (requires running server)
  python manage.py roster_data_audit --session SY2025-26 --find-missing-by-name-dob path/to/roster.csv
"""
import csv
import json
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q

from sessions.management.commands.import_from_access import derive_service_type, parse_dob_robust
from sessions.models import AcademicSession, Student


def _serialize_value(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _student_db_row(student):
    """Return a JSON-serializable dict of one student's raw DB fields (roster columns)."""
    return {
        "id": student.id,
        "session_id": student.session_id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "date_of_birth": _serialize_value(student.date_of_birth),
        "address": student.address,
        "home_phone": student.home_phone,
        "mother_cell": student.mother_cell,
        "father_cell": student.father_cell,
        "parent_email": student.parent_email,
        "email": student.email,
        "parent_phone": student.parent_phone,
        "district": student.district,
        "school_district": student.school_district,
        "is_active": student.is_active,
        "discharge_date": _serialize_value(student.discharge_date),
        "discharge_notes": student.discharge_notes,
        "vaccines_status": student.vaccines_status,
        "vaccines_last_reviewed": _serialize_value(student.vaccines_last_reviewed),
        "vaccines_notes": student.vaccines_notes,
        "medical_start_date": _serialize_value(student.medical_start_date),
        "medical_end_date": _serialize_value(student.medical_end_date),
        "medical_due_date": _serialize_value(student.medical_due_date),
        "sped_indiv_code": student.sped_indiv_code,
        "service_type": student.service_type,
        "class_num": student.class_num,
        "funding_code": student.funding_code,
        "notes": (student.notes[:200] + "…") if student.notes and len(student.notes) > 200 else student.notes,
    }


class Command(BaseCommand):
    help = "Audit roster data path: dump one student from DB, run field counts, optional API comparison."

    def add_arguments(self, parser):
        parser.add_argument("--session", default="SY2025-26", help="Session name (e.g. SY2025-26)")
        parser.add_argument("--student-id", type=int, default=None, help="Student PK; if omitted use first student in session")
        parser.add_argument("--site", default="rockland", help="Site slug when resolving session by name")
        parser.add_argument("--with-api", action="store_true", help="Print reminder to compare with GET /api/sessions/students/<id>/")
        parser.add_argument("--breakdown", action="store_true", help="Print program/service type breakdown (Center-based, Related service, SEIT, Unknown)")
        parser.add_argument("--find-missing-by-name-dob", metavar="CSV_PATH", default=None, help="Compare CSV roster to DB by (last, first, dob); print students in CSV but not in DB and counts by inferred service type")

    def _find_missing_by_name_dob(self, session, csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"CSV not found: {csv_path}"))
            self.stdout.write(
                "Next recommended command: Export \"Student Data (All)\" from Access to a CSV, save at the path above, and re-run this command."
            )
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        def get_col(row, *keys):
            for k in keys:
                if k in row and row.get(k) is not None and str(row.get(k)).strip():
                    return (row.get(k) or "").strip()
                low = {str(h).lower(): h for h in row.keys()}
                for key in keys:
                    if key.lower() in low and row.get(low[key.lower()]) is not None:
                        v = (row.get(low[key.lower()]) or "").strip()
                        if v:
                            return v
            return ""

        def get_raw_dob(row):
            for col in ("DOB", "dob", "Date of Birth", "date_of_birth", "BIRTHDATE", "Birthdate", "birthdate"):
                if col in row and row.get(col) is not None:
                    return str(row[col]).strip()
            low = {str(h).lower(): h for h in row.keys()}
            for col in ("dob", "date of birth", "birthdate"):
                if col in low and row.get(low[col]) is not None:
                    return str(row[low[col]]).strip()
            return ""

        db_students = Student.objects.filter(session=session).values_list("last_name", "first_name", "date_of_birth")
        db_set = set()
        for last, first, dob in db_students:
            key = ((last or "").strip().lower(), (first or "").strip().lower(), dob.isoformat() if dob else "")
            db_set.add(key)
        missing = []
        rows_with_name = 0
        rows_dob_ok = 0
        rows_dob_missing_invalid = 0
        dob_missing_sample = []
        failed_raw_dob_examples = set()
        type_counts_all = {"center_based": 0, "related_service": 0, "seit": 0, "unknown": 0}
        type_counts_missing = {"center_based": 0, "related_service": 0, "seit": 0, "unknown": 0}
        for row_idx, row in enumerate(rows):
            last = get_col(row, "Last name", "LASTNAME", "last_name", "LastName")
            first = get_col(row, "First name", "FIRSTNAME", "first_name", "FirstName")
            raw_dob = get_raw_dob(row)
            dob_s = get_col(row, "DOB", "dob", "Date of Birth", "date_of_birth", "BIRTHDATE", "Birthdate", "birthdate")
            if not dob_s and raw_dob:
                dob_s = raw_dob
            dob = parse_dob_robust(dob_s or raw_dob)
            if not last and not first:
                continue
            rows_with_name += 1
            if dob is not None:
                rows_dob_ok += 1
            else:
                rows_dob_missing_invalid += 1
                if len(dob_missing_sample) < 25:
                    dob_missing_sample.append({"last": last, "first": first, "raw_dob": raw_dob, "row_index": row_idx})
            last_lower = (last or "").strip().lower()
            first_lower = (first or "").strip().lower()
            dob_iso = dob.isoformat() if dob else ""
            key = (last_lower, first_lower, dob_iso)
            # Match by (last, first, dob) only; CSV "Student ID" is external (e.g. 000920440), not DB pk
            matched = key in db_set
            spedserv = get_col(row, "SPEDSERV", "SPED SERV", "Service Type", "Program", "SERVICE TYPE")
            class_num = get_col(row, "CLASSNUM", "Class num", "class_num")
            sped_indiv = get_col(row, "SPEDINDIV codes", "SPED INDIV CODE", "sped_indiv_code", "SPEDINDIV codes")
            inferred = derive_service_type(spedserv or None, class_num or None, sped_indiv or None)
            type_counts_all[inferred] = type_counts_all.get(inferred, 0) + 1
            if not matched:
                missing.append({"last": last, "first": first, "dob": dob_iso, "inferred_service_type": inferred})
                type_counts_missing[inferred] = type_counts_missing.get(inferred, 0) + 1

        type_label = {"center_based": "CTR", "related_service": "RS", "seit": "SEIT", "unknown": "Unknown"}
        self.stdout.write(f"\n=== Find missing by name/DOB: {csv_path} vs session {session.name} ===\n")
        self.stdout.write(f"CSV rows with name present: {rows_with_name}")
        self.stdout.write(f"DOB parsed successfully: {rows_dob_ok}")
        self.stdout.write(f"DOB missing/invalid: {rows_dob_missing_invalid}")
        if failed_raw_dob_examples:
            self.stdout.write("\n--- Examples of raw DOB values that failed to parse ---")
            for ex in sorted(failed_raw_dob_examples)[:15]:
                self.stdout.write(f"  {ex!r}")
        if dob_missing_sample:
            self.stdout.write("\n--- First 25 rows where name present but DOB missing/invalid (last, first, raw_dob, row_index) ---")
            for s in dob_missing_sample:
                self.stdout.write(f"  {s['last']!r}, {s['first']!r}, raw_dob={s['raw_dob']!r}, row_index={s['row_index']}")
        self.stdout.write(f"\nCSV named rows count (for type breakdown): {sum(type_counts_all.values())}")
        self.stdout.write(f"DB session students count: {len(db_set)}")
        self.stdout.write(f"Missing rows count (in CSV but not in DB session): {len(missing)}")
        self.stdout.write("\n--- Inferred service type (all CSV rows with name): CTR / RS / SEIT / Unknown ---")
        for k, v in sorted(type_counts_all.items()):
            self.stdout.write(f"  {type_label.get(k, k)}: {v}")
        if missing:
            self.stdout.write("\n--- Missing breakdown by inferred type (CTR/RS/SEIT/Unknown) ---")
            for k, v in sorted(type_counts_missing.items()):
                self.stdout.write(f"  {type_label.get(k, k)}: {v}")
        if missing:
            self.stdout.write("\n--- Missing (in CSV, not in DB) ---")
            for m in missing[:100]:
                self.stdout.write(f"  {m['last']!r}, {m['first']!r} DOB={m['dob']!r} -> {m['inferred_service_type']}")
            if len(missing) > 100:
                self.stdout.write(f"  ... and {len(missing) - 100} more")
        missing_rs_seit = (type_counts_missing.get("related_service", 0) or 0) + (type_counts_missing.get("seit", 0) or 0)
        if missing and missing_rs_seit > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Next recommended command: python manage.py import_students_csv <same-csv-path> --session SY2025-26 --add-missing-to-session --dry-run"
                )
            )
        elif missing:
            self.stdout.write(
                self.style.SUCCESS(
                    "Next recommended command: python manage.py import_students_csv <same-csv-path> --session SY2025-26 --add-missing-to-session --dry-run (to add missing CTR/Unknown to session)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Next recommended command: python manage.py import_from_access \"<accdb-path>\" --table \"Student data\" --session SY2025-26 --update-existing (to refresh fields; check coverage report for ambiguous/no_match)"
                )
            )
        self.stdout.write("")

    def handle(self, *args, **options):
        session_name = options["session"]
        site_slug = options["site"]
        student_id = options.get("student_id")
        with_api = options.get("with_api", False)

        try:
            from sessions.models import Site
            site = Site.objects.get(slug=site_slug)
            session = AcademicSession.objects.get(site=site, name=session_name)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Session not found: {e}"))
            return

        csv_path = options.get("find_missing_by_name_dob")
        if csv_path:
            self._find_missing_by_name_dob(session, csv_path)
            return

        qs = Student.objects.filter(session=session)
        total = qs.count()
        self.stdout.write(f"\n=== Roster data audit - Session: {session.name} (id={session.id}) ===\n")
        self.stdout.write(f"Total students in session: {total}\n")

        if options.get("breakdown"):
            center = qs.filter(service_type="center_based").count()
            related = qs.filter(service_type="related_service").count()
            seit = qs.filter(service_type="seit").count()
            unknown = qs.exclude(service_type__in=("center_based", "related_service", "seit")).count()
            pct_unknown = (100 * unknown / total) if total else 0
            self.stdout.write("--- Service type breakdown ---")
            self.stdout.write(f"  Center-based: {center}")
            self.stdout.write(f"  Related service: {related}")
            self.stdout.write(f"  SEIT: {seit}")
            self.stdout.write(f"  Unknown: {unknown} ({pct_unknown:.1f}%)")
            self.stdout.write("")
            if related == 0 and seit == 0 and total > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Next recommended command: python manage.py roster_data_audit --session SY2025-26 --find-missing-by-name-dob <path-to-student_data_all.csv> (if RS/SEIT belong in this session, then run add-missing-to-session)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Next recommended command: (none) Breakdown has RS/SEIT; re-run import_from_access --update-existing to refresh fields if needed."
                    )
                )
            self.stdout.write("")

        # Step 3: SQL counts for roster columns
        def count_nonempty(queryset, field_name):
            return queryset.exclude(Q(**{f"{field_name}__isnull": True}) | Q(**{field_name: ""})).count()

        counts = {
            "mother_cell": count_nonempty(qs, "mother_cell"),
            "father_cell": count_nonempty(qs, "father_cell"),
            "email": count_nonempty(qs, "email"),
            "parent_email": count_nonempty(qs, "parent_email"),
            "home_phone": count_nonempty(qs, "home_phone"),
            "parent_phone": count_nonempty(qs, "parent_phone"),
            "address": count_nonempty(qs, "address"),
            "district": count_nonempty(qs, "district"),
            "school_district": count_nonempty(qs, "school_district"),
            "medical_start_date": qs.exclude(medical_start_date__isnull=True).count(),
            "medical_end_date": qs.exclude(medical_end_date__isnull=True).count(),
            "sped_indiv_code": count_nonempty(qs, "sped_indiv_code"),
            "vaccines_status": count_nonempty(qs, "vaccines_status"),
            "discharge_date": qs.exclude(discharge_date__isnull=True).count(),
            "is_active_true": qs.filter(is_active=True).count(),
            "is_active_false_discharged": qs.filter(is_active=False).count(),
        }
        self.stdout.write("--- Counts (non-null / non-empty) per field ---")
        for key, val in counts.items():
            pct = (100 * val / total) if total else 0
            self.stdout.write(f"  {key}: {val} / {total} ({pct:.0f}%)")
        self.stdout.write("")

        # Step 1: Pick one student and dump raw DB
        if student_id:
            student = qs.filter(pk=student_id).first()
            if not student:
                self.stderr.write(self.style.ERROR(f"Student id={student_id} not found in this session."))
                return
        else:
            student = qs.order_by("last_name", "first_name").first()
            if not student:
                self.stdout.write("No students in session; nothing to dump.")
                return
            student_id = student.id

        self.stdout.write(f"--- Raw DB row for student id={student_id} ({student.last_name}, {student.first_name}) ---")
        self.stdout.write(json.dumps(_student_db_row(student), indent=2))
        self.stdout.write("")

        # Step 2: Compare with API
        self.stdout.write("--- Compare with API ---")
        self.stdout.write(f"  GET /api/sessions/students/{student_id}/")
        self.stdout.write("  Compare the JSON response fields with the raw DB row above.")
        self.stdout.write("  If DB has data but API is blank -> serializer mapping is wrong.")
        self.stdout.write("  If DB is blank -> import/migration did not populate these columns.")
        if with_api:
            self.stdout.write(self.style.WARNING(
                "  Run the request in browser DevTools or curl and diff the response."
            ))
        self.stdout.write("")

        # Session scoping note
        self.stdout.write("--- Session scoping ---")
        self.stdout.write(f"  Roster and student detail use session_id={session.id}. Medical/SPED/contact are on Student; no separate tables.")
        if any(c == 0 or (total and c < total * 0.1) for c in [counts["mother_cell"], counts["email"], counts["medical_start_date"]]):
            self.stdout.write(self.style.WARNING(
                "  Counts above are near zero for key fields -> data was not imported. Re-run import_from_access (with full column mapping) or import_students_csv."
            ))
        else:
            self.stdout.write("  If counts above are low, re-run import_from_access or import_students_csv with full columns.")
        self.stdout.write("")
