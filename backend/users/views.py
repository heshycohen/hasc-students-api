"""
Views for user authentication and management.
"""
import secrets
from urllib.parse import urlencode

import requests
import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import login as otp_login
from .models import User
from .serializers import UserSerializer, CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Email+password JWT login. Returns 403 if ONLY_MICROSOFT_LOGIN is True."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        if getattr(settings, 'ONLY_MICROSOFT_LOGIN', False):
            return Response(
                {'detail': 'Password sign-in is disabled. Use Sign in with Microsoft.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().post(request, *args, **kwargs)


@login_required
def profile_view(request):
    """Simple post-login page when using Django session login (/accounts/login/)."""
    return render(request, 'account/profile.html', {'user': request.user})


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Return the currently authenticated user (for SPA / JWT). Includes site_id, site_name, is_admin for multi-site."""
        user = User.objects.select_related('site').get(pk=request.user.pk)
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class MFASetupView(APIView):
    """View to set up MFA for a user."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create or get MFA device."""
        user = request.user
        
        # Check if device already exists
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device:
            return Response({
                'detail': 'MFA already configured',
                'device_id': device.id
            })
        
        # Create new device
        device = TOTPDevice.objects.create(user=user, name='Default')
        device.save()
        
        # Get provisioning URI for QR code
        url = device.config_url
        
        return Response({
            'device_id': device.id,
            'provisioning_url': url,
            'secret': device.bin_key.hex() if not device.confirmed else None
        })


class MFAVerifyView(APIView):
    """View to verify MFA token."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Verify MFA token and enable MFA."""
        token = request.data.get('token')
        device_id = request.data.get('device_id')
        
        if not token or not device_id:
            return Response(
                {'detail': 'Token and device_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = TOTPDevice.objects.get(id=device_id, user=request.user)
        except TOTPDevice.DoesNotExist:
            return Response(
                {'detail': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if device.verify_token(token):
            if not device.confirmed:
                device.confirmed = True
                device.save()
                request.user.mfa_enabled = True
                request.user.save()
            
            # Log user in with OTP
            otp_login(request, device)
            
            return Response({
                'detail': 'MFA verified and enabled',
                'mfa_enabled': True
            })
        
        return Response(
            {'detail': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


# --- Microsoft (Azure AD) OAuth for HASC single-tenant ---

def _microsoft_config():
    """Return Azure AD config; empty dict if not configured."""
    tenant = getattr(settings, 'AZURE_AD_TENANT_ID', None) or ''
    client_id = getattr(settings, 'AZURE_AD_CLIENT_ID', None) or ''
    secret = getattr(settings, 'AZURE_AD_CLIENT_SECRET', None) or ''
    frontend_url = (getattr(settings, 'FRONTEND_URL', None) or '').rstrip('/')
    if not all([tenant, client_id, secret, frontend_url]):
        return {}
    return {
        'tenant': tenant,
        'client_id': client_id,
        'client_secret': secret,
        'frontend_url': frontend_url,
        'authorize_url': f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
        'token_url': f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
        'jwks_uri': f'https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys',
        'issuer': f'https://login.microsoftonline.com/{tenant}/v2.0',
    }


class MicrosoftLoginView(APIView):
    """Redirect to Microsoft (Azure AD) authorize URL for HASC tenant. No auth required."""
    permission_classes = [AllowAny]

    def get(self, request):
        config = _microsoft_config()
        if not config:
            return Response(
                {'detail': 'Microsoft login is not configured (AZURE_AD_*, FRONTEND_URL).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        redirect_uri = request.build_absolute_uri('/api/auth/microsoft/callback/')
        state = secrets.token_urlsafe(32)
        request.session['microsoft_oauth_state'] = state
        params = {
            'client_id': config['client_id'],
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'state': state,
            'response_mode': 'query',
        }
        url = config['authorize_url'] + '?' + urlencode(params)
        return redirect(url)


class MicrosoftCallbackView(APIView):
    """Exchange authorization code for tokens, validate ID token (HASC tenant), create/link User, issue JWT, redirect to SPA."""
    permission_classes = [AllowAny]

    def get(self, request):
        config = _microsoft_config()
        if not config:
            return Response(
                {'detail': 'Microsoft login is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        code = request.GET.get('code')
        state = request.GET.get('state')
        if not code:
            error = request.GET.get('error_description') or request.GET.get('error') or 'Missing code'
            return redirect(config['frontend_url'] + '/login?error=' + requests.utils.quote(error))

        saved_state = request.session.pop('microsoft_oauth_state', None)
        if not state or state != saved_state:
            return redirect(config['frontend_url'] + '/login?error=invalid_state')

        redirect_uri = request.build_absolute_uri('/api/auth/microsoft/callback/')
        token_data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        resp = requests.post(config['token_url'], data=token_data, headers={'Accept': 'application/json'}, timeout=15)
        if resp.status_code != 200:
            return redirect(config['frontend_url'] + '/login?error=token_exchange_failed')
        data = resp.json()
        id_token = data.get('id_token')
        if not id_token:
            return redirect(config['frontend_url'] + '/login?error=no_id_token')

        try:
            jwks_client = PyJWKClient(config['jwks_uri'])
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            payload = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=['RS256'],
                audience=config['client_id'],
                issuer=config['issuer'],
            )
        except Exception:
            return redirect(config['frontend_url'] + '/login?error=invalid_id_token')

        tid = payload.get('tid')
        if tid != config['tenant']:
            return redirect(config['frontend_url'] + '/login?error=wrong_tenant')

        email = (payload.get('email') or payload.get('preferred_username') or '').strip().lower()
        if not email:
            return redirect(config['frontend_url'] + '/login?error=no_email')
        oid = payload.get('oid') or payload.get('sub') or ''

        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=secrets.token_urlsafe(32),
            )
            user.set_unusable_password()
            user.save()
        user.oauth_provider = 'microsoft'
        user.oauth_id = oid
        user.save(update_fields=['oauth_provider', 'oauth_id'])

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)
        frontend = config['frontend_url']
        redirect_to = f"{frontend}/login/callback?access_token={requests.utils.quote(access)}&refresh_token={requests.utils.quote(refresh_str)}"
        return redirect(redirect_to)
