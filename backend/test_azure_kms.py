"""
Test script to verify Azure Key Vault envelope encryption setup.
Run this after granting RBAC permissions and installing packages.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compliance.encryption import encryption_service

print("=" * 60)
print("Azure Key Vault Envelope Encryption Test")
print("=" * 60)

# Test 1: Small data (should use direct encryption)
print("\n1. Testing small data (direct encryption):")
print("-" * 60)
small_data = "Test SSN: 123-45-6789"
try:
    encrypted = encryption_service.encrypt(small_data)
    decrypted = encryption_service.decrypt(encrypted)
    
    if decrypted == small_data:
        print("   ✓ SUCCESS: Small data encrypted and decrypted correctly")
        print(f"   Original: {small_data}")
        print(f"   Decrypted: {decrypted}")
        print(f"   Using envelope encryption: {encryption_service._is_envelope_encrypted(encrypted)}")
    else:
        print("   ✗ FAILED: Data doesn't match after encryption/decryption")
        print(f"   Original: {small_data}")
        print(f"   Decrypted: {decrypted}")
except Exception as e:
    print(f"   ✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 2: Large data (should use envelope encryption)
print("\n2. Testing large data (envelope encryption):")
print("-" * 60)
large_data = "X" * 5000  # 5000 bytes - exceeds 4KB threshold
try:
    encrypted_large = encryption_service.encrypt(large_data)
    decrypted_large = encryption_service.decrypt(encrypted_large)
    is_envelope = encryption_service._is_envelope_encrypted(encrypted_large)
    
    if decrypted_large == large_data:
        print("   ✓ SUCCESS: Large data encrypted and decrypted correctly")
        print(f"   Original length: {len(large_data)} bytes")
        print(f"   Decrypted length: {len(decrypted_large)} bytes")
        print(f"   Using envelope encryption: {is_envelope}")
        
        if is_envelope:
            print("   ✓ Envelope encryption is working correctly!")
        else:
            print("   ⚠ WARNING: Expected envelope encryption but got direct encryption")
            print("   This might mean KMS_PROVIDER is set to 'local' or threshold not met")
    else:
        print("   ✗ FAILED: Data doesn't match after encryption/decryption")
        print(f"   Original length: {len(large_data)} bytes")
        print(f"   Decrypted length: {len(decrypted_large)} bytes")
except Exception as e:
    print(f"   ✗ ERROR: {str(e)}")
    print("\n   Common issues:")
    print("   - RBAC permissions not granted or not propagated yet (wait 5-10 minutes)")
    print("   - Azure Key Vault credentials incorrect in .env file")
    print("   - Key name doesn't match in Azure Key Vault")
    print("   - Client secret expired or incorrect")
    import traceback
    traceback.print_exc()

# Test 3: Check configuration
print("\n3. Checking configuration:")
print("-" * 60)
from django.conf import settings
print(f"   KMS Provider: {getattr(settings, 'KMS_PROVIDER', 'Not set')}")
print(f"   Key Vault URL: {getattr(settings, 'AZURE_KEY_VAULT_URL', 'Not set')}")
print(f"   Key Name: {getattr(settings, 'AZURE_KEY_NAME', 'Not set')}")
print(f"   Tenant ID: {getattr(settings, 'AZURE_TENANT_ID', 'Not set')[:20]}..." if getattr(settings, 'AZURE_TENANT_ID', None) else "   Tenant ID: Not set")
print(f"   Client ID: {getattr(settings, 'AZURE_CLIENT_ID', 'Not set')[:20]}..." if getattr(settings, 'AZURE_CLIENT_ID', None) else "   Client ID: Not set")
print(f"   Client Secret: {'Set' if getattr(settings, 'AZURE_CLIENT_SECRET', None) else 'Not set'}")
print(f"   Envelope Threshold: {getattr(settings, 'ENVELOPE_ENCRYPTION_THRESHOLD', 'Not set')} bytes")

print("\n" + "=" * 60)
print("Testing completed!")
print("=" * 60)
