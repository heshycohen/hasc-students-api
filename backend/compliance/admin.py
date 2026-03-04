from django.contrib import admin
from .models import ConsentRecord, DisclosureLog, AccessLog, SecurityEvent


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'consent_type', 'status', 'date_signed', 'expiration_date']
    list_filter = ['consent_type', 'status', 'date_signed']
    search_fields = ['student__first_name', 'student__last_name']


@admin.register(DisclosureLog)
class DisclosureLogAdmin(admin.ModelAdmin):
    list_display = ['student', 'disclosed_to', 'date_disclosed', 'user', 'consent_obtained']
    list_filter = ['date_disclosed', 'consent_obtained']
    search_fields = ['student__first_name', 'student__last_name', 'disclosed_to']


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_type', 'action', 'timestamp', 'ip_address']
    list_filter = ['action', 'record_type', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['timestamp']


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'severity', 'user', 'timestamp', 'resolved']
    list_filter = ['event_type', 'severity', 'resolved', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['timestamp']
