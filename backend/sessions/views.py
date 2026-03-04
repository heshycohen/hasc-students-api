"""
Views for session, student, and employee management.
Multi-site: site-bound users see only their site; admin uses query param `site` or header `X-Site-Id`.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from datetime import date, datetime, timedelta
from .models import (
    AcademicSession, Student, Employee, Classroom, FundingCode, SchoolDistrict, Site,
    Incident, AbsenceReason, AttendanceRecord,
)
from .serializers import (
    AcademicSessionSerializer, StudentSerializer, StudentDetailSerializer,
    StudentDetailContractSerializer,
    EmployeeSerializer, ClassroomSerializer, FundingCodeSerializer, SchoolDistrictSerializer,
    SiteSerializer,
    IncidentSerializer, AbsenceReasonSerializer, AttendanceRecordSerializer,
)
from .services import SessionInheritanceService
from compliance.utils import log_access
from users.permissions import IsAdminOrEditor, IsAdmin
from .utils.vaccines import parse_vaccines_status


def _json_safe_changes(validated_data):
    """Convert validated_data to JSON-serializable dict for audit log (dates, FKs, etc.)."""
    out = {}
    for k, v in validated_data.items():
        if hasattr(v, 'pk'):
            out[k] = v.pk
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        elif v is None or isinstance(v, (bool, int, float, str)):
            out[k] = v
        elif isinstance(v, (list, dict)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of sites for admin dropdown. Site-bound users see only their site."""
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'site_id', None):
            return Site.objects.filter(pk=user.site_id)
        return Site.objects.filter(is_active=True)


def _resolve_site_id(request):
    """
    Resolve the effective site_id for this request.
    - Site-bound user (user.site_id set): return that site_id.
    - Admin (user.site_id null): return request query param `site` or header `X-Site-Id` (integer or slug), or None for "all sites".
    """
    user = request.user
    if getattr(user, 'site_id', None):
        return user.site_id
    site_param = request.query_params.get('site') or request.headers.get('X-Site-Id')
    if not site_param:
        return None
    try:
        return int(site_param)
    except (TypeError, ValueError):
        site = Site.objects.filter(slug=site_param).first()
        return site.id if site else None


def _get_active_session_for_site(site_id):
    """Return the active session for the given site, or None."""
    if site_id is None:
        return AcademicSession.objects.filter(is_active=True).first()
    return AcademicSession.objects.filter(site_id=site_id, is_active=True).first()


def _apply_student_roster_filters(request, qs):
    """
    Apply unified roster filters for discharge, SPED INDIV code, service_type, and district.
    Used by the main roster API, CSV export, and print/roster endpoints so they stay in sync.
    """
    # --- Discharge filter ---
    discharge = request.query_params.get("discharge", "all")
    if discharge == "active":
        qs = qs.filter(is_active=True)
    elif discharge == "discharged":
        qs = qs.filter(is_active=False)

    # --- SPED INDIV filter ---
    sped = (request.query_params.get("sped_indiv_code") or "").strip()
    if sped:
        qs = qs.filter(sped_indiv_code__iexact=sped)

    # --- Service Type filter ---
    stype = (request.query_params.get("service_type") or "").strip()
    if stype:
        qs = qs.filter(service_type=stype)

    # --- District filter (existing behavior, centralized) ---
    district = request.query_params.get("district")
    if district:
        qs = qs.filter(Q(district__iexact=district) | Q(school_district__iexact=district))

    return qs


class AcademicSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for academic sessions. Filtered by site (site-bound user or admin's site param)."""
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        qs = AcademicSession.objects.all().select_related('site')
        if site_id is not None:
            qs = qs.filter(site_id=site_id)
        return qs.order_by('-start_date')

    def perform_create(self, serializer):
        site = serializer.validated_data.get('site')
        site_id = (
            getattr(self.request.user, 'site_id', None)
            or (site.id if site else None)
            or _resolve_site_id(self.request)
        )
        if not site_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'site': 'Site is required. Set site (id or slug) in body or query.'})
        serializer.save(site_id=site_id)
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        """Set a session as active (only deactivates other sessions in the same site)."""
        session = self.get_object()
        AcademicSession.objects.filter(site=session.site, is_active=True).update(is_active=False)
        session.is_active = True
        session.save()
        
        log_access(request.user, 'session', session.id, 'update', request, 
                  changes={'is_active': True}, site_id=session.site_id)
        
        return Response({'detail': 'Session activated'})
    
    @action(detail=True, methods=['post'])
    def inherit_data(self, request, pk=None):
        """Manually trigger data inheritance from source session."""
        target_session = self.get_object()
        if not target_session.source_session:
            return Response(
                {'detail': 'No source session configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = SessionInheritanceService()
        result = service.copy_session_data(
            target_session.source_session,
            target_session,
            request.user
        )
        
        return Response(result)


class StudentViewSet(viewsets.ModelViewSet):
    """ViewSet for students."""
    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use full contract serializer for detail (one-call: student + incidents + placeholders)."""
        if self.action == 'retrieve':
            return StudentDetailContractSerializer
        return StudentSerializer
    
    def get_queryset(self):
        """Filter by session, discharge, SPED INDIV code, service_type, district; order alphabetically."""
        site_id = _resolve_site_id(self.request)
        active_session = _get_active_session_for_site(site_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = Student.objects.filter(session_id=session_id)
            if site_id is not None:
                qs = qs.filter(session__site_id=site_id)
        else:
            qs = Student.objects.all()
            if active_session:
                qs = qs.filter(session=active_session)
        qs = _apply_student_roster_filters(self.request, qs)
        qs = qs.order_by('last_name', 'first_name', 'date_of_birth')
        if self.action == 'retrieve':
            qs = qs.select_related('session').prefetch_related('incidents')
        return qs
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_pdf', 'delete_pdf']:
            return [IsAuthenticated(), IsAdminOrEditor()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Create student and log access. Reject 'floater' as last_name (non-student placeholder)."""
        from rest_framework.exceptions import ValidationError
        last = (serializer.validated_data.get('last_name') or '').strip().lower()
        if last == 'floater':
            raise ValidationError(
                {'last_name': 'Cannot create a student with last name "floater" (reserved for non-student placeholders).'}
            )
        student = serializer.save()
        log_access(self.request.user, 'student', student.id, 'create',
                  self.request, changes=_json_safe_changes(serializer.validated_data),
                  site_id=student.session.site_id)
    
    def perform_update(self, serializer):
        """Update student and log access with optimistic locking."""
        student = self.get_object()
        
        # Check version for optimistic locking
        expected_version = self.request.data.get('version')
        if expected_version and student.version != expected_version:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'version': f'Record was modified. Current version: {student.version}'
            })
        
        old_data = StudentSerializer(student).data
        serializer.save(version=student.version + 1)
        log_access(self.request.user, 'student', student.id, 'update',
                  self.request, changes={'old': old_data, 'new': serializer.validated_data}, site_id=student.session.site_id)
    
    def perform_destroy(self, instance):
        """Delete student and log access."""
        log_access(self.request.user, 'student', instance.id, 'delete', self.request, site_id=instance.session.site_id)
        instance.delete()

    def get_parsers(self):
        """Allow multipart for upload_pdf."""
        if getattr(self, 'action', None) == 'upload_pdf':
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    @action(detail=True, methods=['post'], url_path='upload-pdf')
    def upload_pdf(self, request, pk=None):
        """Upload a PDF file to this student's record. Accepts multipart/form-data with 'file' key."""
        student = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'detail': 'No file provided. Use form field "file".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        name = (file.name or '').lower()
        if not name.endswith('.pdf'):
            return Response(
                {'detail': 'Only PDF files are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if file.content_type and 'pdf' not in file.content_type:
            return Response(
                {'detail': 'Only PDF files are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        student.uploaded_pdf = file
        student.save(update_fields=['uploaded_pdf'])
        log_access(request.user, 'student', student.id, 'update', request, changes={'uploaded_pdf': 'uploaded'}, site_id=student.session.site_id)
        serializer = self.get_serializer(student)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='uploaded-pdf')
    def delete_pdf(self, request, pk=None):
        """Remove the uploaded PDF from this student's record."""
        student = self.get_object()
        if not student.uploaded_pdf:
            return Response(
                {'detail': 'No PDF attached.'},
                status=status.HTTP_404_NOT_FOUND
            )
        student.uploaded_pdf.delete(save=False)
        student.uploaded_pdf = None
        student.save(update_fields=['uploaded_pdf'])
        log_access(request.user, 'student', student.id, 'update', request, changes={'uploaded_pdf': 'removed'}, site_id=student.session.site_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        """List students (roster). Supports export=csv for CSV download."""
        if request.query_params.get('export') == 'csv':
            qs = self.filter_queryset(self.get_queryset())
            import csv
            from django.http import HttpResponse as HttpResponseBase
            resp = HttpResponseBase(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="student_roster.csv"'
            writer = csv.writer(resp)
            headers = [
                'Last name', 'First name', 'DOB', 'Address', 'Home phone', 'Mother cell', 'Father cell', 'Email',
                'Discharge', 'District', 'Vaccines', 'Medical start date', 'Medical end date', 'SPED INDIV Code',
                'Service type',
            ]
            writer.writerow(headers)
            for s in qs:
                vax = parse_vaccines_status(s.vaccines_status or s.vaccines_notes or '')
                if vax["medical_exemption"]:
                    vaccines_display = "Medical exemption"
                elif vax["utd"] and not vax["missing"]:
                    vaccines_display = "UTD"
                elif vax["missing"]:
                    vaccines_display = "Missing: " + ", ".join(vax["missing"])
                else:
                    vaccines_display = "Unknown"
                writer.writerow([
                    s.last_name or '', s.first_name or '', s.date_of_birth.isoformat() if s.date_of_birth else '',
                    s.address or '', s.home_phone or s.parent_phone or '', s.mother_cell or '', s.father_cell or '',
                    s.email or s.parent_email or '',
                    (('Yes' if not s.is_active else 'No') + (f' ({s.discharge_date.isoformat()})' if s.discharge_date else '') + (f' {s.discharge_notes}' if s.discharge_notes else '')),
                    s.district or s.school_district or '', vaccines_display,
                    s.medical_start_date.isoformat() if s.medical_start_date else '',
                    s.medical_end_date.isoformat() if s.medical_end_date else '',
                    s.sped_indiv_code or '', dict(Student.SERVICE_TYPE_CHOICES).get(s.service_type) or "Unknown",
                ])
            return resp
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='pdf')
    def get_pdf(self, request, pk=None):
        """Return the uploaded PDF file (authenticated)."""
        student = self.get_object()
        if not student.uploaded_pdf:
            return Response(
                {'detail': 'No PDF attached.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            student.uploaded_pdf.open('rb'),
            as_attachment=False,
            filename='record.pdf',
            content_type='application/pdf',
        )


class EmployeeViewSet(viewsets.ModelViewSet):
    """ViewSet for employees. Filtered by session / active session for resolved site."""
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        active_session = _get_active_session_for_site(site_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = Employee.objects.filter(session_id=session_id)
            if site_id is not None:
                qs = qs.filter(session__site_id=site_id)
        else:
            qs = Employee.objects.all()
            if active_session:
                qs = qs.filter(session=active_session)
        return qs
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrEditor()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Create employee and log access."""
        employee = serializer.save()
        log_access(self.request.user, 'employee', employee.id, 'create',
                  self.request, changes=_json_safe_changes(serializer.validated_data),
                  site_id=employee.session.site_id)
    
    def perform_update(self, serializer):
        """Update employee and log access with optimistic locking."""
        employee = self.get_object()
        
        # Check version for optimistic locking
        expected_version = self.request.data.get('version')
        if expected_version and employee.version != expected_version:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'version': f'Record was modified. Current version: {employee.version}'
            })
        
        old_data = EmployeeSerializer(employee).data
        serializer.save(version=employee.version + 1)
        log_access(self.request.user, 'employee', employee.id, 'update',
                  self.request, changes={'old': old_data, 'new': serializer.validated_data}, site_id=employee.session.site_id)
    
    def perform_destroy(self, instance):
        """Delete employee and log access."""
        log_access(self.request.user, 'employee', instance.id, 'delete', self.request, site_id=instance.session.site_id)
        instance.delete()


class ClassroomViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of classrooms for a session (unpaginated for dropdown). Scoped by site."""
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        active_session = _get_active_session_for_site(site_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = Classroom.objects.filter(session_id=session_id)
            if site_id is not None:
                qs = qs.filter(session__site_id=site_id)
        else:
            qs = Classroom.objects.all()
            if active_session:
                qs = qs.filter(session=active_session)
        return qs.order_by('class_num')


class FundingCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of funding codes for a session (unpaginated for dropdown). Scoped by site."""
    serializer_class = FundingCodeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        active_session = _get_active_session_for_site(site_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = FundingCode.objects.filter(session_id=session_id)
            if site_id is not None:
                qs = qs.filter(session__site_id=site_id)
        else:
            qs = FundingCode.objects.all()
            if active_session:
                qs = qs.filter(session=active_session)
        return qs.order_by('code')


class SchoolDistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of school districts for a session (unpaginated for dropdown). Scoped by site."""
    serializer_class = SchoolDistrictSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        active_session = _get_active_session_for_site(site_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = SchoolDistrict.objects.filter(session_id=session_id)
            if site_id is not None:
                qs = qs.filter(session__site_id=site_id)
        else:
            qs = SchoolDistrict.objects.all()
            if active_session:
                qs = qs.filter(session=active_session)
        return qs.order_by('name')


def _normalize_class_num(val):
    """Strip and return class_num for consistent grouping."""
    return (val or '').strip()


class StudentRosterView(APIView):
    """GET: Student roster for printing (grouped by class, matches PDF layout). Scoped by site."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        site_id = _resolve_site_id(request)
        session_id = request.query_params.get('session')
        if session_id:
            q = AcademicSession.objects.filter(pk=session_id)
            if site_id is not None:
                q = q.filter(site_id=site_id)
            session = q.first()
        else:
            session = _get_active_session_for_site(site_id)
        if not session:
            return Response(
                {'detail': 'No session found'},
                status=status.HTTP_404_NOT_FOUND
            )
        # Load classrooms from DB (class_num, class_size, teacher, assistant1, assistant2)
        classrooms = list(Classroom.objects.filter(session=session).order_by('class_num'))
        classroom_by_num = {c.class_num: c for c in classrooms}

        # Roster = center-based only. Load only students with a class_num; related-service children (no class_num) are excluded.
        students_qs = Student.objects.filter(session=session)
        students_qs = _apply_student_roster_filters(request, students_qs)
        students_raw = list(
            students_qs
            .exclude(class_num__isnull=True)
            .exclude(class_num='')
            .order_by('last_name', 'first_name')
            .values(
                'first_name', 'last_name', 'date_of_birth',
                'school_district', 'funding_code', 'parent_phone', 'class_num', 'aide_1to1'
            )
        )
        students = []
        for s in students_raw:
            class_num = _normalize_class_num(s.get('class_num'))
            if not class_num:
                continue
            row = {
                'first_name': (s.get('first_name') or '').strip(),
                'last_name': (s.get('last_name') or '').strip(),
                'date_of_birth': s.get('date_of_birth'),
                'school_district': (s.get('school_district') or '').strip(),
                'funding_code': (s.get('funding_code') or '').strip(),
                'parent_phone': (s.get('parent_phone') or '').strip(),
                'class_num': class_num,
                'aide_1to1': (s.get('aide_1to1') or '').strip(),
            }
            if row['date_of_birth']:
                row['date_of_birth'] = row['date_of_birth'].isoformat()
            students.append(row)

        # Section order: classroom order first, then any student-only class_nums (sorted). No "Other" section.
        class_nums_from_students = {s['class_num'] for s in students if s['class_num']}
        class_nums_from_classrooms = set(classroom_by_num.keys())

        roster = []
        # 1) Sections for each classroom that has at least one student (skip empty classes)
        for c in classrooms:
            class_students = [s for s in students if s['class_num'] == c.class_num]
            if not class_students:
                continue
            roster.append({
                'class_num': c.class_num,
                'class_size': (c.class_size or '').strip(),
                'teacher': (c.teacher or '').strip(),
                'assistant1': (c.assistant1 or '').strip(),
                'assistant2': (c.assistant2 or '').strip(),
                'students': class_students,
            })
        # 2) Sections for class_nums that appear in students but have no Classroom row
        for class_num in sorted(class_nums_from_students - class_nums_from_classrooms):
            class_students = [s for s in students if s['class_num'] == class_num]
            if not class_students:
                continue
            roster.append({
                'class_num': class_num,
                'class_size': '',
                'teacher': '',
                'assistant1': '',
                'assistant2': '',
                'students': class_students,
            })
        # Students without CLASSNUM are excluded from the roster (not shown).

        return Response({
            'session_name': session.name,
            'generated_date': date.today().isoformat(),
            'classrooms': roster,
        })


class CopySessionView(APIView):
    """Copy data from one session to another. Source and target must be in the same site."""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, pk):
        """Copy data from source session to target session."""
        site_id = _resolve_site_id(request)
        target_session = AcademicSession.objects.filter(pk=pk)
        if site_id is not None:
            target_session = target_session.filter(site_id=site_id)
        target_session = target_session.first()
        if not target_session:
            return Response({'detail': 'Target session not found'}, status=status.HTTP_404_NOT_FOUND)

        source_session_id = request.data.get('source_session_id')
        if not source_session_id:
            return Response(
                {'detail': 'source_session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        source_session = AcademicSession.objects.filter(pk=source_session_id)
        if site_id is not None:
            source_session = source_session.filter(site_id=site_id)
        source_session = source_session.first()
        if not source_session:
            return Response(
                {'detail': 'Source session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if source_session.site_id != target_session.site_id:
            return Response(
                {'detail': 'Source and target session must be in the same site'},
                status=status.HTTP_400_BAD_REQUEST
            )
        service = SessionInheritanceService()
        result = service.copy_session_data(source_session, target_session, request.user)
        return Response(result)


class CurrentSessionView(APIView):
    """Get current active session for the resolved site (query param `site` or header `X-Site-Id`)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        site_id = _resolve_site_id(request)
        session = _get_active_session_for_site(site_id)
        if session:
            serializer = AcademicSessionSerializer(session)
            return Response(serializer.data)
        return Response(
            {'detail': 'No active session'},
            status=status.HTTP_404_NOT_FOUND
        )


def _medical_due_student_row(student):
    """Build a dict for medical due report rows."""
    end = student.medical_end_date
    today = date.today()
    days_until = (end - today).days if end else None
    district = student.district or student.school_district or ''
    return {
        'id': student.id,
        'last_name': student.last_name,
        'first_name': student.first_name,
        'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
        'district': district,
        'service_type': student.service_type,
        'medical_start_date': student.medical_start_date.isoformat() if student.medical_start_date else None,
        'medical_end_date': student.medical_end_date.isoformat() if student.medical_end_date else None,
        'days_until_due': days_until,
        'home_phone': student.home_phone or student.parent_phone or '',
        'mother_cell': student.mother_cell or '',
        'father_cell': student.father_cell or '',
        'email': student.email or student.parent_email or '',
    }


class MedicalDueReportView(APIView):
    """GET: Medical due report - overdue, due_soon (next N days), missing medical dates. CSV export via query param."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        site_id = _resolve_site_id(request)
        session_id = request.query_params.get('session')
        if session_id:
            q = AcademicSession.objects.filter(pk=session_id)
            if site_id is not None:
                q = q.filter(site_id=site_id)
            session = q.first()
        else:
            session = _get_active_session_for_site(site_id)
        if not session:
            return Response({'detail': 'No session found'}, status=status.HTTP_404_NOT_FOUND)

        days_param = request.query_params.get('days', '30')
        try:
            days = int(days_param)
        except ValueError:
            days = 30
        include_inactive = request.query_params.get('include_inactive', '').lower() in ('true', '1', 'yes')
        service_type = request.query_params.get('service_type')

        base = Student.objects.filter(session=session)
        if not include_inactive:
            base = base.filter(is_active=True)
        if service_type in ('center_based', 'related_service', 'seit', 'unknown'):
            base = base.filter(service_type=service_type)

        today = date.today()
        end_window = today + timedelta(days=days)

        overdue = base.filter(medical_end_date__lt=today).exclude(medical_end_date__isnull=True).order_by('medical_end_date', 'last_name', 'first_name')
        due_soon = base.filter(medical_end_date__gte=today, medical_end_date__lte=end_window).order_by('medical_end_date', 'last_name', 'first_name')
        missing = base.filter(Q(medical_end_date__isnull=True) | Q(medical_start_date__isnull=True)).order_by('last_name', 'first_name')

        result = {
            'session_id': session.id,
            'session_name': session.name,
            'overdue': [_medical_due_student_row(s) for s in overdue],
            'due_soon': [_medical_due_student_row(s) for s in due_soon],
            'missing': [_medical_due_student_row(s) for s in missing],
        }
        if request.query_params.get('export') == 'csv':
            import csv
            from django.http import HttpResponse as HttpResponseBase
            resp = HttpResponseBase(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="medical_due_report.csv"'
            writer = csv.writer(resp)
            headers = ['Last name', 'First name', 'DOB', 'District', 'Service type', 'Medical start', 'Medical end', 'Days until due', 'Home phone', 'Mother cell', 'Father cell', 'Email']
            writer.writerow(headers)
            for row in result['overdue'] + result['due_soon'] + result['missing']:
                writer.writerow([
                    row.get('last_name'), row.get('first_name'), row.get('date_of_birth'), row.get('district'),
                    row.get('service_type'), row.get('medical_start_date'), row.get('medical_end_date'),
                    row.get('days_until_due'), row.get('home_phone'), row.get('mother_cell'), row.get('father_cell'), row.get('email'),
                ])
            return resp
        return Response(result)


class IncidentViewSet(viewsets.ModelViewSet):
    """Incident log: list/create/update/delete. Filter by session, student, date range, type, status."""
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        session_id = self.request.query_params.get('session')
        qs = Incident.objects.select_related('student', 'session').all()
        if session_id:
            qs = qs.filter(session_id=session_id)
        if site_id is not None:
            qs = qs.filter(session__site_id=site_id)
        student_id = self.request.query_params.get('student_id')
        if student_id:
            qs = qs.filter(student_id=student_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(incident_date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(incident_date__lte=date_to)
        incident_type = self.request.query_params.get('incident_type')
        if incident_type:
            qs = qs.filter(incident_type=incident_type)
        status_filter = self.request.query_params.get('status')
        if status_filter in ('open', 'closed'):
            qs = qs.filter(status=status_filter)
        return qs.order_by('-incident_date', '-incident_time', '-id')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrEditor()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        session_id = self.request.data.get('session') or self.request.query_params.get('session')
        active = _get_active_session_for_site(_resolve_site_id(self.request))
        if not session_id and active:
            session_id = active.id
        serializer.save(session_id=session_id)


class AbsenceReasonViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of absence reason codes for attendance dropdown."""
    queryset = AbsenceReason.objects.all()
    serializer_class = AbsenceReasonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """Attendance records: one per student per day. List by date/session; create/update; daily absent report."""
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        site_id = _resolve_site_id(self.request)
        session_id = self.request.query_params.get('session')
        date_param = self.request.query_params.get('date')
        qs = AttendanceRecord.objects.select_related('student', 'absence_reason').all()
        if session_id:
            qs = qs.filter(student__session_id=session_id)
            if site_id is not None:
                qs = qs.filter(student__session__site_id=site_id)
        elif site_id is not None:
            qs = qs.filter(student__session__site_id=site_id)
        if date_param:
            qs = qs.filter(date=date_param)
        return qs.order_by('-date', 'student__last_name', 'student__first_name')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrEditor()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        data = serializer.validated_data
        if data.get('status') == 'absent' and not data.get('absence_reason_id'):
            absence_reason = AbsenceReason.objects.filter(reason_code='UNKNOWN').first()
            if absence_reason:
                serializer.validated_data['absence_reason'] = absence_reason
            else:
                raise ValidationError({'absence_reason': 'Required when status is absent (or add UNKNOWN reason).'})
        serializer.save(recorded_by=getattr(self.request.user, 'email', None) or str(self.request.user))

    def perform_update(self, serializer):
        from rest_framework.exceptions import ValidationError
        data = serializer.validated_data
        if data.get('status') == 'absent' and not data.get('absence_reason') and not getattr(serializer.instance, 'absence_reason_id', None):
            absence_reason = AbsenceReason.objects.filter(reason_code='UNKNOWN').first()
            if absence_reason:
                serializer.validated_data['absence_reason'] = absence_reason
        serializer.save(recorded_by=getattr(self.request.user, 'email', None) or str(self.request.user))

    @action(detail=False, methods=['get'], url_path='daily-absent-report')
    def daily_absent_report(self, request):
        """GET ?date=YYYY-MM-DD&session=: list absent students + missing attendance entries for that date. Export CSV."""
        site_id = _resolve_site_id(request)
        session_id = request.query_params.get('session')
        date_param = request.query_params.get('date')
        if not date_param:
            return Response({'detail': 'date (YYYY-MM-DD) is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            report_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        if session_id:
            q = AcademicSession.objects.filter(pk=session_id)
            if site_id is not None:
                q = q.filter(site_id=site_id)
            session = q.first()
        else:
            session = _get_active_session_for_site(site_id)
        if not session:
            return Response({'detail': 'No session found'}, status=status.HTTP_404_NOT_FOUND)

        active_students = Student.objects.filter(session=session, is_active=True).order_by('last_name', 'first_name')
        recorded = set(
            AttendanceRecord.objects.filter(date=report_date, student__session=session)
            .values_list('student_id', flat=True)
        )
        absent_records = AttendanceRecord.objects.filter(
            date=report_date, student__session=session, status='absent'
        ).select_related('student', 'absence_reason').order_by('student__last_name', 'student__first_name')

        absent_rows = []
        for rec in absent_records:
            s = rec.student
            district = s.district or s.school_district or ''
            absent_rows.append({
                'student_id': s.id,
                'student_name': f"{s.last_name}, {s.first_name}",
                'district': district,
                'service_type': dict(Student.SERVICE_TYPE_CHOICES).get(s.service_type) or "Unknown",
                'home_phone': s.home_phone or s.parent_phone or '',
                'mother_cell': s.mother_cell or '',
                'father_cell': s.father_cell or '',
                'email': s.email or s.parent_email or '',
                'absence_reason': rec.absence_reason.reason_label if rec.absence_reason_id else '',
                'notes': rec.notes or '',
            })
        missing_ids = [s.id for s in active_students if s.id not in recorded]
        missing_students = Student.objects.filter(id__in=missing_ids).order_by('last_name', 'first_name')
        missing_rows = []
        for s in missing_students:
            district = s.district or s.school_district or ''
            missing_rows.append({
                'student_id': s.id,
                'student_name': f"{s.last_name}, {s.first_name}",
                'district': district,
                'service_type': dict(Student.SERVICE_TYPE_CHOICES).get(s.service_type) or "Unknown",
                'home_phone': s.home_phone or s.parent_phone or '',
                'mother_cell': s.mother_cell or '',
                'father_cell': s.father_cell or '',
                'email': s.email or s.parent_email or '',
            })

        result = {
            'date': date_param,
            'session_id': session.id,
            'session_name': session.name,
            'absent': absent_rows,
            'missing_attendance_entry': missing_rows,
        }
        if request.query_params.get('export') == 'csv':
            import csv
            from django.http import HttpResponse as HttpResponseBase
            resp = HttpResponseBase(content_type='text/csv')
            resp['Content-Disposition'] = f'attachment; filename="daily_absent_{date_param}.csv"'
            writer = csv.writer(resp)
            writer.writerow(['Status', 'Student', 'District', 'Service type', 'Home phone', 'Mother cell', 'Father cell', 'Email', 'Absence reason', 'Notes'])
            for row in absent_rows:
                writer.writerow(['Absent', row['student_name'], row['district'], row['service_type'], row['home_phone'], row['mother_cell'], row['father_cell'], row['email'], row['absence_reason'], row['notes']])
            for row in missing_rows:
                writer.writerow(['Missing entry', row['student_name'], row['district'], row['service_type'], row['home_phone'], row['mother_cell'], row['father_cell'], row['email'], '', ''])
            return resp
        return Response(result)
