# Student Detail UI Groups

Child detail view must show all columns in **grouped sections**. Each group corresponds to a logical area of the spreadsheet/source data.

---

## A) Demographics / Contact

- **LASTNAME** → last_name  
- **FIRSTNAME** → first_name  
- **DOB** → date_of_birth  
- **Student ID** → id (or future student_id)  
- **PHONE** → home_phone, parent_phone  
- **MOTHER CELL** → mother_cell  
- **FATHER CELL** → father_cell  
- **EMAIL** → email, parent_email  
- **DISCHARGE** → discharge_date, discharge_notes  
- **SCHOOLDIST** → district_display (district or school_district)  
- **SPECALERT** → (GAP: not in DB)  
- **ABA** → (GAP: not in DB)  
- **Address** → address  
- **Class / Funding / Aide** → class_num, funding_code, aide_1to1  

---

## B) Medical

- **VACCINES** → vaccines_status, vaccines_notes, vaccines_last_reviewed  
- **MEDICALDATE** → medical_start_date, medical_end_date  
- **MEDICAL DUE** → medical_due_date, medical_end_date  
- **Nurses Medical Notes** → notes; medical_info (admin-only encrypted)  

---

## C) SPED / Program / IFSP-IEP

- **SPEDINDIV codes** → sped_indiv_code  
- **SPEDSERV** → (GAP)  
- **IFSPIEP, IFSPIEPST, IFSPIEPEND, DATERECVD** → (GAP)  

---

## D) Services (list/table)

Rendered from a **services** array (API: `services`). When no services table exists, show empty list or placeholder.

- Speech: SPEECHSERV, SPEECHTHER, STDATE, STDUE  
- OT: OTSERVICE, OTTHERAPIS, OTDATE, OT DUE  
- PT: PTSERVICE, PTTHERAPIST, PTDATE, PT DUE  
- Vision, Hearing, Play, Counseling, SPED therapy  

---

## E) Reporting

- **Quarterly Report Type, Bi-annual, Bi-annual Report Type** → API: `reports` object (placeholder until schema exists).  

---

## F) Meetings

- **Meeting Date, Time, Place, Packet Sent, Packet Recieved** → API: `meetings` array (placeholder).  

---

## G) Notes

- **Notes (general)** → notes  
- Any other fields that don’t fit above.  

---

## Implementation

- **StudentDetailPage** (React) consumes `GET /api/sessions/students/:id/` and renders these groups as separate sections (e.g. `<Paper>` or `<Card>` per group).  
- Each spreadsheet field that exists in the API appears in the correct group; GAPs are either omitted or shown as “—” / “Not recorded” until DB support is added.  
- **Floater:** If `last_name` is “floater” (case-insensitive), block create or show non-student type.  
- **Duplicate warning:** If another student exists with same (last_name, first_name, dob) in the session, show banner: “Possible duplicate record detected.”  
