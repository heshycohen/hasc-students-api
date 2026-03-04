"""
Import students from a CSV file (e.g. exported from Access "Student Data").
Deduplicates by (last_name, first_name, dob). Summary: inserted / updated / skipped.

Usage:
  python manage.py import_students_csv path/to/students.csv --session SY2025-26
  python manage.py import_students_csv students.csv --session SY2025-26 --add-missing-to-session --dry-run
"""
import csv
import os
from datetime import datetime, date

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from sessions.management.commands.import_from_access import derive_service_type, normalize_x_bool, parse_dob_robust
from sessions.models import AcademicSession, Student, Site


def parse_date_or_none(val):
    """
    Returns datetime.date or None. Use for all Student DateField assignments.
    Accepts: YYYY-MM-DD, M/D/YYYY [optionally with ' 0:00:00' time suffix].
    Treats blank/None and flag values like 'x'/'X'/'yes' as None.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.lower() in {"x", "yes", "y", "true", "1"}:
        return None
    if " " in s:
        first = s.split(" ", 1)[0].strip()
        if "/" in first or "-" in first:
            s = first
    return parse_dob_robust(s)


def date_from_str(s):
    """Parse date from string; uses parse_date_or_none for consistency."""
    return parse_date_or_none(s)


def str_clean(s, max_len=None):
    if s is None:
        return ''
    out = str(s).strip()
    if max_len and len(out) > max_len:
        out = out[:max_len]
    return out


def norm_header(h):
    """Normalize header for matching: strip, strip quotes, lowercase, collapse whitespace, treat _ as space."""
    if h is None:
        return ""
    s = str(h).strip().strip('"').lower().replace("_", " ")
    return " ".join(s.split())


# Map common Access/CSV header names (case-insensitive) to our Student field names
COLUMN_MAP = {
    'last name': 'last_name',
    'lastname': 'last_name',
    'first name': 'first_name',
    'firstname': 'first_name',
    'dob': 'date_of_birth',
    'date of birth': 'date_of_birth',
    'dateofbirth': 'date_of_birth',
    'birthdate': 'date_of_birth',
    'birth date': 'date_of_birth',
    'address': 'address',
    'home phone': 'home_phone',
    'homephone': 'home_phone',
    'mother cell': 'mother_cell',
    'mothercell': 'mother_cell',
    'father cell': 'father_cell',
    'fathercell': 'father_cell',
    'email': 'email',
    'parent email': 'parent_email',
    # DISCHARGE is a boolean flag (x/yes = discharged); use only for is_active, never for discharge_date
    'discharge date': 'discharge_date',
    'district': 'district',
    'school district': 'school_district',
    'schooldist': 'school_district',
    'vaccines': 'vaccines_status',
    'vaccines status': 'vaccines_status',
    'medical start date': 'medical_start_date',
    'medical start': 'medical_start_date',
    'medical end date': 'medical_end_date',
    'medical end': 'medical_end_date',
    'medical due': 'medical_due_date',
    'sped indiv code': 'sped_indiv_code',
    'spedindivcode': 'sped_indiv_code',
    'classnum': 'class_num',
    'class num': 'class_num',
    'clasnum': 'class_num',
    'funding code': 'funding_code',
    'funding': 'funding_code',
    'phone': 'parent_phone',
    'parent phone': 'parent_phone',
    'notes': 'notes',
    '1:1 aide': 'aide_1to1',
    'aide_1to1': 'aide_1to1',
    'spedserv': 'spedserv_raw',
    'sped serv': 'spedserv_raw',
    'service type': 'spedserv_raw',
    'program': 'spedserv_raw',
}


class Command(BaseCommand):
    help = 'Import students from CSV (e.g. exported from Access Student Data). Deduplicate by last_name, first_name, dob.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to CSV file')
        parser.add_argument('--session', default='SY2025-26', help='Session name (e.g. SY2025-26)')
        parser.add_argument('--site', default='rockland', help='Site slug')
        parser.add_argument('--clear', action='store_true', help='Delete existing students in session before import')
        parser.add_argument('--update-existing', action='store_true', help='Only update existing students (match by last, first, dob); do not create new ones. Use for CSV export from Access "Student Data (All)".')
        parser.add_argument('--add-missing-to-session', action='store_true', help='Add rows that are in CSV but not in session (no duplicate across sessions). Writes import_missing_to_session.csv. Use with --dry-run first.')
        parser.add_argument('--link-existing-elsewhere', action='store_true', help='When used with --add-missing-to-session: create a new Student in this session for rows that match a student in another session (attach to session instead of skipping as possible_existing_elsewhere).')
        parser.add_argument('--dry-run', action='store_true', help='Only report what would be done')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        session_name = options['session']
        site_slug = options['site']
        clear = options['clear']
        update_existing = options.get('update_existing', False)
        add_missing_to_session = options.get('add_missing_to_session', False)
        link_existing_elsewhere = options.get('link_existing_elsewhere', False)
        dry_run = options['dry_run']

        site = Site.objects.filter(slug=site_slug).first()
        if not site:
            self.stderr.write(self.style.ERROR(f'Site "{site_slug}" not found.'))
            return
        session = AcademicSession.objects.filter(site=site, name=session_name).first()
        if not session:
            self.stderr.write(self.style.ERROR(f'Session "{session_name}" not found for site {site_slug}.'))
            return

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {csv_path}'))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        if not rows:
            self.stdout.write('CSV is empty.')
            return

        raw_headers = list(rows[0].keys())
        norm_to_orig = {norm_header(h): h for h in raw_headers}

        def get_col(row, *names):
            for name in names:
                key = norm_header(name)
                if key in norm_to_orig:
                    orig = norm_to_orig[key]
                    val = row.get(orig)
                    if val is not None and str(val).strip() != "":
                        return str(val).strip()
            return None

        header_map = {}
        for orig in raw_headers:
            n = norm_header(orig)
            header_map[orig] = COLUMN_MAP.get(n) or (n.replace(" ", "_") if n else None)

        self.stdout.write("Detected fieldnames (first 10): %s" % (raw_headers[:10],))
        resolved_last = "?"
        for alias in ("lastname", "last name", "last"):
            if norm_header(alias) in norm_to_orig:
                resolved_last = norm_to_orig[norm_header(alias)]
                break
        resolved_first = "?"
        for alias in ("firstname", "first name", "first"):
            if norm_header(alias) in norm_to_orig:
                resolved_first = norm_to_orig[norm_header(alias)]
                break
        resolved_dob = "?"
        for alias in ("dob", "date of birth", "dateofbirth", "birthdate"):
            if norm_header(alias) in norm_to_orig:
                resolved_dob = norm_to_orig[norm_header(alias)]
                break
        resolved_student_id = "?"
        for alias in ("student id", "studentid", "student_id"):
            if norm_header(alias) in norm_to_orig:
                resolved_student_id = norm_to_orig[norm_header(alias)]
                break
        self.stdout.write("Resolved: last=%s, first=%s, dob=%s, student_id=%s" % (resolved_last, resolved_first, resolved_dob, resolved_student_id))

        inserted = updated = skipped = 0
        skipped_missing_dob = 0
        skipped_bad_dob = 0
        skipped_missing_fields = 0
        skipped_no_match = 0
        missing_report = []

        if clear and not dry_run:
            with transaction.atomic():
                n = Student.objects.filter(session=session).delete()[0]
            self.stdout.write(f'Cleared {n} existing students.')

        for row_idx, row in enumerate(rows):
            raw_last = get_col(row, "lastname", "last name", "last")
            raw_first = get_col(row, "firstname", "first name", "first")
            last_name = str_clean(raw_last or "", 100)
            first_name = str_clean(raw_first or "", 100)
            if not last_name and not first_name:
                skipped += 1
                if add_missing_to_session:
                    missing_report.append({
                        "action": "skipped_missing_fields",
                        "last_name": "",
                        "first_name": "",
                        "raw_dob": "",
                        "dob": "",
                        "inferred_service_type": "unknown",
                        "row_index": row_idx,
                        "student_id": "",
                        "student_id_raw": "",
                    })
                    skipped_missing_fields += 1
                continue

            raw_dob = get_col(row, "dob", "date of birth", "dateofbirth", "birthdate", "birth date")
            dob = parse_dob_robust(raw_dob) if raw_dob else None
            student_id_raw = get_col(row, "student id", "studentid", "student_id") or ""
            # Match by (last, first, dob) only; CSV "Student ID" is external (e.g. 000920440), not DB pk
            existing = Student.objects.filter(
                session=session,
                last_name__iexact=last_name,
                first_name__iexact=first_name,
            )
            if dob:
                existing = existing.filter(date_of_birth=dob)
            else:
                existing = existing.filter(date_of_birth__isnull=True)
            existing = existing.first()

            spedserv_raw = get_col(row, "sped serv", "service type", "program", "spedserv") or None
            class_num = get_col(row, "class num", "classnum", "clasnum") or None
            sped_indiv = get_col(row, "spedindiv codes", "sped indiv code", "sped_indiv_code") or None
            service_type = derive_service_type(spedserv_raw, class_num, sped_indiv)
            discharge_raw = get_col(row, "discharge") or None
            is_active = not normalize_x_bool(discharge_raw)

            data = {'session': session, 'last_name': last_name, 'first_name': first_name, 'date_of_birth': dob or date(2000, 1, 1), 'service_type': service_type, 'is_active': is_active}
            for orig, field in header_map.items():
                if field in ('spedserv_raw',):
                    continue
                if not field or field in ('session', 'last_name', 'first_name', 'date_of_birth'):
                    continue
                if not hasattr(Student, field):
                    continue
                val = row.get(orig)
                if val is None or (isinstance(val, str) and not val.strip()):
                    continue
                val = str_clean(val)
                if field in ('date_of_birth', 'enrollment_date', 'discharge_date', 'medical_start_date', 'medical_end_date', 'medical_due_date', 'vaccines_last_reviewed'):
                    val = parse_date_or_none(val)
                data[field] = val

            if update_existing and not add_missing_to_session and not existing:
                skipped += 1
                skipped_no_match += 1
                continue

            if not existing and add_missing_to_session:
                # Safety: never create a student if DOB is missing (unless Student ID matched existing—we don't use that currently).
                if not dob:
                    has_raw_dob = bool(raw_dob and str(raw_dob).strip())
                    action = "skipped_bad_dob" if has_raw_dob else "skipped_missing_identity"
                    missing_report.append({
                        "action": action,
                        "last_name": last_name,
                        "first_name": first_name,
                        "raw_dob": (raw_dob or ""),
                        "dob": "",
                        "inferred_service_type": service_type,
                        "row_index": row_idx,
                        "student_id": "",
                        "student_id_raw": student_id_raw,
                    })
                    if has_raw_dob:
                        skipped_bad_dob += 1
                    else:
                        skipped_missing_dob += 1
                    skipped += 1
                    continue
                elsewhere = Student.objects.filter(
                    last_name__iexact=last_name,
                    first_name__iexact=first_name,
                )
                if dob:
                    elsewhere = elsewhere.filter(date_of_birth=dob)
                else:
                    elsewhere = elsewhere.filter(date_of_birth__isnull=True)
                elsewhere = elsewhere.exclude(session=session)
                if elsewhere.exists():
                    if link_existing_elsewhere:
                        if dry_run:
                            missing_report.append({
                                "action": "would_link_elsewhere",
                                "last_name": last_name,
                                "first_name": first_name,
                                "raw_dob": (raw_dob or ""),
                                "dob": (dob.isoformat() if dob else ""),
                                "inferred_service_type": service_type,
                                "row_index": row_idx,
                                "student_id": "",
                                "student_id_raw": student_id_raw,
                            })
                            inserted += 1
                        else:
                            try:
                                new_student = Student.objects.create(**data)
                            except ValidationError as e:
                                self.stderr.write(
                                    self.style.ERROR(
                                        f"ValidationError row_index={row_idx} name={last_name},{first_name} errors={getattr(e, 'message_dict', getattr(e, 'messages', str(e)))}"
                                    )
                                )
                                raise
                            missing_report.append({
                                "action": "linked_elsewhere",
                                "last_name": last_name,
                                "first_name": first_name,
                                "raw_dob": (raw_dob or ""),
                                "dob": (dob.isoformat() if dob else ""),
                                "inferred_service_type": service_type,
                                "row_index": row_idx,
                                "student_id": str(new_student.id),
                                "student_id_raw": student_id_raw,
                            })
                            inserted += 1
                    else:
                        missing_report.append({
                            "action": "possible_existing_elsewhere",
                            "last_name": last_name,
                            "first_name": first_name,
                            "raw_dob": (raw_dob or ""),
                            "dob": (dob.isoformat() if dob else ""),
                            "inferred_service_type": service_type,
                            "row_index": row_idx,
                            "student_id": "",
                            "student_id_raw": student_id_raw,
                        })
                        skipped += 1
                    continue
                if dry_run:
                    missing_report.append({
                        "action": "would_create",
                        "last_name": last_name,
                        "first_name": first_name,
                        "raw_dob": (raw_dob or ""),
                        "dob": (dob.isoformat() if dob else ""),
                        "inferred_service_type": service_type,
                        "row_index": row_idx,
                        "student_id": "",
                        "student_id_raw": student_id_raw,
                    })
                    inserted += 1
                    continue
                try:
                    new_student = Student.objects.create(**data)
                except ValidationError as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"ValidationError row_index={row_idx} name={last_name},{first_name} errors={getattr(e, 'message_dict', getattr(e, 'messages', str(e)))}"
                        )
                    )
                    raise
                missing_report.append({
                    "action": "created",
                    "last_name": last_name,
                    "first_name": first_name,
                    "raw_dob": (raw_dob or ""),
                    "dob": (dob.isoformat() if dob else ""),
                    "inferred_service_type": service_type,
                    "row_index": row_idx,
                    "student_id": str(new_student.id),
                    "student_id_raw": student_id_raw,
                })
                inserted += 1
                continue

            if update_existing and not existing:
                skipped += 1
                skipped_no_match += 1
                continue

            if dry_run:
                if existing:
                    updated += 1
                else:
                    inserted += 1
                continue

            if existing:
                for k, v in data.items():
                    if k != 'session' and hasattr(existing, k):
                        setattr(existing, k, v)
                bad = []
                for f in existing._meta.fields:
                    if f.get_internal_type() == "DateField":
                        v = getattr(existing, f.name, None)
                        if isinstance(v, str):
                            bad.append((f.name, v))
                if bad:
                    self.stderr.write(
                        self.style.ERROR(
                            f"BAD DATE row_index={row_idx} student_id={existing.id} name={existing.last_name},{existing.first_name} bad={bad}"
                        )
                    )
                try:
                    existing.save()
                except ValidationError as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"ValidationError row_index={row_idx} student_id={existing.id} name={existing.last_name},{existing.first_name} errors={getattr(e, 'message_dict', getattr(e, 'messages', str(e)))}"
                        )
                    )
                    raise
                updated += 1
            else:
                if not data.get('date_of_birth'):
                    data['date_of_birth'] = date(2000, 1, 1)
                if not data.get('enrollment_date'):
                    data['enrollment_date'] = date.today()
                try:
                    Student.objects.create(**data)
                except ValidationError as e:
                    self.stderr.write(
                        self.style.ERROR(
                            f"ValidationError row_index={row_idx} name={last_name},{first_name} errors={getattr(e, 'message_dict', getattr(e, 'messages', str(e)))}"
                        )
                    )
                    raise
                inserted += 1

        if add_missing_to_session:
            report_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "import_missing_to_session.csv"))
            fieldnames = ["action", "last_name", "first_name", "raw_dob", "dob", "inferred_service_type", "row_index", "student_id", "student_id_raw"]
            with open(report_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(missing_report)
            self.stdout.write(self.style.SUCCESS(f"Wrote {len(missing_report)} rows to {report_path}"))
            n_created = sum(1 for r in missing_report if r.get("action") == "created")
            n_would = sum(1 for r in missing_report if r.get("action") == "would_create")
            n_elsewhere = sum(1 for r in missing_report if r.get("action") == "possible_existing_elsewhere")
            n_skipped_identity = sum(1 for r in missing_report if r.get("action") == "skipped_missing_identity")
            n_skipped_bad_dob = sum(1 for r in missing_report if r.get("action") == "skipped_bad_dob")
            n_skipped_fields = sum(1 for r in missing_report if r.get("action") == "skipped_missing_fields")
            n_linked = sum(1 for r in missing_report if r.get("action") in ("linked_elsewhere", "would_link_elsewhere"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Add-missing breakdown: would_create={n_would}, created={n_created}, linked_elsewhere={n_linked}, updated={updated}, "
                    f"possible_existing_elsewhere={n_elsewhere}, skipped_missing_identity={n_skipped_identity}, "
                    f"skipped_bad_dob={n_skipped_bad_dob}, skipped_missing_fields={n_skipped_fields}, skipped_no_match={skipped_no_match}"
                )
            )
            if n_created or n_would or n_linked:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Next recommended command: python manage.py import_from_access \"<accdb-path>\" --table \"Student data\" --session SY2025-26 --update-existing (refresh fields for newly added students)"
                    )
                )
            elif n_elsewhere and not (n_created or n_would or n_linked) and not n_skipped_identity and not n_skipped_bad_dob:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Next recommended command: Review import_missing_to_session.csv; students exist in another session. No add needed, or link manually."
                    )
                )
            if n_skipped_identity or n_skipped_bad_dob:
                self.stdout.write(
                    self.style.WARNING(
                        f"Next: Fix DOB so {n_skipped_identity + n_skipped_bad_dob} rows parse (missing identity or bad format); then re-run add-missing."
                    )
                )

        self.stdout.write(self.style.SUCCESS(
            f'Summary: inserted={inserted}, updated={updated}, skipped={skipped}' + (' (dry run)' if dry_run else '')
        ))
        if add_missing_to_session:
            n_created = sum(1 for r in missing_report if r.get("action") == "created")
            n_would = sum(1 for r in missing_report if r.get("action") == "would_create")
            n_elsewhere = sum(1 for r in missing_report if r.get("action") == "possible_existing_elsewhere")
            n_skipped_identity = sum(1 for r in missing_report if r.get("action") == "skipped_missing_identity")
            n_skipped_bad_dob = sum(1 for r in missing_report if r.get("action") == "skipped_bad_dob")
            n_skipped_fields = sum(1 for r in missing_report if r.get("action") == "skipped_missing_fields")
            n_linked = sum(1 for r in missing_report if r.get("action") in ("linked_elsewhere", "would_link_elsewhere"))
            self.stdout.write(self.style.SUCCESS(
                f"Add-missing counts: would_create={n_would}, created={n_created}, linked_elsewhere={n_linked}, updated={updated}, "
                f"possible_existing_elsewhere={n_elsewhere}, skipped_missing_identity={n_skipped_identity}, "
                f"skipped_bad_dob={n_skipped_bad_dob}, skipped_missing_fields={n_skipped_fields}, skipped_no_match={skipped_no_match}"
            ))
