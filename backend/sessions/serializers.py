"""
Serializers for session models.
"""
from rest_framework import serializers
from .utils.vaccines import parse_vaccines_status
from .models import (
    AcademicSession, Student, Employee, Classroom, FundingCode, SchoolDistrict, Site,
    Incident, AbsenceReason, AttendanceRecord,
)


class SiteSerializer(serializers.ModelSerializer):
    """Serializer for Site (read-only list for dropdown)."""
    class Meta:
        model = Site
        fields = ['id', 'name', 'slug', 'is_active', 'display_order']


class AcademicSessionSerializer(serializers.ModelSerializer):
    """Serializer for AcademicSession."""
    student_count = serializers.SerializerMethodField(read_only=True)
    employee_count = serializers.SerializerMethodField(read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    def get_student_count(self, obj):
        return obj.students.count() if obj.pk else 0

    def get_employee_count(self, obj):
        return obj.employees.count() if obj.pk else 0

    class Meta:
        model = AcademicSession
        fields = [
            'id', 'site', 'site_name', 'session_type', 'name', 'start_date', 'end_date',
            'is_active', 'source_session', 'student_count', 'employee_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student (roster + detail)."""
    session_name = serializers.CharField(source='session.name', read_only=True)
    version = serializers.IntegerField(read_only=True)
    locked_by_email = serializers.SerializerMethodField(read_only=True)
    uploaded_pdf_url = serializers.SerializerMethodField(read_only=True)
    student_type = serializers.SerializerMethodField(read_only=True)
    district_display = serializers.SerializerMethodField(read_only=True)
    vaccines_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'session', 'session_name', 'first_name', 'last_name',
            'date_of_birth', 'enrollment_date', 'status', 'is_active', 'service_type', 'class_num', 'student_type',
            'address', 'home_phone', 'mother_cell', 'father_cell', 'parent_email', 'email', 'parent_phone',
            'district', 'district_display', 'school_district', 'funding_code', 'aide_1to1',
            'discharge_date', 'discharge_notes',
            'vaccines_status', 'vaccines_last_reviewed', 'vaccines_notes', 'vaccines_display',
            'medical_due_date', 'medical_start_date', 'medical_end_date',
            'sped_indiv_code', 'directory_info_opt_out', 'emergency_contact', 'notes',
            'uploaded_pdf_url', 'version', 'locked_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'locked_by_email', 'student_type', 'district_display', 'created_at', 'updated_at']

    def get_locked_by_email(self, obj):
        return obj.locked_by.email if obj.locked_by_id else None

    def get_student_type(self, obj):
        """Backward compat: center_based if class_num else related_service."""
        if getattr(obj, 'service_type', None):
            return obj.service_type
        cn = (obj.class_num or '').strip()
        return 'center_based' if cn else 'related_service'

    def get_district_display(self, obj):
        return obj.district or obj.school_district or ''

    def get_uploaded_pdf_url(self, obj):
        if not obj.uploaded_pdf:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.uploaded_pdf.url)
        return obj.uploaded_pdf.url

    def get_vaccines_display(self, obj):
        data = parse_vaccines_status(obj.vaccines_status or obj.vaccines_notes or "")
        if data["medical_exemption"]:
            return "Medical exemption"
        if data["utd"] and not data["missing"]:
            return "UTD"
        if data["missing"]:
            return "Missing: " + ", ".join(data["missing"])
        return "Unknown"


class ClassroomSerializer(serializers.ModelSerializer):
    """Serializer for Classroom (class_num / class_size dropdown)."""
    label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Classroom
        fields = ['id', 'session', 'class_num', 'class_size', 'teacher', 'assistant1', 'assistant2', 'label']

    def get_label(self, obj):
        return f"{obj.class_num} / {(obj.class_size or '').strip() or '—'}"


class FundingCodeSerializer(serializers.ModelSerializer):
    """Serializer for FundingCode (dropdown options)."""

    class Meta:
        model = FundingCode
        fields = ['id', 'session', 'code']


class SchoolDistrictSerializer(serializers.ModelSerializer):
    """Serializer for SchoolDistrict (dropdown options)."""

    class Meta:
        model = SchoolDistrict
        fields = ['id', 'session', 'name']


class StudentDetailSerializer(StudentSerializer):
    """Detailed serializer for Student with encrypted fields (admin only)."""
    ssn = serializers.SerializerMethodField()
    medical_info = serializers.SerializerMethodField()

    class Meta(StudentSerializer.Meta):
        fields = StudentSerializer.Meta.fields + ['ssn', 'medical_info', 'phi_encrypted']

    def get_ssn(self, obj):
        """Get decrypted SSN (admin only)."""
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user and getattr(user, 'role', None) == 'admin':
            return obj.get_ssn()
        return None

    def get_medical_info(self, obj):
        """Get decrypted medical info (admin only)."""
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user and getattr(user, 'role', None) == 'admin':
            return obj.get_medical_info()
        return None


class StudentDetailContractSerializer(StudentDetailSerializer):
    """
    Full contract for child detail: one API call returns student + incidents + placeholders
    for services/meetings/reports so the UI can render all groups without extra requests.
    Extends StudentDetailSerializer so admin also gets ssn, medical_info when allowed.
    """
    incidents = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    meetings = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()
    duplicate_warning = serializers.SerializerMethodField()

    class Meta(StudentDetailSerializer.Meta):
        fields = StudentDetailSerializer.Meta.fields + [
            'incidents', 'services', 'meetings', 'reports', 'duplicate_warning',
        ]

    def get_incidents(self, obj):
        """Prefetched incidents for this student (uses prefetch_related when available)."""
        incidents = list(getattr(obj, 'incidents', None).all()[:100] if hasattr(obj, 'incidents') else [])
        return [
            {
                'id': i.id,
                'incident_date': i.incident_date.isoformat() if i.incident_date else None,
                'incident_time': i.incident_time.strftime('%H:%M') if i.incident_time else None,
                'location': i.location,
                'incident_type': i.incident_type,
                'description': (i.description or '')[:200],
                'status': i.status,
            }
            for i in incidents
        ]

    def get_services(self, obj):
        """Placeholder until student_services table exists."""
        return []

    def get_meetings(self, obj):
        """Placeholder until student_meetings table exists."""
        return []

    def get_reports(self, obj):
        """Placeholder until student_reports table exists."""
        return {}

    def get_duplicate_warning(self, obj):
        """True if another student in same session has same last_name, first_name, dob."""
        from .models import Student
        qs = Student.objects.filter(
            session_id=obj.session_id,
            last_name__iexact=obj.last_name,
            first_name__iexact=obj.first_name,
        ).exclude(pk=obj.pk)
        if obj.date_of_birth:
            qs = qs.filter(date_of_birth=obj.date_of_birth)
        return qs.exists()


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee."""
    session_name = serializers.CharField(source='session.name', read_only=True)
    version = serializers.IntegerField(read_only=True)
    locked_by_email = serializers.EmailField(source='locked_by.email', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'session', 'session_name', 'first_name', 'last_name',
            'email', 'position', 'medical_due_date',
            'phone', 'mobile_phone', 'notes', 'version', 'locked_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'locked_by_email', 'created_at', 'updated_at']


class AbsenceReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbsenceReason
        fields = ['reason_code', 'reason_label', 'billable_flag']


class IncidentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'session', 'incident_date', 'incident_time', 'student', 'student_name', 'student_name_freeform',
            'location', 'incident_type', 'description', 'reported_by', 'actions_taken',
            'parent_notified', 'parent_notified_at', 'follow_up_required', 'status', 'closed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        if obj.student_id:
            return f"{obj.student.last_name}, {obj.student.first_name}"
        return obj.student_name_freeform or ''


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField(read_only=True)
    absence_reason_code = serializers.CharField(source='absence_reason.reason_code', read_only=True)
    absence_reason_label = serializers.CharField(source='absence_reason.reason_label', read_only=True)

    def get_student_name(self, obj):
        if obj.student_id:
            return f"{obj.student.last_name}, {obj.student.first_name}"
        return ''

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'date', 'student', 'student_name', 'status',
            'late_arrival_time', 'early_dismissal_time', 'absence_reason', 'absence_reason_code', 'absence_reason_label',
            'notes', 'recorded_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
