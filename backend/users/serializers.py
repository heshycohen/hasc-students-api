"""
Serializers for user models.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept 'email' in the request body (frontend sends email, not username)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']
        self.fields['email'] = serializers.EmailField(write_only=True, required=True)



class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model. Includes site for multi-site (site-bound vs admin)."""
    site_id = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'site_id', 'site_name', 'is_admin',
            'mfa_enabled', 'is_active', 'last_login',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_login', 'created_at', 'updated_at']

    def get_site_id(self, obj):
        return obj.site_id if getattr(obj, 'site_id', None) else None

    def get_site_name(self, obj):
        return obj.site.name if getattr(obj, 'site', None) else None

    def get_is_admin(self, obj):
        return obj.role == 'admin'
