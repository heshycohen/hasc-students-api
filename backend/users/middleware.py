"""
Middleware for session timeout and access control.
"""
import time
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth import logout
from django.shortcuts import redirect
from compliance.models import AccessLog, SecurityEvent


class CsrfExemptAPIMiddleware:
    """
    Exempt /api/ from CSRF so the SPA (JWT auth) can POST without a CSRF token.
    Must run before CsrfViewMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/api/'):
            view_func.csrf_exempt = True
        return None


class SessionTimeoutMiddleware:
    """Middleware to enforce 15-minute session timeout (HIPAA requirement)."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Check session timeout
            session_key = request.session.session_key
            if session_key:
                try:
                    session = Session.objects.get(session_key=session_key)
                    decoded = session.get_decoded()
                    last_activity = decoded.get('last_activity')
                    current_time = time.time()
                    # Only expire if last_activity was set and is older than 15 min
                    # (missing/0 means first request after login – don't treat as expired)
                    if last_activity is not None and last_activity and (current_time - last_activity > 900):
                        # Session expired
                        logout(request)
                        if request.path.startswith('/api/'):
                            from rest_framework.response import Response
                            from rest_framework import status
                            return Response(
                                {'detail': 'Session expired. Please log in again.'},
                                status=status.HTTP_401_UNAUTHORIZED
                            )
                        return redirect('/accounts/login/?expired=1')
                    # Update last activity (or set it on first request after login)
                    request.session['last_activity'] = current_time
                except Session.DoesNotExist:
                    pass
        
        response = self.get_response(request)
        return response


class AccessControlMiddleware:
    """Middleware for RBAC/ABAC access control."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if account is locked
            if request.user.is_locked:
                logout(request)
                if request.path.startswith('/api/'):
                    from rest_framework.response import Response
                    from rest_framework import status
                    return Response(
                        {'detail': 'Account is locked. Please contact administrator.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                return redirect('/accounts/login/?locked=1')
            
            # Log API access
            if request.path.startswith('/api/'):
                self._log_access(request)
        
        response = self.get_response(request)
        return response
    
    def _log_access(self, request):
        """Log API access for audit purposes."""
        try:
            AccessLog.objects.create(
                user=request.user,
                record_type='api',
                record_id=None,
                action='view',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                purpose='api_access',
                legitimate_interest=True,
            )
        except Exception:
            # Don't fail request if logging fails
            pass
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
