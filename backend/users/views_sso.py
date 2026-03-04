"""
SSO success view and Microsoft login redirect for Allauth-based flow.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken


class MicrosoftLoginRedirectView(View):
    """
    GET /api/auth/microsoft/login/
    Redirects to allauth's Microsoft provider login URL so the SPA has a stable API entry point.
    """
    def get(self, request):
        login_url = request.build_absolute_uri('/accounts/microsoft/login/')
        return HttpResponseRedirect(login_url)


class SSOSuccessView(View):
    """
    GET /api/auth/sso/success/
    Requires session-authenticated user (after Allauth Microsoft login).
    Mints SimpleJWT access + refresh, redirects to SPA callback with tokens in fragment.
    If not authenticated, redirects to frontend login page.
    """
    def get(self, request):
        if not request.user.is_authenticated:
            frontend_url = (getattr(settings, 'FRONTEND_URL', None) or '').strip().rstrip('/')
            if frontend_url:
                return HttpResponseRedirect(f"{frontend_url}/login")
            return HttpResponse('Unauthorized', status=401)
        frontend_url = (getattr(settings, 'FRONTEND_URL', None) or '').strip().rstrip('/')
        if not frontend_url:
            return HttpResponse('FRONTEND_URL not configured', status=503)
        user = request.user
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)
        params = {'access_token': access, 'refresh_token': refresh_str}
        redirect_url = f"{frontend_url}/login/callback#{urlencode(params)}"
        return HttpResponseRedirect(redirect_url)
