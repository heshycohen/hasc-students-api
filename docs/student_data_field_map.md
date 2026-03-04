# Student Data Field Map

**Purpose:** Map spreadsheet/source column names to DB model fields, API response keys, and UI groups. Used to ensure "select a child → show everything" and to identify gaps.

**Source:** `sessions.models.Student` (single core table); related: `sessions.models.Incident` (student.incidents). No separate Medical/SPED/Services/Meetings/Reports tables in current schema.

---

## Column → DB field → API field → UI group

| Spreadsheet column | DB model.field | API field (GET /api/sessions/students/:id/) | UI group | Status |
|--------------------|----------------|---------------------------------------------|----------|--------|
| LASTNAME | Student.last_name | last_name | Demographics / Contact | present |
| FIRSTNAME | Student.first_name | first_name | Demographics / Contact | present |
| DOB | Student.date_of_birth | date_of_birth | Demographics / Contact | present |
| Student ID | — | id (numeric) | Demographics / Contact | present (id only; no human student_id) |
| PHONE | Student.home_phone, Student.parent_phone | home_phone, parent_phone | Demographics / Contact | present |
| MOTHER CELL | Student.mother_cell | mother_cell | Demographics / Contact | present |
| FATHER CELL | Student.father_cell | father_cell | Demographics / Contact | present |
| EMAIL | Student.email, Student.parent_email | email, parent_email | Demographics / Contact | present |
| DISCHARGE | Student.discharge_date, Student.discharge_notes | discharge_date, discharge_notes | Demographics / Contact | present |
| SCHOOLDIST | Student.school_district, Student.district | school_district, district, district_display | Demographics / Contact | present |
| SPECALERT | — | — | Demographics / Contact | **missing in DB** |
| ABA | — | — | Demographics / Contact | **missing in DB** |
| ADDRESS | Student.address | address | Demographics / Contact | present |
| VACCINES | Student.vaccines_status, vaccines_notes | vaccines_status, vaccines_notes, vaccines_last_reviewed | Medical | present |
| MEDICALDATE | Student.medical_start_date, medical_end_date | medical_start_date, medical_end_date | Medical | present |
| MEDICAL DUE | Student.medical_due_date, medical_end_date | medical_due_date, medical_end_date | Medical | present |
| Nurses Medical Notes | Student.medical_info_encrypted (admin), notes | medical_info (admin), notes | Medical | present (notes); medical_info encrypted |
| SPEDINDIV codes | Student.sped_indiv_code | sped_indiv_code | SPED / Program / IFSP-IEP | present |
| SPEDSERV | — | — | SPED / Program / IFSP-IEP | **missing in DB** |
| IFSPIEP | — | — | SPED / Program / IFSP-IEP | **missing in DB** |
| IFSPIEPST | — | — | SPED / Program / IFSP-IEP | **missing in DB** |
| IFSPIEPEND | — | — | SPED / Program / IFSP-IEP | **missing in DB** |
| DATERECVD | — | — | SPED / Program / IFSP-IEP | **missing in DB** |
| Speech (SPEECHSERV, SPEECHTHER, STDATE, STDUE) | — | services[] (placeholder) | Services | **missing in DB** |
| OT (OTSERVICE, OTTHERAPIS, OTDATE, OT DUE) | — | services[] | Services | **missing in DB** |
| PT (PTSERVICE, PTTHERAPIST, PTDATE, PT DUE) | — | services[] | Services | **missing in DB** |
| Vision, Hearing, Play, Counseling, SPED therapy | — | services[] | Services | **missing in DB** |
| Quarterly Report Type, Bi-annual, Bi-annual Report Type | — | reports (placeholder) | Reporting | **missing in DB** |
| Meeting Date, Time, Place, Packet Sent, Packet Recieved | — | meetings[] (placeholder) | Meetings | **missing in DB** |
| Notes (general) | Student.notes | notes | Notes | present |
| Class / funding / aide | Student.class_num, funding_code, aide_1to1 | class_num, funding_code, aide_1to1 | Demographics / Contact | present |
| Incidents | Incident (FK student) | incidents[] | — | present (related) |

---

## GAPS (spreadsheet columns with no matching DB field)

- **Demographics / Contact:** SPECALERT, ABA  
- **SPED / Program / IFSP-IEP:** SPEDSERV, IFSPIEP, IFSPIEPST, IFSPIEPEND, DATERECVD  
- **Services:** All service-specific columns (Speech, OT, PT, Vision, Hearing, Play, Counseling, SPED therapy) — no `student_services` or equivalent table.  
- **Reporting:** Quarterly Report Type, Bi-annual, Bi-annual Report Type — no reports table.  
- **Meetings:** Meeting Date, Time, Place, Packet Sent, Packet Recieved — no meetings table.  

**Student ID:** The API returns numeric `id` (primary key). A human-readable "Student ID" column can be added to the model if required.

---

## Related tables (inventory)

| Table | Purpose | Relation to Student |
|-------|---------|---------------------|
| students | Core child record | — |
| incidents | Incident log entries | student_id FK → students.id |
| attendance_records | Daily attendance | student_id FK → students.id |
| academic_sessions | Session (SY) | session_id on Student |
| classrooms | Class (class_num) | Lookup by session + class_num |
| school_districts | District lookup | Session-scoped; display via district/school_district |
| funding_codes | Funding lookup | Session-scoped |

There are no separate `student_medical`, `student_sped_profile`, `student_services`, `student_meetings`, or `student_reports` tables. Medical/SPED data lives on `Student`; services/meetings/reports are placeholders in the API/UI until schema is extended.

---

## Data path audit (roster columns blank)

If the roster shows 145 students but most columns are blank:

1. Run **`python manage.py roster_data_audit --session SY2025-26`** to get DB counts and a raw row dump for one student.
2. Compare that dump with **GET /api/sessions/students/<id>/**; if DB has values but API does not, the serializer is wrong; if DB is empty, the import did not populate those columns.
3. Re-run **import_from_access** with `--update-existing` (or **import_students_csv**) so roster columns are filled. See **docs/roster_data_audit.md** for full steps.

---

## Medical due report endpoint

- **GET** `/api/sessions/medical-due-report/`
- Query params: `session`, `days` (7/14/30/60), `service_type`, `include_inactive`; `export=csv` for CSV.
- Returns: `overdue`, `due_soon`, `missing` (each list of student rows with identifiers, contact, medical_end_date, medical_start_date, vaccines, etc.).
- Satisfies: “Medical due reports still work with the migrated schema” (filter due soon ≤ window, overdue past).
