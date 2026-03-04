from django.contrib import admin
from .models import AcademicSession, Student, Employee


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'session_type', 'start_date', 'end_date', 'is_active']
    list_filter = ['session_type', 'is_active']
    search_fields = ['name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'session', 'status', 'enrollment_date']
    list_filter = ['status', 'session', 'directory_info_opt_out']
    search_fields = ['first_name', 'last_name', 'parent_email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'position', 'session']
    list_filter = ['session']
    search_fields = ['first_name', 'last_name', 'email']
