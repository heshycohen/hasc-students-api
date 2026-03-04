"""
URLs for user authentication.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from . import views_sso
from .serializers import CustomTokenObtainPairSerializer


router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('sso/success/', views_sso.SSOSuccessView.as_view(), name='sso_success'),
    path('microsoft/login/', views_sso.MicrosoftLoginRedirectView.as_view(), name='microsoft_login'),
    path('microsoft/callback/', views.MicrosoftCallbackView.as_view(), name='microsoft_callback'),
    path('mfa/setup/', views.MFASetupView.as_view(), name='mfa_setup'),
    path('mfa/verify/', views.MFAVerifyView.as_view(), name='mfa_verify'),
]
