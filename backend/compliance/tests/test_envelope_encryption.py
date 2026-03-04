"""
Unit tests for envelope encryption functionality.
"""
from django.test import TestCase, override_settings
from unittest.mock import Mock, patch, MagicMock
from compliance.encryption import EncryptionService
import json
import base64


class EnvelopeEncryptionTestCase(TestCase):
    """Test envelope encryption functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = EncryptionService()
        self.small_text = "Test SSN: 123-45-6789"
        self.large_text = "X" * 5000  # 5000 bytes - exceeds 4KB threshold
    
    def test_is_envelope_encrypted(self):
        """Test detection of envelope-encrypted format."""
        # Valid envelope format
        envelope_data = {
            "version": "1.0",
            "method": "envelope",
            "wrapped_key": "test_key",
            "encrypted_data": "test_data",
            "nonce": "test_nonce",
            "tag": "test_tag"
        }
        self.assertTrue(self.service._is_envelope_encrypted(json.dumps(envelope_data)))
        
        # Invalid format (not JSON)
        self.assertFalse(self.service._is_envelope_encrypted("not json"))
        
        # Invalid format (missing method)
        invalid_data = {"version": "1.0", "encrypted_data": "test"}
        self.assertFalse(self.service._is_envelope_encrypted(json.dumps(invalid_data)))
        
        # Direct encryption format (base64 string)
        self.assertFalse(self.service._is_envelope_encrypted("dGVzdA=="))
    
    def test_generate_dek(self):
        """Test data encryption key generation."""
        dek1 = self.service._generate_dek()
        dek2 = self.service._generate_dek()
        
        # DEK should be 32 bytes (AES-256)
        self.assertEqual(len(dek1), 32)
        self.assertEqual(len(dek2), 32)
        
        # Each DEK should be unique
        self.assertNotEqual(dek1, dek2)
    
    @override_settings(KMS_PROVIDER='local')
    def test_small_data_uses_direct_encryption(self):
        """Test that small data uses direct encryption."""
        encrypted = self.service.encrypt(self.small_text)
        
        # Should not be envelope format
        self.assertFalse(self.service._is_envelope_encrypted(encrypted))
        
        # Should decrypt correctly
        decrypted = self.service.decrypt(encrypted)
        self.assertEqual(decrypted, self.small_text)
    
    @override_settings(KMS_PROVIDER='local')
    def test_large_data_fallback_to_local_when_kms_not_configured(self):
        """Test that large data falls back to local encryption when KMS not configured."""
        encrypted = self.service.encrypt(self.large_text)
        
        # When KMS is local, should use direct encryption even for large data
        self.assertFalse(self.service._is_envelope_encrypted(encrypted))
        
        # Should decrypt correctly
        decrypted = self.service.decrypt(encrypted)
        self.assertEqual(decrypted, self.large_text)
    
    @override_settings(
        KMS_PROVIDER='azure',
        AZURE_KEY_VAULT_URL='https://test-vault.vault.azure.net/',
        AZURE_KEY_NAME='test-key',
        AZURE_TENANT_ID='test-tenant',
        AZURE_CLIENT_ID='test-client',
        AZURE_CLIENT_SECRET='test-secret',
        ENVELOPE_ENCRYPTION_THRESHOLD=4096
    )
    @patch('compliance.encryption.EncryptionService._generate_dek')
    @patch('compliance.encryption._azure_crypto_client')
    @patch('compliance.encryption.KeyClient')
    @patch('compliance.encryption.ClientSecretCredential')
    def test_large_data_uses_envelope_encryption(self, mock_credential, mock_key_client, mock_crypto_client, mock_generate_dek):
        """Test that large data uses envelope encryption with Azure Key Vault."""
        # Fixed DEK so encrypt and decrypt use the same key
        test_dek = b'\x01' * 32
        mock_generate_dek.return_value = test_dek
        
        mock_wrap_result = Mock()
        mock_wrap_result.encrypted_key = b'wrapped_key_bytes'
        
        mock_crypto = Mock()
        mock_crypto.wrap_key.return_value = mock_wrap_result
        
        mock_unwrap_result = Mock()
        mock_unwrap_result.key = test_dek
        mock_crypto.unwrap_key.return_value = mock_unwrap_result
        
        # Set the global crypto client so _get_azure_crypto_client returns our mock
        import compliance.encryption
        compliance.encryption._azure_crypto_client = mock_crypto
        
        # Use a fresh service so it picks up KMS_PROVIDER='azure' from override_settings
        service = EncryptionService()
        encrypted = service.encrypt(self.large_text)
        
        # Should be envelope format
        self.assertTrue(service._is_envelope_encrypted(encrypted))
        
        # Parse and verify structure
        envelope = json.loads(encrypted)
        self.assertEqual(envelope['method'], 'envelope')
        self.assertEqual(envelope['version'], '1.0')
        self.assertIn('wrapped_key', envelope)
        self.assertIn('encrypted_data', envelope)
        self.assertIn('nonce', envelope)
        self.assertIn('tag', envelope)
        
        # Decrypt
        decrypted = service.decrypt(encrypted)
        self.assertEqual(decrypted, self.large_text)
    
    @override_settings(KMS_PROVIDER='local')
    def test_backward_compatibility_direct_encryption(self):
        """Test backward compatibility with existing direct-encrypted data."""
        # Create a direct-encrypted value (simulating old format)
        encrypted = self.service._encrypt_local(self.small_text)
        
        # Should decrypt correctly
        decrypted = self.service.decrypt(encrypted)
        self.assertEqual(decrypted, self.small_text)
        
        # Should not be detected as envelope
        self.assertFalse(self.service._is_envelope_encrypted(encrypted))
    
    @override_settings(
        KMS_PROVIDER='azure',
        AZURE_KEY_VAULT_URL='https://test-vault.vault.azure.net/',
        AZURE_KEY_NAME='test-key',
        AZURE_TENANT_ID='test-tenant',
        AZURE_CLIENT_ID='test-client',
        AZURE_CLIENT_SECRET='test-secret',
        ENVELOPE_ENCRYPTION_THRESHOLD=4096
    )
    @patch('compliance.encryption.EncryptionService._generate_dek')
    @patch('compliance.encryption._azure_crypto_client')
    def test_envelope_encrypt_decrypt_roundtrip(self, mock_crypto_client, mock_generate_dek):
        """Test full roundtrip of envelope encryption and decryption."""
        # Use a fixed DEK so encrypt and decrypt use the same key
        test_dek = b'\x01' * 32
        mock_generate_dek.return_value = test_dek
        
        mock_wrap_result = Mock()
        mock_wrap_result.encrypted_key = b'wrapped_key_bytes'
        
        mock_crypto = Mock()
        mock_crypto.wrap_key.return_value = mock_wrap_result
        
        mock_unwrap_result = Mock()
        mock_unwrap_result.key = test_dek
        mock_crypto.unwrap_key.return_value = mock_unwrap_result
        
        # Set the global crypto client
        import compliance.encryption
        compliance.encryption._azure_crypto_client = mock_crypto
        
        test_data = "This is a test of envelope encryption with large text. " * 100
        
        # Encrypt
        encrypted = self.service.encrypt_envelope(test_data)
        self.assertTrue(self.service._is_envelope_encrypted(encrypted))
        
        # Decrypt (uses same DEK via mock unwrap_key)
        decrypted = self.service.decrypt_envelope(encrypted)
        self.assertEqual(decrypted, test_data)
    
    def test_encrypt_none_returns_none(self):
        """Test that encrypting None returns None."""
        self.assertIsNone(self.service.encrypt(None))
        self.assertIsNone(self.service.encrypt_envelope(None))
    
    def test_decrypt_none_returns_none(self):
        """Test that decrypting None returns None."""
        self.assertIsNone(self.service.decrypt(None))
        self.assertIsNone(self.service.decrypt_envelope(None))
    
    @override_settings(
        KMS_PROVIDER='azure',
        ENVELOPE_ENCRYPTION_THRESHOLD=100  # Low threshold for testing
    )
    @patch('compliance.encryption._azure_crypto_client')
    def test_threshold_detection(self, mock_crypto_client):
        """Test that threshold correctly determines encryption method."""
        # Mock Azure Key Vault client (even though it won't be used for small data)
        import compliance.encryption
        compliance.encryption._azure_crypto_client = None
        
        small_data = "X" * 50  # 50 bytes - below 100 byte threshold
        
        # Should use direct encryption
        encrypted = self.service.encrypt(small_data)
        self.assertFalse(self.service._is_envelope_encrypted(encrypted))
    
    @override_settings(
        KMS_PROVIDER='azure',
        ENVELOPE_ENCRYPTION_THRESHOLD=100
    )
    @patch('compliance.encryption._azure_crypto_client')
    def test_encryption_handles_unicode(self, mock_crypto_client):
        """Test that encryption handles Unicode characters correctly."""
        unicode_text = "测试加密 🔒 Тест шифрования " * 200  # Mix of languages
        
        # Mock Azure Key Vault for envelope encryption
        mock_wrap_result = Mock()
        mock_wrap_result.encrypted_key = b'wrapped_key_bytes'
        
        mock_crypto = Mock()
        mock_crypto.wrap_key.return_value = mock_wrap_result
        
        mock_unwrap_result = Mock()
        mock_unwrap_result.key = b'\x01' * 32
        mock_crypto.unwrap_key.return_value = mock_unwrap_result
        
        import compliance.encryption
        compliance.encryption._azure_crypto_client = mock_crypto
        
        encrypted = self.service.encrypt(unicode_text)
        decrypted = self.service.decrypt(encrypted)
        
        self.assertEqual(decrypted, unicode_text)
    
    @override_settings(KMS_PROVIDER='local')
    def test_student_model_integration(self):
        """Test that Student model encryption methods work with both formats."""
        from sessions.models import Student, AcademicSession, Site
        from django.utils import timezone
        
        # Create a site and session (AcademicSession requires site)
        site, _ = Site.objects.get_or_create(slug='test', defaults={'name': 'Test Site', 'display_order': 0})
        session = AcademicSession.objects.create(
            site=site,
            session_type='SY',
            name='SY2024-25',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True
        )
        
        # Create a student
        student = Student.objects.create(
            session=session,
            first_name='John',
            last_name='Doe',
            date_of_birth=timezone.now().date(),
            enrollment_date=timezone.now().date()
        )
        
        # Test SSN (small data) - should use direct encryption
        ssn = "123-45-6789"
        student.set_ssn(ssn)
        student.save()
        
        retrieved_ssn = student.get_ssn()
        self.assertEqual(retrieved_ssn, ssn)
        
        # Verify it's not envelope format
        self.assertFalse(self.service._is_envelope_encrypted(student.ssn_encrypted))
        
        # Test medical info (could be large) - with local provider, uses direct
        medical_info = "Medical information for testing. " * 100  # 3000 bytes
        student.set_medical_info(medical_info)
        student.save()
        
        retrieved_medical = student.get_medical_info()
        self.assertEqual(retrieved_medical, medical_info)
    
    @override_settings(KMS_PROVIDER='local')
    def test_encryption_with_existing_encrypted_data(self):
        """Test that decrypt can handle legacy encrypted data format."""
        # Create legacy encrypted data
        legacy_encrypted = self.service._encrypt_local("legacy encrypted data")
        
        # Should decrypt correctly
        decrypted = self.service.decrypt(legacy_encrypted)
        self.assertEqual(decrypted, "legacy encrypted data")
        
        # New encryption should still work
        new_encrypted = self.service.encrypt("new data")
        new_decrypted = self.service.decrypt(new_encrypted)
        self.assertEqual(new_decrypted, "new data")
