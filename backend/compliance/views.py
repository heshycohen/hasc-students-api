"""
Views for compliance and audit logging.
Multi-site: site-bound users see only their site; admin can filter by site/sites or see all.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from .models import AccessLog, DisclosureLog, ConsentRecord, SecurityEvent
from .serializers import (
    AccessLogSerializer, DisclosureLogSerializer,
    ConsentRecordSerializer, SecurityEventSerializer
)
from sessions.models import Site


def _report_site_ids(request):
    """
    Return list of site_ids to filter compliance data, or None for "all sites".
    - Site-bound user: [user.site_id]
    - Admin with site= or sites= param: those site ids (single or comma-separated)
    - Admin with no param: None (all sites)
    """
    user = request.user
    if getattr(user, 'site_id', None):
        return [user.site_id]
    site_param = request.query_params.get('site') or request.query_params.get('sites')
    if not site_param:
        return None
    ids = []
    for part in str(site_param).split(','):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            site = Site.objects.filter(slug=part).first()
            if site:
                ids.append(site.id)
    return ids if ids else None


class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for access logs (read-only). Filtered by site for site-bound users; admin can filter by site/sites."""
    queryset = AccessLog.objects.all()
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        user = self.request.user
        base = AccessLog.objects.all()
        if user.role != 'admin':
            base = base.filter(user=user)
        site_ids = _report_site_ids(self.request)
        if site_ids is not None:
            base = base.filter(site_id__in=site_ids)
        return base


class DisclosureLogViewSet(viewsets.ModelViewSet):
    """ViewSet for disclosure logs. Filtered by site; site set from student on create."""
    queryset = DisclosureLog.objects.all()
    serializer_class = DisclosureLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        base = DisclosureLog.objects.all()
        if user.role == 'admin':
            pass
        else:
            base = base.filter(user=user)
        site_ids = _report_site_ids(self.request)
        if site_ids is not None:
            base = base.filter(site_id__in=site_ids)
        return base
    
    def perform_create(self, serializer):
        from sessions.models import Student
        student_id = serializer.validated_data.get('student_id')
        site_id = None
        if student_id:
            student = Student.objects.select_related('session').filter(pk=student_id).first()
            if student and student.session:
                site_id = student.session.site_id
        serializer.save(user=self.request.user, site_id=site_id)


class ConsentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for consent records."""
    queryset = ConsentRecord.objects.all()
    serializer_class = ConsentRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        if user.role in ['admin', 'editor']:
            return ConsentRecord.objects.all()
        return ConsentRecord.objects.none()


class SecurityEventViewSet(viewsets.ModelViewSet):
    """ViewSet for security events."""
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a security event."""
        event = self.get_object()
        event.resolved = True
        event.resolved_at = timezone.now()
        event.resolved_by = request.user
        event.resolution_notes = request.data.get('notes', '')
        event.save()
        return Response({'detail': 'Event resolved'})


class AccessReportView(APIView):
    """Generate access report for compliance. Admin can filter by site= or sites= (comma-separated)."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        queryset = AccessLog.objects.all()
        site_ids = _report_site_ids(request)
        if site_ids is not None:
            queryset = queryset.filter(site_id__in=site_ids)
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        from django.db.models import Count
        summary = queryset.values('action').annotate(count=Count('id'))
        return Response({
            'total_accesses': queryset.count(),
            'summary': list(summary),
            'logs': AccessLogSerializer(queryset[:100], many=True).data
        })


class DisclosureReportView(APIView):
    """Generate disclosure report for FERPA compliance. Admin can filter by site= or sites=."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        queryset = DisclosureLog.objects.all()
        site_ids = _report_site_ids(request)
        if site_ids is not None:
            queryset = queryset.filter(site_id__in=site_ids)
        if start_date:
            queryset = queryset.filter(date_disclosed__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_disclosed__lte=end_date)
        return Response({
            'total_disclosures': queryset.count(),
            'disclosures': DisclosureLogSerializer(queryset, many=True).data
        })
