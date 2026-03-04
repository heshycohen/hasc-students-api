"""
Custom adapters for django-allauth.
Enforces HASC single-tenant (tid) and optional ALLOWED_EMAIL_DOMAINS on Microsoft login.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.conf import settings
from django.http import HttpResponseForbidden


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for OAuth."""

    def is_open_for_signup(self, request):
        """Control whether new signups are allowed."""
        # Only allow signups through OAuth
        return False

    def save_user(self, request, user, form, commit=True):
        """Save user with OAuth information."""
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter: tenant + email domain enforcement; allow OAuth signups."""

    def is_open_for_signup(self, request, sociallogin):
        """Allow OAuth signups."""
        return True

    def pre_social_login(self, request, sociallogin):
        """Enforce HASC single-tenant and optional ALLOWED_EMAIL_DOMAINS on Microsoft login."""
        if sociallogin.account.provider != 'microsoft':
            return
        user = sociallogin.user
        email = (user.email or '').strip().lower()
        if not email:
            raise ImmediateHttpResponse(HttpResponseForbidden('No email from provider.'))

        # Optional: enforce tenant id if present in extra_data (Microsoft Graph may not provide it)
        allowed_tid = (getattr(settings, 'AZURE_AD_TENANT_ID', None) or '').strip()
        if allowed_tid:
            tid = (sociallogin.account.extra_data or {}).get('tid') or (sociallogin.account.extra_data or {}).get('tenantId')
            if tid and tid != allowed_tid:
                raise ImmediateHttpResponse(HttpResponseForbidden('Unauthorized tenant.'))

        # Enforce allowed email domains when configured
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', None)
        if allowed_domains:
            domain = email.split('@')[-1] if '@' in email else ''
            if domain not in allowed_domains:
                raise ImmediateHttpResponse(HttpResponseForbidden('Unauthorized email domain.'))
