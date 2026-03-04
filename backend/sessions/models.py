"""
Models for academic sessions, students, and employees.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from cryptography.fernet import Fernet
from django.conf import settings
from compliance.encryption import encryption_service
import base64
import os


def _student_pdf_upload_to(instance, filename):
    """Store one PDF per student; re-upload replaces (e.g. student_docs/123/record.pdf)."""
    if instance.pk:
        return f'student_docs/{instance.pk}/record.pdf'
    return f'student_docs/tmp/{filename}'


class Site(models.Model):
    """School/location site; data is scoped by site (Rockland, Woodmere, 55th Street, 14th Ave., SEIT)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0, help_text='Order in UI dropdowns')

    class Meta:
        db_table = 'sites'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class AcademicSession(models.Model):
    """Model for School Year (SY) and Summer sessions. Scoped by site."""
    
    SESSION_TYPE_CHOICES = [
        ('SY', 'School Year'),
        ('SUMMER', 'Summer Session'),
    ]
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text='Site this session belongs to.',
    )
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES)
    name = models.CharField(max_length=50)  # unique per site via Meta constraint
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    source_session = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_sessions',
        help_text='Session from which data was inherited'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academic_sessions'
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(fields=['site', 'name'], name='academic_sessions_site_name_uniq'),
        ]
    
    def __str__(self):
        return self.name


