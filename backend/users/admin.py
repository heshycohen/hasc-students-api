from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = ['email', 'username', 'role', 'mfa_enabled', 'is_active', 'last_login']
    list_filter = ['role', 'mfa_enabled', 'is_active', 'is_staff', 'is_superuser']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('OAuth', {'fields': ('oauth_provider', 'oauth_id')}),
        ('Role & Permissions', {'fields': ('role',)}),
        ('Security', {'fields': ('mfa_enabled', 'last_login_ip', 'failed_login_attempts', 
                                'account_locked_until', 'security_clearance_level')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('OAuth', {'fields': ('oauth_provider', 'oauth_id')}),
        ('Role & Permissions', {'fields': ('role',)}),
    )
