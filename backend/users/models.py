"""
User models for authentication and authorization.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice


class User(AbstractUser):
    """Custom user model with OAuth and MFA support."""
    
    email = models.EmailField(unique=True)
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    oauth_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Site restriction: null = can access all sites (admin); set = restricted to that site
    site = models.ForeignKey(
        'academic_sessions.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    # Roles
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    
    # Security fields
    mfa_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    security_clearance_level = models.IntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email
    
    @property
    def is_locked(self):
        """Check if account is locked."""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration."""
        from django.utils import timezone
        from datetime import timedelta
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
    
    def increment_failed_login(self):
        """Increment failed login attempts and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account()
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    
    def reset_failed_login(self):
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def has_mfa_device(self):
        """Check if user has MFA device configured."""
        return TOTPDevice.objects.filter(user=self, confirmed=True).exists()