class Student(models.Model):
    """Model for student/child information (roster matches Access → Student Data)."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
        ('transferred', 'Transferred'),
    ]
    SERVICE_TYPE_CHOICES = [
        ('center_based', 'Center-based'),
        ('related_service', 'Related service'),
        ('seit', 'SEIT'),
        ('unknown', 'Unknown'),
    ]

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='students'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    enrollment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True, help_text='False when discharged; keeps discharge info.')

    # Service type: Center-based / Related service / SEIT / Unknown (subdivides roster, billing)
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='center_based',
        blank=True,
        help_text='Center-based = has class; Related service / SEIT = distinct for billing; Unknown = unclassified.',
    )

    # FERPA compliance fields
    directory_info_opt_out = models.BooleanField(
        default=False,
        help_text='Parent/student has opted out of directory information'
    )

    # Encrypted fields for PHI/PII
    ssn_encrypted = models.TextField(blank=True, null=True)
    medical_info_encrypted = models.TextField(blank=True, null=True)
    phi_encrypted = models.BooleanField(default=False)

    # Roster / contact (match Access Student Data labels)
    class_num = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='CLASSNUM from QRY_student Data Center Based; determines class/teacher/assistants on roster.',
    )
    address = models.TextField(blank=True, null=True)
    home_phone = models.CharField(max_length=32, blank=True, null=True)
    mother_cell = models.CharField(max_length=32, blank=True, null=True)
    father_cell = models.CharField(max_length=32, blank=True, null=True)
    parent_email = models.CharField(max_length=254, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True, help_text='Student/parent email (display as Email).')
    district = models.CharField(max_length=100, blank=True, null=True, help_text='District (display label).')
    school_district = models.CharField(max_length=100, blank=True, null=True, help_text='School district from Access (legacy).')
    funding_code = models.CharField(max_length=20, blank=True, null=True, help_text='Funding code from Access')
    aide_1to1 = models.CharField(max_length=100, blank=True, null=True, help_text='1:1 aide name for roster report')
    emergency_contact = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Discharge
    discharge_date = models.DateField(blank=True, null=True)
    discharge_notes = models.TextField(blank=True, null=True)

    # Vaccines (minimum viable: status + last reviewed + notes)
    vaccines_status = models.CharField(max_length=100, blank=True, null=True)
    vaccines_last_reviewed = models.DateField(blank=True, null=True)
    vaccines_notes = models.TextField(blank=True, null=True)

    # Medical dates (reports: due soon / overdue)
    medical_due_date = models.DateField(blank=True, null=True, help_text='Legacy: next medical due.')
    medical_start_date = models.DateField(blank=True, null=True)
    medical_end_date = models.DateField(blank=True, null=True, help_text='Medical clearance end; used for due/overdue reports.')

    # SPED
    sped_indiv_code = models.CharField(max_length=50, blank=True, null=True, help_text='SPED INDIV Code.')

    # Legacy contact (map to parent_phone if needed)
    parent_phone = models.CharField(max_length=32, blank=True, null=True)

    uploaded_pdf = models.FileField(
        upload_to=_student_pdf_upload_to,
        blank=True,
        null=True,
        help_text='PDF file attached to this child\'s record',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    locked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_students',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'students'
        ordering = ['last_name', 'first_name', 'date_of_birth']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['last_name', 'first_name', 'date_of_birth'], name='students_roster_name_dob_idx'),
            models.Index(fields=['session', 'is_active']),
            models.Index(fields=['session', 'service_type']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.session.name})"
    
    def set_ssn(self, ssn):
        """Encrypt and store SSN."""
        if ssn:
            # Use encryption_service which automatically chooses appropriate method
            self.ssn_encrypted = encryption_service.encrypt(ssn)
            self.phi_encrypted = True
        else:
            self.ssn_encrypted = None
    
    def get_ssn(self):
        """Decrypt and return SSN."""
        if self.ssn_encrypted:
            return encryption_service.decrypt(self.ssn_encrypted)
        return None
    
    def set_medical_info(self, medical_info):
        """Encrypt and store medical information."""
        if medical_info:
            # Use encryption_service which automatically uses envelope encryption for large data
            self.medical_info_encrypted = encryption_service.encrypt(medical_info)
            self.phi_encrypted = True
        else:
            self.medical_info_encrypted = None
    
    def get_medical_info(self):
        """Decrypt and return medical information."""
        if self.medical_info_encrypted:
            return encryption_service.decrypt(self.medical_info_encrypted)
        return None
    
    def _encrypt_field(self, value):
        """Encrypt a field value (deprecated - use encryption_service instead)."""
        # Legacy method kept for backward compatibility
        # Now delegates to encryption_service
        return encryption_service.encrypt(value)
    
    def _decrypt_field(self, encrypted_value):
        """Decrypt a field value (deprecated - use encryption_service instead)."""
        # Legacy method kept for backward compatibility
        # Now delegates to encryption_service
        return encryption_service.decrypt(encrypted_value)


class Employee(models.Model):
    """Model for staff/employee information."""

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    position = models.CharField(max_length=100)

    # Additional fields
    medical_due_date = models.DateField(blank=True, null=True, help_text='Next medical clearance / physical due date')
    phone = models.CharField(max_length=20, blank=True, null=True, help_text='Home phone')
    mobile_phone = models.CharField(max_length=20, blank=True, null=True, help_text='Mobile phone')
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optimistic locking field for concurrent editing
    version = models.IntegerField(default=1)
    locked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_employees'
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position} ({self.session.name})"


class Classroom(models.Model):
    """Classroom from Access Classes table (CLASSNUM, CLASSSIZE, TEACHER, ASSISTANT1, ASSISTANT2) per session."""
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='classrooms'
    )
    class_num = models.CharField(max_length=50)
    class_size = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Ratio e.g. 12:1:2 = 12 students, 1 teacher, 2 assistants; 8:1:2 = 8,1,2; 6:1:2 = 6,1,2. With 1:1 aides, class may exceed ratio with special approval.',
    )
    teacher = models.CharField(max_length=100, blank=True, null=True)
    assistant1 = models.CharField(max_length=100, blank=True, null=True)
    assistant2 = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'classrooms'
        ordering = ['class_num']
        unique_together = [['session', 'class_num']]

    def __str__(self):
        return f"{self.class_num} / {self.class_size or ''}"


class FundingCode(models.Model):
    """Funding codes from Access 'Funding Codes' table, per session."""
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='funding_codes'
    )
    code = models.CharField(max_length=50)

    class Meta:
        db_table = 'funding_codes'
        ordering = ['code']
        unique_together = [['session', 'code']]

    def __str__(self):
        return self.code


class SchoolDistrict(models.Model):
    """School districts from Access lookup table, per session."""
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='school_districts'
    )
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'school_districts'
        ordering = ['name']
        unique_together = [['session', 'name']]

    def __str__(self):
        return self.name


class Incident(models.Model):
    """Incident log (spreadsheet-style): date, student or freeform name, type, description, etc."""
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='incidents',
        null=True,
        blank=True,
        help_text='Optional: scope by session.',
    )
    incident_date = models.DateField()
    incident_time = models.TimeField(null=True, blank=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents',
    )
    student_name_freeform = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    incident_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    reported_by = models.CharField(max_length=200, blank=True, null=True)
    actions_taken = models.TextField(blank=True, null=True)
    parent_notified = models.BooleanField(default=False)
    parent_notified_at = models.DateTimeField(null=True, blank=True)
    follow_up_required = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[('open', 'Open'), ('closed', 'Closed')],
        default='open',
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'incidents'
        ordering = ['-incident_date', '-incident_time', '-id']

    def __str__(self):
        return f"Incident {self.id} ({self.incident_date})"


class AbsenceReason(models.Model):
    """Lookup: reason code for absences (SICK, APPT, etc.); optional billable flag for billing."""
    reason_code = models.CharField(max_length=50, primary_key=True)
    reason_label = models.CharField(max_length=200)
    billable_flag = models.BooleanField(default=False, blank=True)

    class Meta:
        db_table = 'absence_reasons'
        ordering = ['reason_label']

    def __str__(self):
        return f"{self.reason_code}: {self.reason_label}"


class AttendanceRecord(models.Model):
    """One record per student per day: present/absent, late/early, absence reason."""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    date = models.DateField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    late_arrival_time = models.TimeField(null=True, blank=True)
    early_dismissal_time = models.TimeField(null=True, blank=True)
    absence_reason = models.ForeignKey(
        AbsenceReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
    )
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_records'
        ordering = ['-date', 'student__last_name', 'student__first_name']
        constraints = [
            models.UniqueConstraint(fields=['date', 'student'], name='attendance_record_date_student_uniq'),
        ]

    def __str__(self):
        return f"{self.student_id} {self.date} {self.status}"
