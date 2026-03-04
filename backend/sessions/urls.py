"""
URLs for session management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sites', views.SiteViewSet, basename='site')
router.register(r'sessions', views.AcademicSessionViewSet, basename='session')
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'classrooms', views.ClassroomViewSet, basename='classroom')
router.register(r'funding-codes', views.FundingCodeViewSet, basename='fundingcode')
router.register(r'school-districts', views.SchoolDistrictViewSet, basename='schooldistrict')
router.register(r'incidents', views.IncidentViewSet, basename='incident')
router.register(r'absence-reasons', views.AbsenceReasonViewSet, basename='absencereason')
router.register(r'attendance', views.AttendanceRecordViewSet, basename='attendancerecord')

urlpatterns = [
    path('', include(router.urls)),
    path('sessions/<int:pk>/copy/', views.CopySessionView.as_view(), name='copy-session'),
    path('current-session/', views.CurrentSessionView.as_view(), name='current-session'),
    path('roster/', views.StudentRosterView.as_view(), name='student-roster'),
    path('medical-due-report/', views.MedicalDueReportView.as_view(), name='medical-due-report'),
]
