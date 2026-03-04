"""
Serializers for compliance models.
"""
from rest_framework import serializers
from .models import ConsentRecord, DisclosureLog, AccessLog, SecurityEvent
from sessions.serializers import StudentSerializer


class ConsentRecordSerializer(serializers.ModelSerializer):
    """Serializer for ConsentRecord."""
    student = StudentSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ConsentRecord
        fields = [
            'id', 'student', 'student_id', 'consent_type', 'status',
            'parent_signature', 'date_signed', 'expiration_date', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DisclosureLogSerializer(serializers.ModelSerializer):
    """Serializer for DisclosureLog."""
    student = StudentSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True, allow_null=True)
    
    class Meta:
        model = DisclosureLog
        fields = [
            'id', 'student', 'student_id', 'site', 'site_name', 'disclosed_to', 'purpose',
            'date_disclosed', 'user', 'user_email', 'consent_obtained',
            'consent_record', 'notes'
        ]
        read_only_fields = ['id', 'date_disclosed']


class AccessLogSerializer(serializers.ModelSerializer):
    """Serializer for AccessLog."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True, allow_null=True)
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'user', 'user_email', 'site', 'site_name', 'record_type', 'record_id',
            'action', 'ip_address', 'user_agent', 'timestamp',
            'purpose', 'legitimate_interest', 'changes'
        ]
        read_only_fields = ['id', 'timestamp']


class SecurityEventSerializer(serializers.ModelSerializer):
    """Serializer for SecurityEvent."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    resolved_by_email = serializers.EmailField(source='resolved_by.email', read_only=True)
    
    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'event_type', 'user', 'user_email', 'ip_address',
            'details', 'severity', 'timestamp', 'resolved',
            'resolved_at', 'resolved_by', 'resolved_by_email', 'resolution_notes'
        ]
        read_only_fields = ['id', 'timestamp']
