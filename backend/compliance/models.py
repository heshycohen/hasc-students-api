"""
Compliance models for HIPAA and FERPA.
"""
from django.db import models
from django.contrib.auth import get_user_model
from sessions.models import Student

User = get_user_model()


class ConsentRecord(models.Model):
    """FERPA consent management."""
    
    CONSENT_TYPE_CHOICES = [
        ('directory_info', 'Directory Information'),
        ('disclosure', 'Disclosure'),
        ('research', 'Research'),
    ]
    
    STATUS_CHOICES = [
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('pending', 'Pending'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='consent_records'
    )
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parent_signature = models.TextField(blank=True, null=True)
    date_signed = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consent_records'
        ordering = ['-date_signed']
        indexes = [
            models.Index(fields=['student', 'consent_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.get_consent_type_display()} ({self.get_status_display()})"


class DisclosureLog(models.Model):
    """FERPA disclosure tracking."""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='disclosures'
    )
    site = models.ForeignKey(
        'academic_sessions.Site',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='disclosure_logs',
        help_text='Site of student (for report filtering).',
    )
    disclosed_to = models.CharField(max_length=200, help_text='Name/organization receiving disclosure')
    purpose = models.TextField(help_text='Purpose of disclosure')
    date_disclosed = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='disclosures_made'
    )
    consent_obtained = models.BooleanField(default=False)
    consent_record = models.ForeignKey(
        ConsentRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disclosures'
    )
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'disclosure_log'
        ordering = ['-date_disclosed']
        indexes = [
            models.Index(fields=['student', 'date_disclosed']),
            models.Index(fields=['user', 'date_disclosed']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.disclosed_to} ({self.date_disclosed.date()})"


class AccessLog(models.Model):
    """Comprehensive access logging for HIPAA/FERPA."""
    
    ACTION_CHOICES = [
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('print', 'Print'),
    ]
    
    RECORD_TYPE_CHOICES = [
        ('student', 'Student'),
        ('employee', 'Employee'),
        ('session', 'Session'),
        ('api', 'API'),
        ('report', 'Report'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='access_logs'
    )
    site = models.ForeignKey(
        'academic_sessions.Site',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='access_logs',
        help_text='Site context (for report filtering).',
    )
    record_type = models.CharField(max_length=50, choices=RECORD_TYPE_CHOICES)
    record_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=200, blank=True, null=True)
    legitimate_interest = models.BooleanField(default=True)
    changes = models.JSONField(null=True, blank=True, help_text='JSON of changed fields')
    
    class Meta:
        db_table = 'access_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['record_type', 'record_id']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} {self.get_record_type_display()} ({self.timestamp})"


class SecurityEvent(models.Model):
    """Security monitoring events."""
    
    EVENT_TYPE_CHOICES = [
        ('failed_login', 'Failed Login'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('data_export', 'Data Export'),
        ('data_deletion', 'Data Deletion'),
        ('account_locked', 'Account Locked'),
        ('mfa_failed', 'MFA Failed'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('configuration_change', 'Configuration Change'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(help_text='Event details in JSON format')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_events'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['severity', 'resolved']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.get_severity_display()} ({self.timestamp})"
