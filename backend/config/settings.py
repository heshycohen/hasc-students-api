"""
Django settings for School Year Management System.
HIPAA and FERPA compliant configuration.
"""

import os
import warnings
from pathlib import Path
import environ

# Silence pkg_resources deprecation warning from rest_framework_simplejwt (third-party)
warnings.filterwarnings('ignore', category=UserWarning, message='.*pkg_resources is deprecated.*')

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    DB_NAME=(str, 'rock_access'),
    DB_USER=(str, 'postgres'),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, 'localhost'),
    DB_PORT=(str, '5432'),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


def _parse_comma_separated_list(value, default=None):
    """Parse comma-separated env string into list of stripped non-empty strings."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default if default is not None else []
    if isinstance(value, list):
        return [x.strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value).split(',') if x.strip()]


# Security Settings
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')
# DEBUG must be False in production. Prefer DJANGO_DEBUG, fall back to DEBUG env; both default to False.
DEBUG = env.bool('DJANGO_DEBUG', default=env('DEBUG', default=False))
# Azure App Service: include students-api.azurewebsites.net, students-api.hasc.net (or set ALLOWED_HOSTS env)
_allowed_hosts_default = [
    'localhost', '127.0.0.1',
    'students-api.azurewebsites.net', 'students-api.hasc.net',
]
ALLOWED_HOSTS = _parse_comma_separated_list(env('ALLOWED_HOSTS', default=None), _allowed_hosts_default)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.microsoft',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'cryptography',
    'auditlog',
    'drf_spectacular',
    'channels',
    
    # Local apps (sessions.apps.SessionsConfig uses label 'academic_sessions' to avoid clash with django.contrib.sessions)
    'users',
    'sessions.apps.SessionsConfig',
    'compliance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'users.middleware.CsrfExemptAPIMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'users.middleware.SessionTimeoutMiddleware',
    'users.middleware.AccessControlMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Channels configuration for WebSocket support (Azure Cache for Redis: use REDIS_URL)
_redis_url = env('REDIS_URL', default='')
if _redis_url:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [_redis_url]},
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(env('REDIS_HOST', default='127.0.0.1'), env.int('REDIS_PORT', default=6379))],
            },
        },
    }

# Database: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT from env (e.g. Azure: hasc-students-prod-pg, db: students)
_db_host = env('DB_HOST', default='localhost')
_db_options = {'sslmode': 'disable' if _db_host in ('localhost', '127.0.0.1') else 'require'}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': _db_host,
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': _db_options,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files for Azure App Service (WhiteNoise serves /static/ in production; run collectstatic on deploy)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# WhiteNoise: compress and cache static files (Azure does not serve static from disk by default)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
# React build dir for SPA catch-all (when Django serves the frontend)
FRONTEND_BUILD_DIR = env('FRONTEND_BUILD_DIR', default=str(BASE_DIR.parent / 'frontend' / 'build'))
# Include SPA static assets in collectstatic (Option A: CRA build/static → /static/)
_spa_static = os.path.join(FRONTEND_BUILD_DIR, 'static')
STATICFILES_DIRS = [('static', _spa_static)] if os.path.isdir(_spa_static) else []

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Site ID for allauth
SITE_ID = 1

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.OptionalPageSizePagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',
        'anon': '100/hour',
    },
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Email (use console backend in dev to avoid SMTP connection refused)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = env('EMAIL_HOST', default='localhost')
    EMAIL_PORT = env.int('EMAIL_PORT', default=25)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# Allauth Settings
AUTHENTICATION_BACKENDS = (
    'users.backends.EmailBackend',  # JWT login with email
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

ACCOUNT_EMAIL_REQUIRED = True
# In dev, avoid SMTP: no server on localhost. Use 'optional' or 'none'. In production use 'mandatory' with real SMTP.
ACCOUNT_EMAIL_VERIFICATION = 'optional' if DEBUG else env('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_ADAPTER = 'users.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'

# After successful login (including Allauth Microsoft), redirect to SSO success to mint JWT for SPA
LOGIN_REDIRECT_URL = '/api/auth/sso/success/'

# OAuth Providers (Microsoft: single-tenant HASC; scopes openid, email, profile)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
    'microsoft': {
        'TENANT': env('AZURE_AD_TENANT_ID', default='common'),
        'SCOPE': ['openid', 'email', 'profile'],
    },
}

# Security Settings (production: healthcare-grade; behind App Service / Front Door)
# Force HTTPS and secure cookies in production (env: DEBUG=False, SECRET_KEY, ALLOWED_HOSTS, FRONTEND_URL)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True if not DEBUG else False
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=3600 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_SECURE = True if not DEBUG else False
CSRF_COOKIE_SECURE = True if not DEBUG else False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
# CSRF: from env, or production defaults (FRONTEND_URL + https://students.hasc.net), or dev defaults
_frontend_url = env('FRONTEND_URL', default='').strip().rstrip('/')
_production_origins = [o for o in [_frontend_url, 'https://students.hasc.net'] if o]
_csrf_default = (
    _production_origins
    if (not DEBUG and _production_origins)
    else [
        'http://localhost:8000', 'http://127.0.0.1:8000',
        'http://localhost:3000', 'http://127.0.0.1:3000',
    ]
)
CSRF_TRUSTED_ORIGINS = _parse_comma_separated_list(env('CSRF_TRUSTED_ORIGINS', default=None), _csrf_default)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Session Timeout (15 minutes for HIPAA compliance)
SESSION_COOKIE_AGE = 900  # 15 minutes
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CORS: production uses FRONTEND_URL + https://students.hasc.net; else env or dev origins
_DEV_CORS_ORIGINS = [
    'http://localhost:3000', 'http://127.0.0.1:3000',
    'http://localhost:3001', 'http://127.0.0.1:3001',
    'http://localhost:5173', 'http://127.0.0.1:5173',
    'http://localhost:8080', 'http://127.0.0.1:8080',
    'http://192.168.176.1:3000',
]
_cors_origins_env = env('CORS_ALLOWED_ORIGINS', default=None)
if _cors_origins_env is not None:
    _cors_default = _parse_comma_separated_list(_cors_origins_env, None) or _DEV_CORS_ORIGINS
elif not DEBUG and _production_origins:
    _cors_default = _production_origins
else:
    _cors_default = _DEV_CORS_ORIGINS
_EXTRA = _parse_comma_separated_list(env('CORS_EXTRA_ORIGINS', default=None), [])
CORS_ALLOWED_ORIGINS = _cors_default + _EXTRA
CORS_ALLOW_CREDENTIALS = True

# Audit Log Settings
AUDITLOG_INCLUDE_ALL_MODELS = True
AUDITLOG_EXCLUDE_TRACKING_FIELDS = ['created_at', 'updated_at']

# Encryption Settings
ENCRYPTION_KEY = env('ENCRYPTION_KEY', default='')
KMS_PROVIDER = env('KMS_PROVIDER', default='local')  # local, aws, azure, gcp

# Azure Key Vault Settings (for envelope encryption)
AZURE_KEY_VAULT_URL = env('AZURE_KEY_VAULT_URL', default='')
AZURE_KEY_NAME = env('AZURE_KEY_NAME', default='')
AZURE_TENANT_ID = env('AZURE_TENANT_ID', default='')
AZURE_CLIENT_ID = env('AZURE_CLIENT_ID', default='')
AZURE_CLIENT_SECRET = env('AZURE_CLIENT_SECRET', default='')

# AWS KMS (optional; set KMS_PROVIDER=aws)
AWS_KMS_KEY_ID = env('AWS_KMS_KEY_ID', default='')
AWS_REGION = env('AWS_REGION', default='us-east-1')
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')

# GCP KMS (optional; set KMS_PROVIDER=gcp)
GCP_PROJECT_ID = env('GCP_PROJECT_ID', default='')
GCP_LOCATION = env('GCP_LOCATION', default='us-east1')
GCP_KEY_RING = env('GCP_KEY_RING', default='')
GCP_KEY_NAME = env('GCP_KEY_NAME', default='')
GCP_CREDENTIALS_PATH = env('GCP_CREDENTIALS_PATH', default='')

# Microsoft (Azure AD / Entra ID) login for HASC single-tenant
AZURE_AD_TENANT_ID = env('AZURE_AD_TENANT_ID', default='')
AZURE_AD_CLIENT_ID = env('AZURE_AD_CLIENT_ID', default='')
AZURE_AD_CLIENT_SECRET = env('AZURE_AD_CLIENT_SECRET', default='')
FRONTEND_URL = env('FRONTEND_URL', default='').strip().rstrip('/')
ACCOUNT_LOGOUT_REDIRECT_URL = (FRONTEND_URL + '/login') if FRONTEND_URL else '/accounts/profile/'
# Optional: comma-separated allowed email domains (e.g. hasc.net); enforced on social login
ALLOWED_EMAIL_DOMAINS = _parse_comma_separated_list(env('ALLOWED_EMAIL_DOMAINS', default=None), None)
# When True, /api/auth/token/ (email+password) returns 403; use Microsoft sign-in only.
# ALLOW_PASSWORD_LOGIN=False in prod is equivalent to ONLY_MICROSOFT_LOGIN=True.
ONLY_MICROSOFT_LOGIN = env.bool('ONLY_MICROSOFT_LOGIN', default=not env.bool('ALLOW_PASSWORD_LOGIN', True))

# Envelope Encryption Settings
ENVELOPE_ENCRYPTION_THRESHOLD = env.int('ENVELOPE_ENCRYPTION_THRESHOLD', default=4096)  # Bytes - use envelope encryption for data >= this size

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'application.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 1024 * 1024 * 100,  # 100 MB
            'backupCount': 100,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'audit': {
            'handlers': ['audit'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
