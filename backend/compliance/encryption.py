"""
Encryption utilities for PHI/PII field-level encryption.
Supports local encryption and cloud KMS providers.
Implements envelope encryption for large data fields (>= 4KB) using AES-256-GCM
with cloud KMS wrapping the data encryption keys.
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from django.conf import settings
import base64
import os
import json
import logging

logger = logging.getLogger(__name__)

# Module-level globals for Azure Key Vault client (used by _get_azure_crypto_client).
_azure_crypto_client = None
try:
    from azure.identity import ClientSecretCredential
    from azure.keyvault.keys import KeyClient
except ImportError:
    ClientSecretCredential = None
    KeyClient = None


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        self.kms_provider = getattr(settings, 'KMS_PROVIDER', 'local')
        self.encryption_key = self._get_encryption_key()
        self.envelope_threshold = getattr(settings, 'ENVELOPE_ENCRYPTION_THRESHOLD', 4096)
        self.envelope_threshold = getattr(settings, 'ENVELOPE_ENCRYPTION_THRESHOLD', 4096)
    
    def _get_encryption_key(self):
        """Get encryption key from settings or generate one."""
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            # Generate a key (should be set in production via environment variable)
            key = Fernet.generate_key().decode()
        if isinstance(key, str):
            key = key.encode()
        return key
    
    def encrypt(self, value):
        """Encrypt a value. Automatically uses envelope encryption for large data."""
        if not value:
            return None
        
        # Determine data size
        data_bytes = value.encode('utf-8') if isinstance(value, str) else value
        data_size = len(data_bytes)
        
        # Use envelope encryption for large data when using cloud KMS
        if data_size >= self.envelope_threshold and self.kms_provider != 'local':
            return self.encrypt_envelope(value)
        
        # Use direct encryption for small data or local provider
        if self.kms_provider == 'local':
            return self._encrypt_local(value)
        elif self.kms_provider == 'aws':
            return self._encrypt_aws(value)
        elif self.kms_provider == 'azure':
            return self._encrypt_azure(value)
        elif self.kms_provider == 'gcp':
            return self._encrypt_gcp(value)
        else:
            return self._encrypt_local(value)
    
    def decrypt(self, encrypted_value):
        """Decrypt a value. Dispatches to decrypt_envelope for envelope-encrypted data."""
        if not encrypted_value:
            return None
        
        if self._is_envelope_encrypted(encrypted_value):
            return self.decrypt_envelope(encrypted_value)
        
        if self.kms_provider == 'local':
            return self._decrypt_local(encrypted_value)
        elif self.kms_provider == 'aws':
            return self._decrypt_aws(encrypted_value)
        elif self.kms_provider == 'azure':
            return self._decrypt_azure(encrypted_value)
        elif self.kms_provider == 'gcp':
            return self._decrypt_gcp(encrypted_value)
        else:
            return self._decrypt_local(encrypted_value)
    
    def _encrypt_local(self, value):
        """Encrypt using local Fernet encryption."""
        f = Fernet(self.encryption_key)
        encrypted = f.encrypt(value.encode() if isinstance(value, str) else value)
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_local(self, encrypted_value):
        """Decrypt using local Fernet decryption."""
        try:
            f = Fernet(self.encryption_key)
            decoded = base64.b64decode(encrypted_value.encode())
            decrypted = f.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            # Log error but don't expose details
            return None
    
    def _encrypt_aws(self, encrypted_value):
        """Encrypt using AWS KMS (placeholder for implementation)."""
        # TODO: Implement AWS KMS encryption
        # import boto3
        # kms = boto3.client('kms')
        # response = kms.encrypt(KeyId=settings.AWS_KMS_KEY_ID, Plaintext=value)
        # return base64.b64encode(response['CiphertextBlob']).decode()
        return self._encrypt_local(encrypted_value)
    
    def _decrypt_aws(self, encrypted_value):
        """Decrypt using AWS KMS (placeholder for implementation)."""
        # TODO: Implement AWS KMS decryption
        return self._decrypt_local(encrypted_value)
    
    def _encrypt_azure(self, encrypted_value):
        """Encrypt using Azure Key Vault (placeholder for implementation)."""
        # TODO: Implement Azure Key Vault encryption
        return self._encrypt_local(encrypted_value)
    
    def _decrypt_azure(self, encrypted_value):
        """Decrypt using Azure Key Vault for small data (direct decryption).
        Note: Envelope-encrypted data is automatically handled by decrypt()."""
        # For small data with Azure, use local decryption as fallback
        return self._decrypt_local(encrypted_value)
    
    def _encrypt_gcp(self, encrypted_value):
        """Encrypt using GCP KMS (placeholder for implementation)."""
        # TODO: Implement GCP KMS encryption
        return self._encrypt_local(encrypted_value)
    
    def _decrypt_gcp(self, encrypted_value):
        """Decrypt using GCP KMS (placeholder for implementation)."""
        # TODO: Implement GCP KMS decryption
        return self._decrypt_local(encrypted_value)
    
    def _is_envelope_encrypted(self, encrypted_value):
        """Check if encrypted value is in envelope encryption format."""
        try:
            if isinstance(encrypted_value, str):
                data = json.loads(encrypted_value)
                return data.get('method') == 'envelope' and 'wrapped_key' in data
        except (json.JSONDecodeError, TypeError):
            pass
        return False
    
    def _generate_dek(self):
        """Generate a random AES-256 data encryption key (32 bytes for AES-256)."""
        return os.urandom(32)
    
    def _get_azure_crypto_client(self):
        """Get or create Azure Key Vault crypto client with caching."""
        global _azure_crypto_client
        
        if _azure_crypto_client is not None:
            return _azure_crypto_client
        
        if ClientSecretCredential is None or KeyClient is None:
            logger.warning("Azure Key Vault libraries not installed")
            return None
        
        try:
            from azure.keyvault.keys.crypto import CryptographyClient
            
            vault_url = getattr(settings, 'AZURE_KEY_VAULT_URL', '')
            key_name = getattr(settings, 'AZURE_KEY_NAME', '')
            tenant_id = getattr(settings, 'AZURE_TENANT_ID', '')
            client_id = getattr(settings, 'AZURE_CLIENT_ID', '')
            client_secret = getattr(settings, 'AZURE_CLIENT_SECRET', '')
            
            if not all([vault_url, key_name, tenant_id, client_id, client_secret]):
                logger.warning("Azure Key Vault credentials not fully configured")
                return None
            
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            key_client = KeyClient(vault_url=vault_url, credential=credential)
            key = key_client.get_key(key_name)
            _azure_crypto_client = CryptographyClient(key, credential=credential)
            
            return _azure_crypto_client
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {str(e)}")
            return None
    
    def _wrap_key_azure(self, dek):
        """Wrap (encrypt) a data encryption key using Azure Key Vault."""
        try:
            crypto_client = self._get_azure_crypto_client()
            if crypto_client is None:
                raise Exception("Azure Key Vault client not available")
            
            from azure.keyvault.keys.crypto import EncryptionAlgorithm
            
            # Wrap the DEK using RSA-OAEP
            wrap_result = crypto_client.wrap_key(EncryptionAlgorithm.rsa_oaep, dek)
            return base64.b64encode(wrap_result.encrypted_key).decode()
        except Exception as e:
            logger.error(f"Failed to wrap key with Azure Key Vault: {str(e)}")
            raise
    
    def _unwrap_key_azure(self, wrapped_key):
        """Unwrap (decrypt) a data encryption key using Azure Key Vault."""
        try:
            crypto_client = self._get_azure_crypto_client()
            if crypto_client is None:
                raise Exception("Azure Key Vault client not available")
            
            from azure.keyvault.keys.crypto import EncryptionAlgorithm
            
            wrapped_key_bytes = base64.b64decode(wrapped_key.encode())
            
            # Unwrap the DEK using RSA-OAEP
            unwrap_result = crypto_client.unwrap_key(EncryptionAlgorithm.rsa_oaep, wrapped_key_bytes)
            return unwrap_result.key
        except Exception as e:
            logger.error(f"Failed to unwrap key with Azure Key Vault: {str(e)}")
            raise
    
    def encrypt_envelope(self, value):
        """Encrypt large data using envelope encryption (AES-256-GCM + Key Vault wrapping)."""
        if not value:
            return None
        
        try:
            # Convert to bytes if string
            data_bytes = value.encode('utf-8') if isinstance(value, str) else value
            
            # Generate a random data encryption key (DEK)
            dek = self._generate_dek()
            
            # Generate a random nonce (12 bytes recommended for GCM)
            nonce = os.urandom(12)
            
            # Encrypt data with AES-256-GCM
            aesgcm = AESGCM(dek)
            encrypted_data = aesgcm.encrypt(nonce, data_bytes, None)
            
            # The encrypted_data includes the tag (16 bytes) appended
            # Separate the ciphertext and tag
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[:-16]
            
            # Wrap the DEK with Key Vault
            wrapped_key = self._wrap_key_azure(dek)
            
            # Create envelope structure
            envelope = {
                "version": "1.0",
                "method": "envelope",
                "wrapped_key": wrapped_key,
                "encrypted_data": base64.b64encode(ciphertext).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "tag": base64.b64encode(tag).decode()
            }
            
            return json.dumps(envelope)
        except Exception as e:
            logger.error(f"Envelope encryption failed: {str(e)}")
            raise
    
    def decrypt_envelope(self, encrypted_value):
        """Decrypt envelope-encrypted data."""
        if not encrypted_value:
            return None
        
        try:
            # Parse envelope structure
            envelope = json.loads(encrypted_value)
            
            if envelope.get('method') != 'envelope':
                raise ValueError("Not an envelope-encrypted value")
            
            wrapped_key = envelope['wrapped_key']
            encrypted_data_b64 = envelope['encrypted_data']
            nonce_b64 = envelope['nonce']
            tag_b64 = envelope['tag']
            
            # Decode base64 values
            encrypted_data = base64.b64decode(encrypted_data_b64.encode())
            nonce = base64.b64decode(nonce_b64.encode())
            tag = base64.b64decode(tag_b64.encode())
            
            # Unwrap the DEK from Key Vault
            dek = self._unwrap_key_azure(wrapped_key)
            
            # Combine ciphertext and tag for GCM
            ciphertext_with_tag = encrypted_data + tag
            
            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(dek)
            decrypted_data = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
            
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Envelope decryption failed: {str(e)}")
            return None


# Global encryption service instance
encryption_service = EncryptionService()
