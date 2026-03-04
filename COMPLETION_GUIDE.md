# Step-by-Step Completion Guide

This guide provides detailed steps to complete all pending/incomplete items for HIPAA and FERPA compliance.

## Table of Contents

1. [Cloud KMS Integration](#1-cloud-kms-integration)
2. [Encryption at Rest (Database)](#2-encryption-at-rest-database)
3. [TLS 1.3 Configuration](#3-tls-13-configuration)
4. [MFA Enforcement](#4-mfa-enforcement)
5. [Audit Logging Configuration](#5-audit-logging-configuration)
6. [Backup Encryption](#6-backup-encryption)
7. [Access Controls Configuration](#7-access-controls-configuration)
8. [Business Associate Agreements](#8-business-associate-agreements)
9. [Incident Response Plan](#9-incident-response-plan)
10. [Security Monitoring](#10-security-monitoring)

---

## 1. Cloud KMS Integration

### Step 1.1: Install Required Packages

Add cloud KMS SDKs to `backend/requirements.txt`:

```bash
# Add these lines to backend/requirements.txt
boto3==1.34.0          # AWS KMS
azure-keyvault-keys==4.8.0  # Azure Key Vault
google-cloud-kms==2.21.0    # GCP KMS
```

Then install:
```bash
cd rock-access-web/backend
pip install -r requirements.txt
```

### Step 1.2: Update Environment Variables

Add to `.env` file (or `.env.example`):

```env
# KMS Configuration
KMS_PROVIDER=local  # Options: local, aws, azure, gcp

# AWS KMS (if using AWS)
AWS_KMS_KEY_ID=arn:aws:kms:region:account-id:key/key-id
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Azure Key Vault (if using Azure)
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net/
AZURE_KEY_NAME=your-key-name
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# GCP KMS (if using GCP)
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-east1
GCP_KEY_RING=your-key-ring
GCP_KEY_NAME=your-key-name
GCP_CREDENTIALS_PATH=/path/to/service-account.json
```

### Step 1.3: Implement AWS KMS

Update `backend/compliance/encryption.py`:

```python
def _encrypt_aws(self, value):
    """Encrypt using AWS KMS."""
    import boto3
    from django.conf import settings
    
    kms = boto3.client(
        'kms',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    response = kms.encrypt(
        KeyId=settings.AWS_KMS_KEY_ID,
        Plaintext=value.encode() if isinstance(value, str) else value
    )
    return base64.b64encode(response['CiphertextBlob']).decode()

def _decrypt_aws(self, encrypted_value):
    """Decrypt using AWS KMS."""
    import boto3
    from django.conf import settings
    
    kms = boto3.client(
        'kms',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    decoded = base64.b64decode(encrypted_value.encode())
    response = kms.decrypt(CiphertextBlob=decoded)
    return response['Plaintext'].decode()
```

### Step 1.4: Implement Azure Key Vault

Add to `backend/compliance/encryption.py`:

```python
def _encrypt_azure(self, value):
    """Encrypt using Azure Key Vault."""
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
    from azure.keyvault.keys import KeyClient
    from django.conf import settings
    
    credential = ClientSecretCredential(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET
    )
    
    key_client = KeyClient(vault_url=settings.AZURE_KEY_VAULT_URL, credential=credential)
    key = key_client.get_key(settings.AZURE_KEY_NAME)
    
    crypto_client = CryptographyClient(key, credential=credential)
    result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, value.encode() if isinstance(value, str) else value)
    return base64.b64encode(result.ciphertext).decode()

def _decrypt_azure(self, encrypted_value):
    """Decrypt using Azure Key Vault."""
    from azure.identity import ClientSecretCredential
    from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
    from azure.keyvault.keys import KeyClient
    from django.conf import settings
    
    credential = ClientSecretCredential(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET
    )
    
    key_client = KeyClient(vault_url=settings.AZURE_KEY_VAULT_URL, credential=credential)
    key = key_client.get_key(settings.AZURE_KEY_NAME)
    
    crypto_client = CryptographyClient(key, credential=credential)
    decoded = base64.b64decode(encrypted_value.encode())
    result = crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep, decoded)
    return result.plaintext.decode()
```

### Step 1.5: Implement GCP KMS

Add to `backend/compliance/encryption.py`:

```python
def _encrypt_gcp(self, value):
    """Encrypt using GCP KMS."""
    from google.cloud import kms
    from google.oauth2 import service_account
    from django.conf import settings
    import json
    
    credentials = service_account.Credentials.from_service_account_file(
        settings.GCP_CREDENTIALS_PATH
    )
    
    client = kms.KeyManagementServiceClient(credentials=credentials)
    key_name = client.crypto_key_path(
        settings.GCP_PROJECT_ID,
        settings.GCP_LOCATION,
        settings.GCP_KEY_RING,
        settings.GCP_KEY_NAME
    )
    
    plaintext = value.encode() if isinstance(value, str) else value
    encrypt_response = client.encrypt(request={'name': key_name, 'plaintext': plaintext})
    return base64.b64encode(encrypt_response.ciphertext).decode()

def _decrypt_gcp(self, encrypted_value):
    """Decrypt using GCP KMS."""
    from google.cloud import kms
    from google.oauth2 import service_account
    from django.conf import settings
    
    credentials = service_account.Credentials.from_service_account_file(
        settings.GCP_CREDENTIALS_PATH
    )
    
    client = kms.KeyManagementServiceClient(credentials=credentials)
    key_name = client.crypto_key_path(
        settings.GCP_PROJECT_ID,
        settings.GCP_LOCATION,
        settings.GCP_KEY_RING,
        settings.GCP_KEY_NAME
    )
    
    decoded = base64.b64decode(encrypted_value.encode())
    decrypt_response = client.decrypt(request={'name': key_name, 'ciphertext': decoded})
    return decrypt_response.plaintext.decode()
```

### Step 1.6: Update Settings

Add to `backend/config/settings.py`:

```python
# AWS KMS Settings
AWS_KMS_KEY_ID = env('AWS_KMS_KEY_ID', default='')
AWS_REGION = env('AWS_REGION', default='us-east-1')
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')

# Azure Key Vault Settings
AZURE_KEY_VAULT_URL = env('AZURE_KEY_VAULT_URL', default='')
AZURE_KEY_NAME = env('AZURE_KEY_NAME', default='')
AZURE_TENANT_ID = env('AZURE_TENANT_ID', default='')
AZURE_CLIENT_ID = env('AZURE_CLIENT_ID', default='')
AZURE_CLIENT_SECRET = env('AZURE_CLIENT_SECRET', default='')

# GCP KMS Settings
GCP_PROJECT_ID = env('GCP_PROJECT_ID', default='')
GCP_LOCATION = env('GCP_LOCATION', default='us-east1')
GCP_KEY_RING = env('GCP_KEY_RING', default='')
GCP_KEY_NAME = env('GCP_KEY_NAME', default='')
GCP_CREDENTIALS_PATH = env('GCP_CREDENTIALS_PATH', default='')
```

### Step 1.7: Test KMS Integration

Create test script `backend/compliance/tests/test_kms.py`:

```python
from django.test import TestCase
from compliance.encryption import encryption_service

class KMSTestCase(TestCase):
    def test_encryption_decryption(self):
        test_value = "Test SSN: 123-45-6789"
        encrypted = encryption_service.encrypt(test_value)
        decrypted = encryption_service.decrypt(encrypted)
        self.assertEqual(test_value, decrypted)
```

Run tests:
```bash
python manage.py test compliance.tests.test_kms
```

---

## 2. Encryption at Rest (Database)

### Step 2.1: Configure PostgreSQL Encryption

For **managed PostgreSQL** (AWS RDS, Azure Database, GCP Cloud SQL):

**AWS RDS:**
- Enable encryption at rest when creating the database instance
- Or enable on existing instance (requires snapshot/restore):
  1. Create snapshot
  2. Copy snapshot with encryption enabled
  3. Restore from encrypted snapshot

**Azure Database:**
- Enable "Transparent Data Encryption (TDE)" in Azure Portal
- Or use Azure Key Vault for key management

**GCP Cloud SQL:**
- Enable "Encryption at rest" during instance creation
- Uses Google-managed keys or Customer-Managed Encryption Keys (CMEK)

### Step 2.2: Update Docker Compose (Local Development)

Update `docker-compose.yml` to use encrypted volumes:

```yaml
services:
  db:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: rock_access
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: postgres -c ssl=on -c ssl_cert_file=/etc/ssl/certs/server.crt -c ssl_key_file=/etc/ssl/certs/server.key
```

### Step 2.3: Verify Encryption

Check database encryption status:

**PostgreSQL:**
```sql
-- Check if encryption is enabled
SHOW ssl;
SELECT * FROM pg_stat_ssl;
```

**AWS RDS:**
```bash
aws rds describe-db-instances --db-instance-identifier your-instance
# Check "StorageEncrypted": true
```

---

## 3. TLS 1.3 Configuration

### Step 3.1: Update Django Settings

Add to `backend/config/settings.py`:

```python
# TLS/SSL Settings
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Step 3.2: Configure Web Server (Nginx)

Create `nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # TLS 1.3 only (with 1.2 fallback for compatibility)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    
    # Modern cipher suites
    ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256';
    
    # SSL certificates
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Step 3.3: Update Docker Compose

Add Nginx service:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
```

### Step 3.4: Verify TLS 1.3

Test with:
```bash
openssl s_client -connect yourdomain.com:443 -tls1_3
# Or use online tools like SSL Labs: https://www.ssllabs.com/ssltest/
```

---

## 4. MFA Enforcement

### Step 4.1: Create MFA Enforcement Middleware

Create `backend/users/mfa_middleware.py`:

```python
from django.shortcuts import redirect
from django.contrib.auth import logout
from django_otp import user_has_device
from django_otp.decorators import otp_required
from rest_framework.response import Response
from rest_framework import status

class MFAEnforcementMiddleware:
    """Enforce MFA for all authenticated users."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_anonymous:
            # Skip for MFA setup/verification endpoints
            excluded_paths = [
                '/accounts/login/',
                '/accounts/logout/',
                '/api/auth/mfa/setup/',
                '/api/auth/mfa/verify/',
                '/admin/login/',
            ]
            
            if not any(request.path.startswith(path) for path in excluded_paths):
                # Check if MFA is required but not verified
                if not request.user.mfa_enabled:
                    # Redirect to MFA setup
                    if request.path.startswith('/api/'):
                        return Response(
                            {'detail': 'MFA setup required. Please configure MFA.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    return redirect('/accounts/mfa/setup/')
                
                # Check if MFA is enabled but not verified in this session
                if request.user.mfa_enabled and not request.session.get('mfa_verified', False):
                    if request.path.startswith('/api/'):
                        return Response(
                            {'detail': 'MFA verification required.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    return redirect('/accounts/mfa/verify/')
        
        response = self.get_response(request)
        return response
```

### Step 4.2: Add Middleware to Settings

Add to `backend/config/settings.py` MIDDLEWARE:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'users.mfa_middleware.MFAEnforcementMiddleware',  # Add this
]
```

### Step 4.3: Update MFA Setup View

Update `backend/users/views.py` to mark MFA as verified:

```python
@action(detail=False, methods=['post'])
def verify_mfa(self, request):
    """Verify MFA token."""
    token = request.data.get('token')
    device = TOTPDevice.objects.get(user=request.user)
    
    if device.verify_token(token):
        request.session['mfa_verified'] = True
        return Response({'status': 'verified'})
    return Response({'error': 'Invalid token'}, status=400)
```

### Step 4.4: Create Admin Command to Enforce MFA

Create `backend/users/management/commands/enforce_mfa.py`:

```python
from django.core.management.base import BaseCommand
from users.models import User

class Command(BaseCommand):
    help = 'Enforce MFA for all users'
    
    def handle(self, *args, **options):
        users = User.objects.filter(mfa_enabled=False)
        count = users.count()
        users.update(mfa_enabled=True)  # Or send notification instead
        self.stdout.write(f'Enabled MFA for {count} users')
```

### Step 4.5: Test MFA Enforcement

1. Login without MFA configured
2. Should redirect to MFA setup
3. Configure MFA
4. Verify access granted after MFA verification

---

## 5. Audit Logging Configuration

### Step 5.1: Configure Audit Log Models

The models are already created. Ensure they're registered in admin:

Update `backend/compliance/admin.py`:

```python
from django.contrib import admin
from .models import AccessLog, DisclosureLog, ConsentRecord, SecurityEvent

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_type', 'action', 'timestamp', 'ip_address']
    list_filter = ['action', 'record_type', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'record_type', 'record_id', 'action', 'timestamp']
    date_hierarchy = 'timestamp'

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'severity', 'user', 'timestamp', 'resolved']
    list_filter = ['event_type', 'severity', 'resolved', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['event_type', 'user', 'timestamp']
    date_hierarchy = 'timestamp'
```

### Step 5.2: Create Audit Log Signal Handlers

Create `backend/compliance/signals.py`:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from sessions.models import Student, Employee
from compliance.utils import log_access

@receiver(post_save, sender=Student)
def log_student_change(sender, instance, created, **kwargs):
    action = 'create' if created else 'update'
    # Get request from thread local or pass via signal
    log_access(
        user=None,  # Will be set from request context
        record_type='student',
        record_id=instance.id,
        action=action
    )

@receiver(post_delete, sender=Student)
def log_student_delete(sender, instance, **kwargs):
    log_access(
        user=None,
        record_type='student',
        record_id=instance.id,
        action='delete'
    )
```

### Step 5.3: Register Signals

Add to `backend/compliance/apps.py`:

```python
from django.apps import AppConfig

class ComplianceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'compliance'
    
    def ready(self):
        import compliance.signals
```

### Step 5.4: Configure Log Rotation

Update `backend/config/settings.py` LOGGING:

```python
LOGGING = {
    # ... existing config ...
    'handlers': {
        'audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 1024 * 1024 * 100,  # 100 MB
            'backupCount': 100,
            'formatter': 'json',
        },
        'audit_db': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit_db.log',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 100,
            'formatter': 'json',
        },
    },
    'loggers': {
        'audit': {
            'handlers': ['audit', 'audit_db'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Step 5.5: Create Audit Report View

Add to `backend/compliance/views.py`:

```python
@action(detail=False, methods=['get'])
def audit_report(self, request):
    """Generate audit report."""
    from datetime import datetime, timedelta
    from django.db.models import Count
    
    days = int(request.query_params.get('days', 30))
    start_date = datetime.now() - timedelta(days=days)
    
    logs = AccessLog.objects.filter(timestamp__gte=start_date)
    summary = logs.values('action').annotate(count=Count('id'))
    
    return Response({
        'period': f'Last {days} days',
        'total_accesses': logs.count(),
        'by_action': list(summary),
        'by_user': list(logs.values('user__email').annotate(count=Count('id'))[:10])
    })
```

---

## 6. Backup Encryption

### Step 6.1: Create Backup Script

Create `backend/management/commands/backup_encrypted.py`:

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import os
from datetime import datetime
from compliance.encryption import encryption_service

class Command(BaseCommand):
    help = 'Create encrypted database backup'
    
    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output file path')
    
    def handle(self, *args, **options):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = options.get('output') or f'backup_{timestamp}.sql'
        encrypted_file = f'{output_file}.encrypted'
        
        # Create database dump
        db_settings = settings.DATABASES['default']
        cmd = [
            'pg_dump',
            '-h', db_settings['HOST'],
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-F', 'c',  # Custom format
            '-f', output_file
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        subprocess.run(cmd, env=env, check=True)
        
        # Encrypt backup
        with open(output_file, 'rb') as f:
            data = f.read()
        
        encrypted_data = encryption_service.encrypt(data.decode('latin-1'))
        
        with open(encrypted_file, 'w') as f:
            f.write(encrypted_data)
        
        # Remove unencrypted backup
        os.remove(output_file)
        
        self.stdout.write(f'Encrypted backup created: {encrypted_file}')
```

### Step 6.2: Create Restore Script

Create `backend/management/commands/restore_encrypted.py`:

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import os
from compliance.encryption import encryption_service

class Command(BaseCommand):
    help = 'Restore from encrypted backup'
    
    def add_arguments(self, parser):
        parser.add_argument('backup_file', type=str, help='Encrypted backup file path')
    
    def handle(self, *args, **options):
        backup_file = options['backup_file']
        
        # Decrypt backup
        with open(backup_file, 'r') as f:
            encrypted_data = f.read()
        
        decrypted_data = encryption_service.decrypt(encrypted_data)
        
        temp_file = f'{backup_file}.decrypted'
        with open(temp_file, 'wb') as f:
            f.write(decrypted_data.encode('latin-1'))
        
        # Restore database
        db_settings = settings.DATABASES['default']
        cmd = [
            'pg_restore',
            '-h', db_settings['HOST'],
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-c',  # Clean before restore
            temp_file
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        subprocess.run(cmd, env=env, check=True)
        
        # Remove decrypted file
        os.remove(temp_file)
        
        self.stdout.write('Database restored successfully')
```

### Step 6.3: Schedule Automated Backups

Create `scripts/backup_scheduler.sh`:

```bash
#!/bin/bash
cd /path/to/rock-access-web/backend
source venv/bin/activate
python manage.py backup_encrypted --output /backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Keep only last 30 days of backups
find /backups -name "*.encrypted" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/scripts/backup_scheduler.sh
```

---

## 7. Access Controls Configuration

### Step 7.1: Enhance Permission System

Update `backend/users/permissions.py`:

```python
class CanViewStudent(permissions.BasePermission):
    """Permission to view student records."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Check if user has access to the session
        return request.user.role in ['admin', 'editor', 'viewer']

class CanEditStudent(permissions.BasePermission):
    """Permission to edit student records."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'editor']
    
    def has_object_permission(self, request, view, obj):
        return request.user.role in ['admin', 'editor']
```

### Step 7.2: Apply Permissions to Views

Update `backend/sessions/views.py`:

```python
from users.permissions import CanViewStudent, CanEditStudent

class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanViewStudent]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanEditStudent()]
        return [IsAuthenticated(), CanViewStudent()]
```

### Step 7.3: Create Access Control Tests

Create `backend/users/tests/test_permissions.py`:

```python
from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User

class PermissionTestCase(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            email='viewer@test.com',
            role='viewer'
        )
        self.editor = User.objects.create_user(
            email='editor@test.com',
            role='editor'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            role='admin'
        )
    
    def test_viewer_cannot_edit(self):
        client = APIClient()
        client.force_authenticate(user=self.viewer)
        response = client.post('/api/students/', {})
        self.assertEqual(response.status_code, 403)
```

---

## 8. Business Associate Agreements

### Step 8.1: Create BAA Template

Create `docs/BAA_TEMPLATE.md`:

```markdown
# Business Associate Agreement Template

## Parties
- Covered Entity: [Your Organization]
- Business Associate: [Service Provider]

## Purpose
This agreement ensures HIPAA compliance for handling PHI.

## Obligations
1. Use and disclosure of PHI only as permitted
2. Implement safeguards to prevent unauthorized use
3. Report any breaches
4. Return or destroy PHI upon termination

## Signature
Date: ___________
Covered Entity: ___________________
Business Associate: ___________________
```

### Step 8.2: Document BAAs

Create `docs/BAAs.md`:

```markdown
# Business Associate Agreements

## Active BAAs

| Service Provider | Service | Signed Date | Expiration | Status |
|-----------------|---------|-------------|------------|--------|
| AWS | Cloud Infrastructure | YYYY-MM-DD | YYYY-MM-DD | Active |
| Azure | Cloud Infrastructure | YYYY-MM-DD | YYYY-MM-DD | Active |
| GCP | Cloud Infrastructure | YYYY-MM-DD | YYYY-MM-DD | Active |
| [Hosting Provider] | Web Hosting | YYYY-MM-DD | YYYY-MM-DD | Active |

## Pending BAAs
- [List any pending]

## Expired BAAs
- [List any expired that need renewal]
```

### Step 8.3: Create BAA Tracking System

Add to `backend/compliance/models.py`:

```python
class BusinessAssociateAgreement(models.Model):
    """Track Business Associate Agreements."""
    
    service_provider = models.CharField(max_length=200)
    service_description = models.TextField()
    signed_date = models.DateField()
    expiration_date = models.DateField()
    document_path = models.FileField(upload_to='baas/')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'baa_agreements'
        ordering = ['-signed_date']
    
    def __str__(self):
        return f"{self.service_provider} - {self.signed_date}"
```

---

## 9. Incident Response Plan

### Step 9.1: Create Incident Response Plan Document

Create `docs/INCIDENT_RESPONSE_PLAN.md`:

```markdown
# Incident Response Plan

## 1. Incident Classification

### Severity Levels
- **Critical**: Data breach, unauthorized access to PHI
- **High**: System compromise, failed authentication attempts
- **Medium**: Suspicious activity, configuration errors
- **Low**: Minor security events

## 2. Response Procedures

### Step 1: Detection
- Monitor security events
- Review audit logs daily
- Automated alerts for critical events

### Step 2: Containment
- Isolate affected systems
- Disable compromised accounts
- Preserve evidence

### Step 3: Investigation
- Review access logs
- Identify scope of breach
- Document findings

### Step 4: Notification
- Notify management within 1 hour
- Notify affected individuals within 72 hours (HIPAA requirement)
- Report to HHS if breach affects 500+ individuals

### Step 5: Recovery
- Restore from backups
- Patch vulnerabilities
- Update security controls

### Step 6: Post-Incident
- Conduct post-mortem
- Update procedures
- Train staff

## 3. Contact Information

- Security Team: security@yourdomain.com
- Legal: legal@yourdomain.com
- Management: management@yourdomain.com

## 4. Breach Notification Template

[Include template for breach notifications]
```

### Step 9.2: Create Incident Response Views

Add to `backend/compliance/views.py`:

```python
class IncidentResponseView(APIView):
    """Handle security incidents."""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Report and respond to incident."""
        event_type = request.data.get('event_type')
        severity = request.data.get('severity', 'medium')
        details = request.data.get('details', {})
        
        # Create security event
        event = SecurityEvent.objects.create(
            event_type=event_type,
            user=request.user,
            ip_address=self._get_client_ip(request),
            details=details,
            severity=severity
        )
        
        # Send alerts for critical events
        if severity == 'critical':
            self._send_critical_alert(event)
        
        return Response({'event_id': event.id, 'status': 'reported'})
    
    def _send_critical_alert(self, event):
        """Send critical alert to security team."""
        # Implement email/SMS notification
        pass
```

---

## 10. Security Monitoring

### Step 10.1: Create Security Monitoring Service

Create `backend/compliance/monitoring.py`:

```python
from django.utils import timezone
from datetime import timedelta
from .models import SecurityEvent, AccessLog
from users.models import User

class SecurityMonitoringService:
    """Monitor security events and generate alerts."""
    
    def check_failed_logins(self, hours=24):
        """Check for excessive failed login attempts."""
        threshold = timezone.now() - timedelta(hours=hours)
        
        # Get users with multiple failed logins
        events = SecurityEvent.objects.filter(
            event_type='failed_login',
            timestamp__gte=threshold
        ).values('user').annotate(count=Count('id'))
        
        for event in events:
            if event['count'] > 5:
                # Create high severity event
                SecurityEvent.objects.create(
                    event_type='suspicious_activity',
                    user_id=event['user'],
                    details={'failed_login_count': event['count']},
                    severity='high'
                )
    
    def check_unauthorized_access(self):
        """Check for unauthorized access attempts."""
        threshold = timezone.now() - timedelta(hours=1)
        
        events = SecurityEvent.objects.filter(
            event_type='unauthorized_access',
            timestamp__gte=threshold,
            resolved=False
        )
        
        if events.exists():
            # Send alert
            self._send_alert('Multiple unauthorized access attempts detected')
    
    def check_data_exports(self, hours=24):
        """Monitor data exports for unusual patterns."""
        threshold = timezone.now() - timedelta(hours=hours)
        
        exports = AccessLog.objects.filter(
            action='export',
            timestamp__gte=threshold
        )
        
        # Alert if more than 10 exports in 24 hours
        if exports.count() > 10:
            self._send_alert('Unusual data export activity detected')
    
    def _send_alert(self, message):
        """Send security alert."""
        # Implement email/SMS/webhook notification
        pass
```

### Step 10.2: Create Monitoring Management Command

Create `backend/compliance/management/commands/monitor_security.py`:

```python
from django.core.management.base import BaseCommand
from compliance.monitoring import SecurityMonitoringService

class Command(BaseCommand):
    help = 'Run security monitoring checks'
    
    def handle(self, *args, **options):
        service = SecurityMonitoringService()
        service.check_failed_logins()
        service.check_unauthorized_access()
        service.check_data_exports()
        self.stdout.write('Security monitoring completed')
```

### Step 10.3: Schedule Monitoring

Add to crontab:
```bash
*/15 * * * * cd /path/to/rock-access-web/backend && python manage.py monitor_security
```

### Step 10.4: Create Security Dashboard

Update `backend/compliance/views.py`:

```python
class SecurityDashboardView(APIView):
    """Security monitoring dashboard."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        from datetime import timedelta
        from django.db.models import Count, Q
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        
        return Response({
            'critical_events': SecurityEvent.objects.filter(
                severity='critical',
                resolved=False
            ).count(),
            'failed_logins_24h': SecurityEvent.objects.filter(
                event_type='failed_login',
                timestamp__gte=last_24h
            ).count(),
            'unauthorized_access_24h': SecurityEvent.objects.filter(
                event_type='unauthorized_access',
                timestamp__gte=last_24h
            ).count(),
            'data_exports_24h': AccessLog.objects.filter(
                action='export',
                timestamp__gte=last_24h
            ).count(),
        })
```

---

## Testing Checklist

After completing each section, test:

- [ ] Cloud KMS encryption/decryption works
- [ ] Database encryption is enabled
- [ ] TLS 1.3 is active (test with SSL Labs)
- [ ] MFA is enforced for all users
- [ ] Audit logs are being created
- [ ] Backups are encrypted
- [ ] Access controls prevent unauthorized access
- [ ] BAAs are documented
- [ ] Incident response plan is accessible
- [ ] Security monitoring is running

---

## Final Steps

1. **Update DEPLOYMENT.md checklist** - Mark completed items
2. **Run full test suite** - Ensure nothing broke
3. **Security audit** - Have security team review
4. **Documentation** - Update all documentation
5. **Training** - Train staff on new procedures

---

## Notes

- Test each change in a development environment first
- Keep backups before making database changes
- Review cloud provider documentation for specific KMS setup
- Consult legal team for BAA templates
- Regular security audits recommended
