"""
URLs for compliance endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'access-logs', views.AccessLogViewSet, basename='access-log')
router.register(r'disclosures', views.DisclosureLogViewSet, basename='disclosure')
router.register(r'consents', views.ConsentRecordViewSet, basename='consent')
router.register(r'security-events', views.SecurityEventViewSet, basename='security-event')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/access/', views.AccessReportView.as_view(), name='access-report'),
    path('reports/disclosures/', views.DisclosureReportView.as_view(), name='disclosure-report'),
]
