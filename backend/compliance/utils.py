"""
Utility functions for compliance and audit logging.
"""
from django.contrib.auth import get_user_model
from .models import AccessLog, SecurityEvent
from django.utils import timezone

User = get_user_model()


def log_access(user, record_type, record_id, action, request=None, changes=None, purpose=None, site_id=None):
    """Log access to PHI/educational records. site_id used for multi-site report filtering."""
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AccessLog.objects.create(
        user=user,
        site_id=site_id,
        record_type=record_type,
        record_id=record_id,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        purpose=purpose or 'routine_access',
        legitimate_interest=True,
        changes=changes
    )


def log_security_event(event_type, user=None, ip_address=None, details=None, severity='medium'):
    """Log security event."""
    SecurityEvent.objects.create(
        event_type=event_type,
        user=user,
        ip_address=ip_address,
        details=details or {},
        severity=severity
    )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
