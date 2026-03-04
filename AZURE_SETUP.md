# Azure Key Vault Setup Guide

This guide walks you through setting up Azure Key Vault for envelope encryption in the Rock Access application.

## Prerequisites

1. Azure subscription with appropriate permissions
2. Azure CLI installed and configured (optional, but recommended)
3. Access to Azure Portal

## Step 1: Create Azure Key Vault

### Using Azure Portal

1. Log in to [Azure Portal](https://portal.azure.com/)
2. Click **Create a resource** → Search for **Key Vault** → Click **Create**
3. Fill in the details:
   - **Subscription**: Select your subscription
   - **Resource Group**: Create new or select existing
   - **Key Vault name**: Choose a unique name (e.g., `rock-access-vault`)
   - **Region**: Select your region
   - **Pricing tier**: Standard (recommended)
4. Click **Review + create** → **Create**

### Using Azure CLI

```bash
az keyvault create \
  --name rock-access-vault \
  --resource-group your-resource-group \
  --location eastus
```

## Step 2: Create an RSA Key in Key Vault

### Using Azure Portal

1. Navigate to your Key Vault
2. In the left menu, click **Keys**
3. Click **+ Generate/Import**
4. Fill in:
   - **Options**: Generate
   - **Name**: `yencryption-ke` (or your preferred name)
   - **Key Type**: RSA
   - **RSA Key Size**: 2048 or 4096 (recommended: 2048)
   - **Key Operations**: 
     - ✅ Wrap Key (encrypt)
     - ✅ Unwrap Key (decrypt)
5. Click **Create**

### Using Azure CLI

```bash
az keyvault key create \
  --vault-name rock-access-vault \
  --name encryption-key \
  --protection software \
  --kty RSA \
  --size 2048 \
  --ops wrap unwrap
```

## Step 3: Create Service Principal for Application Access

The application needs credentials to access the Key Vault. We'll use a Service Principal with a client secret.

### Using Azure Portal

1. Navigate to **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Fill in:
   - **Name**: `rock-access-app` (or your preferred name)
   - **Supported account types**: Accounts in this organizational directory only
4. Click **Register**
5. Note the **Application (client) ID** and **Directory (tenant) ID**
6. Click **Certificates & secrets** → **New client secret**
7. Add a description and expiration, then click **Add**
8. **IMPORTANT**: Copy the **Value** immediately (you won't see it again)
9. Go to **API permissions** → **Add a permission** → **Azure Key Vault**
   - Select **Delegated permissions**
   - Check **user_impersonation** (if needed)
   - Or select **Application permissions** → Check **Keys** → **Get**, **WrapKey**, **UnwrapKey**
   - Click **Add permissions**
10. Click **Grant admin consent** (if you have permissions)

### Using Azure CLI

```bash
# Create service principal
az ad sp create-for-rbac --name rock-access-app --skip-assignment

# Note the output - you'll need:
# - appId (client ID)
# - password (client secret)
# - tenant (tenant ID)

# Get your subscription ID
az account show --query id -o tsv

# Grant Key Vault permissions
az keyvault set-policy \
  --name rock-access-vault \
  --spn <appId-from-above> \
  --key-permissions get wrapKey unwrapKey
```

## Step 4: Configure Application Environment Variables

Add the following to your `.env` file or environment configuration:

```env
# Set KMS provider to Azure
KMS_PROVIDER=azure

# Azure Key Vault Configuration
AZURE_KEY_VAULT_URL=https://rock-access-vault.vault.azure.net/
AZURE_KEY_NAME=encryption-key
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# Optional: Adjust envelope encryption threshold (default: 4096 bytes)
ENVELOPE_ENCRYPTION_THRESHOLD=4096
```

### Finding Your Values

- **AZURE_KEY_VAULT_URL**: Found in Key Vault overview page
  - Format: `https://<vault-name>.vault.azure.net/`
- **AZURE_KEY_NAME**: Name you gave to the key (e.g., `encryption-key`)
- **AZURE_TENANT_ID**: Found in Azure AD → App registrations → Your app → Overview
- **AZURE_CLIENT_ID**: Same as Application (client) ID from Step 3
- **AZURE_CLIENT_SECRET**: The secret value you copied in Step 3

## Step 5: Install Dependencies

The Azure Key Vault dependencies should already be in `requirements.txt`:

```bash
cd rock-access-web/backend
pip install -r requirements.txt
```

This installs:
- `azure-keyvault-keys==4.8.0`
- `azure-identity==1.15.0`

## Step 6: Verify Configuration

### Test Azure Key Vault Connection

You can create a simple test script to verify the connection:

```python
# test_azure_kms.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compliance.encryption import encryption_service

# Test with small data (should use direct encryption)
small_data = "Test SSN: 123-45-6789"
encrypted = encryption_service.encrypt(small_data)
decrypted = encryption_service.decrypt(encrypted)
print(f"Small data test: {decrypted == small_data}")

# Test with large data (should use envelope encryption)
large_data = "X" * 5000
encrypted_large = encryption_service.encrypt(large_data)
decrypted_large = encryption_service.decrypt(encrypted_large)
print(f"Large data test: {decrypted_large == large_data}")
print(f"Is envelope encrypted: {encryption_service._is_envelope_encrypted(encrypted_large)}")
```

Run it:
```bash
python manage.py shell < test_azure_kms.py
```

## Step 7: Security Best Practices

### Key Rotation

1. **Create a new key version**:
   ```bash
   az keyvault key create \
     --vault-name rock-access-vault \
     --name encryption-key \
     --protection software \
     --kty RSA \
     --size 2048
   ```

2. Update your application to use the new key version (if needed)

3. Keep old key versions active until all encrypted data is re-encrypted

### Access Control

- Use **Managed Identity** instead of client secrets in production (Azure VMs, App Service, etc.)
- Implement **Key Vault access policies** or **Azure RBAC**
- Enable **Key Vault logging** and **monitoring**
- Set up **alerts** for unusual access patterns

### Secrets Management

- **Never commit** `.env` files to version control
- Use **Azure Key Vault Secrets** for storing sensitive configuration
- Use **Azure App Configuration** for application settings
- Rotate client secrets regularly (set expiration when creating)

## Troubleshooting

### Common Issues

#### 1. "Azure Key Vault credentials not fully configured"
- **Solution**: Verify all environment variables are set correctly
- Check that `AZURE_KEY_VAULT_URL`, `AZURE_KEY_NAME`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` are all populated

#### 2. "Failed to initialize Azure Key Vault client"
- **Solution**: 
  - Verify service principal has correct permissions
  - Check that Key Vault name is correct
  - Verify client secret hasn't expired
  - Check network connectivity to Azure

#### 3. "Access denied" errors
- **Solution**:
  - Verify service principal has `wrapKey` and `unwrapKey` permissions
  - Check Key Vault access policy or RBAC assignments
  - Ensure admin consent was granted for API permissions

#### 4. Large data still using direct encryption
- **Solution**: 
  - Verify `KMS_PROVIDER=azure` is set
  - Check that data size exceeds `ENVELOPE_ENCRYPTION_THRESHOLD` (default: 4096 bytes)
  - Verify Azure Key Vault client initializes successfully

### Enable Logging

Check application logs for detailed error messages:

```python
# In Django settings
LOGGING = {
    'loggers': {
        'compliance.encryption': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## Production Deployment

### Using Managed Identity (Recommended)

Instead of client secrets, use Managed Identity for better security:

1. **Enable Managed Identity** on your Azure resource (App Service, VM, etc.)

2. **Grant access** to Key Vault:
   ```bash
   az keyvault set-policy \
     --name rock-access-vault \
     --object-id <managed-identity-object-id> \
     --key-permissions get wrapKey unwrapKey
   ```

3. **Update code** to use DefaultAzureCredential:
   ```python
   # In encryption.py, replace ClientSecretCredential with:
   from azure.identity import DefaultAzureCredential
   credential = DefaultAzureCredential()
   ```

### Environment-Specific Configuration

- **Development**: Use client secrets in `.env` file (never commit)
- **Staging/Production**: Use Managed Identity or Azure App Configuration
- **CI/CD**: Use Azure Key Vault Secrets or secure variables

## Monitoring

### Enable Key Vault Logging

1. In Azure Portal, navigate to your Key Vault
2. Go to **Diagnostics settings** → **Add diagnostic setting**
3. Enable logs for:
   - AuditEvent
   - AzureMetrics
4. Send to Log Analytics workspace or Storage Account

### Monitor Access Patterns

Set up alerts for:
- Unusual number of wrap/unwrap operations
- Failed authentication attempts
- Access from unexpected locations

## Additional Resources

- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
- [Azure Key Vault Keys Client Library](https://docs.microsoft.com/python/api/azure-keyvault-keys/)
- [Azure Identity Library](https://docs.microsoft.com/python/api/azure-identity/)
- [Key Vault Best Practices](https://docs.microsoft.com/azure/key-vault/general/best-practices)
