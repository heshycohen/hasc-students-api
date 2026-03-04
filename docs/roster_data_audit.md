# Roster Data Path Audit

When roster columns are blank despite 145 students loading, trace data end-to-end.

## Operational checklist (RS/SEIT coverage)

**Status:** Implementation is complete. Current results are CTR-only because the required source files are not yet at the paths used. No code changes are needed; follow these steps locally.

**Quick reference (command sequence):**

| Step | Command |
|------|--------|
| Export CSV from Access | Save as `C:\Dev\Rock-Access\student data\SY 2025-2026\student_data_all.csv` (see below) |
| Truth check | `roster_data_audit --find-missing-by-name-dob "<csv>"` |
| Dry-run link/add | `import_students_csv "<csv>" --add-missing-to-session --dry-run` |
| Apply link/add | Same command without `--dry-run` |
| Refresh fields from Access | `import_from_access "<accdb>" --update-existing` |
| Final proof | `roster_data_audit --breakdown` |

1. **Confirm folder exists:** `C:\Dev\Rock-Access\student data\SY 2025-2026\`. Create it if missing.
2. **Export CSV from Access → save as `...\student_data_all.csv`:**  
   In Access (e.g. Rockland 2025-2026.accdb), open the query/report **"Student Data (All)"** (CTR + RS + SEIT). **External Data → Export → Text File** → CSV, delimited, include field names, UTF-8 if offered. Save as:  
   **`C:\Dev\Rock-Access\student data\SY 2025-2026\student_data_all.csv`**  
   Include at least: Last name, First name, DOB; SPEDINDIV codes (or column with ctr/rs/seit); contact/medical fields as needed.
3. **Truth check:**  
   `cd C:\Dev\Rock-Access\rock-access-web\backend`  
   `.\venv\Scripts\python.exe manage.py roster_data_audit --session SY2025-26 --find-missing-by-name-dob "C:\Dev\Rock-Access\student data\SY 2025-2026\student_data_all.csv"`  
   If missing rows exist (especially RS/SEIT), continue.
4. **Dry-run add missing:**  
   `.\venv\Scripts\python.exe manage.py import_students_csv "C:\Dev\Rock-Access\student data\SY 2025-2026\student_data_all.csv" --session SY2025-26 --add-missing-to-session --dry-run`  
   Open `backend\import_missing_to_session.csv` and sanity-check would_create counts and inferred types (RS/SEIT if expected).
5. **Apply add missing:**  
   `.\venv\Scripts\python.exe manage.py import_students_csv "C:\Dev\Rock-Access\student data\SY 2025-2026\student_data_all.csv" --session SY2025-26 --add-missing-to-session`
6. **Optional:** Ensure `C:\Dev\Rock-Access\student data\SY 2025-2026\Rockland 2025-2026.accdb` exists, then run:  
   `.\venv\Scripts\python.exe manage.py import_from_access "C:\Dev\Rock-Access\student data\SY 2025-2026\Rockland 2025-2026.accdb" --table "Student data" --session SY2025-26 --update-existing`  
   to enrich newly added students with full medical/contact fields.
7. **Final proof:**  
   `.\venv\Scripts\python.exe manage.py roster_data_audit --session SY2025-26 --breakdown`  
   Expected (if RS/SEIT belong in SY2025-26): Related service &gt; 0 and/or SEIT &gt; 0.

## Step 1 — Pick one known student with full data

Use an example from the old spreadsheet that has Mother cell, Email, Medical start/end, SPED code, Vaccines.

## Step 2 — Run the audit command

```bash
cd backend
python manage.py roster_data_audit --session SY2025-26
```

This will:

- Print **counts** of students with non-null `mother_cell`, `email`, `medical_start_date`, `medical_end_date`, `sped_indiv_code`, etc.
- Dump the **raw DB row** (JSON) for one student (first in session, or use `--student-id 123`).
- Remind you to compare with the API.

## Step 3 — Compare DB → API

1. Call **GET /api/sessions/students/<id>/** (same student id as in the dump).
2. Compare:
   - **Raw DB values** (from audit output) vs **API response values**.
   - If DB has data but API is blank → **serializer mapping** is wrong.
   - If DB is blank → **import/migration** did not populate these columns.

## Step 4 — Interpret counts

- If counts for `mother_cell`, `email`, `medical_start_date`, etc. are **near zero** → data was not imported into the new normalized columns. Re-run:
  - **import_from_access** with the extended column mapping (all roster fields), or
  - **import_students_csv** with a CSV that has the correct column headers.
- If counts are high but roster UI still shows blanks → check frontend (wrong field names) or serializer (wrong field names).

## Step 5 — Session scoping

- Roster and student detail use **session_id** (e.g. current session). Medical/SPED/contact data lives on **Student**; there are no separate `StudentMedical` or `StudentSpedProfile` tables.
- If your data was imported for a different session, switch the session in the UI or pass the correct `session` query param.

## Step 6 — If data exists in DB but not on roster

The roster uses **StudentSerializer**, which exposes flat fields from `Student` (no nested `medical` or `sped_profile`). If the API returns the values but the UI does not, check:

- **Frontend** `StudentRosterList.js`: column bindings use `row.mother_cell`, `row.email ?? row.parent_email`, `row.district_display ?? row.district ?? row.school_district`, etc.

## Step 7 — If data does NOT exist in DB

- **import_from_access** now maps: Mother cell, Father cell, Email, Address, Home phone, Medical start/end/due, Vaccines, SPED INDIV code, Discharge date/notes, District. Re-run:

  ```bash
  python manage.py import_from_access "C:\path\to\Rockland 2025-2026.accdb" --session SY2025-26 --update-existing
  ```

  Use `--update-existing` to fill in roster columns for existing students without clearing the session.

- Or use **import_students_csv** with a CSV that has headers matching `COLUMN_MAP` in `import_students_csv.py` (e.g. "Mother cell", "Medical start date", "SPED INDIV Code").

## Listing Access tables (find SEIT/RS source)

To see all tables/queries in the .accdb and spot ones that might contain SEIT or Related Service students:

```bash
python manage.py import_from_access "C:\path\to\Rockland 2025-2026.accdb" --list-tables
```

Tables whose names contain SEIT, RS, Related, Service, Center, or Student are highlighted. If there is no separate SEIT/RS table, those students may be in the same "Student data" table and distinguished by a column (e.g. SPEDSERV); the import maps SPEDSERV (and similar) to `service_type` (related_service when SEIT/RS/Related appears).

## Discovering Access column names

If the Access .accdb uses different column names, list them:

```bash
python manage.py import_from_access "C:\path\to\Rockland 2025-2026.accdb" --list-columns
```

Then add any missing names to the `get_first(rec, ["COL1", "COL2", ...])` lists in `import_from_access.py`.

## Find missing by name/DOB (CSV comparison)

To see whether RS/SEIT students are missing from the session DB (vs. just not matched by the Access import), run:

```bash
python manage.py roster_data_audit --session SY2025-26 --find-missing-by-name-dob path/to/student_data_all.csv
```

The command prints:

- **CSV named rows count** — rows in the CSV with at least last or first name
- **DB session students count** — students in the session
- **Missing rows count** — in CSV but not in DB (by last, first, DOB)
- **Missing breakdown by inferred type** — CTR / RS / SEIT / Unknown for those missing rows

**Interpretation:** If missing rows include RS/SEIT, those students are not in the session DB; use `import_students_csv --add-missing-to-session` to add them. If missing is near zero but RS/SEIT is still 0 in the DB breakdown, the issue is match/dedupe (see coverage report and tie-breakers).

## Add missing to session (safe add)

When the CSV comparison shows RS/SEIT students missing from the session, add them in a controlled way:

```bash
python manage.py import_students_csv path/to/student_data_all.csv --session SY2025-26 --add-missing-to-session --dry-run
python manage.py import_students_csv path/to/student_data_all.csv --session SY2025-26 --add-missing-to-session
```

- Only students with (last, first, dob) in the CSV and **no** matching student in the session are added.
- If a student with the same name/DOB exists in **another** session, they are **not** duplicated; the command logs `possible_existing_elsewhere` and writes `import_missing_to_session.csv` with action, identifiers, inferred service type, and row index.

## Coverage report (after Access import)

After `import_from_access`, the command prints a **coverage report** by inferred type (CTR / RS / SEIT / Unknown):

- **Total Access rows** (with name)
- Per type: **inferred** count, **applied** (matched and updated), **ambiguous** (skipped), **no_match** (not in session), **skipped** (e.g. CLASSNUM 17)

Use this to see whether RS/SEIT rows are failing mainly on matching/ambiguity vs. not being in the source.
