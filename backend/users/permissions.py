"""
Custom permissions for RBAC.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission check for admin role (or superuser)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'is_superuser', False) or request.user.role == 'admin'


class IsAdminOrEditor(permissions.BasePermission):
    """Permission check for admin or editor role (or superuser)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'is_superuser', False) or request.user.role in ['admin', 'editor']


class IsViewerOrAbove(permissions.BasePermission):
    """Permission check for viewer role or above."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
