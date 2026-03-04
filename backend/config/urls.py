"""
URL configuration for School Year Management System.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.views import profile_view
from config.views import api_root, serve_logo, serve_spa, health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health),  # Azure App Service health check (GET/HEAD /health)
    path('api/', api_root),
    path('api/health/', health),  # health check for Front Door / LB (no PHI)
    path('logo.png', serve_logo, {'filename': 'logo.png'}),
    path('logo.svg', serve_logo, {'filename': 'logo.svg'}),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/auth/', include('users.urls')),
    path('api/sessions/', include('sessions.urls')),
    path('api/compliance/', include('compliance.urls')),
    path('accounts/profile/', profile_view, name='account_profile'),
    path('accounts/', include('allauth.urls')),
    # SPA catch-all last: non-API paths serve index.html (Option A: Django serves React build)
    re_path(r'^.*$', serve_spa),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
